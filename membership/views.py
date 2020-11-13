from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.db.models import Q
from .models import MembershipPackage, Member, Equine
from .forms import MembershipPackageForm, MemberForm, EquineForm
from random import randint
from json import dumps
import stripe


class MembershipBase(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['memberships'] = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                                  Q(admins=self.request.user) |
                                                                  Q(members=self.request.user))
        return context


class Membership(LoginRequiredMixin, MembershipBase):
    template_name = 'dashboard.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class CreateMembershipPackageView(LoginRequiredMixin, FormView):
    template_name = 'create-membership-package.html'
    login_url = '/login/'
    form_class = MembershipPackageForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super(CreateMembershipPackageView, self).get_context_data(**kwargs)
        if self.request.user.is_superuser:
            context['public_api_key'] = settings.STRIPE_PUBLIC_TEST_KEY
        else:
            context['public_api_key'] = settings.STRIPE_PUBLIC_KEY
        return context

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        result = validate_card(self.request)
        print(result)
        return HttpResponse(dumps(result))
        form.save()
        return super().form_valid(form)


def generate_username(first_name, last_name):
    return f"{first_name.lower().replace(' ', '')}.{last_name.lower().replace(' ', '')}{randint(1000, 9999)}"


class AddMember(LoginRequiredMixin, FormView):
    template_name = 'add_member.html'
    login_url = '/login/'
    form_class = MemberForm
    success_url = '/membership/add-member'

    def get_context_data(self, **kwargs):
        context = super(AddMember, self).get_context_data(**kwargs)
        self.package = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                        Q(admins=self.request.user)).distinct()
        if self.package[0].bolton != "none":
            context['package'] = self.package[0]
            context['bolton_form'] = getattr(self, 'bolton_form', self.get_bolton_form())
        return context

    def get_bolton_form(self):
        if self.package[0].bolton == "equine":
            if self.request.method == 'POST':
                return EquineForm(self.request.POST)
            else:
                return EquineForm()

    def form_valid(self, form):
        self.bolton_form = self.get_bolton_form()
        if self.bolton_form.is_valid():
            # All good logic goes here, which in the simplest case is
            # returning super.form_valid
            form.save()
            self.bolton_form.save()
            return super(AddMember, self).form_valid(form)
        else:
            # Otherwise treat as if the first form was invalid
            print("bolton form is invalid!")
            return super(AddMember, self).form_invalid(form)
        #
        # return super(AddMember, self).form_valid(form)
        # AddMember, self

    # Do this only if you need to validate second form when first form is
    # invalid
    def form_invalid(self, form):
        self.second_form = self.get_bolton_form()
        self.second_form.is_valid()
        return super(AddMember, self).form_invalid(form)


def validate_card(request):
    # get strip secret key
    if request.user.is_superuser:
        stripe.api_key = settings.STRIPE_SECRET_TEST_KEY
    else:
        stripe.api_key = settings.STRIPE_SECRET_KEY

    # create or get customer id
    if not member.stripe_id:
        # create stripe user
        customer = stripe.Customer.create(
            name=request.user.get_full_name(),
            email=request.user.email
        )
        customer_id = customer['id']
        member.stripe_id = customer_id
        member.save()
    else:
        stripe.Customer.modify(
            member.stripe_id,
            name=request.user.get_full_name(),
            email=request.user.email
        )

    # add payment token to user
    try:
        payment_method = stripe.Customer.modify(
            member.stripe_id,
            source=request.POST.get('token[id]')
        )
    except stripe.error.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        feedback = send_payment_error(e)
        result = {'result': 'fail',
                  'feedback': feedback}
        return HttpResponse(dumps(result))

    except stripe.error.RateLimitError as e:
        # Too many requests made to the API too quickly
        feedback = send_payment_error(e)
        result = {'result': 'fail',
                  'feedback': feedback}
        return HttpResponse(dumps(result))

    except stripe.error.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        feedback = send_payment_error(e)
        result = {'result': 'fail',
                  'feedback': feedback}
        return HttpResponse(dumps(result))

    except stripe.error.AuthenticationError as e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        feedback = send_payment_error(e)
        result = {'result': 'fail',
                  'feedback': feedback}
        return HttpResponse(dumps(result))

    except stripe.error.APIConnectionError as e:
        # Network communication with Stripe failed
        feedback = send_payment_error(e)
        result = {'result': 'fail',
                  'feedback': feedback}
        return HttpResponse(dumps(result))

    except stripe.error.StripeError as e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        feedback = send_payment_error(e)
        result = {'result': 'fail',
                  'feedback': feedback}
        return HttpResponse(dumps(result))

    except Exception as e:
        # Something else happened, completely unrelated to Stripe
        feedback = send_payment_error(e)
        result = {'result': 'fail',
                  'feedback': feedback}
        return HttpResponse(dumps(result))


def send_payment_error(error):
    body = error.json_body
    err = body.get('error', {})

    feedback = "<strong>Status is:</strong> %s" % error.http_status
    feedback += "<br><strong>Type is:</strong> %s" % err.get('type')
    feedback += "<br><strong>Code is:</strong> %s" % err.get('code')
    feedback += "<br><strong>Message is:</strong> <span class='text-danger'>%s</span>" % err.get('message')
    return feedback
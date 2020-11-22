from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect, get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q
from memberships.functions import generate_username, get_stripe_secret_key
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
    template_name = 'membership-package.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


class SelectMembershipPackageView(LoginRequiredMixin, MembershipBase):
    template_name = 'select-membership-package.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['membership_packages'] = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                                          Q(admins=self.request.user))

        return context

    def get(self, *args, **kwargs):
        membership_packages = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                               Q(admins=self.request.user))
        if len(membership_packages) < 1:
            return HttpResponseRedirect(f'membership-package-settings')
        if len(membership_packages) == 1:
            return HttpResponseRedirect(f'org/{membership_packages[0].organisation_name}')
        if len(membership_packages) > 1:
            return super().get(*args, **kwargs)


class MembershipPackageView(LoginRequiredMixin, MembershipBase):
    template_name = 'membership-package.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membership_packages'] = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                                    Q(admins=self.request.user))
        context['package'] = context['membership_packages'][0]
        context['members'] = Member.objects.filter(membership_package=context['package'])

        # get strip secret key
        stripe.api_key = get_stripe_secret_key(self.request)
        context['stripe_package'] = stripe.Account.retrieve(context['package'].stripe_acct_id)
        return context


class MembershipPackageSettings(LoginRequiredMixin, FormView):
    template_name = 'membership-package-settings.html'
    login_url = '/login/'
    form_class = MembershipPackageForm
    success_url = '/membership/add-member'

    def get_form(self, form_class=MembershipPackageForm):
        try:
            contact = MembershipPackage.objects.get(owner=self.request.user)
            return form_class(instance=contact, **self.get_form_kwargs())
        except MembershipPackage.DoesNotExist:
            return form_class(**self.get_form_kwargs())

    def form_valid(self, form):
        # try:
        #     form = MembershipPackageForm(form or None, instance=MembershipPackage.objects.get(owner=self.request.user))
        # except:
        #     form = MembershipPackageForm(form or None)

        # save form
        form.instance.owner = self.request.user
        membership = form.save()
        # get strip secret key
        stripe.api_key = get_stripe_secret_key(self.request)

        if not membership.stripe_acct_id:
            # create initial account
            account = stripe.Account.create(
                type="express",
                email=f"{self.request.user.email}",
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                business_type="company",
                company={
                    'name': membership.organisation_name,
                    "directors_provided": True,
                    "executives_provided": True,
                },
                country="GB",
                default_currency="GBP",
            )

            # add stripe account id
            membership.stripe_acct_id = account.id
            membership.save()
        else:
            # edit account
            pass

        account_links = stripe.AccountLink.create(
            account=membership.stripe_acct_id,
            refresh_url=f'http://{settings.SITE_NAME}/membership/membership-package-settings',
            return_url=f'http://{settings.SITE_NAME}/membership',
            type='account_onboarding',
        )

        return redirect(account_links.url)


class AddMember(LoginRequiredMixin, FormView):
    template_name = 'member_form.html'
    login_url = '/login/'
    form_class = MemberForm
    success_url = '/membership/'

    def get_context_data(self, **kwargs):
        context = super(AddMember, self).get_context_data(**kwargs)
        self.package = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                        Q(admins=self.request.user))
        if self.package[0].bolton != "none":
            context['package'] = self.package[0]
            context['bolton_form'] = getattr(self, 'bolton_form', self.get_bolton_form())
        return context

    def get_bolton_form(self):
        self.package = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                        Q(admins=self.request.user))
        if self.package[0].bolton == "equine":
            if self.request.method == 'POST':
                return EquineForm(self.request.POST)
            else:
                return EquineForm()
        else:
            return None

    def form_valid(self, form):
        self.bolton_form = self.get_bolton_form()
        if self.bolton_form and self.bolton_form.is_valid():
            # All good logic goes here, which in the simplest case is
            # returning super.form_valid
            self.member = form.save()
            self.bolton_form.save()
            self.create_and_link_user()
            return super(AddMember, self).form_valid(form)
        elif not self.bolton_form:
            self.member = form.save()
            self.create_and_link_user()
            return super(AddMember, self).form_valid(form)
        else:
            # Otherwise treat as if the first form was invalid
            return super(AddMember, self).form_invalid(form)

    def form_invalid(self, form):
        self.second_form = self.get_bolton_form()
        self.second_form.is_valid()
        return super(AddMember, self).form_invalid(form)

    def create_and_link_user(self):
        """
        Create and link user
        :return:
        """
        user, created = User.objects.get_or_create(username=generate_username(self.member.first_name,
                                                                              self.member.last_name),
                                                   email=self.member.email,
                                                   first_name=self.member.first_name,
                                                   last_name=self.member.last_name)
        self.member.user_account = user
        self.member.membership_package = self.package[0]
        self.member.save()


class UpdateMember(LoginRequiredMixin, UpdateView):
    template_name = 'member_form.html'
    login_url = '/login/'
    form_class = MemberForm
    model = Member
    success_url = '/membership/'

    def get_context_data(self, **kwargs):
        context = super(UpdateMember, self).get_context_data(**kwargs)

        self.package = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                        Q(admins=self.request.user))
        if self.package[0].bolton != "none":
            context['package'] = self.package[0]
            context['bolton_form'] = getattr(self, 'bolton_form', self.get_bolton_form())
        return context

    def get_bolton_form(self):
        self.package = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                        Q(admins=self.request.user))
        if self.package[0].bolton == "equine":
            if self.request.method == 'POST':
                return EquineForm(self.request.POST)
            else:
                return EquineForm()
        else:
            return None

    def form_valid(self, form):
        self.bolton_form = self.get_bolton_form()
        if self.bolton_form and self.bolton_form.is_valid():
            # All good logic goes here, which in the simplest case is
            # returning super.form_valid
            self.member = form.save()
            self.bolton_form.save()
            self.create_and_link_user()
            return super(UpdateMember, self).form_valid(form)
        elif not self.bolton_form:
            self.member = form.save()
            self.create_and_link_user()
            return super(UpdateMember, self).form_valid(form)
        else:
            # Otherwise treat as if the first form was invalid
            return super(UpdateMember, self).form_invalid(form)

    def form_invalid(self, form):
        self.second_form = self.get_bolton_form()
        self.second_form.is_valid()
        return super(UpdateMember, self).form_invalid(form)

    def create_and_link_user(self):
        """
        Create and link user
        :return:
        """
        user, created = User.objects.get_or_create(username=generate_username(self.member.first_name,
                                                                              self.member.last_name),
                                                   email=self.member.email,
                                                   first_name=self.member.first_name,
                                                   last_name=self.member.last_name)
        self.member.user_account = user
        self.member.membership_package = self.package[0]
        self.member.save()


def validate_card(request):
    # get strip secret key
    stripe.api_key = get_stripe_secret_key(request)

    membership_package = MembershipPackage.objects.get(owner=request.user)
    # add payment token to user
    try:
        payment_method = stripe.Account.modify(
          membership_package.stripe_acct_id,
          source=request.POST.get('token[id]'),
        )
        result = {'result': 'success',
              'feedback': payment_method}
        return HttpResponse(dumps(result))

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
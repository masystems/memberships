from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect, get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q
from memberships.functions import generate_username, get_stripe_secret_key, get_stripe_public_key
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
        if context['package'].stripe_acct_id:
            try:
                context['edit_account'] = stripe.Account.create_login_link(context['package'].stripe_acct_id)
            except:
                # stripe account created but not setup
                context['stripe_package_setup'] = get_account_link(context['package'])
            if context['stripe_package'].requirements.errors:
                context['account_link'] = get_account_link(context['package'])
        else:
            # stripe account not setup
            context['stripe_package_setup'] = create_package_on_stripe(self.request)
        return context


class MembershipPackageSettings(LoginRequiredMixin, TemplateView):
    template_name = 'membership-package-settings.html'
    login_url = '/login/'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        context['public_api_key'] = get_stripe_public_key(self.request)
        context['form'] = MembershipPackageForm()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        try:
            membership_package = MembershipPackage.objects.get(owner=request.user)
            form = MembershipPackageForm(self.request.POST or None, instance=membership_package)
        except MembershipPackage.DoesNotExist:
            form = MembershipPackageForm(self.request.POST or None)

        if form.is_valid():
            # save form
            form.instance.owner = self.request.user
            form.save()
            return HttpResponse(dumps({'status': "success"}), content_type='application/json')
        else:
            message = {'status': "fail",
                       'errors': f"{form.errors}"}
            return HttpResponse(dumps(message), content_type='application/json')


def create_package_on_stripe(request):
    # get strip secret key
    stripe.api_key = get_stripe_secret_key(request)
    membership_package = MembershipPackage.objects.get(owner=request.user)

    if not membership_package.stripe_acct_id:
        # create initial account
        account = stripe.Account.create(
            type="express",
            email=f"{request.user.email}",
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            business_type="company",
            company={
                'name': membership_package.organisation_name,
                "directors_provided": True,
                "executives_provided": True,
            },
            country="GB",
            default_currency="GBP",
        )
        membership_package.stripe_acct_id = account.id

    if not membership_package.stripe_product_id:
        # create product
        product = stripe.Product.create(name=membership_package.organisation_name)
        membership_package.stripe_product_id = product.id

    if not membership_package.membership_price_per_month_id:
        # create price(s)
        price_per_month = stripe.Price.create(
            unit_amount=int(membership_package.membership_price_per_month*100),
            currency="gbp",
            recurring={"interval": "month"},
            product=product.id,
        )
        membership_package.membership_price_per_month_id = price_per_month.id
    if not membership_package.membership_price_per_year_id:
        price_per_year = stripe.Price.create(
            unit_amount=int(membership_package.membership_price_per_year*100),
            currency="gbp",
            recurring={"interval": "year"},
            product=product.id,
        )
        membership_package.membership_price_per_year_id = price_per_year.id

    membership_package.save()

    return get_account_link(membership_package)


def organisation_payment(request):
    if request.POST:
        membership_package = MembershipPackage.objects.get(owner=request.user)

        # get package IDs
        if request.user.is_superuser:
            price_id = settings.MEMBERSHIP_ORG_PRICE_TEST_ID
        else:
            price_id = settings.MEMBERSHIP_ORG_PRICE_ID

        # get strip secret key
        stripe.api_key = get_stripe_secret_key(request)

        # create or get customer id
        if not membership_package.stripe_owner_id:
            # create stripe user
            customer = stripe.Customer.create(
                name=request.user.get_full_name(),
                email=request.user.email
            )
            customer_id = customer['id']
            membership_package.stripe_owner_id = customer_id
            membership_package.save()
        else:
            stripe.Customer.modify(
                membership_package.stripe_owner_id,
                name=request.user.get_full_name(),
                email=request.user.email
            )

        # validate the card
        result = validate_card(request)
        if result['result'] == 'fail':
            return HttpResponse(dumps(result))

        subscription = stripe.Subscription.create(
            customer=membership_package.stripe_owner_id,
            items=[
                {
                    "plan": price_id,
                },
            ],
        )
        if subscription['status'] != 'active':
            result = {'result': 'fail',
                      'feedback': f"<strong>Failure message:</strong> <span class='text-danger'>{subscription['status']}</span>"}
            return HttpResponse(dumps(result))
        else:
            invoice = stripe.Invoice.list(customer=membership_package.stripe_owner_id, subscription=subscription.id, limit=1)
            receipt = stripe.Charge.list(customer=membership_package.stripe_owner_id)

            result = {'result': 'success',
                      'invoice': invoice.data[0].invoice_pdf,
                      'receipt': receipt.data[0].receipt_url}

            return HttpResponse(dumps(result))


def get_account_link(membership):
    account_link = stripe.AccountLink.create(
        account=membership.stripe_acct_id,
        refresh_url=f'http://{settings.SITE_NAME}/membership/membership-package-settings',
        return_url=f'http://{settings.SITE_NAME}/membership',
        type='account_onboarding',
    )
    return account_link


class AddMember(LoginRequiredMixin, FormView):
    template_name = 'member_form.html'
    login_url = '/login/'
    form_class = MemberForm
    success_url = '/membership/'

    def get_context_data(self, **kwargs):
        context = super(AddMember, self).get_context_data(**kwargs)

        context['public_api_key'] = get_stripe_public_key(self.request)
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

        stripe_customer = stripe.Customer.create(
            name=user.get_full_name,
            email=user.email
        )
        self.member.stripe_id = stripe_customer.id
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


class MemberPaymentView(LoginRequiredMixin, MembershipBase):
    template_name = 'member_payment.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['public_api_key'] = get_stripe_public_key(self.request)
        context['package'] = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        context['member'] = Member.objects.get(id=self.kwargs['pk'])

        return context

    def post(self, request, *args, **kwargs):
        package = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        member = Member.objects.get(id=self.kwargs['pk'])

        result = validate_card(request)
        if result['result'] == 'fail':
            return HttpResponse(dumps(result))

        if member.billing_period == "monthly":
            price_id = package.membership_price_per_month_id
        else:
            price_id = package.membership_price_per_year_id

        subscription = stripe.Subscription.create(
            customer=member.stripe_id,
            items=[
                {
                    "plan": price_id,
                },
            ],
        )
        member.stripe_subscription_id = subscription.id
        member.save()

        if subscription['status'] != 'active':
            result = {'result': 'fail',
                      'feedback': f"<strong>Failure message:</strong> <span class='text-danger'>{subscription['status']}</span>"}
            return HttpResponse(dumps(result))


def validate_card(request):
    # get strip secret key
    stripe.api_key = get_stripe_secret_key(request)

    membership_package = MembershipPackage.objects.get(owner=request.user)
    # add payment token to user
    try:
        payment_method = stripe.Customer.modify(
          membership_package.stripe_owner_id,
          source=request.POST.get('token[id]'),
        )
        return {'result': 'success',
              'feedback': payment_method}

    except stripe.error.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        feedback = send_payment_error(e)
        return {'result': 'fail',
                  'feedback': feedback}

    except stripe.error.RateLimitError as e:
        # Too many requests made to the API too quickly
        feedback = send_payment_error(e)
        return {'result': 'fail',
                  'feedback': feedback}

    except stripe.error.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        feedback = send_payment_error(e)
        return {'result': 'fail',
                  'feedback': feedback}

    except stripe.error.AuthenticationError as e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        feedback = send_payment_error(e)
        return {'result': 'fail',
                  'feedback': feedback}

    except stripe.error.APIConnectionError as e:
        # Network communication with Stripe failed
        feedback = send_payment_error(e)
        return {'result': 'fail',
                  'feedback': feedback}

    except stripe.error.StripeError as e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        feedback = send_payment_error(e)
        return {'result': 'fail',
                  'feedback': feedback}

    except Exception as e:
        # Something else happened, completely unrelated to Stripe
        feedback = send_payment_error(e)
        return {'result': 'fail',
                  'feedback': feedback}


def send_payment_error(error):
    body = error.json_body
    err = body.get('error', {})

    feedback = "<strong>Status is:</strong> %s" % error.http_status
    feedback += "<br><strong>Type is:</strong> %s" % err.get('type')
    feedback += "<br><strong>Code is:</strong> %s" % err.get('code')
    feedback += "<br><strong>Message is:</strong> <span class='text-danger'>%s</span>" % err.get('message')
    return feedback
from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect, get_object_or_404, reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q
from memberships.functions import *
from .models import MembershipPackage, Member, Equine
from .forms import MembershipPackageForm, MemberForm, EquineForm
from json import dumps
import stripe
from re import search
from urllib.parse import unquote


def get_packages(request):
    if request.user.is_authenticated:
        return {'membership_packages': MembershipPackage.objects.filter(Q(owner=request.user) |
                                                                        Q(admins=request.user), enabled=True),
                'memberships': Member.objects.filter(user_account=request.user),
                'all_packages': MembershipPackage.objects.filter(enabled=True)}
    else:
        return {'authenticated': False}


class MembershipBase(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
            return HttpResponseRedirect('membership-package-settings')
        if len(membership_packages) == 1:
            return HttpResponseRedirect(f'org/{membership_packages[0].organisation_name}')
        if len(membership_packages) > 1:
            return super().get(*args, **kwargs)


class MembershipPackageView(LoginRequiredMixin, MembershipBase):
    template_name = 'membership-package.html'
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        """
        Only allow the owner and admins to view this page
        :param request:
        :param args:
        :param kwargs:
        :return:
        """

        if MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                            Q(admins=self.request.user),
                                            organisation_name=kwargs['title'],
                                            enabled=True).exists():
            # kwargs.update({'foo': 'bar'})  # inject the foo value
            # now process dispatch as it otherwise normally would
            return super().dispatch(request, *args, **kwargs)

        # disallow access to page
        return HttpResponseRedirect('/')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membership_packages'] = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                                          Q(admins=self.request.user))
        context['package'] = context['membership_packages'][0]
        context['members'] = Member.objects.filter(membership_package=context['package'])

        # get strip secret key
        stripe.api_key = get_stripe_secret_key(self.request)
        context['stripe_package'] = stripe.Account.retrieve(context['package'].stripe_acct_id,
                                                            stripe_account=context['package'].stripe_acct_id)
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


class CreateMembershipPackage(LoginRequiredMixin, TemplateView):
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
            membership_package = form.save()

            # send confirmation email
            body = f"""This is a confirmation email for your new Membership Organisation package.
            
            Membership Organisation: {membership_package.organisation_name}
            
            Thank you for choosing Cloud-Lines Memberships and please contact us if you need anything.
             
            """
            send_email(f"Organisation Confirmation: {membership_package.organisation_name}", request.user.get_full_name, body, reply_to=request.user.email)
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
        product = stripe.Product.create(name=membership_package.organisation_name,
                                        stripe_account=membership_package.stripe_acct_id)
        membership_package.stripe_product_id = product.id

    if not membership_package.membership_price_per_month_id:
        # create price(s)
        price_per_month = stripe.Price.create(
            unit_amount=int(membership_package.membership_price_per_month*100),
            currency="gbp",
            recurring={"interval": "month"},
            product=product.id,
            stripe_account=membership_package.stripe_acct_id
        )
        membership_package.membership_price_per_month_id = price_per_month.id
    if not membership_package.membership_price_per_year_id:
        price_per_year = stripe.Price.create(
            unit_amount=int(membership_package.membership_price_per_year*100),
            currency="gbp",
            recurring={"interval": "year"},
            product=product.id,
            stripe_account=membership_package.stripe_acct_id
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
        result = validate_card(request, 'package')
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
        refresh_url=f'http://{settings.SITE_NAME}/membership',
        return_url=f'http://{settings.SITE_NAME}/membership',
        type='account_onboarding',
    )
    return account_link


class MemberRegForm(LoginRequiredMixin, FormView):
    template_name = 'member_form_new.html'
    login_url = '/login/'
    form_class = MemberForm
    success_url = '/membership/'

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super().get_initial()

        # get membership title
        decoded_url = unquote(self.request.get_full_path())
        org = decoded_url.split('/')[3]

        if not MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                Q(admins=self.request.user),
                                                  organisation_name=org).exists():
            initial['email'] = self.request.user.email
            initial['first_name'] = self.request.user.first_name
            initial['last_name'] = self.request.user.last_name
            initial['membership_number'] = self.get_membership_number(org)

        return initial

    @staticmethod
    def get_membership_number(org):
        # get next available member number
        try:
            membership_package = MembershipPackage.objects.get(organisation_name=org)
            latest_added = Member.objects.filter(membership_package=membership_package).latest('membership_number')
            latest_member_number = latest_added.membership_number
            reg_ints_re = search("[0-9]+", latest_member_number)
            return latest_member_number.replace(str(reg_ints_re.group(0)),
                                               str(int(reg_ints_re.group(0)) + 1).zfill(len(reg_ints_re.group(0))))
        except Member.DoesNotExist:
            return 'REG12345'

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        self.context['membership_package'] = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])

        return self.context

    def form_valid(self, form, **kwargs):
        self.context = self.get_context_data(**kwargs)
        self.member = form.save()
        self.create_andor_link_user()
        if self.context['membership_package'].bolton != 'none':
            return redirect(f"/membership/member-bolton-form/{self.context['membership_package'].organisation_name}/{self.member.id}")
        elif self.member.payment_type == 'card_payment':
            return redirect(f"/membership/member-payment/{self.context['membership_package'].organisation_name}/{self.member.id}")
        else:
            return super().form_valid(form)

    def create_andor_link_user(self):
        """
        Create and link user
        :return:
        """
        user, created = User.objects.get_or_create(email=self.member.email)
        user.username = generate_username(self.member.first_name, self.member.last_name)
        user.first_name = self.member.first_name
        user.last_name = self.member.last_name
        user.save()

        self.member.user_account = user
        self.member.membership_package = self.context['membership_package']

        stripe.api_key = get_stripe_secret_key(self.request)

        stripe_customer = stripe.Customer.create(
            name=user.get_full_name(),
            email=user.email,
            stripe_account=self.context['membership_package'].stripe_acct_id
        )
        self.member.stripe_id = stripe_customer.id

        self.member.save()


@login_required(login_url='/login/')
def member_bolton_form(request, title, pk):

    membership_package = MembershipPackage.objects.get(organisation_name=title)
    member = Member.objects.get(id=pk)

    # access permissions
    if not MembershipPackage.objects.filter(Q(owner=request.user,
                                              organisation_name=title) |
                                            Q(admins=request.user,
                                              organisation_name=title) |
                                            Q(members=request.user, organisation_name=title)).exists():
        # disallow access to page
        return redirect('dashboard')

    if request.method == "POST":
        # get the correct bolton
        if membership_package.bolton == 'equine':
            if Equine.objects.filter(membership_package=membership_package, member=member).exists():
                form = EquineForm(request.POST, instance=Equine.objects.get(membership_package=membership_package, member=member))
            else:
                form = EquineForm(request.POST)
        else:
            form = None
        # check the form is valid
        if form.is_valid():
            bolton_form = form.save()
            # attach form to package and member
            bolton_form.membership_package = membership_package
            bolton_form.member = member
            bolton_form.save()

            # redirect to payment form IF card payment selected
            if member.payment_type == 'card_payment':
                return redirect(
                    f"/membership/member-payment/{membership_package.organisation_name}/{member.id}")
            else:
                return redirect('membership')
        else:
            return render(request, 'member_bolton_form.html', {'bolton_form': form,
                                                               'membership_package': membership_package,
                                                               'member': member})

    else:
        if membership_package.bolton == 'equine':
            # check for existing object
            if Equine.objects.filter(membership_package=membership_package, member=member).exists():
                form = EquineForm(instance=Equine.objects.get(membership_package=membership_package, member=member))
            else:
                form = EquineForm()
            return render(request, 'member_bolton_form.html', {'bolton_form': form,
                                                               'membership_package': membership_package,
                                                               'member': member})
        else:
            return redirect('membership')


class UpdateMember(LoginRequiredMixin, UpdateView):
    template_name = 'member_form_update.html'
    login_url = '/login/'
    form_class = MemberForm
    model = Member
    success_url = '/membership/'

    def dispatch(self, request, *args, **kwargs):
        """
        Only allow the owner and admins to view this page
        :param request:
        :param args:
        :param kwargs:
        :return:
        """

        if not MembershipPackage.objects.filter(Q(owner=self.request.user,
                                                  organisation_name=kwargs['title']) |
                                                Q(admins=self.request.user),
                                                  organisation_name=kwargs['title']).exists():
            # disallow access to page
            return HttpResponseRedirect('/')

        #kwargs.update({'foo': 'bar'})  # inject the foo value
        # now process dispatch as it otherwise normally would
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        self.context['membership_package'] = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        self.context['member'] = Member.objects.get(id=self.kwargs['pk'])
        return self.context

    def form_valid(self, form, **kwargs):
        self.context = self.get_context_data(**kwargs)
        self.member = form.save()
        self.update_andor_link_user()
        if self.context['membership_package'].bolton != 'none':
            return redirect(
                f"/membership/member-bolton-form/{self.context['membership_package'].organisation_name}/{self.member.id}")
        elif self.member.payment_type == 'card_payment':
            return redirect(
                f"/membership/member-payment/{self.context['membership_package'].organisation_name}/{self.member.id}")
        else:
            return super().form_valid(form)

    def update_andor_link_user(self):
        """
        Update and link user
        :return:
        """
        user, created = User.objects.get_or_create(email=self.member.email)
        user.username = generate_username(self.member.first_name, self.member.last_name)
        user.first_name = self.member.first_name
        user.last_name = self.member.last_name
        user.save()

        self.member.user_account = user
        self.member.membership_package = self.context['membership_package']

        stripe.api_key = get_stripe_secret_key(self.request)
        stripe_customer = stripe.Customer.modify(
            self.member.stripe_id,
            name=user.get_full_name(),
            email=user.email,
            stripe_account=self.context['membership_package'].stripe_acct_id
        )
        self.member.stripe_id = stripe_customer.id

        self.member.save()


class MemberPaymentView(LoginRequiredMixin, MembershipBase):
    template_name = 'member_payment.html'
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        """
        Only allow the owner and admins to view this page
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        # allow access if requesting user is an owner or admin or if page belongs to the member
        if MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                Q(admins=self.request.user),
                                                  organisation_name=kwargs['title']).exists() \
                or Member.objects.filter(id=self.kwargs['pk'],
                                         membership_package=MembershipPackage.objects.get(
                                             organisation_name=kwargs['title']),
                                         user_account=self.request.user).exists():
            # kwargs.update({'foo': 'bar'})  # inject the foo value
            # now process dispatch as it otherwise normally would
            return super().dispatch(request, *args, **kwargs)
        else:
            # disallow access to page
            return HttpResponseRedirect('/')



    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['public_api_key'] = get_stripe_public_key(self.request)
        context['package'] = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        context['member'] = Member.objects.get(id=self.kwargs['pk'])
        if context['member'].stripe_subscription_id:
            stripe.api_key = get_stripe_secret_key(self.request)
            context['subscription'] = stripe.Subscription.retrieve(context['member'].stripe_subscription_id,
                                                                   stripe_account=context['package'].stripe_acct_id)
            context['customer'] = stripe.Customer.retrieve(context['member'].stripe_id,
                                                           stripe_account=context['package'].stripe_acct_id)
        return context

    def post(self, request, *args, **kwargs):
        package = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        member = Member.objects.get(id=self.kwargs['pk'])

        result = validate_card(request, 'member', member.pk)
        if result['result'] == 'fail':
            return HttpResponse(dumps(result))

        if member.billing_period == "monthly":
            price_id = package.membership_price_per_month_id
        else:
            price_id = package.membership_price_per_year_id

        if not member.stripe_subscription_id:
            # new subscription
            subscription = stripe.Subscription.create(
                customer=member.stripe_id,
                items=[
                    {
                        "plan": price_id,
                    },
                ],
                stripe_account=package.stripe_acct_id,
            )
            member.stripe_subscription_id = subscription.id
            member.save()
            if subscription['status'] != 'active':
                result = {'result': 'fail',
                          'feedback': f"<strong>Failure message:</strong> <span class='text-danger'>{subscription['status']}</span>"}
                return HttpResponse(dumps(result))

        invoice = stripe.Invoice.list(customer=member.stripe_id, subscription=member.stripe_subscription_id,
                                      limit=1, stripe_account=package.stripe_acct_id,)
        receipt = stripe.Charge.list(customer=member.stripe_id, stripe_account=package.stripe_acct_id,)
        result = {'result': 'success',
                  'invoice': invoice.data[0].invoice_pdf,
                  'receipt': receipt.data[0].receipt_url
                  }
        return HttpResponse(dumps(result))


class MemberProfileView(MembershipBase):
    template_name = 'member_profile.html'
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        """
        Only allow the owner and admins to view this page
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        # allow access if requesting user is and owner or admin OR if page is members own profile
        if MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                Q(admins=self.request.user), organisation_name=kwargs['title']).exists()\
            or Member.objects.filter(id=self.kwargs['pk'],
                                     membership_package=MembershipPackage.objects.get(organisation_name=kwargs['title']),
                                     user_account=self.request.user).exists():
            # kwargs.update({'foo': 'bar'})  # inject the foo value
            # now process dispatch as it otherwise normally would
            return super().dispatch(request, *args, **kwargs)
        else:
            # disallow access to page
            return HttpResponseRedirect('/')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['member'] = Member.objects.get(id=self.kwargs['pk'])
        context['package'] = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        if context['member'].stripe_subscription_id:
            stripe.api_key = get_stripe_secret_key(self.request)
            context['subscription'] = stripe.Subscription.retrieve(context['member'].stripe_subscription_id,
                                                                   stripe_account=context['package'].stripe_acct_id)
            context['customer'] = stripe.Customer.retrieve(context['member'].stripe_id,
                                                           stripe_account=context['package'].stripe_acct_id)
            context['payments'] = stripe.Charge.list(customer=context['member'].stripe_id,
                                                           stripe_account=context['package'].stripe_acct_id)
        return context


def validate_card(request, type, pk=0):
    # get strip secret key
    stripe.api_key = get_stripe_secret_key(request)

    if type == 'package':
        membership_package = MembershipPackage.objects.get(owner=request.user)
        stripe_id = membership_package.stripe_owner_id
        account_id = membership_package.stripe_acct_id
    else:
        member = Member.objects.get(id=pk)
        stripe_id = member.stripe_id
        account_id = member.membership_package.stripe_acct_id
    # add payment token to user
    try:
        payment_method = stripe.Customer.modify(
          stripe_id,
          source=request.POST.get('token[id]'),
            stripe_account=account_id
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
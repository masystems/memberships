from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect, get_object_or_404, reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q
from memberships.functions import *
from .models import MembershipPackage, Price, PaymentMethod, Member, Payment, MembershipSubscription, Equine
from .forms import MembershipPackageForm, MemberForm, EquineForm
from json import dumps
import stripe
from re import search, match
from urllib.parse import unquote
from datetime import datetime


def generate_site_vars(request):
    context = {}
    if request.user.is_authenticated:
        context['membership_packages'] = MembershipPackage.objects.filter(Q(owner=request.user) |
                                                                          Q(admins=request.user), enabled=True).distinct()
        context['membership'] = Member.objects.get(user_account=request.user)

        context['public_api_key'] = get_stripe_public_key(request)
        context['all_packages'] = MembershipPackage.objects.filter(enabled=True)
    else:
        context['authenticated'] = False

    return context


# this function is not used, as it wouldn't work. Instead, the check is done inside each dispatch method.
def check_authentication(request):
    if request.user.is_authenticated:
        return
    else:
        return redirect('/accounts/login/')


def get_login_url():
    return "/accounts/login/?next=/membership/"


class MembershipBase(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class Membership(LoginRequiredMixin, MembershipBase):
    template_name = 'membership-package.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


@login_required(login_url='/accounts/login/')
def manage_admins(request, title):
    # validate request user is owner or admin of org
    if not MembershipPackage.objects.filter(Q(owner=request.user) |
                                        Q(admins=request.user),
                                        organisation_name=title,
                                        enabled=True).exists():
        return redirect('dashboard')

    membership_package = MembershipPackage.objects.get(organisation_name=title)

    if request.method == "POST":
        if request.POST['type'] == "add_admin":
            # validate email address
            if not match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", request.POST['email']):
                return HttpResponse(dumps({'status': "fail",
                                           'message': 'Not a valid email address'}), content_type='application/json')
            # validate user not already an admin
            try:
                user = User.objects.get(email=request.POST['email'])
                if user in membership_package.admins.all():
                    return HttpResponse(dumps({'status': "fail",
                                               'message': 'Admin already exists!'}), content_type='application/json')
            except User.DoesNotExist:
                # passed validation
                pass
            # get/create user
            user, created = User.objects.get_or_create(email=request.POST['email'])
            if created:
                user.username = generate_username(request.POST['first_name'],
                                                  request.POST['last_name'])
                user.first_name = request.POST['first_name']
                user.last_name = request.POST['last_name']
                user.save()
                # create member object
                member = Member(user_account=user)
                member.save()
                # send email to new user
                body = f"""<p>You have been added as an admin to the {membership_package.organisation_name} Cloud-Lines Memberships subscription.</p>

                        <p>To login to Cloud-Lines Memberships go to <a href="http://memberships.cloud-lines.com">http://memberships.cloud-lines.com</a> and select "forgot password" to reset your password.</p>

                        """

                send_email(f"New Admin Account: {membership_package.organisation_name}",
                           user.get_full_name(), body, send_to=user.email, reply_to=request.user.email)

            # add user admin of membership_package
            membership_package.admins.add(user)
            return HttpResponse(dumps({'status': "success",
                                       'message': "Member assigned successfully!"}), content_type='application/json')
            # send email to user
        elif request.POST['type'] == "remove_admin":
            # get user
            try:
                user = User.objects.get(email=request.POST['email'])
            except User.DoesNotExist:
                return HttpResponse(dumps({'status': "fail",
                                           'message': "User doesn't exists!"}), content_type='application/json')
            # remove from admins
            membership_package.admins.remove(user)
            # return success
            return HttpResponse(dumps({'status': "success",
                                       'message': "User successfully removed"}), content_type='application/json')
        return HttpResponse(dumps({'status': "fail",
                                   'message': "Request not recognised"}), content_type='application/json')
    else:
        return render(request, 'manage-admins.html', {'membership_package': membership_package})


@login_required(login_url='/accounts/login/')
def manage_membership_types(request, title):
    # validate request user is owner or admin of org
    if not MembershipPackage.objects.filter(Q(owner=request.user) |
                                        Q(admins=request.user),
                                        organisation_name=title,
                                        enabled=True).exists():
        return redirect('dashboard')

    membership_package = MembershipPackage.objects.get(organisation_name=title)
    # get strip secret key
    stripe.api_key = get_stripe_secret_key(request)
    visible_value = True

    if request.method == "POST":
        if 'visible' not in request.POST:
            visible_value = False

        # nickname validation
        if request.POST.get('nickname') in ("", None):
            return HttpResponse(dumps({'status': "fail",
                                       'message': "You must enter a valid Membership Name"}), content_type='application/json')

        if request.POST.get('type_id'):
            # edit
            if request.POST.get('type') == "delete":
                # mark objects as active false
                Price.objects.filter(stripe_price_id=request.POST.get('type_id')).update(active=False)
                return HttpResponse(dumps({'status': "success",
                                           'message': "Price Deleted"}), content_type='application/json')
            else:
                price = stripe.Price.modify(
                    request.POST.get('type_id'),
                    # recurring={"interval": request.POST.get('interval')},
                    nickname=request.POST.get('nickname'),
                    # unit_amount=int(float(request.POST.get('amount')) * 100),
                    stripe_account=membership_package.stripe_acct_id
                )
                Price.objects.filter(stripe_price_id=request.POST.get('type_id')).update(nickname=price.nickname, visible=visible_value)
                return HttpResponse(dumps({'status': "success",
                                           'message': "Price successfully updated"}), content_type='application/json')

        else:
            # new price object
            try:
                price = stripe.Price.create(
                    request.POST.get('type_id'),
                    product=membership_package.stripe_product_id,
                    currency="gbp",
                    recurring={"interval": request.POST.get('interval')},
                    nickname=request.POST.get('nickname'),
                    unit_amount=int(float(request.POST.get('amount')) * 100),
                    stripe_account=membership_package.stripe_acct_id
                )
                Price.objects.create(membership_package=membership_package,
                                     stripe_price_id=price.id,
                                     nickname=price.nickname,
                                     interval=price.recurring.interval,
                                     visible=visible_value,
                                     amount=price.unit_amount,
                                     active=True)
                return HttpResponse(dumps({'status': "success",
                                           'message': "Price successfully added"}), content_type='application/json')
            except ValueError:
                return HttpResponse(dumps({'status': "fail",
                                           'message': "You must enter a valid amount"}), content_type='application/json')

    else:
        membership_types_list = []
        price_list = []

        for price in Price.objects.filter(membership_package=membership_package, active=True):
            membership_types_list.append(stripe.Price.retrieve(price.stripe_price_id, stripe_account=membership_package.stripe_acct_id))
            price_list.append(price.visible)

        return render(request, 'manage-membership-types.html', {'membership_package': membership_package,
                                                                'membership_types_list': membership_types_list,
                                                                'price_list': price_list})


@login_required(login_url='/accounts/login/')
def manage_payment_methods(request, title):
    # validate request user is owner or admin of org
    if not MembershipPackage.objects.filter(Q(owner=request.user) |
                                            Q(admins=request.user),
                                            organisation_name=title,
                                            enabled=True).exists():
        return redirect('dashboard')

    membership_package = MembershipPackage.objects.get(organisation_name=title)
    active = True
    visible = True

    if request.method == "POST":
        # capture if active value given from form
        if request.POST.get('active') != "on":
            active = False

        # capture if visible value given from form
        if request.POST.get('visible') != "on":
            visible = False

        if request.POST.get('type_id'):
            if request.POST.get('type') == "delete":
                # mark objects as active false
                PaymentMethod.objects.filter(id=request.POST.get('type_id')).delete()
                return HttpResponse(dumps({'status': "success",
                                           'message': f"{request.POST.get('payment_name')} successfully deleted"}), content_type='application/json')
            else:
                # edit existing
                PaymentMethod.objects.filter(id=request.POST.get('type_id')).update(
                    payment_name=request.POST.get('payment_name'),
                    information=request.POST.get('information'),
                    visible=visible,
                    active=active)
                return HttpResponse(dumps({'status': "success",
                                           'message': f"{request.POST.get('payment_name')} successfully updated"}), content_type='application/json')

        else:
            # new
            PaymentMethod.objects.create(membership_package=membership_package,
                                         payment_name=request.POST.get('payment_name'),
                                         information=request.POST.get('information'),
                                         visible=visible,
                                         active=active)
            return HttpResponse(dumps({'status': "success",
                                       'message': f"{request.POST.get('payment_name')} successfully added"}), content_type='application/json')


    else:
        payment_methods = PaymentMethod.objects.filter(membership_package=membership_package)
        return render(request, 'manage-payment-methods.html', {'membership_package': membership_package,
                                                                'payment_methods': payment_methods})


class SelectMembershipPackageView(LoginRequiredMixin, MembershipBase):
    template_name = 'select-membership-package.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context

    def get(self, *args, **kwargs):
        membership_packages = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                               Q(admins=self.request.user))

        if len(membership_packages) < 1:
            return HttpResponseRedirect('membership-package-settings')
        if len(membership_packages) == 1:
            return HttpResponseRedirect(f'org/{membership_packages[0].organisation_name}')
        if len(membership_packages) > 1:
            return HttpResponseRedirect(f'/')

        return super().get(*args, **kwargs)


def get_members(request, title):
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    start = int(request.GET.get('start', 0))
    end = int(request.GET.get('length', 20))
    search = request.GET.get('search[value]', "")
    members = []
    if search == "":
        all_members = Member.objects.filter(subscription__membership_package=membership_package, subscription__price__isnull=False).distinct()[start:start+end]
    else:
        all_members = Member.objects.filter(Q(user_account__first_name__contains=search) |
                                            Q(user_account__last_name__contains=search) |
                                            Q(user_account__email__contains=search) |
                                            Q(user_account__email__contains=search),
                                            subscription__membership_package=membership_package,
                                            subscription__price__isnull=False).distinct()[start:start + end]
    total_members = Member.objects.filter(subscription__membership_package=membership_package,
                                        subscription__price__isnull=False).distinct().count()
    if all_members.count() > 0:
        for member in all_members:
            # get membership type
            for sub in member.subscription.all():
                if sub.membership_package == membership_package:
                    membership_type = f"""<span class="badge py-1 badge-info">{sub.price.nickname}</span>"""
                    break
                else:
                    membership_type = ""

            # buttons!
            for sub in member.subscription.all():
                if sub.membership_package == membership_package:
                    if sub.payment_method or sub.stripe_subscription_id:
                        pass
                        card_button = f"""<a href="{reverse('member_payment', kwargs={'title': membership_package.organisation_name,
                                                        'pk': member.id})}">
                                            <button class="btn btn-sm btn-rounded btn-light mr-1 mt-1" data-toggle="tooltip" data-placement="top" title="Visit Payment Page">
                                                <i class="fad fa-credit-card-front text-success"></i>
                                            </button>
                                        </a>"""
                    else:
                        card_button = f"""<a href="{reverse('member_payment', kwargs={'title': membership_package.organisation_name,
                                                        'pk': member.id})}">
                                                    <button class="btn btn-sm btn-rounded btn-light mr-1 mt-1" data-toggle="tooltip" data-placement="top" title="Card details not added">
                                                        <i class="fad fa-credit-card-front text-danger"></i>
                                                    </button>
                                                </a>"""
                edit_member_button = f"""<a href="{reverse('edit_member', kwargs={'title': membership_package.organisation_name,
                                                                                'pk': member.id})}"><button class="btn btn-sm btn-rounded btn-light mr-1 mt-1" data-toggle="tooltip" title="Edit Member Details"><i class="fad fa-user-edit text-info"></i></button></a>"""
                reset_password_button = f"""<button class="btn btn-sm btn-rounded btn-light mt-1 passRstBtnIn" value="{ member.user_account.email }" data-toggle="tooltip" title="Reset Password"><i class="fad fa-key text-success"></i></button>"""
                remove_member_button = f"""<button class="btn btn-sm btn-rounded btn-light mt-1 removeUserBtn" data-toggle="tooltip" title="Remove Member" value="{ member.id }"><i class="fad fa-user-slash text-danger"></i></button>"""
                payment_reminder_button = f"""<a href="{reverse('payment_reminder', kwargs={'title': membership_package.organisation_name,
                                                                                            'pk': member.id})}"><button class="btn btn-sm btn-rounded btn-light mt-1" data-toggle="tooltip" data-placement="top" title="Send payment reminder"><i class="fad fa-envelope-open-dollar"></i></button></a>"""

            # # set member id, name, email, mambership_type and buttons
            members.append({'id': member.id,
                            'name': f"""<a href="{reverse('member_profile', kwargs={'pk': member.id})}"><button class="btn waves-effect waves-light btn-rounded btn-sm btn-success">{member.user_account.get_full_name()}</button></a>""",
                            'email': member.user_account.email,
                            'membership_type': membership_type,
                            'action': f"{card_button}{edit_member_button}{reset_password_button}{remove_member_button}{payment_reminder_button}"})
            complete_data = {
              "draw": 0,
              "recordsTotal": all_members.count(),
              "recordsFiltered": total_members,
              "data": members
            }
    else:
        complete_data = {
            "draw": 0,
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": []
        }
    return HttpResponse(dumps(complete_data))


class MembershipPackageView(LoginRequiredMixin, MembershipBase):
    template_name = 'membership-package.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        # check user is logged in
        if request.user.is_authenticated:
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
        # redirect to login page if user not logged in
        else:
            return HttpResponseRedirect(f"{get_login_url()}org/{kwargs['title']}")
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membership_package'] = MembershipPackage.objects.filter(Q(owner=self.request.user, organisation_name=self.kwargs['title']) |
                                                                         Q(admins=self.request.user, organisation_name=self.kwargs['title'])).distinct()
        # sigh
        context['membership_package'] = context['membership_package'][0]

        context['members'] = Member.objects.filter(subscription__membership_package=context['membership_package'], subscription__price__isnull=False).distinct()

        context['incomplete_members'] = Member.objects.filter(subscription__membership_package=context['membership_package'], subscription__price__isnull=True)


        # get strip secret key
        stripe.api_key = get_stripe_secret_key(self.request)
        context['stripe_package'] = stripe.Account.retrieve(context['membership_package'].stripe_acct_id)

        if context['membership_package'].stripe_acct_id:
            try:
                context['edit_account'] = stripe.Account.create_login_link(context['membership_package'].stripe_acct_id)
            except stripe.error.InvalidRequestError:
                # stripe account created but not setup
                context['stripe_package_setup'] = get_account_link(context['membership_package'])
            if context['stripe_package'].requirements.errors:
                context['account_link'] = get_account_link(context['membership_package'])
        else:
            # stripe account not setup
            context['stripe_package_setup'] = create_package_on_stripe(self.request)
        return context
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membership_package'] = MembershipPackage.objects.filter(Q(owner=self.request.user, organisation_name=self.kwargs['title']) |
                                                                         Q(admins=self.request.user, organisation_name=self.kwargs['title'])).distinct()
        # sigh
        context['membership_package'] = context['membership_package'][0]

        context['members'] = Member.objects.filter(subscription__membership_package=context['membership_package']).count()

        context['incomplete_members'] = Member.objects.filter(subscription__membership_package=context['membership_package'], subscription__price__isnull=True)


        # get strip secret key
        stripe.api_key = get_stripe_secret_key(self.request)
        context['stripe_package'] = stripe.Account.retrieve(context['membership_package'].stripe_acct_id)

        if context['membership_package'].stripe_acct_id:
            try:
                context['edit_account'] = stripe.Account.create_login_link(context['membership_package'].stripe_acct_id)
            except stripe.error.InvalidRequestError:
                # stripe account created but not setup
                context['stripe_package_setup'] = get_account_link(context['membership_package'])
            if context['stripe_package'].requirements.errors:
                context['account_link'] = get_account_link(context['membership_package'])
        else:
            # stripe account not setup
            context['stripe_package_setup'] = create_package_on_stripe(self.request)
        return context


class CreateMembershipPackage(LoginRequiredMixin, TemplateView):
    template_name = 'membership-package-settings.html'
    login_url = '/accounts/login/'

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

            return HttpResponse(dumps({'status': "success"}), content_type='application/json')
        else:
            message = {'status': "fail",
                       'errors': f"{form.errors}"}
            return HttpResponse(dumps(message), content_type='application/json')


@login_required(login_url='/accounts/login/')
def delete_membership_package(request, title):
    """
    validate that the user is the owner
    validate that there are no existing members
    stop payments to stripe
    delete org account
    email confirmation email
    redirect user to home page, and pass success message in
    :param request:
    :param title:
    :return:
    """

    try:
        membership_package = MembershipPackage.objects.get(owner=request.user, organisation_name=title, enabled=True)
    except MembershipPackage.DoesNotExist:
        # disallow access to page
        # return to previous page
        return redirect('membership_package', membership_package.organisation_name)
    # validate that there are no existing subscriptions
    if MembershipSubscription.objects.filter(membership_package=membership_package).exists():
        raise MembershipPackage.DoesNotExist
        return redirect('membership_package', membership_package.organisation_name)

    # stop payments to stripe
    # get stripe secret key
    stripe.api_key = get_stripe_secret_key(request)
    membership_package = MembershipPackage.objects.get(owner=request.user)

    # try to delete stripe account
    try:
        account = stripe.Account.delete(membership_package.stripe_acct_id)
    except Account.DoesNotExist:
        # THIS EXCEPTION DOESNT LOOK RIGHT
        # account does not exist
        return redirect('membership_package', membership_package.organisation_name)

    # delete org account
    membership_package.delete()

    # send email confirmation
    body = f"""<p>This is an email confirming the deletion of your Membership Organisation package.</p>

                    <ul>
                    <li>Membership Organisation: {membership_package.organisation_name}</li>
                    </ul>

                    <p>Thank you for choosing Cloud-Lines Memberships. Please contact us if we can help in the future - contact@masys.co.uk</p>

                    """
    send_email(f"Organisation Deletion Confirmation: {membership_package.organisation_name}", request.user.get_full_name(), body, send_to=request.user.email, reply_to=request.user.email)

    # success message
    return redirect('/')


@login_required(login_url='/accounts/login/')
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
            business_type=membership_package.business_type,
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

    membership_package.save()

    return get_account_link(membership_package)


@login_required(login_url='/accounts/login/')
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

            membership_package.enabled = True
            membership_package.save()

            # send confirmation email
            body = f"""<p>This email confirms the successful creation of your new Cloud-Lines Memberships package.

                    <ul>
                    <li>Membership Organisation: {membership_package.organisation_name}</li>
                    </ul>

                    <p>Thank you for choosing Cloud-Lines Memberships. Please contact us if you need anything - contact@masys.co.uk</p>

                    """
            send_email(f"New Organisation Created: {membership_package.organisation_name}",
                       request.user.get_full_name(), body, send_to=request.user.email)#, reply_to=request.user.email)
            #send_email(f"Organisation Confirmation: {membership_package.organisation_name}",
                       #request.user.get_full_name(), body, reply_to=request.user.email)

            return HttpResponse(dumps(result))


@login_required(login_url='/accounts/login/')
def payment_reminder(request, title, pk):
    
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    # the member that needs reminding
    member = Member.objects.get(id=pk)

    subscription = membership_package.membership_package.get(member=member, membership_package=membership_package)
    
    # variables used to construct the email
    temp_payment_method = subscription.payment_method
    outstanding_string = ""
    body = ""

    # if payment_method == None, it is a card payment, and stripe can be used
    if subscription.payment_method == None:
        temp_payment_method = "Card payment"

        # stripe subscription
        stripe.api_key = get_stripe_secret_key(request)
        stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id, stripe_account=membership_package.stripe_acct_id)
        
        # if payments are outstanding
        if stripe_subscription.status == "past_due":
            outstanding_string = f"<p>Payment to renew your subscription failed. Please try again or contact the owner or an admin of {membership_package.organisation_name}.</p>"

        body = f"""<p>This is a reminder for you to pay for your subscription.</p>
                    {outstanding_string}
                    <ul>
                        <li>Membership Organisation: {membership_package.organisation_name}</li>
                        <li>Next Payment: £{"{:.2f}".format(int(subscription.price.amount) / 100)} due by {datetime.fromtimestamp(stripe_subscription.current_period_end)}.</li>
                        <li>Payment Method: {temp_payment_method}</li>
                        <li>Payment Interval: {subscription.price.interval}</li>
                    </ul>
                    """

    # payment method is not card payment
    else:
        payment_method = subscription.payment_method
        payment_info_string = ""
        if payment_method.information != '':
            payment_info_string = f"<li>Payment Information: {payment_method.information}</li>"
        body = f"""<p>This is a reminder for you to pay for your subscription.
                    <ul>
                        <li>Membership Organisation: {membership_package.organisation_name}</li>
                        <li>Amount Due: £{"{:.2f}".format(int(subscription.price.amount) / 100)}</li>
                        <li>Payment Method: {payment_method.payment_name}</li>
                        <li>Payment Interval: {subscription.price.interval}</li>
                        {payment_info_string}
                    </ul>
                    """
    
    send_email(f"Payment Reminder: {membership_package.organisation_name}", request.user.get_full_name(), body, send_to=member.user_account.email)

    return redirect('membership_package', membership_package.organisation_name)


def get_account_link(membership):
    account_link = stripe.AccountLink.create(
        account=membership.stripe_acct_id,
        refresh_url=f'{settings.HTTP_PROTOCOL}://{settings.SITE_NAME}/membership',
        return_url=f'{settings.HTTP_PROTOCOL}://{settings.SITE_NAME}/membership',
        type='account_onboarding',
    )
    return account_link


class MembersDetailed(LoginRequiredMixin, MembershipBase):
    template_name = 'members_detailed.html'

    def dispatch(self, request, *args, **kwargs):
        # check user is logged in
        if request.user.is_authenticated:
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
        # redirect to login page if user not logged in
        else:
            return HttpResponseRedirect(f"{get_login_url()}members-detailed/{self.kwargs['title']}")

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        self.context['membership_package'] = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        self.context['members'] = Member.objects.filter(subscription__membership_package=self.context['membership_package'])

        hidden_bolon_fields = ['id', 'membership_package', 'subscription']
        if self.context['membership_package'].bolton == "equine":

            self.context['bolton_columns'] = [field for field in Equine._meta.get_fields(include_parents=False, include_hidden=False) if field.name not in hidden_bolon_fields]
            self.context['bolton'] = Equine.objects.filter(membership_package=self.context['membership_package']).defer('id', 'membership_package', 'subscription', 'subscription_id')
        return self.context


class MemberRegForm(LoginRequiredMixin, FormView):
    template_name = 'member_form_new.html'
    login_url = '/accounts/login/'
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

        return initial

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        self.context['membership_package'] = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        
        # check to see if membership type exists
        self.context['is_price'] = False
        prices = None
        try:
            prices = Price.objects.filter(membership_package=self.context['membership_package'])
        except Price.DoesNotExist:
            pass
        for price in prices:
            if price.active:
                self.context['is_price'] = True

        # check to see if stripe has been set up
        stripe.api_key = get_stripe_secret_key(self.request)
        self.context['is_stripe'] = False
        if self.context['membership_package'].stripe_acct_id:
            try:
                stripe.Account.create_login_link(self.context['membership_package'].stripe_acct_id)
                self.context['is_stripe'] = True
            except stripe.error.InvalidRequestError:
                # stripe account created but not setup
                pass
        else:
            # stripe account not setup
            pass

        return self.context

    def form_valid(self, form, **kwargs):
        self.context = self.get_context_data(**kwargs)
        # validate user not already a member of package
        try:
            if MembershipSubscription.objects.filter(member=Member.objects.get(user_account=User.objects.get(email=form.cleaned_data['email'])),
                                                     membership_package=self.context['membership_package']).exists():
                form.add_error('email', f"This email address is already in use for {self.context['membership_package'].organisation_name}.")
                return super(MemberRegForm, self).form_invalid(form)
        except Member.DoesNotExist:
            pass
        except User.DoesNotExist:
            pass

        self.form = form
        self.get_or_create_user()

        # get or create member object
        self.member, created = Member.objects.get_or_create(user_account=self.user)
        self.member.title = self.form.cleaned_data['title']
        self.member.address_line_1 = self.form.cleaned_data['address_line_1']
        self.member.address_line_2 = self.form.cleaned_data['address_line_2']
        self.member.town = self.form.cleaned_data['town']
        self.member.county = self.form.cleaned_data['county']
        self.member.postcode = self.form.cleaned_data['postcode']
        self.member.contact_number = self.form.cleaned_data['contact_number']
        self.member.save()


        # create subscription object
        try:
            subscription = MembershipSubscription.objects.get(member=self.member, membership_package=self.context['membership_package'])
        except MembershipSubscription.DoesNotExist:
            subscription = MembershipSubscription.objects.create(member=self.member, membership_package=self.context['membership_package'])

        subscription.membership_package = self.context['membership_package']
        subscription.member = self.member

        # create/ update stripe customer
        stripe.api_key = get_stripe_secret_key(self.request)
        if subscription.stripe_id:
            # stripe user already exists
            stripe_customer = stripe.Customer.modify(
                subscription.stripe_id,
                name=self.member.user_account.get_full_name(),
                email=self.member.user_account.email,
                stripe_account=self.context['membership_package'].stripe_acct_id
            )
        else:
            stripe_customer = stripe.Customer.create(
                name=self.member.user_account.get_full_name(),
                email=self.member.user_account.email,
                stripe_account=self.context['membership_package'].stripe_acct_id
            )

        subscription.stripe_id = stripe_customer.id
        subscription.save()

        if self.context['membership_package'].bolton != 'none' and MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                                    Q(admins=self.request.user),
                                                                      organisation_name=self.context['membership_package'].organisation_name).exists():
            return redirect(
                f"member_bolton_form", self.context['membership_package'].organisation_name, self.member.id)
        else:
            return redirect(
                f"member_payment", self.context['membership_package'].organisation_name, self.member.id)

    def get_or_create_user(self):
        """
        Get or create a new user
        :return:
        """
        self.user, created = User.objects.get_or_create(email=self.form.cleaned_data['email'])
        if created:
            self.user.username = generate_username(self.form.cleaned_data['first_name'], self.form.cleaned_data['last_name'])
        self.user.first_name = self.form.cleaned_data['first_name']
        self.user.last_name = self.form.cleaned_data['last_name']
        self.user.save()

        # # send confirmation email
        # body = f"""<p>This is a confirmation email for your new Organisation Subscription.

        #                                <ul>
        #                                <li>Congratulations, you are now a member of {self.context['membership_package']} Organisation.</li>
        #                                </ul>

        #                                <p>Thank you for choosing Cloud-Lines Memberships and please contact us if you need anything.</p>

        #                                """
        # send_email(f"Organisation Confirmation: {self.context['membership_package']}",
        #            self.user.get_full_name(), body, send_to=self.user.email, reply_to=self.user.email)



@login_required(login_url='/accounts/login/')
def member_bolton_form(request, title, pk):

    membership_package = MembershipPackage.objects.get(organisation_name=title)
    member = Member.objects.get(id=pk)
    subscription = MembershipSubscription.objects.get(member=member, membership_package=membership_package)
    # access permissions
    if MembershipPackage.objects.filter(Q(owner=request.user) |
                                        Q(admins=request.user), organisation_name=title).exists() or \
            request.user == member.user_account:
        # allow access to page
        pass

    else:
        # disallow access to page
        return redirect('dashboard')

    if request.method == "POST":
        # get the correct bolton
        if membership_package.bolton == 'equine':
            if Equine.objects.filter(membership_package=membership_package, subscription=subscription).exists():
                form = EquineForm(request.POST, instance=Equine.objects.get(membership_package=membership_package, subscription=subscription))
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
            bolton_form.subscription = subscription
            bolton_form.save()

            return redirect(
                f"member_payment", membership_package.organisation_name, member.id)
                
        else:
            return render(request, 'member_bolton_form.html', {'bolton_form': form,
                                                               'membership_package': membership_package,
                                                               'member': member})

    else:
        if membership_package.bolton == 'equine':
            # check for existing object
            if Equine.objects.filter(membership_package=membership_package, subscription=subscription).exists():
                form = EquineForm(instance=Equine.objects.get(membership_package=membership_package, subscription=subscription))
            else:
                form = EquineForm()
            return render(request, 'member_bolton_form.html', {'bolton_form': form,
                                                               'membership_package': membership_package,
                                                               'member': member})
        else:
            return redirect('membership')


class UpdateMember(LoginRequiredMixin, UpdateView):
    template_name = 'member_form_update.html'
    login_url = '/accounts/login/'
    form_class = MemberForm
    model = Member
    success_url = '/membership/'

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super().get_initial()

        # get membership title
        decoded_url = unquote(self.request.get_full_path())
        member_id = decoded_url.split('/')[4]
        member = Member.objects.get(id=member_id)
        initial['email'] = member.user_account.email
        initial['first_name'] = member.user_account.first_name
        initial['last_name'] = member.user_account.last_name

        return initial

    def dispatch(self, request, *args, **kwargs):
        # check user is logged in
        if request.user.is_authenticated:
            """
            Only allow the owner and admins to view this page
            :param request:
            :param args:
            :param kwargs:
            :return:
            """

            if not MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                    Q(admins=self.request.user),
                                                    organisation_name=kwargs['title']).exists():
                # disallow access to page
                return HttpResponseRedirect('/')

            #kwargs.update({'foo': 'bar'})  # inject the foo value
            # now process dispatch as it otherwise normally would
            return super().dispatch(request, *args, **kwargs)
        # redirect to login page if user not logged in
        else:
            return HttpResponseRedirect(f"{get_login_url()}edit-member/{self.kwargs['title']}/{self.kwargs['pk']}")

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        self.context['membership_package'] = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        self.context['member'] = Member.objects.get(id=self.kwargs['pk'])
        return self.context

    def form_valid(self, form, **kwargs):
        self.context = self.get_context_data(**kwargs)
        self.form = form
        self.member = self.form.save()
        self.update_user()
        self.update_stripe_customer()

        if self.context['membership_package'].bolton != 'none':
            return redirect(
                f"member_bolton_form", self.context['membership_package'].organisation_name, self.member.id)
        else:
            return super().form_valid(form)

        # if self.request.user == self.context['membership_package'].owner or self.request.user in self.context[
        #     'membership_package'].admins.all():
        #     return redirect(f"member_sub_form", self.context['membership_package'].organisation_name, self.member.id)
        # else:
        #     return super().form_valid(form)

    def update_user(self):
        """
        Update and link user
        :return:
        """
        # update the user from the member id
        self.member.user_account.email = self.form.cleaned_data['email']
        self.member.user_account.first_name = self.form.cleaned_data['first_name']
        self.member.user_account.last_name = self.form.cleaned_data['last_name']
        self.member.save()

    def update_stripe_customer(self):
        stripe.api_key = get_stripe_secret_key(self.request)

        subscription = MembershipSubscription.objects.get(member=self.member,
                                                          membership_package=self.context['membership_package'])
        if subscription.stripe_id:
            stripe_customer = stripe.Customer.modify(
                subscription.stripe_id,
                name=self.member.user_account.get_full_name(),
                email=self.member.user_account.email,
                stripe_account=self.context['membership_package'].stripe_acct_id
            )


class MemberPaymentView(LoginRequiredMixin, MembershipBase):
    template_name = 'member_payment.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        # check user is logged in
        if request.user.is_authenticated:
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
                                                                        subscription=MembershipSubscription.objects.get(member=Member.objects.get(id=self.kwargs['pk']),
                                                                                                                        membership_package=MembershipPackage.objects.get(organisation_name=kwargs['title'])),
                                                                        user_account=self.request.user).exists():

                # kwargs.update({'foo': 'bar'})  # inject the foo value
                # now process dispatch as it otherwise normally would
                return super().dispatch(request, *args, **kwargs)
            else:
                # disallow access to page
                return HttpResponseRedirect('/')
        # redirect to login page if user not logged in
        else:
            return HttpResponseRedirect(f"{get_login_url()}member-payment/{self.kwargs['title']}/{self.kwargs['pk']}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['public_api_key'] = get_stripe_public_key(self.request)
        context['package'] = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        context['member'] = Member.objects.get(id=self.kwargs['pk'])

        if self.request.user == context['package'].owner or self.request.user in context['package'].admins.all():
            context['payment_methods'] = PaymentMethod.objects.filter(membership_package=context['package'], active=True)
        else:
            context['payment_methods'] = PaymentMethod.objects.filter(membership_package=context['package'],
                                                                      visible=True, active=True)

        context['subscription'] = MembershipSubscription.objects.get(member=context['member'],
                                                                     membership_package=context['package'])
        context['membership_types_list'] = []
        # get strip secret key
        stripe.api_key = get_stripe_secret_key(self.request)
        if self.request.user == context['package'].owner or self.request.user in context['package'].admins.all():
            for price in Price.objects.filter(membership_package=context['package'], active=True):
                context['membership_types_list'].append(stripe.Price.retrieve(price.stripe_price_id,
                                                       stripe_account=context['package'].stripe_acct_id))
        else:
            for price in Price.objects.filter(membership_package=context['package'], visible=True, active=True):
                context['membership_types_list'].append(stripe.Price.retrieve(price.stripe_price_id,
                                                       stripe_account=context['package'].stripe_acct_id))
        return context

    def post(self, request, *args, **kwargs):
        package = MembershipPackage.objects.get(organisation_name=self.kwargs['title'])
        member = Member.objects.get(id=self.kwargs['pk'])
        subscription = MembershipSubscription.objects.get(member=member, membership_package=package)

        result = validate_card(request, 'member', subscription.pk)
        if result['result'] == 'fail':
            return HttpResponse(dumps(result))
        print(stripe.Invoice.list(customer=subscription.stripe_id, stripe_account=package.stripe_acct_id))
        # new subscription
        subscription_details = stripe.Subscription.create(
            customer=subscription.stripe_id,
            items=[
                {
                    "plan": subscription.price.stripe_price_id,
                },
            ],
            stripe_account=package.stripe_acct_id,
        )
        subscription.stripe_subscription_id = subscription_details.id
        subscription.active = True
        subscription.save()
        if subscription_details['status'] != 'active':
            result = {'result': 'fail',
                      'feedback': f"<strong>Failure message:</strong> <span class='text-danger'>{subscription_details['status']}</span>"}
            return HttpResponse(dumps(result))

        invoice = stripe.Invoice.list(customer=subscription.stripe_id, subscription=subscription.stripe_subscription_id,
                                      limit=1, stripe_account=package.stripe_acct_id,)
        receipt = stripe.Charge.list(customer=subscription.stripe_id, stripe_account=package.stripe_acct_id,)

        result = {'result': 'success',
                  'invoice': invoice.data[0].invoice_pdf,
                  'receipt': receipt.data[0].receipt_url
                  }
        return HttpResponse(dumps(result))


@login_required(login_url="/accounts/login")
def update_membership_type(request, title, pk):
    if request.method == 'POST':
        if not request.POST.get('membership_type'):
            return HttpResponse(dumps({'status': "fail",
                                       'message': "You must enter a valid Membership Type"}), content_type='application/json')

        package = MembershipPackage.objects.get(organisation_name=title)
        member = Member.objects.get(id=pk)
        if request.POST.get('payment_method') != 'Card Payment':
            MembershipSubscription.objects.filter(member=member, membership_package=package).update(price=Price.objects.get(stripe_price_id=request.POST.get('membership_type')),
                                                                                                    payment_method=PaymentMethod.objects.get(payment_name=request.POST.get('payment_method'),
                                                                                                                                             membership_package=package))
            
            # send confirmation email to new member
            body = f"""<p>This is a confirmation email for your new Organisation Subscription.

                                        <ul>
                                        <li>Congratulations, you are now a member of {package.organisation_name} Organisation.</li>
                                        </ul>

                                        <p>Thank you for choosing Cloud-Lines Memberships and please contact us if you need anything.</p>

                                        """
            send_email(f"Organisation Confirmation: {package.organisation_name}",
                    member.user_account.get_full_name(), body, send_to=member.user_account.email)
            
            return HttpResponse(dumps({'status': "success",
                                       'redirect': True}), content_type='application/json')
        else:
            MembershipSubscription.objects.filter(member=member, membership_package=package).update(
                price=Price.objects.get(stripe_price_id=request.POST.get('membership_type')))

            # send confirmation email to new member
            body = f"""<p>This is a confirmation email for your new Organisation Subscription.

                                        <ul>
                                        <li>Congratulations, you are now a member of {package.organisation_name} Organisation.</li>
                                        </ul>

                                        <p>Thank you for choosing Cloud-Lines Memberships and please contact us if you need anything.</p>

                                        """
            send_email(f"Organisation Confirmation: {package.organisation_name}",
                    member.user_account.get_full_name(), body, send_to=member.user_account.email)

            return HttpResponse(dumps({'status': "success"}), content_type='application/json')


class MemberProfileView(MembershipBase):
    template_name = 'member_profile.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        # check user is logged in
        if request.user.is_authenticated:
            """
            Only allow the owner and admins to view this page
            :param request:
            :param args:
            :param kwargs:
            :return:
            """
            # allow access if requesting user is and owner or admin of one of members subscriptions
            # OR
            # if page is members own profile
            member = Member.objects.get(id=self.kwargs['pk'])
            if request.user == member.user_account:
                return super().dispatch(request, *args, **kwargs)
            for subscription in member.subscription.all():
                if self.request.user == subscription.membership_package.owner or \
                        self.request.user in subscription.membership_package.admins.all():
                    # kwargs.update({'foo': 'bar'})  # inject the foo value
                    # now process dispatch as it otherwise normally would
                    return super().dispatch(request, *args, **kwargs)
            else:
                # disallow access to page
                return HttpResponseRedirect('/')
        # redirect to login page if user not logged in
        else:
            return HttpResponseRedirect(f"{get_login_url()}member-profile/{self.kwargs['pk']}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['members'] = Member.objects.all()
        context['member'] = Member.objects.get(id=self.kwargs['pk'])
        context['public_api_key'] = get_stripe_public_key(self.request)

        context['subscriptions'] = {}
        stripe.api_key = get_stripe_secret_key(self.request)
        for subscription in context['member'].subscription.all():
            if subscription.stripe_subscription_id:
                context['subscriptions'][subscription.id] = {}
                context['subscriptions'][subscription.id]['subscription'] = stripe.Subscription.retrieve(subscription.stripe_subscription_id,
                                                                       stripe_account=subscription.membership_package.stripe_acct_id)

                context['subscriptions'][subscription.id]['customer'] = stripe.Customer.retrieve(subscription.stripe_id,
                                                               stripe_account=subscription.membership_package.stripe_acct_id)
                context['subscriptions'][subscription.id]['payments'] = stripe.Charge.list(customer=subscription.stripe_id,
                                                               stripe_account=subscription.membership_package.stripe_acct_id)
        return context


@login_required(login_url="/accounts/login")
def update_user(request, pk):
    # where the user can update their own basic information
    if request.method == 'POST':
        # update user and get user object
        member = Member.objects.get(id=pk)
        member.user_account.first_name = request.POST.get('user-settings-first-name')
        member.user_account.last_name = request.POST.get('user-settings-last-name')
        member.user_account.email = request.POST.get('user-settings-email')
        # set users password
        if request.POST.get('user-settings-password') != "":
            member.user_account.set_password(request.POST.get('user-settings-password'))
        member.user_account.save()
        member.title = request.POST.get('user-settings-title')
        member.first_name = request.POST.get('user-settings-first-name')
        member.last_name = request.POST.get('user-settings-last-name')
        member.email = request.POST.get('user-settings-email')
        member.address_line_1 = request.POST.get('user-settings-address1')
        member.address_line_2 = request.POST.get('user-settings-address2')
        member.town = request.POST.get('user-settings-town')
        member.county = request.POST.get('user-settings-county')
        member.postcode = request.POST.get('user-settings-postcode')
        member.contact_number = request.POST.get('user-settings-phone')
        member.save()

        return HttpResponse(True)

    return HttpResponse(False)


@login_required(login_url="/accounts/login")
def validate_card(request, type, pk=0):
    # get strip secret key
    stripe.api_key = get_stripe_secret_key(request)

    if type == 'package':
        membership_package = MembershipPackage.objects.get(owner=request.user)
        stripe_id = membership_package.stripe_owner_id
        account_id = membership_package.stripe_acct_id
    else:
        subscription = MembershipSubscription.objects.get(id=pk)
        stripe_id = subscription.stripe_id
        account_id = subscription.membership_package.stripe_acct_id
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


@login_required(login_url='/accounts/login/')
def remove_member(request, title, pk):
    """
    Validate request.user is owner/admin
    cancel subscription
    delete user from stripe account
    delete member object

    :param request:
    :param title:
    :param id:
    :return:
    """
    try:
        membership_package = MembershipPackage.objects.filter(Q(owner=request.user) |
                                                              Q(admins=request.user),
                                                              organisation_name=title,
                                                              enabled=True).distinct()
        # sigh
        membership_package = membership_package[0]

    except MembershipPackage.DoesNotExist:
        # disallow access to page
        # return to previous page
        return redirect('membership_package', membership_package.organisation_name)

    member = Member.objects.get(id=pk)
    subscription = MembershipSubscription.objects.get(member=member, membership_package=membership_package)
    stripe.api_key = get_stripe_secret_key(request)

    # cancel subscription
    if subscription.stripe_subscription_id:
        stripe.Subscription.delete(subscription.stripe_subscription_id,
                                   stripe_account=membership_package.stripe_acct_id)

    # delete customer from stripe account
    if subscription.stripe_id:
        stripe.Customer.delete(subscription.stripe_id,
                               stripe_account=membership_package.stripe_acct_id)

    subscription.delete()

    return redirect('membership')

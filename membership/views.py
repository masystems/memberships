from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect, get_object_or_404, reverse
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q
from memberships.functions import *
from .models import MembershipPackage, Price, PaymentMethod, Member, Payment, MembershipSubscription, Equine
from .forms import MembershipPackageForm, MemberForm, PaymentForm, EquineForm
from json import dumps, loads, JSONDecodeError
import stripe
from re import match
from datetime import datetime
from dateutil.relativedelta import relativedelta
import csv
import xlwt


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


@login_required(login_url='/accounts/login/')
def manage_custom_fields(request, title):
    def get_field_type():
        if request.POST.get('field_type') in ("text_field", "Text"):
            return "text_field"
        elif request.POST.get('field_type') in ("text_area", "Text Area"):
            return "text_area"
        elif request.POST.get('field_type') in ("date", "Date"):
            return "date"
        elif request.POST.get('field_type') in ("bool", "Tick Box"):
            return "bool"
        else:
            # just in case
            return "text_field"

    # validate request user is owner or admin of org
    if not MembershipPackage.objects.filter(Q(owner=request.user) |
                                            Q(admins=request.user),
                                            organisation_name=title,
                                            enabled=True).exists():
        return redirect('dashboard')

    membership_package = MembershipPackage.objects.get(organisation_name=title)
    visible_value = True
    try:
        custom_fields = loads(membership_package.custom_fields)
    except JSONDecodeError:
        custom_fields = {}

    if request.method == "POST":
        # get visible var
        if 'visible' not in request.POST:
            visible_value = False

        # field name validation
        if request.POST.get('field_name') in ("", None) and request.POST.get('type') != "delete":
            return HttpResponse(dumps({'status': "fail",
                                       'message': "Field Name must not be blank"}),
                                content_type='application/json')

        if request.POST.get('type_id'):
            # edit
            if request.POST.get('type') == "delete":
                # remove field type from json
                custom_fields.pop(request.POST.get('type_id'), None)
                membership_package.custom_fields = dumps(custom_fields)
                membership_package.save()
                # remove field from subs
                subscriptions = MembershipSubscription.objects.filter(membership_package=membership_package)
                for sub in subscriptions.all():
                    custom_fields_updated = {}
                    if sub.custom_fields:
                        for key, val in loads(sub.custom_fields).items():
                            if key in custom_fields:
                                custom_fields_updated[key] = val

                    sub.custom_fields = dumps(custom_fields_updated)
                    sub.save()
                return HttpResponse(dumps({'status': "success",
                                           'message': "Field Deleted!"}), content_type='application/json')
            else:
                field_type = get_field_type()
                custom_fields[request.POST.get('type_id')] = {'id': request.POST.get('type_id'),
                                                              'field_name': request.POST.get('field_name'),
                                                              'field_type': field_type,
                                                              'help_text': request.POST.get('help_text'),
                                                              'visible': visible_value}
                membership_package.custom_fields = dumps(custom_fields)
                membership_package.save()

                # update sub objects
                subscriptions = MembershipSubscription.objects.filter(membership_package=membership_package)
                for sub in subscriptions.all():
                    try:
                        custom_fields = loads(sub.custom_fields)
                    except JSONDecodeError:
                        custom_fields = {}

                    custom_fields[request.POST.get('type_id')]['field_name'] = request.POST.get('field_name')
                    custom_fields[request.POST.get('type_id')]['field_type'] = field_type
                    custom_fields[request.POST.get('type_id')]['help_text'] = request.POST.get('help_text')
                    custom_fields[request.POST.get('type_id')]['visible'] = visible_value

                    sub.custom_fields = dumps(custom_fields)
                    sub.save()
                return HttpResponse(dumps({'status': "success",
                                           'message': "Field successfully updated"}), content_type='application/json')

        else:
            # new custom field
            # create unique key
            for suffix in range(0, len(custom_fields) + 2):
                if f'cf_{suffix}' not in custom_fields:
                    field_key = f'cf_{suffix}'
                    break

            field_type = get_field_type()
            custom_fields[field_key] = {'id': field_key,
                                        'field_name': request.POST.get('field_name'),
                                        'field_type': field_type,
                                        'help_text': request.POST.get('help_text'),
                                        'visible': request.POST.get('visible')}
            membership_package.custom_fields = dumps(custom_fields)
            membership_package.save()

            # update sub objects
            subscriptions = MembershipSubscription.objects.filter(membership_package=membership_package)

            for sub in subscriptions.all():
                try:
                    object_custom_fields = loads(sub.custom_fields)
                except JSONDecodeError:
                    object_custom_fields = {}

                field_type = get_field_type()
                object_custom_fields[field_key] = {'id': field_key,
                                                   'field_name': request.POST.get('field_name'),
                                                   'field_type': field_type,
                                                   'help_text': request.POST.get('help_text'),
                                                   'visible': request.POST.get('visible')}

                sub.custom_fields = dumps(object_custom_fields)
                sub.save()

            return HttpResponse(dumps({'status': "success",
                                       'message': "Custom field successfully added"}), content_type='application/json')

    else:
        return render(request, 'manage-custom-fields.html', {'membership_package': membership_package,
                                                             'custom_fields': custom_fields})


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


def export_members_detailed(request, title):
    if request.POST:
        membership_package = MembershipPackage.objects.get(organisation_name=title)
        date = datetime.now()
        stripe.api_key = get_stripe_secret_key(request)

        search = request.POST.get('search_param')
        if search == "":
            all_subscriptions = MembershipSubscription.objects.filter(membership_package=membership_package,
                                                                      price__isnull=False).distinct()
        else:
            all_subscriptions = MembershipSubscription.objects.filter(
                Q(member__user_account__first_name__icontains=search) |
                Q(member__user_account__last_name__icontains=search) |
                Q(member__user_account__email__icontains=search) |
                Q(membership_number__icontains=search) |
                Q(comments__icontains=search) |
                Q(custom_fields__icontains=search),
                membership_package=membership_package)
        if 'csv' in request.POST:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{membership_package}-Export-{date.strftime("%Y-%m-%d")}.csv"'

            writer = csv.writer(response, delimiter=",")
            headers = ['Member ID',
                       'Name',
                       'Email',
                       'Address',
                       'Contact',
                       'Membership Status',
                       'Payment Method',
                       'Billing Interval',
                       'Comments',
                       'Membership Start',
                       'Membership Expiry']
            # custom fields
            custom_fields = []
            custom_fields_raw = loads(membership_package.custom_fields)
            for key, field in custom_fields_raw.items():
                try:
                    custom_fields.append(field['field_name'])
                except KeyError:
                    custom_fields.append("")
            headers.extend(custom_fields)
            writer.writerow(headers)
            for subscription in all_subscriptions.all():
                try:
                    membership_type = subscription.price.nickname
                except AttributeError:
                    membership_type = ""
                try:
                    payment_type = subscription.payment_method.payment_name
                except AttributeError:
                    payment_type = ""
                if subscription.price:
                    billing_interval = subscription.price.interval.title()
                else:
                    billing_interval = ""

                membership_start_date = subscription.membership_start
                if subscription.stripe_subscription_id:
                    stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id,
                                                                       stripe_account=membership_package.stripe_acct_id)
                    membership_start_date = datetime.fromtimestamp(stripe_subscription.start_date).strftime(
                        "%d/%m/%Y<br/>%H:%M")

                # custom fields
                custom_fields = []
                custom_fields_raw = loads(subscription.custom_fields)
                for key, field in custom_fields_raw.items():
                    try:
                        custom_fields.append(field['field_value'])
                    except KeyError:
                        custom_fields.append("")

                inbuilt_items = [subscription.membership_number,
                                 subscription.member.user_account.get_full_name(),
                                 subscription.member.user_account.email,
                                 f"""{subscription.member.company}\n{subscription.member.address_line_1}\n{subscription.member.address_line_2}\n{subscription.member.company}\n{subscription.member.county}\n{subscription.member.postcode}""",
                                 subscription.member.contact_number,
                                 membership_type,
                                 payment_type,
                                 billing_interval,
                                 subscription.comments,
                                 f'{membership_start_date or ""}',
                                 f'{subscription.membership_expiry or ""}']
                # add custom fields to the mix
                inbuilt_items.extend(custom_fields)
                writer.writerow(inbuilt_items)
            return response


def update_membership_status(request, pk, status, title, page):
    member = Member.objects.get(id=pk)
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    subscription = member.subscription.get(member=member, membership_package=membership_package)

    subscription.active = status
    subscription.save()

    # redirect user depending on where they have come from
    return HttpResponseRedirect('/membership/' + page + '/' + membership_package.organisation_name)


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

        # generate report data
        total_stripe_subscriptions = stripe.Subscription.list(stripe_account=context['membership_package'].stripe_acct_id)
        context['stripe_members'] = 0
        for sub in total_stripe_subscriptions:
            if sub.plan.active:
                context['stripe_members'] += 1
        
        # url for donation page
        context['donation_url'] = f"{settings.HTTP_PROTOCOL}://{settings.SITE_NAME}/donation/?org-name={context['membership_package'].organisation_name}"

        # get active members with overdue subscriptions
        context['overdue_members'] = {}
        for member in context['members'].all()[:500]:
            sub = member.subscription.get(member=member, membership_package=context['membership_package'])
            if get_overdue_and_next(self.request, sub)['overdue'] and sub.active:
                context['overdue_members'][member] = get_overdue_and_next(self.request, sub)['next_payment_date']
        return context


@login_required(login_url='/accounts/login/')
def reports(request, title, report, file_type):
    # just do it for SHS for now
    title = 'Suffolk Horse Society'
    
    # validate request user is owner or admin of organisation
    if not MembershipPackage.objects.filter(Q(owner=request.user) |
                                            Q(admins=request.user),
                                            organisation_name=title,
                                            enabled=True).exists():
        return redirect('dashboard')
    
    file_type = 'xlsx'

    membership_package = MembershipPackage.objects.get(organisation_name=title)
    date = datetime.now()
    if file_type == 'xlsx':
        # generate the raffle report
        if report == 'raffle':
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{membership_package}-Export-{date.strftime("%Y-%m-%d")}.xls"'
            
            # creating workbook
            workbook = xlwt.Workbook(encoding='utf-8')

            # adding sheet
            worksheet = workbook.add_sheet("sheet1")

            # Sheet header, first row
            row_num = 0

            font_style = xlwt.XFStyle()
            # headers are bold
            font_style.font.bold = True

            # column header names
            # member_number, name, email etc
            columns = ['Title', 'First Name', 'Surname', 'Second Name', 'Membership Type', 'Company Name', 'Address 1', 'Address 2', 'Address 3', 'Address 4', 'Postcode', 'Country', 'Raffle Tickets']

            # write column headers in sheet
            for col_num in range(len(columns)):
                worksheet.write(row_num, col_num, columns[col_num], font_style)

            # Sheet body, remaining rows
            font_style = xlwt.XFStyle()

            # get rows
            subscriptions = MembershipSubscription.objects.filter(membership_package=membership_package)
            for subscription in subscriptions:
                # check they are active
                if subscription.active:
                    # get custom fields
                    mail = True
                    second_name = ''
                    raffle_tickets = 'Yes'
                    custom_fields = loads(subscription.custom_fields)

                    for key, field in custom_fields.items():
                        # do not mail
                        if field['field_name'] == 'Do not mail':
                            try:
                                # do not mail is true, so don't mail
                                if field['field_value']:
                                    mail = False
                                    break
                            # they haven't ever ticked the box, so mail
                            except KeyError:
                                pass
                        # second name
                        elif field['field_name'] == 'Second name':
                            try:
                                second_name = field['field_value']
                            except KeyError:
                                pass
                        # raffle tickets
                        elif field['field_name'] == 'No raffle tickets':
                            try:
                                # no raffle tickets is true, so no
                                if field['field_value']:
                                    raffle_tickets = 'No'
                            # they haven't ever ticked the box, so yes
                            except KeyError:
                                pass
                    
                    # try to get membership type
                    try:
                        membership_type = subscription.price.nickname
                    except AttributeError:
                        membership_type = ''
                    
                    # add subscription data to table if mail is True
                    if mail:
                        row_num = row_num + 1
                        # title
                        worksheet.write(row_num, 0, subscription.member.title, font_style)
                        # first name
                        worksheet.write(row_num, 1, subscription.member.user_account.first_name, font_style)
                        # surname
                        worksheet.write(row_num, 2, subscription.member.user_account.last_name, font_style)
                        # second name
                        worksheet.write(row_num, 3, second_name, font_style)
                        # membership type
                        worksheet.write(row_num, 4, membership_type, font_style)
                        # company name
                        worksheet.write(row_num, 5, subscription.member.company, font_style)
                        # address 1
                        worksheet.write(row_num, 6, subscription.member.address_line_1, font_style)
                        # address 2
                        worksheet.write(row_num, 7, subscription.member.address_line_2, font_style)
                        # address 3 (town)
                        worksheet.write(row_num, 8, subscription.member.town, font_style)
                        # address 4 (county)
                        worksheet.write(row_num, 9, subscription.member.county, font_style)
                        # postcode
                        worksheet.write(row_num, 10, subscription.member.postcode, font_style)
                        # country
                        worksheet.write(row_num, 11, subscription.member.country, font_style)
                        # raffle tickets
                        worksheet.write(row_num, 12, raffle_tickets, font_style)

            workbook.save(response)
            return response

        # generate the gift aid report
        elif report == 'gift_aid':
            response = HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{membership_package}-Export-{date.strftime("%Y-%m-%d")}.xls"'
            
            # creating workbook
            workbook = xlwt.Workbook(encoding='utf-8')

            # adding sheet
            worksheet = workbook.add_sheet("sheet1")

            # Sheet header, first row
            row_num = 0

            font_style = xlwt.XFStyle()
            # headers are bold
            font_style.font.bold = True

            # column header names
            # member_number, name, email etc
            columns = ['Title', 'First Name', 'Surname', 'Second Name', 'Membership Type', 'Company Name', 'Address 1', 'Address 2', 'Address 3', 'Address 4', 'Postcode', 'Country']

            # write column headers in sheet
            for col_num in range(len(columns)):
                worksheet.write(row_num, col_num, columns[col_num], font_style)

            # Sheet body, remaining rows
            font_style = xlwt.XFStyle()

            # get rows
            subscriptions = MembershipSubscription.objects.filter(membership_package=membership_package)
            for subscription in subscriptions:
                # check they are active
                if subscription.active:
                    # get custom fields
                    gift_aid = False
                    second_name = ''
                    custom_fields = loads(subscription.custom_fields)

                    for key, field in custom_fields.items():
                        # gift aid decision
                        if field['field_name'] == 'Gift aid decision':
                            try:
                                # gift aid is true
                                if field['field_value']:
                                    gift_aid = True
                                # gift aid is not true, don't generate report
                                else:
                                    break
                            # they haven't ever ticked the box, so don't generate report
                            except KeyError:
                                break
                        # second name
                        elif field['field_name'] == 'Second name':
                            try:
                                second_name = field['field_value']
                            except KeyError:
                                pass
                        # raffle tickets
                        elif field['field_name'] == 'No raffle tickets':
                            try:
                                # no raffle tickets is true, so no
                                if field['field_value']:
                                    raffle_tickets = 'No'
                            # they haven't ever ticked the box, so yes
                            except KeyError:
                                pass
                    
                    # try to get membership type
                    try:
                        membership_type = subscription.price.nickname
                    except AttributeError:
                        membership_type = ''
                    
                    # add subscription data to table if mail is True
                    if gift_aid:
                        row_num = row_num + 1
                        # title
                        worksheet.write(row_num, 0, subscription.member.title, font_style)
                        # first name
                        worksheet.write(row_num, 1, subscription.member.user_account.first_name, font_style)
                        # surname
                        worksheet.write(row_num, 2, subscription.member.user_account.last_name, font_style)
                        # second name
                        worksheet.write(row_num, 3, second_name, font_style)
                        # membership type
                        worksheet.write(row_num, 4, membership_type, font_style)
                        # company name
                        worksheet.write(row_num, 5, subscription.member.company, font_style)
                        # address 1
                        worksheet.write(row_num, 6, subscription.member.address_line_1, font_style)
                        # address 2
                        worksheet.write(row_num, 7, subscription.member.address_line_2, font_style)
                        # address 3 (town)
                        worksheet.write(row_num, 8, subscription.member.town, font_style)
                        # address 4 (county)
                        worksheet.write(row_num, 9, subscription.member.county, font_style)
                        # postcode
                        worksheet.write(row_num, 10, subscription.member.postcode, font_style)
                        # country
                        worksheet.write(row_num, 11, subscription.member.country, font_style)

            workbook.save(response)
            return response


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

    subscription = MembershipSubscription.objects.get(member=member, membership_package=membership_package)
    
    # variables used to construct the email
    temp_payment_method = subscription.payment_method
    outstanding_string = ""
    body = ""
    customised = False

    # if payment reminder email hasn't been sent, send default emails
    if membership_package.payment_reminder_email == '':
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
    # use custom payment reminder email
    else:
        body = membership_package.payment_reminder_email
        customised = True

        # add in the new lines
        body = body.replace('\n', '<br/>')
    
    send_email(f"Payment Reminder: {membership_package.organisation_name}", request.user.get_full_name(), body, send_to=member.user_account.email, customised=customised)

    return redirect('membership_package', membership_package.organisation_name)


@login_required(login_url='/accounts/login/')
def manage_payment_reminder(request, title):
    # validate request user is owner or admin of org
    if not MembershipPackage.objects.filter(Q(owner=request.user) |
                                        Q(admins=request.user),
                                        organisation_name=title,
                                        enabled=True).exists():
        return redirect('dashboard')

    membership_package = MembershipPackage.objects.get(organisation_name=title)
    
    if request.method == "GET":
        return render(request, 'manage_payment_reminder.html', {'membership_package': membership_package})
    else:
        membership_package.payment_reminder_email = request.POST.get('custom_email')
        membership_package.save()
        
        return HttpResponse(dumps({'status': "success",
                                           'message': "Email successfully updated"}), content_type='application/json')


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

        # get and sort custom fields titles
        custom_fields_raw = loads(self.context['membership_package'].custom_fields)
        self.context['custom_fields'] = []
        for key, field in custom_fields_raw.items():
            self.context['custom_fields'].append(field['field_name'])

        return self.context


@login_required(login_url='/accounts/login/')
def member_reg_form(request, title, pk):
    """
    user is admin/owner editing their own membership details
    user is admin/owner create a new member
    user is admin/owner editing an existing member
    user is creating a membership for themself
    user is editing their own membership
    :param request:
    :param title:
    :param pk:
    :return:
    """
    # get basic objects and validate if new membership
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    # setting user_form_fields to none in cases where it's not set
    user_form_fields = None
    try:
        member = Member.objects.get(id=pk)
        new_membership = False
    except Member.DoesNotExist:
        # must be a new membership
        new_membership = True

    # custom fields
    if not new_membership:
        # there is an existing membership
        try:
            subscription = MembershipSubscription.objects.get(membership_package=membership_package, member=member)
            try:
                # get custom fields
                custom_fields = loads(subscription.custom_fields)
            except JSONDecodeError:
                # failed to get subscription custom fields, save package custom fields to sub custom fields
                subscription.custom_fields = dumps(membership_package.custom_fields)
                custom_fields = loads(subscription.custom_fields)
        # subscription doesn't exist, but member does
        except MembershipSubscription.DoesNotExist:
            try:
                custom_fields = loads(membership_package.custom_fields)
            except JSONDecodeError:
                custom_fields = None
    # membership doesn't exist
    else:
        try:
            custom_fields = loads(membership_package.custom_fields)
        except JSONDecodeError:
            custom_fields = None

    # if user is not owner/admin, remove invisible custom fields
    custom_fields_displayed = custom_fields
    if custom_fields:
        if request.user != membership_package.owner and request.user not in membership_package.admins.all():
            # iterate through each custom field dictionary
            for key, custom_field in dict(custom_fields_displayed).items():
                # if field invisible
                if not custom_field['visible']:
                    # remove field
                    del (custom_fields_displayed[key])

    # initialise member_id so it can be accessed by code that handles POST request
    member_id = 0
    if request.method == "GET" and not new_membership:
        # check if user is the same person as the member
        if member.user_account == request.user:
            # user is admin/owner editing their own membership details
            # user is creating a membership for themself
            # user is editing their own membership
            member_id = member.id
            form = MemberForm(instance=member)
            user_form_fields = User.objects.get(id=member.user_account.id)
        else:
            # user is not member, validate user is admin/owner
            if request.user == membership_package.owner or request.user in membership_package.admins.all():
                # user is admin/owner editing an existing member
                member_id = pk
                form = MemberForm(instance=member)
                user_form_fields = User.objects.get(id=member.user_account.id)
            else:
                # user is not allowed to edit this member
                return redirect('dashboard')

    if request.method == "GET" and new_membership:
        # new user/membership
        # validate user is owner/admin
        if request.user == membership_package.owner or request.user in membership_package.admins.all():
            # user is admin/owner create a new member
            member_id = pk
            form = MemberForm()
        else:
            # user is not allowed to edit this member
            return redirect('dashboard')

    elif request.method == "POST":
        # admin/owner can add any new/existing user
        # admin/owner can edit any existing owner
        # user can edit only themselves
        form = MemberForm(request.POST)
        if form.is_valid():
            if pk == 0 and request.user == membership_package.owner or request.user in membership_package.admins.all():
                # new member
                # validate user not already a member of package
                try:
                    member = Member.objects.get(user_account=User.objects.get(email=form.cleaned_data['email']))
                    if MembershipSubscription.objects.filter(member=member).exists():
                        form.add_error('email', f"This email address is already in use.")
                except Member.DoesNotExist:
                    member = Member.objects.create(user_account=User.objects.get(email=form.cleaned_data['email']),
                                          title=form.cleaned_data['title'],
                                          company=form.cleaned_data['company'],
                                          address_line_1=form.cleaned_data['address_line_1'],
                                          address_line_2=form.cleaned_data['address_line_2'],
                                          town=form.cleaned_data['town'],
                                          county=form.cleaned_data['county'],
                                          country=form.cleaned_data['country'],
                                          postcode=form.cleaned_data['postcode'],
                                          contact_number=form.cleaned_data['contact_number'])
                    
                except User.DoesNotExist:
                    user = User.objects.create(first_name=form.cleaned_data['first_name'],
                                        last_name=form.cleaned_data['last_name'],
                                        email=form.cleaned_data['email'],
                                        username=generate_username(form.cleaned_data['first_name'],
                                                                   form.cleaned_data['last_name']))

                    member = Member.objects.create(user_account=User.objects.get(email=form.cleaned_data['email']),
                                          title=form.cleaned_data['title'],
                                          company=form.cleaned_data['company'],
                                          address_line_1=form.cleaned_data['address_line_1'],
                                          address_line_2=form.cleaned_data['address_line_2'],
                                          town=form.cleaned_data['town'],
                                          county=form.cleaned_data['county'],
                                          country=form.cleaned_data['country'],
                                          postcode=form.cleaned_data['postcode'],
                                          contact_number=form.cleaned_data['contact_number'])
                    
            elif pk != 0 and request.user == membership_package.owner or request.user in membership_package.admins.all():
                # edit member
                # validate email not already in use
                try:
                    # if email is in use, add an error to the form
                    if MembershipSubscription.objects.filter(member=Member.objects.get(user_account=User.objects.get(
                            email=form.cleaned_data['email']))).exclude(member=member).exists():
                        form.add_error('email',
                                       f"This email address is already in use.")
                    # email is in use for a different package, so it for the member
                    else:
                        member.user_account.email = form.cleaned_data['email']
                # email not in use, so save it for the member
                except User.DoesNotExist:
                    member.user_account.email = form.cleaned_data['email']
                finally:
                    member.user_account.first_name = form.cleaned_data['first_name']
                    member.user_account.last_name = form.cleaned_data['last_name']
                    # Member.objects.filter(pk=pk).update(title=form.cleaned_data['title'],
                    #                                     company=form.cleaned_data['company'],
                    #                                     address_line_1=form.cleaned_data['address_line_1'],
                    #                                     address_line_2=form.cleaned_data['address_line_2'],
                    #                                     town=form.cleaned_data['town'],
                    #                                     county=form.cleaned_data['county'],
                    #                                     country=form.cleaned_data['country'],
                    #                                     postcode=form.cleaned_data['postcode'],
                    #                                     contact_number=form.cleaned_data['contact_number']
                    #                                     )
                    member.title = form.cleaned_data['title']
                    member.company = form.cleaned_data['company']
                    member.address_line_1 = form.cleaned_data['address_line_1']
                    member.address_line_2 = form.cleaned_data['address_line_2']
                    member.town = form.cleaned_data['town']
                    member.county = form.cleaned_data['county']
                    member.country = form.cleaned_data['country']
                    member.postcode = form.cleaned_data['postcode']
                    member.contact_number = form.cleaned_data['contact_number']
                    member.save()
                    member.user_account.save()
                    
            else:
                # new membership request but user is not admin/owner tut tut
                redirect('dashboard')

            try:
                subscription = MembershipSubscription.objects.get(member=member, membership_package=membership_package)
            except MembershipSubscription.DoesNotExist:
                # check there are existing subscriptions
                if MembershipSubscription.objects.exists():
                    # get latest membership number
                    latest_valid_mem_num = MembershipSubscription.objects.last().membership_number
                    # check latest membership number is valid
                    if latest_valid_mem_num == None or latest_valid_mem_num == '':
                        i = 1
                        # check we haven't gone past the end of the subscriptions
                        if i < MembershipSubscription.objects.all().count():
                            # get membership number before last before last sub
                            latest_valid_mem_num = MembershipSubscription.objects.all().reverse()[i].membership_number
                            # go through subscription's membership numbers in reverse until we find a valid one
                            while latest_valid_mem_num == None or latest_valid_mem_num == '':
                                i += 1
                                # check we haven't gone past the end of the subscriptions
                                if i < MembershipSubscription.objects.all().count():
                                    latest_valid_mem_num = MembershipSubscription.objects.all().reverse()[
                                        i].membership_number
                                # no valid membership numbers, so set variable to zero
                                else:
                                    latest_valid_mem_num = 0
                        # no valid membership numbers, so set variable to zero
                        else:
                            latest_valid_mem_num = 0
                    membership_number = int(latest_valid_mem_num) + 1
                    # check this membership number isn't taken
                    # if it is taken, increment by 1 then check that one
                    while True:
                        if MembershipSubscription.objects.filter(membership_number=str(membership_number)).exists():
                            membership_number += 1
                        else:
                            break
                # there are no existing subscriptions, so this is the first
                else:
                    membership_number = 1
                # use the membership number to make a new subscription
                subscription = MembershipSubscription.objects.create(member=member,
                                                                     membership_package=membership_package,
                                                                     membership_number=membership_number)

            subscription.membership_package = membership_package
            subscription.member = member

            # create/ update stripe customer
            stripe.api_key = get_stripe_secret_key(request)
            if subscription.stripe_id:
                # stripe user already exists
                stripe_customer = stripe.Customer.modify(
                    subscription.stripe_id,
                    name=member.user_account.get_full_name(),
                    email=member.user_account.email,
                    stripe_account=membership_package.stripe_acct_id
                )
            else:
                stripe_customer = stripe.Customer.create(
                    name=member.user_account.get_full_name(),
                    email=member.user_account.email,
                    stripe_account=membership_package.stripe_acct_id
                )

            subscription.stripe_id = stripe_customer.id

            # save custom fields
            if custom_fields:
                for id, field in custom_fields.items():
                    custom_fields[id]['field_value'] = request.POST.get(custom_fields[id]['field_name'])
                subscription.custom_fields = dumps(custom_fields)
            subscription.save()

            # direct user to correct next location
            # if user is owner/admin...
            if not form.errors:
                if request.user == membership_package.owner or request.user in membership_package.admins.all():
                    # save and continue
                    if request.POST.get('continue') == '':
                        return redirect(
                            f"member_payment", membership_package.organisation_name, member.id)
                    # save and exit to org page
                    elif request.POST.get('exit') == '':
                        return redirect('membership_package', membership_package.organisation_name)
                    # just in case, continue
                    else:
                        return redirect(
                            f"member_payment", membership_package.organisation_name, member.id)
                # user is a member who has clicked Save, so continue
                else:
                    return redirect(
                        f"member_payment", membership_package.organisation_name, member.id)

        else:
            # form not valid
            pass
    # check there is a membership type which is active
    is_price_active = False
    prices = None
    try:
        prices = Price.objects.filter(membership_package=membership_package)
    except Price.DoesNotExist:
        pass
    for price in prices:
        if price.active:
            is_price_active = True
            break
    # check there is a membership type which is both active and visible
    is_price_active_visible = False
    for price in prices:
        if price.active and price.visible:
            is_price_active_visible = True
            break
    # check stripe has been set up
    stripe.api_key = get_stripe_secret_key(request)
    is_stripe = False
    if membership_package.stripe_acct_id:
        try:
            stripe.Account.create_login_link(membership_package.stripe_acct_id)
            is_stripe = True
        except stripe.error.InvalidRequestError:
            # stripe account created but not setup
            pass

    return render(request, 'member_form.html', {'user_form_fields': user_form_fields,
                                                'form': form,
                                                'membership_package': membership_package,
                                                'is_price_active': is_price_active,
                                                'is_price_active_visible': is_price_active_visible,
                                                'is_stripe': is_stripe,
                                                'member_id': member_id,
                                                'custom_fields': custom_fields_displayed})


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

        result = validate_card(request, 'member', subscription)
        if result['result'] == 'fail':
            return HttpResponse(dumps(result))

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

        invoice = stripe.Invoice.list(customer=subscription.stripe_id, subscription=subscription_details.id,
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
        subscription = member.subscription.get(member=member, membership_package=package)
        price = Price.objects.get(stripe_price_id=request.POST.get('membership_type'))
        if request.POST.get('payment_method') != 'Card Payment':
            MembershipSubscription.objects.filter(member=member, membership_package=package).update(price=price, active=True,
                                                                                                    payment_method=PaymentMethod.objects.get(payment_name=request.POST.get('payment_method'),
                                                                                                                                             membership_package=package))

            stripe.api_key = get_stripe_secret_key(request)

            # cancel stripe subscription
            if subscription.stripe_subscription_id:
                stripe.Subscription.delete(subscription.stripe_subscription_id,
                                        stripe_account=package.stripe_acct_id)
                subscription.stripe_subscription_id = ''
                subscription.save()
                
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
            # validate card payment != £0.00
            if price.amount == "0":
                return HttpResponse(dumps({'status': "fail",
                                           'message': f'You cannot select Card Payment with {price.nickname}'}), content_type='application/json')
            MembershipSubscription.objects.filter(member=member, membership_package=package).update(
                price=price, payment_method=None)

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
            # if it's a stripe customer
            if subscription.stripe_id:
                context['subscriptions'][subscription.id] = {}
                context['subscriptions'][subscription.id]['customer'] = stripe.Customer.retrieve(subscription.stripe_id,
                                                               stripe_account=subscription.membership_package.stripe_acct_id)
                context['subscriptions'][subscription.id]['payments'] = stripe.Charge.list(customer=subscription.stripe_id,
                                                               stripe_account=subscription.membership_package.stripe_acct_id)
                # if it's a stripe subscription
                if subscription.stripe_subscription_id:
                    context['subscriptions'][subscription.id]['subscription'] = stripe.Subscription.retrieve(subscription.stripe_subscription_id,
                                                                        stripe_account=subscription.membership_package.stripe_acct_id)

        return context


@login_required(login_url='/accounts/login/')
def edit_sub_comment(request, id):
    if request.method == "GET":
        try:
            comments = MembershipSubscription.objects.get(id=id).comments
        except MembershipSubscription.DoesNotExist:
            return HttpResponse(dumps({'status': "fail",
                                       'message': "Subscription does not exist"}))

        return HttpResponse(dumps({'status': "success",
                                   'message': None,
                                   'comment': comments}))

    elif request.method == "POST":
        try:
            sub = MembershipSubscription.objects.get(id=id)
        except MembershipSubscription.DoesNotExist:
            return HttpResponse(dumps({'status': "fail",
                                       'message': "Subscription does not exist"}))
        sub.comments = request.POST.get('comment')
        sub.save()
        return HttpResponse(dumps({'status': "success",
                                   'message': "Comments updated"}))


def get_overdue_and_next(request, subscription):
    # get date of last payment in our DB, if it exists
    last_db_payment = Payment.objects.filter(subscription=subscription).order_by('-created').first()
    last_db_payment_date = None
    if last_db_payment:
        last_db_payment_date = last_db_payment.created

    # if it's a stripe subscription, get date of last stripe payment
    last_stripe_payment_date = None
    if subscription.stripe_id:
        stripe.api_key = get_stripe_secret_key(request)
        # get the last stripe payment
        last_stripe_payment = stripe.Charge.list(customer=subscription.stripe_id, stripe_account=subscription.membership_package.stripe_acct_id, limit=1)['data']
        # if any stripe payments exist, get the date of the last one
        if len(last_stripe_payment) > 0:
            last_stripe_payment_date = datetime.fromtimestamp(last_stripe_payment[0]['created']).date()

    # get last payment date from stripe payments and db payments
    last_payment_date = None
    if last_db_payment_date and not last_stripe_payment_date:
        last_payment_date = last_db_payment_date
    elif not last_db_payment_date and last_stripe_payment_date:
        last_payment_date = last_stripe_payment_date
    # neither exist, so last payment remins None
    elif not last_db_payment_date and not last_stripe_payment_date:
        pass
    elif last_db_payment_date and last_stripe_payment_date:
        # last db payment is after last stripe payment
        if last_db_payment_date > last_stripe_payment_date:
            last_payment_date = last_db_payment_date
        # last db payment is before last stripe payment
        elif last_db_payment_date < last_stripe_payment_date:
            last_payment_date = last_stripe_payment_date
        # they must be equal, so it doesn't matter which is used
        else:
            last_payment_date = last_db_payment_date
        
    # get date of next payment due, if last date exists
    next_payment_date = None
    # their subscription is free
    if float(subscription.price.amount) == 0:
        pass
    elif last_payment_date:
        if subscription.price.interval == 'monthly':
            next_payment_date = last_payment_date + relativedelta(months=1)
        # must be yearly
        else:
            next_payment_date = last_payment_date + relativedelta(years=1)
    # set next payment to sub start date
    else:
        next_payment_date = subscription.membership_start
    
    # work out if they are overdue
    overdue = False
    # their subscription is free
    if float(subscription.price.amount) == 0:
        pass
    # if they have never paid, they are overdue
    elif not last_payment_date:
        overdue = True
    # if next payment due is in the past
    elif next_payment_date < datetime.now().date():
        overdue = True

    return {
        'next_payment_date': next_payment_date,
        'overdue': overdue
    }


@login_required(login_url='/accounts/login/')
def delete_payment(request, title, pk, payment_id):
    # validate request user is owner or admin of org
    if not MembershipPackage.objects.filter(Q(owner=request.user) |
                                        Q(admins=request.user),
                                        organisation_name=title,
                                        enabled=True).exists():
        return redirect('dashboard')
    
    try:
        payment = Payment.objects.get(id=payment_id)
        payment.delete()
    except Payment.DoesNotExist:
        pass
    
    return redirect('member_payments', title, pk)


@login_required(login_url='/accounts/login/')
def payments_detailed(request, title):
    return render(request, 'payments_detailed.html', {'membership_package': MembershipPackage.objects.get(organisation_name=title)})


@login_required(login_url='/accounts/login/')
def member_payments(request, title, pk):
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    member = Member.objects.get(id=pk)
    subscription = member.subscription.get(member=member, membership_package=membership_package)

    # find out whether the member is overdue, and date of next payment
    overdue_and_next = get_overdue_and_next(request, subscription)
    next_payment_date = overdue_and_next['next_payment_date']
    overdue = overdue_and_next['overdue']
    
    return render(request, 'member_payments.html', {'membership_package': membership_package,
                                                    'member': member,
                                                    'subscription': subscription,
                                                    'next_payment_date': next_payment_date,
                                                    'overdue': overdue})


def member_payment_form(request, title, pk):
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    member = Member.objects.get(id=pk)
    subscription = MembershipSubscription.objects.get(membership_package=membership_package, member=member)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = PaymentForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # check there are existing Payment objects
            if Payment.objects.exists():
                # get latest payment number
                latest_valid_pay_num = Payment.objects.last().payment_number
                # check whether latest payment number is valid
                if latest_valid_pay_num == None or latest_valid_pay_num == '':
                    i = 1
                    # check we haven't gone past the end of the payments
                    if i < Payment.objects.all().count():
                        # get payment number before last
                        latest_valid_pay_num = Payment.objects.all().reverse()[i].payment_number
                        # go through Payment's payment numbers in reverse until we find a valid one
                        while latest_valid_pay_num == None or latest_valid_pay_num == '':
                            i += 1
                            # check we haven't gone past the end of the payments
                            if i < Payment.objects.all().count():
                                latest_valid_pay_num = Payment.objects.all().reverse()[i].payment_number
                            # no valid payment numbers, so set variable to zero
                            else:
                                latest_valid_pay_num = 0
                    # no valid payment numbers, so set variable to zero
                    else:
                        latest_valid_pay_num = 0
                payment_number = int(latest_valid_pay_num) + 1
                # check this payment number isn't taken
                # if it is taken, increment by 1 then check that one
                while True:
                    if Payment.objects.filter(payment_number=str(payment_number)).exists():
                        payment_number += 1
                    else:
                        break
            # there are no existing Payment objects, so set payment_number to 1
            else:
                payment_number = 1

            payment = form.save(commit=False)
            payment.subscription = subscription
            # get next payment number
            payment.payment_number = payment_number

            # if payment.amount not set, set it to subscription amount
            if payment.amount == '':
                payment.amount = subscription.price.amount
            # if it has been set, convert it to pennies
            else:
                try:
                    payment.amount = int(float(payment.amount) * 100)
                except ValueError:
                    form.add_error('amount', f"Please enter a valid amount.")
                    return render(request, 'payment_form.html', {'form': form,
                                                 'membership_package': membership_package,
                                                 'member': member})

            payment.save()

            return redirect('member_payments', membership_package.organisation_name, member.id)
    else:
        form = PaymentForm()

    return render(request, 'payment_form.html', {'form': form,
                                                 'membership_package': membership_package,
                                                 'member': member})


def member_payment_form_edit(request, title, pk, payment_id):
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    member = Member.objects.get(id=pk)
    payment = Payment.objects.get(id=payment_id)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = PaymentForm(request.POST, instance=payment)
        # check whether it's valid:
        if form.is_valid():
            form.save()
            return redirect('member_payments', membership_package.organisation_name, member.id)
    else:
        form = PaymentForm(instance=payment)

    return render(request, 'payment_form_edit.html', {'form': form,
                                                      'membership_package': membership_package,
                                                      'member': member,
                                                      'payment': payment,
                                                      'next_page': request.POST.get('next', '')})


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
        member.company = request.POST.get('user-settings-company')
        member.save()

        return HttpResponse(True)

    return HttpResponse(False)


@login_required(login_url="/accounts/login")
def validate_card(request, type, subscription=None):
    # get strip secret key
    stripe.api_key = get_stripe_secret_key(request)

    if type == 'package':
        membership_package = MembershipPackage.objects.get(owner=request.user)
        stripe_id = membership_package.stripe_owner_id
        account_id = membership_package.stripe_acct_id
    else:
        stripe_id = subscription.stripe_id
        account_id = subscription.membership_package.stripe_acct_id
    # add payment token to user
    if not stripe_id:
        return {'result': 'fail',
                'feedback': "There has been a problem with this Stripe payment, you have not been charged, please try again. If this problem persists, email contact@masys.co.uk"}
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

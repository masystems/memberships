from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from memberships.functions import *
from .models import MembershipPackage, Price, PaymentMethod, Member, Payment, MembershipSubscription
from .forms import MembershipPackageForm, MemberForm, PaymentForm, EquineForm
from json import dumps, loads, JSONDecodeError
import stripe
from datetime import datetime


def get_members_detailed(request, title):
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    start = int(request.POST.get('start', 0))
    end = int(request.POST.get('length', 20))
    search = request.POST.get('search[value]', "")
    sort_by = request.POST.get(f'columns[{request.POST.get("order[0][column]")}][data]')
    stripe.api_key = get_stripe_secret_key(request)

    # desc or asc
    if request.POST.get('order[0][dir]') == 'asc':
        direction = ""
    else:
        direction = "-"
    # sort map
    if sort_by == "id":
        sort_by_col = f"{direction}membership_number"
    elif sort_by == "name":
        sort_by_col = f"{direction}member__user_account__first_name"
    elif sort_by == "email":
        sort_by_col = f"{direction}member__user_account__email"
    elif sort_by == "address":
        sort_by_col = f"{direction}member__address_line_1"
    elif sort_by == "contact":
        sort_by_col = f"{direction}member__contact_number"
    elif sort_by == "membership_type":
        sort_by_col = f"{direction}price"
    elif sort_by == "payment_method":
        sort_by_col = f"{direction}payment_method__payment_name"
    elif sort_by == "billing_interval":
        sort_by_col = f"{direction}price__interval"
    elif sort_by == "comments":
        sort_by_col = f"{direction}comments"
    elif sort_by == "membership_start":
        sort_by_col = f"{direction}membership_start"
    elif sort_by == "membership_expiry":
        sort_by_col = f"{direction}membership_expiry"
    else:
        sort_by_col = f"{direction}membership_number"

    members = []
    if search == "":
        all_subscriptions = MembershipSubscription.objects.filter(membership_package=membership_package,
                                                                  price__isnull=False).order_by(sort_by_col).distinct()[
                            start:start + end]
    else:
        all_subscriptions = MembershipSubscription.objects.filter(
            Q(member__user_account__first_name__icontains=search) |
            Q(member__user_account__last_name__icontains=search) |
            Q(member__user_account__email__icontains=search) |
            Q(membership_number__icontains=search) |
            Q(comments__icontains=search) |
            Q(custom_fields__icontains=search),
            membership_package=membership_package).order_by(sort_by_col).distinct()[start:start + end]
    if search == "":
        total_members = MembershipSubscription.objects.filter(membership_package=membership_package).distinct().count()
    else:
        total_members = MembershipSubscription.objects.filter(Q(member__user_account__first_name__icontains=search) |
                                                              Q(member__user_account__last_name__icontains=search) |
                                                              Q(member__user_account__email__icontains=search) |
                                                              Q(membership_number__icontains=search) |
                                                              Q(comments__icontains=search) |
                                                              Q(custom_fields__icontains=search),
                                                              membership_package=membership_package).order_by(
            sort_by_col).count()

    if all_subscriptions.count() > 0:
        for subscription in all_subscriptions.all():
            # get membership type
            try:
                membership_type = f"""<span class="badge py-1 badge-info">{subscription.price.nickname}</span>"""

                membership_status = f"""<div class="mb-4">
                                        <input type="checkbox" value="{subscription.member.id}" class="membership-status" 
                                        data-on-color="success" 
                                        data-off-color="danger" data-on-text="Active"
                                        data-off-text="Inactive"
                                        data-size="mini">
                                    </div>
                                    """

                if subscription.active:
                    membership_status = f"""<div class="mb-4">
                                                <input type="checkbox" value="{subscription.member.id}" 
                                                class="membership-status" data-on-color="success" 
                                                data-off-color="danger" data-on-text="Active" 
                                                data-off-text="Inactive"
                                                data-size="mini" checked>
                                            </div>
                                            """
            except AttributeError:
                membership_type = f"""<span class="badge py-1 badge-danger">No Membership Type</span>"""
                membership_status = f"""<span class="badge py-1 badge-danger">No Membership</span>"""

            if subscription.payment_method:
                payment_method = subscription.payment_method.payment_name
            else:
                payment_method = "Card Payment"

            if subscription.price:
                billing_interval = subscription.price.interval.title()
            else:
                billing_interval = ""

            # buttons!
            if subscription.payment_method or subscription.stripe_subscription_id:
                pass
                card_button = f"""<a href="{reverse('member_payment', kwargs={'title': membership_package.organisation_name,
                                                                              'pk': subscription.member.id})}" class="dropdown-item">
                                        <i class="fad fa-credit-card-front text-success mr-2"></i>Payment Page
                                </a>"""
            else:
                card_button = f"""<a href="{reverse('member_payment', kwargs={'title': membership_package.organisation_name,
                                                                              'pk': subscription.member.id})}" class="dropdown-item">
                                        <i class="fad fa-credit-card-front text-danger mr-2"></i>Payment Page
                                </a>"""
            member_payments_button = f"""<a href="{reverse('member_payments', kwargs={'title': membership_package.organisation_name,
                                                                                      'pk': subscription.member.id})}" class="dropdown-item"><i class="fad fa-money-check-edit-alt text-info mr-2"></i>Member Payments</a>"""
            edit_member_button = f"""<a href="{reverse('member_form', kwargs={'title': membership_package.organisation_name,
                                                                              'pk': subscription.member.id})}" class="dropdown-item"><i class="fad fa-user-edit text-info mr-2"></i>Edit Member</a>"""
            reset_password_button = f"""<a href="javascript:resetMemberPwd('{subscription.member.user_account.email}');" value="{subscription.member.user_account.email}" class="dropdown-item"><i class="fad fa-key text-success mr-2"></i>Reset Password</a>"""
            payment_reminder_button = f"""<a href="{reverse('payment_reminder', kwargs={'title': membership_package.organisation_name,
                                                                                        'pk': subscription.member.id})}" class="dropdown-item"><i class="fad fa-envelope-open-dollar mr-2"></i>Payment Reminder</a>"""
            remove_member_button = f"""<a href="javascript:removeMember({subscription.member.id});" value="{subscription.member.id}" class="dropdown-item"><i class="fad fa-user-slash text-danger mr-2"></i>Remove Member</a>"""

            # create a string for address to avoid including extra line breaks
            address_string = ""
            if subscription.member.company != '':
                address_string += f'{subscription.member.company}<br/>'
            if subscription.member.address_line_1 != '':
                address_string += f'{subscription.member.address_line_1}<br/>'
            if subscription.member.address_line_2 != '':
                address_string += f'{subscription.member.address_line_2}<br/>'
            if subscription.member.town != '':
                address_string += f'{subscription.member.town}<br/>'
            if subscription.member.county != '':
                address_string += f'{subscription.member.county}<br/>'
            if subscription.member.postcode != '':
                address_string += f'{subscription.member.postcode}<br/>'
            # if all of the above values are empty, display NULL to user instead of an empty box
            if address_string == "":
                address_string = 'NULL'

            # set start date based on whether it is a stripe subscription
            membership_start_date = subscription.membership_start
            if subscription.stripe_subscription_id:
                stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id, stripe_account=membership_package.stripe_acct_id)
                membership_start_date = datetime.fromtimestamp(stripe_subscription.start_date).strftime("%d/%m/%Y<br/>%H:%M")

            # # set member id, name, email, mambership_type and buttons
            row = {'id': subscription.membership_number,
                'name': f"""<a href="{reverse('member_profile', kwargs={'pk': subscription.member.id})}"><button class="btn waves-effect waves-light btn-rounded btn-sm btn-success">{subscription.member.user_account.get_full_name()}</button></a>""",
                'email': subscription.member.user_account.email,
                'address': address_string,
                'contact': f'{subscription.member.contact_number or "NULL"}',
                'membership_type': membership_type,
                'membership_status': membership_status,
                'payment_method': payment_method,
                'billing_interval': billing_interval,
                'comments': f"""{subscription.comments}<a href="javascript:editComment('{subscription.id}');"><i class="fad fa-edit text-success ml-2"></i></a>""",
                'membership_start': f'{membership_start_date or ""}',
                'membership_expiry': f'{subscription.membership_expiry  or ""}',
                'action': f"""<div class="btn-group">
                                    <button type="button" class="btn btn-success dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                        Administer
                                    </button>
                                    <div class="dropdown-menu">
                                        {card_button}
                                        {member_payments_button}
                                        {edit_member_button}
                                        {reset_password_button}
                                        {payment_reminder_button}
                                        {remove_member_button}
                                    </div>
                                </div>"""}

            # custom fields
            try:
                custom_fields = loads(subscription.custom_fields)
            except JSONDecodeError:
                custom_fields = loads(membership_package.custom_fields)

            for key, field in custom_fields.items():
                try:
                    value = field['field_value']

                    # if tickbox has been ticked in the past, ...
                    # ... set it indicating whether it is ticked now
                    if field['field_type'] == 'bool':
                        if field['field_value'] == 'on':
                            value = '<i class="fad fa-check text-success text-center"></i>'
                        else:
                            value = '<i class="fad fa-times"></i>'
                except KeyError:
                    value = ""

                    # if tick box has never been ticked, show times icon
                    if field['field_type'] == 'bool':
                        value = '<i class="fad fa-times"></i>'

                row.update({field['field_name']: value})

            # append all data to the list
            members.append(row)
        complete_data = {
            "draw": 0,
            "recordsTotal": all_subscriptions.count(),
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


def get_members(request, title):
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    start = int(request.GET.get('start', 0))
    end = int(request.GET.get('length', 20))
    search = request.GET.get('search[value]', "")
    sort_by = request.GET.get(f'columns[{request.GET.get("order[0][column]")}][data]')
    # desc or asc
    if request.GET.get('order[0][dir]') == 'asc':
        direction = ""
    else:
        direction = "-"
    # sort map
    if sort_by == "id":
        sort_by_col = f"{direction}membership_number"
    elif sort_by == "name":
        sort_by_col = f"{direction}member__user_account__first_name"
    elif sort_by == "email":
        sort_by_col = f"{direction}member__user_account__email"
    elif sort_by == "comments":
        sort_by_col = f"{direction}comments"
    elif sort_by == "membership_type":
        sort_by_col = f"{direction}price"
    else:
        # this will result in the a page error...
        sort_by_col = f"{direction}membership_number"

    members = []
    if search == "":
        all_subscriptions = MembershipSubscription.objects.filter(membership_package=membership_package, price__isnull=False).order_by(sort_by_col).distinct()[start:start+end]
    else:
        all_subscriptions = MembershipSubscription.objects.filter(Q(member__user_account__first_name__icontains=search) |
                                            Q(member__user_account__last_name__icontains=search) |
                                            Q(member__user_account__email__icontains=search) |
                                            Q(membership_number__icontains=search) |
                                            Q(comments__icontains=search),
                                            membership_package=membership_package).order_by(sort_by_col)[start:start + end]
    if search == "":
        total_members = MembershipSubscription.objects.filter(membership_package=membership_package).distinct().count()
    else:
        total_members = MembershipSubscription.objects.filter(Q(member__user_account__first_name__icontains=search) |
                                            Q(member__user_account__last_name__icontains=search) |
                                            Q(member__user_account__email__icontains=search) |
                                            Q(membership_number__icontains=search) |
                                            Q(comments__icontains=search),
                                            membership_package=membership_package).order_by(sort_by_col).count()

    if all_subscriptions.count() > 0:
        for subscription in all_subscriptions.all():
            # get membership type
            try:
                membership_type = f"""<span class="badge py-1 badge-info">{subscription.price.nickname}</span>"""

                membership_status = f"""<div class="mb-4">
                                        <input type="checkbox" value="{ subscription.member.id }" class="membership-status" 
                                        data-on-color="success" 
                                        data-off-color="danger" data-on-text="Active"
                                        data-off-text="Inactive"
                                        data-size="mini">
                                    </div>
                                    """

                if subscription.active:
                    membership_status = f"""<div class="mb-4">
                                                <input type="checkbox" value="{ subscription.member.id }" 
                                                class="membership-status" data-on-color="success" 
                                                data-off-color="none" data-on-text="Active" 
                                                data-off-text="Inactive"
                                                data-size="mini" checked>
                                            </div>
                                            """
            except AttributeError:
                membership_type = f"""<span class="badge py-1 badge-danger">No Membership Type</span>"""
                membership_status = f"""<span class="badge py-1 badge-danger">No Membership</span>"""

            # buttons!
            if subscription.payment_method or subscription.stripe_subscription_id:
                pass
                card_button = f"""<a href="{reverse('member_payment', kwargs={'title': membership_package.organisation_name,
                                                'pk': subscription.member.id})}" class="dropdown-item">
                                        <i class="fad fa-credit-card-front text-success mr-2"></i>Payment Page
                                </a>"""
            else:
                card_button = f"""<a href="{reverse('member_payment', kwargs={'title': membership_package.organisation_name,
                                                'pk': subscription.member.id})}" class="dropdown-item">
                                        <i class="fad fa-credit-card-front text-danger mr-2"></i>Payment Page
                                </a>"""
            member_payments_button = f"""<a href="{reverse('member_payments', kwargs={'title': membership_package.organisation_name,
                                                                            'pk': subscription.member.id})}" class="dropdown-item"><i class="fad fa-money-check-edit-alt text-info mr-2"></i>Member Payments</a>"""
            edit_member_button = f"""<a href="{reverse('member_form', kwargs={'title': membership_package.organisation_name,
                                                                            'pk': subscription.member.id})}" class="dropdown-item"><i class="fad fa-user-edit text-info mr-2"></i>Edit Member</a>"""
            reset_password_button = f"""<a href="javascript:resetMemberPwd('{ subscription.member.user_account.email }');" value="{ subscription.member.user_account.email }" class="dropdown-item"><i class="fad fa-key text-success mr-2"></i>Reset Password</a>"""
            payment_reminder_button = f"""<a href="{reverse('payment_reminder', kwargs={'title': membership_package.organisation_name,
                                                                                        'pk': subscription.member.id})}" class="dropdown-item"><i class="fad fa-envelope-open-dollar mr-2"></i>Payment Reminder</a>"""
            remove_member_button = f"""<a href="javascript:removeMember({ subscription.member.id });" value="{ subscription.member.id }" class="dropdown-item"><i class="fad fa-user-slash text-danger mr-2"></i>Remove Member</a>"""

            # # set member id, name, email, mambership_type and buttons
            members.append({'id': subscription.membership_number,
                            'name': f"""<a href="{reverse('member_profile', kwargs={'pk': subscription.member.id})}"><button class="btn waves-effect waves-light btn-rounded btn-sm btn-success">{subscription.member.user_account.get_full_name()}</button></a>""",
                            'email': f"{subscription.member.user_account.email}",
                            'comments': f"""{subscription.comments}<a href="javascript:editComment('{subscription.id}');"><i class="fad fa-edit text-success ml-2"></i></a>""",
                            'membership_type': membership_type,
                            'membership_status': membership_status,
                            'action': f"""<div class="btn-group dropleft">
                                                <button type="button" class="btn btn-success dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                                    Administer
                                                </button>
                                                <ul class="dropdown-menu" role="menu">
                                                    <li>{card_button}</li>
                                                    <li>{member_payments_button}</li>
                                                    <li>{edit_member_button}</li>
                                                    <li>{reset_password_button}</li>
                                                    <li>{payment_reminder_button}</li>
                                                    <li>{remove_member_button}</li>
                                                </ul>
                                            </div>"""})

        complete_data = {
          "draw": 0,
          "recordsTotal": all_subscriptions.count(),
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


@login_required(login_url='/accounts/login/')
def get_all_member_payments(request, title):
    membership_package = MembershipPackage.objects.get(organisation_name=title)

    start = int(request.POST.get('start', 0))
    end = int(request.POST.get('length', 20))
    search = request.POST.get('search[value]', "")
    sort_by = request.POST.get(f'columns[{request.POST.get("order[0][column]")}][data]')

    # desc or asc
    if request.POST.get('order[0][dir]') == 'asc':
        direction = ""
    else:
        direction = "-"
    # sort map
    if sort_by == "payment_id":
        sort_by_col = f"{direction}payment_number"
    elif sort_by == "name":
        sort_by_col = f"{direction}subscription__member__user_account__first_name"
    elif sort_by == "membership_id":
        sort_by_col = f"{direction}subscription__member__membership_number"
    elif sort_by == "method":
        sort_by_col = f"{direction}payment_method"
    elif sort_by == "type":
        sort_by_col = f"{direction}type"
    elif sort_by == "amount":
        sort_by_col = f"{direction}amount"
    elif sort_by == "comments":
        sort_by_col = f"{direction}comments"
    elif sort_by == "created":
        sort_by_col = f"{direction}created"
    elif sort_by == "gift_aid":
        sort_by_col = f"{direction}gift_aid"
    elif sort_by == "gift_aid_percentage":
        sort_by_col = f"{direction}gift_aid_percentage"
    else:
        sort_by_col = f"{direction}created"

    payments = []
    if search == "":
        all_payments = Payment.objects.filter(subscription__membership_package=membership_package).order_by(sort_by_col)[start:start + end]
    else:
        all_payments = Payment.objects.filter(Q(payment_method__payment_name__icontains=search) |
                                              Q(payment_number__icontains=search) |
                                              Q(type__icontains=search) |
                                              Q(comments__icontains=search) |
                                              Q(created__icontains=search) |
                                              Q(gift_aid_percentage__icontains=search) |
                                              Q(amount__icontains=search),
                                              subscription__membership_package=membership_package).distinct().order_by(sort_by_col)[start:start + end]
    # get stripe payments
    total_payments = Payment.objects.filter(subscription__membership_package=membership_package).distinct().count()

    for payment in all_payments.all():
        if payment.subscription.stripe_id:
            stripe.api_key = get_stripe_secret_key(request)
            stripe_payments = stripe.Charge.list(customer=payment.subscription.stripe_id,
                                                 stripe_account=payment.subscription.membership_package.stripe_acct_id)
            for stripe_payment in stripe_payments:
                # get the amount as a variable so it can be converted to the correct format to be displayed
                temp_amount = int(stripe_payment['amount']) / 100
                payments.append({
                                    'action': f"""<a href="{stripe_payment['receipt_url']}"><button class="btn btn-sm btn-rounded btn-light" data-toggle="tooltip" title="View Receipt"><i class="fad fa-file-invoice text-info"></i></button></a>""",
                                    'payment_id': stripe_payment['id'],
                                    'name': payment.subscription.member.user_account.get_full_name(),
                                    'membership_id': payment.subscription.membership_number,
                                    'method': 'Card Payment',
                                    'type': 'Card Payment',
                                    'amount': "£%.2f" % temp_amount,
                                    'comments': f"<small>Managed by Stripe</small><br>{stripe_payment['description']}",
                                    'created': datetime.fromtimestamp(stripe_payment['created']).strftime('%c'),
                                    'gift_aid': 'n/a',
                                    'gift_aid_percentage': 'n/a'})

        # if there are payments in our database, or if it is a stripe subscription
        if all_payments.count() > 0 or payment.subscription.stripe_id:
            for payment in all_payments:
                # get the amount as a variable so it can be converted to the correct format to be displayed
                temp_amount = float(payment.amount) / 100
                if payment.gift_aid:
                    giftaid = '<i class="fad fa-check text-success"></i>'
                else:
                    giftaid = '<i class="fad fa-times text-danger"></i>'
                # set params
                payments.append({
                                    'action': f"""<a href="{reverse('member_payment_form_edit', kwargs={'title': membership_package.organisation_name,
                                                                                                        'pk': payment.subscription.member.id, 'payment_id': payment.id})}"><button class="btn btn-sm btn-rounded btn-light mr-1 mt-1" data-toggle="tooltip" title="Edit Payment"><i class="fad fa-money-check-edit-alt text-info"></i></button></a>
                                                    <a href="javascript:deletePayment({payment.subscription.member.id}, {payment.id});"><button class="btn btn-sm btn-rounded btn-light mr-1 mt-1" data-toggle="tooltip" title="Delete Payment"><i class="fad fa-trash-alt text-danger"></i></button></a>""",
                                    'payment_id': payment.payment_number,
                                    'name': payment.subscription.member.user_account.get_full_name(),
                                    'membership_id': payment.subscription.membership_number,
                                    'method': payment.payment_method.payment_name,
                                    'type': payment.type,
                                    'amount': "£%.2f" % temp_amount,
                                    'comments': payment.comments,
                                    'created': str(payment.created),
                                    'gift_aid': giftaid,
                                    'gift_aid_percentage': payment.gift_aid_percentage})
                # sorting
                members_sorted = payments
            complete_data = {
                "draw": 0,
                "recordsTotal": all_payments.count(),
                "recordsFiltered": total_payments,
                "data": members_sorted
            }
        else:
            complete_data = {
                "draw": 0,
                "recordsTotal": 0,
                "recordsFiltered": 0,
                "data": []
            }
        return HttpResponse(dumps(complete_data))
    else:
        complete_data = {
            "draw": 0,
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": []
        }
    return HttpResponse(dumps(complete_data))

@login_required(login_url='/accounts/login/')
def get_member_payments(request, title, pk=None):
    membership_package = MembershipPackage.objects.get(organisation_name=title)
    member = Member.objects.get(id=pk)
    subscription = MembershipSubscription.objects.get(membership_package=membership_package,
                                                      member=member)
    start = int(request.GET.get('start', 0))
    end = int(request.GET.get('length', 20))
    search = request.GET.get('search[value]', "")
    sort_by = request.GET.get(f'columns[{request.GET.get("order[0][column]")}][data]')
    payments = []
    if search == "":
        all_payments = Payment.objects.filter(subscription=subscription).order_by('-created')[start:start + end]
    else:
        all_payments = Payment.objects.filter(Q(payment_method__payment_name__icontains=search) |
                                              Q(payment_number__icontains=search) |
                                              Q(type__icontains=search) |
                                              Q(comments__icontains=search) |
                                              Q(created__icontains=search) |
                                              Q(gift_aid_percentage__icontains=search) |
                                              Q(amount__icontains=search),
                                              subscription=subscription).distinct().order_by('-created')[
                      start:start + end]
    # get stripe payments
    total_payments = Payment.objects.filter(subscription=subscription).distinct().count()
    if subscription.stripe_id:
        stripe.api_key = get_stripe_secret_key(request)
        stripe_payments = stripe.Charge.list(customer=subscription.stripe_id, stripe_account=subscription.membership_package.stripe_acct_id)
        for payment in stripe_payments:
            # get the amount as a variable so it can be converted to the correct format to be displayed
            temp_amount = int(payment['amount'])/100
            payments.append({'action': f"""<a href="{payment['receipt_url']}"><button class="btn btn-sm btn-rounded btn-light" data-toggle="tooltip" title="View Receipt"><i class="fad fa-file-invoice text-info"></i></button></a>""",
                            'id': payment['id'],
                            'method': 'Card Payment',
                            'type': 'Card Payment',
                            'amount': "£%.2f" % temp_amount,
                            'comments': f"<small>Managed by Stripe</small><br>{payment['description']}",
                            'created': datetime.fromtimestamp(payment['created']).strftime('%c'),
                            'gift_aid': 'n/a',
                            'gift_aid_percentage': 'n/a'})

    # if there are payments in our database, or if it is a stripe subscription
    if all_payments.count() > 0 or subscription.stripe_id:
        for payment in all_payments:
            # get the amount as a variable so it can be converted to the correct format to be displayed
            temp_amount = float(payment.amount)/100
            if payment.gift_aid:
                giftaid = '<i class="fad fa-check text-success"></i>'
            else:
                giftaid = '<i class="fad fa-times text-danger"></i>'
            # set params
            payments.append({'action': f"""<a href="{reverse('member_payment_form_edit', kwargs={'title': membership_package.organisation_name,
                                                                                'pk': member.id, 'payment_id': payment.id})}"><button class="btn btn-sm btn-rounded btn-light mr-1 mt-1" data-toggle="tooltip" title="Edit Payment"><i class="fad fa-money-check-edit-alt text-info"></i></button></a>
                                            <a href="javascript:deletePayment({member.id}, {payment.id});"><button class="btn btn-sm btn-rounded btn-light mr-1 mt-1" data-toggle="tooltip" title="Delete Payment"><i class="fad fa-trash-alt text-danger"></i></button></a>""",
                             'id': payment.payment_number,
                             'method': payment.payment_method.payment_name,
                             'type': payment.type,
                             'amount': "£%.2f" % temp_amount,
                             'comments': payment.comments,
                             'created': str(payment.created),
                             'gift_aid': giftaid,
                             'gift_aid_percentage': payment.gift_aid_percentage})
        # sorting
        members_sorted = payments
        # members_sorted = sorted(members, key=lambda k: k[sort_by])
        complete_data = {
            "draw": 0,
            "recordsTotal": all_payments.count(),
            "recordsFiltered": total_payments,
            "data": members_sorted
        }
    else:
        complete_data = {
            "draw": 0,
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": []
        }
    return HttpResponse(dumps(complete_data))

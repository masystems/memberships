from django.shortcuts import redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from memberships.functions import *
from .models import MembershipPackage, MembershipSubscription, Payment
from json import loads
import stripe
from datetime import datetime
import csv
import xlwt


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
            response[
                'Content-Disposition'] = f'attachment; filename="{membership_package}-Export-{date.strftime("%Y-%m-%d")}.xls"'

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
            columns = ['Title', 'First Name', 'Surname', 'Second Name', 'Membership Type', 'Company Name', 'Address 1',
                       'Address 2', 'Address 3', 'Address 4', 'Postcode', 'Country', 'Raffle Tickets']

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
            response[
                'Content-Disposition'] = f'attachment; filename="{membership_package}-Export-{date.strftime("%Y-%m-%d")}.xls"'

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
            columns = ['Title', 'First Name', 'Surname', 'Second Name', 'Membership Type', 'Company Name', 'Address 1',
                       'Address 2', 'Address 3', 'Address 4', 'Postcode', 'Country']

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


@login_required(login_url='/accounts/login/')
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

            headers = get_members_detailed_headers(membership_package)

            writer.writerow(headers)
            for subscription in all_subscriptions.all():
                inbuilt_items = get_inbuilt_items(subscription, membership_package)
                writer.writerow(inbuilt_items)
            return response

        elif 'xls' in request.POST:
            response = HttpResponse(content_type='application/ms-excel')
            response[
                'Content-Disposition'] = f'attachment; filename="{membership_package}-Export-{date.strftime("%Y-%m-%d")}.xls"'

            # creating workbook
            workbook = xlwt.Workbook(encoding='utf-8')

            # adding sheet
            worksheet = workbook.add_sheet("sheet1")

            # Sheet header, first row
            row_num = 0

            font_style = xlwt.XFStyle()
            # headers are bold
            font_style.font.bold = True

            headers = get_members_detailed_headers(membership_package)

            # write column headers in sheet
            for col_num in range(len(headers)):
                worksheet.write(row_num, col_num, headers[col_num], font_style)

            # Sheet body, remaining rows
            font_style = xlwt.XFStyle()

            # Sheet first row
            row_num = 1

            for subscription in all_subscriptions.all():
                col = 0
                inbuilt_items = get_inbuilt_items(subscription, membership_package)
                for item in inbuilt_items:
                    worksheet.write(row_num, col, item, font_style)
                    col += 1
                row_num += 1
            workbook.save(response)
            return response


def get_members_detailed_headers(membership_package):
    # column header names
    # member_number, name, email etc
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
    return headers


def get_inbuilt_items(subscription, membership_package):
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
    n1 = "\n"
    inbuilt_items = [subscription.membership_number,
                     subscription.member.user_account.get_full_name(),
                     subscription.member.user_account.email,
                     f'{f"{subscription.member.company},{n1}" if subscription.member.company else ""}{f"{subscription.member.address_line_1},{n1}" if subscription.member.address_line_1 else ""}{f"{subscription.member.address_line_2},{n1}" if subscription.member.address_line_2 else ""}{f"{subscription.member.county},{n1}" if subscription.member.county else ""}{f"{subscription.member.country},{n1}" if subscription.member.country else ""}{f"{subscription.member.postcode},{n1}" if subscription.member.postcode else ""}',
                     subscription.member.contact_number,
                     membership_type,
                     payment_type,
                     billing_interval,
                     subscription.comments,
                     f'{membership_start_date or ""}',
                     f'{subscription.membership_expiry or ""}']
    # add custom fields to the mix
    inbuilt_items.extend(custom_fields)
    return inbuilt_items


@login_required(login_url='/accounts/login/')
def export_payments_detailed(request, title):
    if request.POST:
        membership_package = MembershipPackage.objects.get(organisation_name=title)
        date = datetime.now()
        stripe.api_key = get_stripe_secret_key(request)

        search = request.POST.get('search_param')
        if search == "":
            all_payments = Payment.objects.filter(subscription__membership_package=membership_package)
        else:
            all_payments = Payment.objects.filter(Q(payment_method__payment_name__icontains=search) |
                                                  Q(payment_number__icontains=search) |
                                                  Q(type__icontains=search) |
                                                  Q(created__icontains=search) |
                                                  Q(gift_aid_percentage__icontains=search) |
                                                  Q(amount__icontains=search),
                                                  subscription__membership_package=membership_package).distinct()
        if 'csv' in request.POST:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{membership_package}-Export-{date.strftime("%Y-%m-%d")}.csv"'

            writer = csv.writer(response, delimiter=",")

            headers = get_members_detailed_headers(membership_package)

            writer.writerow(headers)
            for payment in all_payments.all():
                inbuilt_items = get_inbuilt__payment_items(payment, membership_package)
                writer.writerow(inbuilt_items)
            return response

        # elif 'xls' in request.POST:
        #     response = HttpResponse(content_type='application/ms-excel')
        #     response[
        #         'Content-Disposition'] = f'attachment; filename="{membership_package}-Export-{date.strftime("%Y-%m-%d")}.xls"'
        #
        #     # creating workbook
        #     workbook = xlwt.Workbook(encoding='utf-8')
        #
        #     # adding sheet
        #     worksheet = workbook.add_sheet("sheet1")
        #
        #     # Sheet header, first row
        #     row_num = 0
        #
        #     font_style = xlwt.XFStyle()
        #     # headers are bold
        #     font_style.font.bold = True
        #
        #     headers = get_members_detailed_headers(membership_package)
        #
        #     # write column headers in sheet
        #     for col_num in range(len(headers)):
        #         worksheet.write(row_num, col_num, headers[col_num], font_style)
        #
        #     # Sheet body, remaining rows
        #     font_style = xlwt.XFStyle()
        #
        #     # Sheet first row
        #     row_num = 1
        #
        #     for subscription in all_subscriptions.all():
        #         col = 0
        #         inbuilt_items = get_inbuilt__payment_items(subscription, membership_package)
        #         for item in inbuilt_items:
        #             worksheet.write(row_num, col, item, font_style)
        #             col += 1
        #         row_num += 1
        #     workbook.save(response)
        #     return response


# def get_members_detailed_headers(membership_package):
#     # column header names
#     # member_number, name, email etc
#     headers = ['Member ID',
#                'Name',
#                'Email',
#                'Address',
#                'Contact',
#                'Membership Status',
#                'Payment Method',
#                'Billing Interval',
#                'Comments',
#                'Membership Start',
#                'Membership Expiry']
#
#     # custom fields
#     custom_fields = []
#     custom_fields_raw = loads(membership_package.custom_fields)
#     for key, field in custom_fields_raw.items():
#         try:
#             custom_fields.append(field['field_name'])
#         except KeyError:
#             custom_fields.append("")
#     headers.extend(custom_fields)
#     return headers


def get_inbuilt__payment_items(payment, membership_package):
    # set method to card if it doesn't exist
    if payment.payment_method:
        method = payment.payment_method.payment_name
    else:
        method = 'Card Payment'

    # get the amount as a variable so it can be converted to the correct format to be displayed
    temp_amount = float(payment.amount) / 100
    if payment.gift_aid:
        giftaid = '<i class="fad fa-check text-success"></i>'
    else:
        giftaid = '<i class="fad fa-times text-danger"></i>'

    inbuilt_items = [payment.payment_number,
                     payment.subscription.member.user_account.get_full_name(),
                     payment.subscription.membership_number,
                     method,
                     payment.type,
                     "£%.2f" % temp_amount,
                     payment.comments,
                     str(payment.created),
                     giftaid,
                     payment.gift_aid_percentage]
    return inbuilt_items
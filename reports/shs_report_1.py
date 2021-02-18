import xlwt
from membership.models import MembershipPackage, Price, Member, MembershipSubscription

# this reports information including "No raffle tickets" about members where "Do not mail" is False

file_type = 'xlsx'

#membership_package = MembershipPackage.objects.get(organisation_name='Suffolk Horse Society')
membership_package = MembershipPackage.objects.get(organisation_name='Golf Nest')
date = datetime.now()
if file_type == 'xlsx':
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{membership_package}-Export-{date.strftime("%Y-%m-%d")}.xlsx"'
    
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
        # get custom fields
        mail = True
        second_name = ''
        raffle_tickets = 'Yes'
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
            worksheet.write(row_num, 4, subscription.price.nickname, font_style)
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
    #return response

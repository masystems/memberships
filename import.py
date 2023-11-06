import csv
import json
import stripe
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from membership.models import MembershipPackage, Member, MembershipSubscription, PaymentMethod, Price


# Path to your CSV file
CSV_FILE = '../BWA_data_import_v0.1.csv'
MEMBERSHIP_ORG = 'British Waterfowl Association'
#MEMBERSHIP_ORG = 'Development Organisation'
CUSTOM_FIELDS = """{"cf_0": 
                 {"id": "cf_0", "field_name": "Membership Number", "field_type": "text_field", "help_text": "", "visible": "on", "field_value": ""}, 
                 "cf_1": {"id": "cf_1", "field_name": "Breeder Directory", "field_type": "bool", "help_text": "", "visible": true, "field_value": null}, 
                 "cf_2": {"id": "cf_2", "field_name": "Title", "field_type": "text_field", "help_text": "", "visible": "on", "field_value": ""}, 
                 "cf_3": {"id": "cf_3", "field_name": "First names", "field_type": "text_field", "help_text": "", "visible": "on", "field_value": ""}, 
                 "cf_4": {"id": "cf_4", "field_name": "Surname", "field_type": "text_field", "help_text": "", "visible": "on", "field_value": ""}, 
                 "cf_5": {"id": "cf_5", "field_name": "On Council", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_6": {"id": "cf_6", "field_name": "BWA Officer", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_7": {"id": "cf_7", "field_name": "County", "field_type": "text_field", "help_text": "", "visible": "on", "field_value": ""}, 
                 "cf_8": {"id": "cf_8", "field_name": "Country", "field_type": "text_field", "help_text": "", "visible": "on", "field_value": ""}, 
                 "cf_9": {"id": "cf_9", "field_name": "County Rep", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_10": {"id": "cf_10", "field_name": "Joining Date:Month", "field_type": "text_field", "help_text": "", "visible": null, "field_value": ""}, 
                 "cf_11": {"id": "cf_11", "field_name": "Joining Date:Year", "field_type": "text_field", "help_text": "", "visible": false, "field_value": ""}, 
                 "cf_12": {"id": "cf_12", "field_name": "Unsubscribe Webzine", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_13": {"id": "cf_13", "field_name": "Domestic or Wildfowl?", "field_type": "text_field", "help_text": "", "visible": "on", "field_value": ""}, 
                 "cf_14": {"id": "cf_14", "field_name": "Breeder Directory 2014", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_15": {"id": "cf_15", "field_name": "Region", "field_type": "text_field", "help_text": "", "visible": null, "field_value": ""}, 
                 "cf_16": {"id": "cf_16", "field_name": "Gift Aid Form Held?", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_17": {"id": "cf_17", "field_name": "Breeder Directory 2016", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_18": {"id": "cf_18", "field_name": "Show Schedule", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_19": {"id": "cf_19", "field_name": "Breeder Directory 2018", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_20": {"id": "cf_20", "field_name": "GDPR Agreed", "field_type": "date", "help_text": "", "visible": null, "field_value": ""}, 
                 "cf_21": {"id": "cf_21", "field_name": "GDPR Method", "field_type": "text_field", "help_text": "", "visible": null, "field_value": ""}, 
                 "cf_22": {"id": "cf_22", "field_name": "Email Consent", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_23": {"id": "cf_23", "field_name": "Tel Consent", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_24": {"id": "cf_24", "field_name": "Post Consent", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_25": {"id": "cf_25", "field_name": "Underpaid?", "field_type": "text_field", "help_text": "", "visible": false, "field_value": ""}, 
                 "cf_26": {"id": "cf_26", "field_name": "Card sent out when full subs paid", "field_type": "bool", "help_text": "", "visible": null, "field_value": null}, 
                 "cf_27": {"id": "cf_27", "field_name": "Skills Offered", "field_type": "text_field", "help_text": "", "visible": null, "field_value": ""}, 
                 "cf_28": {"id": "cf_28", "field_name": "Notes", "field_type": "text_field", "help_text": "", "visible": null, "field_value": ""}
                 }"""

stripe.api_key = settings.STRIPE_SECRET_KEY

def str_to_bool(s):
    if not s:
        return False
    return s.lower() in ['true', '1', 't', 'y', 'yes', 'on']

# Function to convert string to datetime and calculate one year before
def convert_date_and_get_past_year(date_string):
    print('Converting date to datetime object')
    # Convert the string to a datetime object
    date_format = "%d-%b-%y"
    date_object = datetime.strptime(date_string, date_format)
    
    # Calculate one year before
    # Check for leap year and adjust accordingly
    year = date_object.year - 1
    try:
        one_year_before = date_object.replace(year=year)
    except ValueError: # February 29 doesn't exist in a non-leap year
        one_year_before = date_object.replace(year=year, day=date_object.day - 1)
    
    return date_object, one_year_before

def process_custom_fields():
    # Process Custom Fields
    print('Importing Custom Fields')
    custom_fields_dict = json.loads(CUSTOM_FIELDS)
    # For each field in custom_fields, check if there's a matching column in the CSV
    for field_id, field_data in custom_fields_dict.items():
        field_name = field_data['field_name']
        if field_name in row:
            # Update the 'field_value' with the data from the CSV
            field_data['field_value'] = row[field_name]
            print(row[field_name])
    # Now CUSTOM_FIELDS has updated 'field_value's, convert it back to a JSON string if needed
    print(json.dumps(custom_fields_dict))
    return json.dumps(custom_fields_dict)

# Open the CSV file
with open(CSV_FILE, newline='') as csvfile:
    csvreader = csv.DictReader(csvfile)  # No need to skip the header, DictReader does that
    membership_package = MembershipPackage.objects.get(organisation_name=MEMBERSHIP_ORG)
    print(membership_package)
    for row in csvreader:
        print(row.get('E-mail address'))
        # Create User
        print('Creating User')
        username = row.get('E-mail address')
        email = row.get('E-mail address')
        first_name = row.get('First names')
        last_name = row.get('Surname')
        user, created = User.objects.get_or_create(username=username, defaults={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
        })
        if created:
            if created:
                # Generate a random password
                password = get_random_string(12)
                user.set_password(password)
                user.save()
        #
        #
        #
        # Create Member
        print('Creating Member')
        title = row.get('Title', '')
        address_line_1 = f"{row.get('Address A', '')} {row.get('Address C', '')}"
        address_line_2 = row.get('Address B', '')
        town = row.get('Town', '')
        county = row.get('County', '')
        country = row.get('Country', '')
        postcode = row.get('Post Code', '')
        contact_number = row.get('Telephone Number', '')
        #
        #
        #
        # Create the Member instance
        member, member_created = Member.objects.get_or_create(
            user_account=user,
            defaults={
                'title': title,
                'address_line_1': address_line_1,
                'address_line_2': address_line_2,
                'town': town,
                'county': county,
                'country': country,
                'postcode': postcode,
                'contact_number': contact_number
            }
        )
        #
        # Create Membership Subscription
        print('Creating Subscription')
        membership_number = row.get('Membership Number')
        print(f"Getting payment method from DB: {row.get('Subscription Type', '')}")
        if row.get('Subscription Type', '').strip():
            payment_method = PaymentMethod.objects.get(membership_package=membership_package,
                                                       payment_name=row.get('Subscription Type', ''))
        else:
            payment_method = None
        if row.get('Membership Type', '').strip():
            print(f"Getting price object from DB: {row.get('Membership Type', '')}")
            price = Price.objects.get(membership_package=membership_package,
                                      nickname=row.get('Membership Type', '').strip())
        else:
            price = None
        if row.get('Renewal Date', ''):
            membership_start, membership_expiry = convert_date_and_get_past_year(row.get('Renewal Date', ''))
        else:
            membership_start, membership_expiry = None, None
        contact_number = row.get('Telephone Number', '')
        subscription, created = MembershipSubscription.objects.get_or_create(member=member,
                                                                             membership_package=membership_package,
                                                                             defaults={
                                                                                 'membership_number': membership_number,
                                                                                 'payment_method': payment_method,
                                                                                 'price': price,
                                                                                 'comments': row.get('Notes', ''),
                                                                                 'membership_start': membership_start,
                                                                                 'membership_expiry': membership_expiry,
                                                                                 'active': True,
                                                                                 'canceled': False,
                                                                                })
        subscription.custom_fields = str(process_custom_fields())
        # 
        #
        #
        # Create Customer in Stripe
        print('Creating Stripe User')
        if subscription.stripe_id:
            # The customer exists, update the customer details
            customer = stripe.Customer.modify(
                subscription.stripe_id,
                email=user.email,
                name=user.get_full_name(),
                stripe_account=membership_package.stripe_acct_id
            )
        else:
            # No customer exists, create a new one
            customer = stripe.Customer.create(
                email=user.email,
                name=user.get_full_name(),
                stripe_account=membership_package.stripe_acct_id
            )
            # Save the stripe_id to your subscription model after creation
        subscription.stripe_id = customer.id
        subscription.save()  # Assuming you have a save method on your subscription object


# for sub in MembershipSubscription.objects.filter(membership_package=membership_package):
#     sub.custom_fields = ""
#     print(sub.custom_fields)
#     sub.save()
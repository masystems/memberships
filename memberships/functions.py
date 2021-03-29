from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from random import randint
from membership.models import Payment
import re


def generate_username(first_name, last_name):
    return f"{first_name.lower().replace(' ', '')}.{last_name.lower().replace(' ', '')}{randint(1000, 999999)}"


def get_stripe_secret_key(request):
    if request.user.is_superuser:
        return settings.STRIPE_SECRET_TEST_KEY
    else:
        return settings.STRIPE_SECRET_KEY


def get_stripe_public_key(request):
    if request.user.is_superuser:
        return settings.STRIPE_PUBLIC_TEST_KEY
    else:
        return settings.STRIPE_PUBLIC_KEY


def send_email(subject, name, body,
              send_to='contact@masys.co.uk',
              send_from='contact@masys.co.uk',
              reply_to='contact@masys.co.uk',
              customised=False):

    # check if the email adress to send the email to is a random one we generated
    pattern_to_ignore = re.compile("^\d+@masys\.co\.uk$")
    if not pattern_to_ignore.fullmatch(send_to):
        if not customised:
            html_content = render_to_string('account/email/email.html', {'name': name,
                                                            'body': body})
        else:
            html_content = render_to_string('account/email/custom_email.html', {'name': name,
                                                            'body': body})
        
        text_content = strip_tags(html_content)

        # create the email, and attach the HTML version as well.
        msg = EmailMultiAlternatives(subject, text_content, send_from, [send_to], reply_to=[reply_to])
        msg.attach_alternative(html_content, "text/html")

        msg.send()
    else:
        print('email not to be sent')

    # example email
    # from memberships.functions import send_email
    # body = f"""This is confirmation that your Membership has been created.
    #             Membership Organisation: {membership_package.organisation_name}
    #             """
    # send_email("Membership Started!", request.user.get_full_name, body, reply_to=request.user.email)


def get_next_payment_number():
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

    return payment_number

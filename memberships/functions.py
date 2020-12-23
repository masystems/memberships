from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from random import randint


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
              reply_to='contact@masys.co.uk'):

    html_content = render_to_string('account/email/email_base.html', {'name': name,
                                                        'body': body})
    text_content = strip_tags(html_content)

    # create the email, and attach the HTML version as well.
    msg = EmailMultiAlternatives(subject, text_content, send_from, [send_to], reply_to=[reply_to])
    msg.attach_alternative(html_content, "text/html")

    msg.send()

    # example email
    # from memberships.functions import send_email
    # body = f"""This is confirmation that your Membership has been created.
    #             Membership Organisation: {membership_package.organisation_name}
    #             """
    # send_email("Membership Started!", request.user.get_full_name, body, reply_to=request.user.email)

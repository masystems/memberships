#! /opt/memberships/venv/bin/python

import django
import sys
import os
import stripe
from json import loads
from datetime import datetime

sys.path.append('/opt/memberships/memberships')
os.environ["DJANGO_SETTINGS_MODULE"] = "memberships.settings"
django.setup()

from django.conf import settings
from membership.models import MembershipPackage, Payment, MembershipSubscription
from memberships.functions import *


class GetStripePayments:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def run(self):
        for sub in MembershipSubscription.objects.filter(stripe_subscription_id__isnull=False,
                                                            stripe_id__isnull=False).exclude(stripe_subscription_id="",
                                                                                             stripe_id=""):
            data = loads(str(stripe.Invoice.list(customer=sub.stripe_id, stripe_account=sub.membership_package.stripe_acct_id)))
            for payment in data['data']:
                if not Payment.objects.filter(stripe_id=payment['charge']).exists():
                    subscription = sub
                    payment_number = get_next_payment_number()
                    if payment['lines']['data'][0]['plan']['interval'] in ('month', 'year'):
                        type = 'subscription'
                    else:
                        type = 'donation'
                    amount = payment['amount_paid']
                    created = datetime.fromtimestamp(payment['created'])
                    stripe_id = payment['charge']
                    if stripe_id:
                        Payment.objects.create(subscription=subscription,
                                               payment_number=payment_number,
                                               type=type,
                                               amount=amount,
                                               created=created,
                                               stripe_id=stripe_id)


if __name__ == '__main__':
    GetStripePayments().run()

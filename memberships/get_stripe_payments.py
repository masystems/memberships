#! /opt/memberships/venv/bin/python

import django
import sys
import os
import stripe
from json import loads
from datetime import datetime

#sys.path.append('/opt/memberships/dev-memberships')
sys.path.append('/opt/memberships/memberships')
os.environ["DJANGO_SETTINGS_MODULE"] = "memberships.settings"
django.setup()

from django.conf import settings
from membership.models import MembershipPackage, Payment, MembershipSubscription
from memberships.functions import *
from membership.charging import *
from pprint import pprint

class GetStripePayments:
    def __init__(self):
        #stripe.api_key = settings.STRIPE_SECRET_TEST_KEY
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def run(self):
        for sub in MembershipSubscription.objects.filter(stripe_subscription_id__isnull=False,
                                                            stripe_id__isnull=False).exclude(stripe_subscription_id="",
                                                                                             stripe_id=""):
            data = loads(str(stripe.Invoice.list(customer=sub.stripe_id, stripe_account=sub.membership_package.stripe_acct_id)))
            for payment in data['data']:
                # 'not' removed able to allow updating existing payment objects
                if not Payment.objects.filter(stripe_id=payment['charge']).exists():
                    subscription = sub
                    payment_number = get_next_payment_number()
                    try:
                        if payment['lines']['data'][0]['plan']['interval'] in ('month', 'year'):
                            type = 'subscription'
                        else:
                            type = 'donation'
                    except IndexError:
                        # no payment plan interval??
                        # pprint(payment)
                        continue
                    # get charge amount
                    amount = payment['amount_paid']
                    # get charge date
                    # print(f"STRIPE ID: {sub.membership_package.stripe_acct_id}")
                    # print(f"PAYMENT ID: {payment['charge']}")
                    if payment['charge'] is not None:
                        charge = stripe.Charge.retrieve(payment['charge'], stripe_account=sub.membership_package.stripe_acct_id)
                        created = datetime.fromtimestamp(charge['created'])
                        stripe_id = payment['charge']
                        if stripe_id:
                            dj_price, was_created = Payment.objects.get_or_create(stripe_id=stripe_id,
                                                                                  defaults={'subscription': subscription,
                                                                                            'payment_number': payment_number,
                                                                                            'type': type,
                                                                                            'amount': amount,
                                                                                            'created': created})
                            if was_created:
                                dj_price.save()


if __name__ == '__main__':
    GetStripePayments().run()

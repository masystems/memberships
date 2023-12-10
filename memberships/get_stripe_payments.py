#! /opt/memberships/venv/bin/python

import django
import sys
import os
import stripe
from json import loads
from datetime import datetime

debug = False
if debug:
    sys.path.append('/opt/memberships/dev-memberships')
else:
    sys.path.append('/opt/memberships/memberships')
os.environ["DJANGO_SETTINGS_MODULE"] = "memberships.settings"
django.setup()

from django.conf import settings
from membership.models import MembershipPackage, Payment, MembershipSubscription
from django.db.models import Q
from memberships.functions import *
from membership.charging import *
from pprint import pprint

class GetStripePayments:
    def __init__(self, sub_id=None):
        if debug:
            stripe.api_key = settings.STRIPE_SECRET_TEST_KEY
        else:
            stripe.api_key = settings.STRIPE_SECRET_KEY
        self.sub_id = sub_id

    def run(self):
        if self.sub_id:
            subscriptions = MembershipSubscription.objects.filter(id=self.sub_id)
        else:
            subscriptions = MembershipSubscription.objects.filter(~Q(stripe_subscription_id__in=["", None]),
                                                         ~Q(stripe_id__in=["", None]),
                                                            canceled=False)
        for sub in subscriptions:
            data = loads(str(stripe.Invoice.list(customer=sub.stripe_id, stripe_account=sub.membership_package.stripe_acct_id)))
            for payment in data['data']:
                # 'not' removed able to allow updating existing payment objects
                if not Payment.objects.filter(stripe_id=payment['id']).exists():
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
                    except TypeError:
                        # outside of a subscription i.e. one off payments
                        stripe_id = payment['id']
                        amount = payment['amount_due']
                        pprint(payment)
                        intent = stripe.PaymentIntent.retrieve(payment['payment_intent'], stripe_account=sub.membership_package.stripe_acct_id)
                        created = datetime.fromtimestamp(intent['created'])
                        dj_price, was_created = Payment.objects.get_or_create(stripe_id=stripe_id,
                                                                              defaults={'subscription': subscription,
                                                                                        'payment_number': payment_number,
                                                                                        'type': 'one off',
                                                                                        'comments': payment['lines']['data'][0]['description'],
                                                                                        'amount': amount,
                                                                                        'created': created})
                        continue
                    # get charge amount
                    amount = payment['amount_due']
                    # get charge date
                    # print(f"STRIPE ID: {sub.membership_package.stripe_acct_id}")
                    # print(f"PAYMENT ID: {payment['charge']}")
                    if payment['payment_intent'] is not None:
                        intent = stripe.PaymentIntent.retrieve(payment['payment_intent'], stripe_account=sub.membership_package.stripe_acct_id)
                        created = datetime.fromtimestamp(intent['created'])
                        stripe_id = payment['id']
                        if stripe_id:
                            dj_price, was_created = Payment.objects.get_or_create(stripe_id=stripe_id,
                                                                                  defaults={'subscription': subscription,
                                                                                            'payment_number': payment_number,
                                                                                            'type': type,
                                                                                            'amount': amount,
                                                                                            'created': created})
                            if was_created:
                                dj_price.save()
            # update the subscription object data
            stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id, stripe_account=sub.membership_package.stripe_acct_id)
            sub.membership_start = datetime.fromtimestamp(stripe_sub['current_period_start'])
            sub.membership_expiry = datetime.fromtimestamp(stripe_sub['current_period_end'])
            sub.save()


if __name__ == '__main__':
    GetStripePayments().run()

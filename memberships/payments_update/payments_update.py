from membership.models import MembershipSubscription, Payment
from membership.views import get_next_payment_number

sys.path.append('memberships.cloud-lines')
os.environ["DJANGO_SETTINGS_MODULE"] = "memberships.cloudlines.settings"
django.setup()

# iterate through subscriptions
for subscription in MembershipSubscription:

    stripe_payments = stripe.Charge.list(customer=subscription.stripe_id)

    # iterate through stripe payments for that subscription
    for stripe_payment in stripe_payments.data:
        
        # store payment as a Payment object in the database, if it isn't already in there
        if not Payment.objects.filter(stripe_id=stripe_payment.id).exists():
            payment = Payment.objects.create(
                subscription=subscription,
                payment_number=get_next_payment_number(),
                amount=stripe_payment.amount,
                stripe_id=stripe_payment.id,
            )
            payment.save()
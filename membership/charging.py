from django.shortcuts import render, HttpResponse, redirect
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required, user_passes_test
import json
import stripe


def get_stripe_secret_key(request=None):
    if request:
        if request.META['HTTP_HOST'] in settings.TEST_STRIPE_DOMAINS:
            return settings.STRIPE_SECRET_TEST_KEY
        else:
            return settings.STRIPE_SECRET_KEY
    else:
        return settings.STRIPE_SECRET_TEST_KEY


def get_stripe_public_key(request=None):
    if request:
        if request.META['HTTP_HOST'] in settings.TEST_STRIPE_DOMAINS:
            return settings.STRIPE_PUBLIC_TEST_KEY
        else:
            return settings.STRIPE_PUBLIC_KEY
    else:
        return settings.STRIPE_PUBLIC_TEST_KEY


@login_required(login_url="/account/login")
def create_charging_session(request, package, member, subscription, price, mode='subscription'):
    stripe.api_key = get_stripe_secret_key(request)

    # get or create customer
    if not subscription.stripe_id:
        customer = stripe.Customer.create(
            email=member.user_account.user.email,
            stripe_account=package.stripe_acct_id
        )
        subscription.stripe_id = customer['id']
    else:
        customer = stripe.Customer.retrieve(subscription.stripe_id,
                                            stripe_account=package.stripe_acct_id)

    # create session
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[
            {
                "price": price.stripe_price_id,
                "quantity": 1,
            },
        ],
        mode=mode,
        customer=customer.id,
        success_url=f"{settings.HTTP_PROTOCOL}://{request.META['HTTP_HOST']}/membership/enable_subscription/{subscription.id}",
        cancel_url=f"{settings.HTTP_PROTOCOL}://{request.META['HTTP_HOST']}/membership",
        stripe_account=package.stripe_acct_id,
    )
    subscription.stripe_payment_token = session['id']
    subscription.save()
    return session.url


@login_required(login_url="/account/login")
def get_checkout_session(request, subscription):
    stripe.api_key = get_stripe_secret_key(request)
    return stripe.checkout.Session.retrieve(
        subscription.stripe_payment_token,
        stripe_account=subscription.membership_package.stripe_acct_id
    )


@login_required(login_url="/account/login")
def modifiy_subscription(request, subscription, price, package):
    stripe.api_key = get_stripe_secret_key(request)
    try:
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            items=[
                {
                    "price": price.stripe_price_id,
                    "quantity": 1,
                },
            ],
            stripe_account=package.stripe_acct_id
        )
    except stripe.error.InvalidRequestError as error:
        body = error.json_body
        err = body.get('error', {})
        return err.get('message')
    return True


@login_required(login_url="/account/login")
def update_card_session(request, subscription):
    stripe.api_key = get_stripe_secret_key(request)
    # print(subscription.member)
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='setup',
        customer=subscription.stripe_id,
        success_url=f"{settings.HTTP_PROTOCOL}://{request.META['HTTP_HOST']}/membership/update-card-success/{subscription.id}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.HTTP_PROTOCOL}://{request.META['HTTP_HOST']}/membership/member-profile/{subscription.member.id}#card-details",
        stripe_account=subscription.membership_package.stripe_acct_id
    )
    return session.url


@login_required(login_url="/account/login")
def get_subscription(request, subscription):
    stripe.api_key = get_stripe_secret_key(request)
    return stripe.Subscription.retrieve(
        subscription.stripe_subscription_id,
        stripe_account=subscription.membership_package.stripe_acct_id
    )


def create_subscription_payment(request, subscription, amount, description):
    stripe.api_key = get_stripe_secret_key(request)
    try:
        amount_in_pennies = int(float(amount) * 100)
        # Retrieve the default payment method
        customer = stripe.Customer.retrieve(subscription.stripe_id,
                                            stripe_account=subscription.membership_package.stripe_acct_id)

        default_payment_method = customer.invoice_settings.default_payment_method

        # Create an invoice item
        invoice_item = stripe.InvoiceItem.create(
            customer=subscription.stripe_id,
            amount=amount_in_pennies,
            currency='gbp',
            description=description,
            stripe_account=subscription.membership_package.stripe_acct_id
        )

        # Create and pay the invoice immediately
        invoice = stripe.Invoice.create(
            customer=subscription.stripe_id,
            auto_advance=True,  # Auto-finalize this invoice
            stripe_account=subscription.membership_package.stripe_acct_id
        )
        invoice = stripe.Invoice.pay(invoice.id, stripe_account=subscription.membership_package.stripe_acct_id)

        return {'status': 'success', 'invoice_id': invoice.id}

    except stripe.error.StripeError as e:
        # Handle Stripe errors
        return {'status': 'error', 'message': str(e)}
    except ValueError:
        return {'status': 'error', 'message': 'Ensure amount is e.g. 5.95 or 10'}


def generate_payment_link(request, subscription, item_name, price, quantity):
    stripe.api_key = get_stripe_secret_key(request)

    # Fetch a list of products
    products = stripe.Product.list(limit=10,
                                   stripe_account=subscription.membership_package.stripe_acct_id)  # Adjust the limit as needed

    # Filter products to find the matching one
    product = next((p for p in products.auto_paging_iter() if p.name == item_name), None)

    if product is None:
        # Product does not exist, create a new one
        product = stripe.Product.create(name=item_name,
                                        stripe_account=subscription.membership_package.stripe_acct_id)
    else:
        # Create a new product
        product = stripe.Product.create(name=item_name,
                                        stripe_account=subscription.membership_package.stripe_acct_id)

    # Check if the price already exists
    prices = stripe.Price.list(product=product.id,
                               active=True,
                               stripe_account=subscription.membership_package.stripe_acct_id)

    existing_price = None
    for p in prices.data:
        if p.unit_amount == price and p.currency == 'gbp':
            existing_price = p
            break

    if not existing_price:
        # Create a price for the product
        existing_price = stripe.Price.create(
            unit_amount=price,
            currency='gbp',
            product=product.id,
            stripe_account=subscription.membership_package.stripe_acct_id
        )

    # Create a payment link
    payment_link = stripe.PaymentLink.create(
        line_items=[{'price': existing_price.id, 'quantity': quantity}],
        stripe_account=subscription.membership_package.stripe_acct_id
    )

    return payment_link.url

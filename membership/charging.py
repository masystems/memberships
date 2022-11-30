from django.shortcuts import render, HttpResponse, redirect
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required, user_passes_test



import json
import stripe


@login_required(login_url="/account/login")
def get_stripe_secret_key(request):
    if request.META['HTTP_HOST'] in settings.TEST_STRIPE_DOMAINS:
        return settings.STRIPE_SECRET_TEST_KEY
    else:
        return settings.STRIPE_SECRET_KEY


@login_required(login_url="/account/login")
def get_stripe_public_key(request):
        if request.META['HTTP_HOST'] in settings.TEST_STRIPE_DOMAINS:
            return settings.STRIPE_PUBLIC_TEST_KEY
        else:
            return settings.STRIPE_PUBLIC_KEY


@login_required(login_url="/account/login")
def create_charging_session(request, package, member, subscription, price):
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
        mode='subscription',
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
        success_url=f"{settings.HTTP_PROTOCOL}://{request.META['HTTP_HOST']}/membership/member-profile/{subscription.member.id}#card-details",
        cancel_url=f"{settings.HTTP_PROTOCOL}://{request.META['HTTP_HOST']}/membership/member-profile/{subscription.member.id}#card-details",
        stripe_account=subscription.membership_package.stripe_acct_id
    )
    return session.url
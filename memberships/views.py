from django.shortcuts import render, redirect, HttpResponseRedirect, reverse, HttpResponse
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from allauth.account.forms import LoginForm
from membership.models import MembershipPackage, Member, MembershipSubscription, Donation
from .functions import *
from json import dumps
from urllib.parse import parse_qs
import stripe


def donation_payment(request):
    form_data = parse_qs(request.POST['form'])
    
    # handle non mandatory fields not being specified
    if 'full_name' in form_data.keys():
        full_name = form_data['full_name'][0]
    else:
        full_name = 'Anonymous'
    if 'message' in form_data.keys():
        message = form_data['message'][0]
    else:
        message = "No message given"

    # process the gift aid input
    if 'gift_aid' in form_data.keys():
        gift_aid = True
    else:
        gift_aid = False

    # process address
    if 'address-1' in form_data.keys():
        address_line_1 = form_data['address-1'][0]
    else:
        address_line_1 = ''
    
    if 'address-2' in form_data.keys():
        address_line_2 = form_data['address-2'][0]
    else:
        address_line_2 = ''
    
    if 'town' in form_data.keys():
        town = form_data['town'][0]
    else:
        town = ''
    
    if 'county' in form_data.keys():
        county = form_data['county'][0]
    else:
        county = ''
    
    if 'country' in form_data.keys():
        country = form_data['country'][0]
    else:
        country = ''
    
    if 'postcode' in form_data.keys():
        postcode = form_data['postcode'][0]
    else:
        postcode = ''

    if request.POST:
        # create donation object
        try:
            donation = Donation.objects.create(donator=request.user,
                                               membership_package=MembershipPackage.objects.get(organisation_name=form_data['membership_package'][0]),
                                               amount=form_data['amount'][0],
                                               full_name=full_name,
                                               email_address=form_data['email_address'][0],
                                               message=message,
                                               gift_aid=gift_aid,
                                               address_line_1=address_line_1,
                                               address_line_2 = address_line_2,
                                               town=town,
                                               county=county,
                                               country=country,
                                               postcode=postcode)
        except ValueError:
            donation = Donation.objects.create(membership_package=MembershipPackage.objects.get(
                                               organisation_name=form_data['membership_package'][0]),
                                               amount=form_data['amount'][0],
                                               full_name=full_name,
                                               email_address=form_data['email_address'][0],
                                               message=message,
                                               gift_aid=gift_aid,
                                               address_line_1=address_line_1,
                                               address_line_2 = address_line_2,
                                               town=town,
                                               county=county,
                                               country=country,
                                               postcode=postcode)

        # check for existing membership
        subscription = False
        if request.user.is_authenticated:
            member = Member.objects.get(user_account=request.user)
            try:
                subscription = MembershipSubscription.objects.get(member=member, membership_package=donation.membership_package)
            except MembershipSubscription.DoesNotExist:
                pass

        # get strip secret key
        stripe.api_key = get_stripe_secret_key(request)

        # if subscription does not exist
        # or does not hve a stripe id
        # create customer on stripe org account
        if not subscription or not subscription.stripe_id:
            # create stripe user
            customer = stripe.Customer.create(
                name=full_name,
                email=form_data['email_address'][0],
                stripe_account=donation.membership_package.stripe_acct_id
            )
            donation.stripe_id = customer['id']
            donation.save()
        else:
            # user has a current subscription, use same customer to pay donation
            donation.stripe_id = subscription.stripe_id
            donation.save()

        # validate the card and create payment
        # add payment token to user
        try:
            payment_method = stripe.Customer.modify(
                donation.stripe_id,
                source=request.POST.get('token[id]'),
                stripe_account=donation.membership_package.stripe_acct_id
            )
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            feedback = send_payment_error(e)
            result = {'result': 'fail',
                      'feedback': feedback}
            return HttpResponse(dumps(result))

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            feedback = send_payment_error(e)
            result = {'result': 'fail',
                      'feedback': feedback}
            return HttpResponse(dumps(result))

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            feedback = send_payment_error(e)
            result = {'result': 'fail',
                      'feedback': feedback}
            return HttpResponse(dumps(result))

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            feedback = send_payment_error(e)
            result = {'result': 'fail',
                      'feedback': feedback}
            return HttpResponse(dumps(result))

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            feedback = send_payment_error(e)
            result = {'result': 'fail',
                      'feedback': feedback}
            return HttpResponse(dumps(result))

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            feedback = send_payment_error(e)
            result = {'result': 'fail',
                      'feedback': feedback}
            return HttpResponse(dumps(result))

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            feedback = send_payment_error(e)
            result = {'result': 'fail',
                      'feedback': feedback}
            return HttpResponse(dumps(result))

        # make payment intent
        payment_intent = stripe.PaymentIntent.create(
            customer=donation.stripe_id,
            amount=int(float(donation.amount) * 100),
            currency="gbp",
            payment_method_types=["card"],
            receipt_email=donation.email_address,
            stripe_account=donation.membership_package.stripe_acct_id
        )
        # take payment
        payment_confirm = stripe.PaymentIntent.confirm(
            payment_intent['id'],
            payment_method=payment_method['default_source'],
            stripe_account=donation.membership_package.stripe_acct_id
        )
        if not payment_confirm['status'] == "succeeded":
            result = {'result': 'fail',
                      'feedback': f"<strong>Failure message:</strong> <span class='text-danger'>{payment_confirm['status']}</span>"}
            return HttpResponse(dumps(result))
        else:
            donation.validated = True
            donation.stripe_payment_id = payment_confirm['id']
            donation.save()

            # display yes or no for gift aid
            if donation.gift_aid:
                gift_aid_string = 'Yes'
            else:
                gift_aid_string = 'No'

            # send confirmation email
            donator_body = f"""<p>Congratulations! You just made a new donation.
                    <p>Donation details:</p>
                    <ul>
                    <li>Donated to: {donation.membership_package.organisation_name}</li>
                    <li>Donated by: {donation.full_name or "Anonymous"}</li>
                    <li>Amount: £{donation.amount}</li>
                    <li>Gift aid: {gift_aid_string}</li>
                    <li>Receipt: {payment_confirm.charges.data[0].receipt_url}</li>
                    </ul>
                    """
            owner_body = f"""<p>Congratulations! You just received a new donation.</p>
                    <p>Donation details:</p>
                    <ul>
                    <li>Donated to: {donation.membership_package.organisation_name}</li>
                    <li>Donated by: {donation.full_name or "Anonymous"}</li>
                    <li>Amount: £{donation.amount}</li>
                    <li>Gift aid: {gift_aid_string}</li>
                    <li>Receipt: {payment_confirm.charges.data[0].receipt_url}</li>
                    <li>Message from donator: {donation.message or "No message given"}</li>
                    </ul>
                    """

            # send to donator
            send_email(f"Donation Confirmation: {donation.membership_package.organisation_name}",
                       form_data['email_address'][0], donator_body, send_to=donation.email_address)
            # send to org owner
            send_email(f"Donation Confirmation: {donation.membership_package.organisation_name}",
                       full_name, owner_body, send_to=donation.membership_package.owner.email, reply_to=form_data['email_address'][0])

            # send success result!
            result = {'result': 'success',
                      'receipt': payment_confirm.charges.data[0].receipt_url}
            return HttpResponse(dumps(result))


def donation(request):
    org_name = request.GET.get('org-name', '')

    # get all packages, as user may not be logged in
    all_packages = MembershipPackage.objects.filter(enabled=True)

    # check that an organisation name was given
    if org_name != '':
        # check the organisation name matches an organisation
        for package in all_packages:
            if org_name == package.organisation_name:
                return render(request, 'donation.html', {'org_name': org_name,
                                                         'public_api_key': get_stripe_public_key(request)})
    # nothing given for oganisation name
    else:
        return render(request, 'donation.html', {'org_name': 'not_given',
                                                 'public_api_key': get_stripe_public_key(request)})
    # organisation name given did not match an enabled organisation
    return render(request, 'donation.html', {'org_name': 'not_match',
                                             'public_api_key': get_stripe_public_key(request),
                                             'all_packages': all_packages})


def send_payment_error(error):
    body = error.json_body
    err = body.get('error', {})

    feedback = "<strong>Status is:</strong> %s" % error.http_status
    feedback += "<br><strong>Type is:</strong> %s" % err.get('type')
    feedback += "<br><strong>Code is:</strong> %s" % err.get('code')
    feedback += "<br><strong>Message is:</strong> <span class='text-danger'>%s</span>" % err.get('message')
    return feedback


class HomeBase(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = LoginForm()
        return context

class HomePage(HomeBase):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        else:
            return super().get(request, *args, **kwargs)


class DashboardBase(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class Dashboard(LoginRequiredMixin, DashboardBase):
    template_name = 'dashboard.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['membership_package'] = MembershipPackage.objects.get(owner=self.request.user)
            context['members'] = Member.objects.filter(subscription__membership_package=context['membership_package'],
                                                       subscription__price__isnull=False)
            context['joined_packages'] = []
            for package in MembershipPackage.objects.all():
                for member in Member.objects.filter(user_account=self.request.user):
                    if member.subscription.filter(membership_package=package).count() > 0:
                        context['joined_packages'].append(package)
                    
        except MembershipPackage.DoesNotExist:
            pass

        return context

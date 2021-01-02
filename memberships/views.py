from django.shortcuts import render, redirect, HttpResponseRedirect, reverse
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from membership.models import MembershipPackage


def donation_payment(request):
    if request.POST:
        donation = Donation.objects.get(donator=request.user)
        donation.organisation_name = request.POST.get('donate-organisation')
        donation.full_name = request.POST.get('donator-full-name')
        donation.email_address = request.POST.get('donator-email')

        # get strip secret key
        stripe.api_key = get_stripe_secret_key(request)

        # create or get customer id
        if not donation.stripe_owner_id:
            # create stripe user
            customer = stripe.Customer.create(
                name=request.user.get_full_name(),
                email=request.user.email
            )
            customer_id = customer['id']
            donation.stripe_owner_id = customer_id
            donation.save()
        else:
            stripe.Customer.modify(
                donation.stripe_owner_id,
                name=request.user.get_full_name(),
                email=request.user.email
            )

        # validate the card
        result = validate_card(request, 'package')
        if result['result'] == 'fail':
            return HttpResponse(dumps(result))

        subscription = stripe.Subscription.create(
            customer=donation.stripe_owner_id,
            items=[
                {
                    "plan": price_id,
                },
            ],
        )
        if subscription['status'] != 'active':
            result = {'result': 'fail',
                      'feedback': f"<strong>Failure message:</strong> <span class='text-danger'>{subscription['status']}</span>"}
            return HttpResponse(dumps(result))
        else:
            invoice = stripe.Invoice.list(customer=membership_package.stripe_owner_id, subscription=subscription.id, limit=1)
            receipt = stripe.Charge.list(customer=membership_package.stripe_owner_id)

            result = {'result': 'success',
                      'invoice': invoice.data[0].invoice_pdf,
                      'receipt': receipt.data[0].receipt_url}

            membership_package.enabled = True
            membership_package.save()

            # send confirmation email
            body = f"""<p>This is a confirmation email for your new donation.

                    <ul>
                    <li>Donated to: {membership_package.organisation_name}</li>
                    </ul>

                    <p>Thank you for choosing Cloud-Lines Memberships and please contact us if you need anything.</p>

                    """
            send_email(f"Donation Confirmation: {membership_package.organisation_name}",
                       request.user.get_full_name(), body, send_to=request.user.email, reply_to=request.user.email)
            send_email(f"Donation Confirmation: {membership_package.organisation_name}",
                       request.user.get_full_name(), body, reply_to=request.user.email)

            return HttpResponse(dumps(result))


class DashboardBase(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class Dashboard(LoginRequiredMixin, DashboardBase):
    template_name = 'dashboard.html'
    login_url = '/accounts/login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['membership_package'] = MembershipPackage.objects.get(owner=self.request.user)
        except MembershipPackage.DoesNotExist:
            pass
        return context

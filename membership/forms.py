from .models import MembershipPackage, Member, MembershipSubscription, Payment, Equine
from django.utils.translation import gettext_lazy as _
from django import forms


class MembershipPackageForm(forms.ModelForm):
    class Meta:
        model = MembershipPackage
        fields = '__all__'
        exclude = ('owner',
                   'admins',
                   'members',
                   'stripe_acct_id',
                   'stripe_owner_id',
                   'stripe_product_id',
                   'bolton',
                   'cloud_lines_account',
                   'enabled')
        help_texts = {
            # 'service': _('If your query is not regarding a service, leave this blank.'),
        }
        widgets = {
            'organisation_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.Select(attrs={'class': 'form-control'})
        }


class MemberForm(forms.ModelForm):
    email = forms.EmailField()
    first_name = forms.CharField()
    last_name = forms.CharField()

    class Meta:
        model = Member
        fields = '__all__'
        exclude = ('user_account',)
        help_texts = {
            # 'service': _('If your query is not regarding a service, leave this blank.'),
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'town': forms.TextInput(attrs={'class': 'form-control'}),
            'county': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postcode': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'})
        }


class MemberSubscriptionForm(forms.ModelForm):
    class Meta:
        model = MembershipSubscription
        fields = '__all__'
        exclude = ('member',
                   'membership_package',
                   'stripe_id',
                   'stripe_subscription_id',
                   'validated')
        help_texts = {
            # 'service': _('If your query is not regarding a service, leave this blank.'),
        }
        widgets = {
            'record_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'billing_period': forms.Select(attrs={'class': 'form-control'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'
        exclude = ('subscription', 'stripe_payment_id', 'payment_number')
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'payment_number': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.TextInput(attrs={'class': 'form-control'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'created': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'gift_aid': forms.CheckboxInput(attrs={'class': ''}),
            'gift_aid_percentage': forms.TextInput(attrs={'class': 'form-control'}),
        }


class EquineForm(forms.ModelForm):
    class Meta:
        model = Equine
        fields = '__all__'
        exclude = ('membership_package',
                   'subscription')
        widgets = {
            'date_resigned': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'date_entered': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'date_updated': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'actual_renewal': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'fk_renewal_status': forms.TextInput(attrs={'class': 'form-control'}),
            'mail_tag': forms.CheckboxInput(attrs={'class': ''}),
            'anonymous': forms.CheckboxInput(attrs={'class': ''}),
            'do_not_mail': forms.CheckboxInput(attrs={'class': ''}),
            'do_not_mail_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'do_not_mail_reason': forms.TextInput(attrs={'class': 'form-control'}),
            'area_code': forms.TextInput(attrs={'class': 'form-control'}),
            'overseas': forms.CheckboxInput(attrs={'class': ''}),
            'home_telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'office_telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'source': forms.TextInput(attrs={'class': 'form-control'}),
            'donor': forms.CheckboxInput(attrs={'class': ''}),
            'signature_given_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'owner_breeder': forms.CheckboxInput(attrs={'class': ''}),
            'volunteer': forms.CheckboxInput(attrs={'class': ''}),
            'no_raffle_tickets': forms.CheckboxInput(attrs={'class': ''}),
            'so_started': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'so_amount': forms.TextInput(attrs={'class': 'form-control'}),
            'bad_address': forms.CheckboxInput(attrs={'class': ''}),
            'second_name': forms.TextInput(attrs={'class': 'form-control'}),
            'returned_gdpr_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'gift_aid_decision': forms.CheckboxInput(attrs={'class': ''}),
            'gift_aid_type': forms.TextInput(attrs={'class': 'form-control'}),
            'gift_aid_decision_made_on': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'gift_aid_signature': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_via_email': forms.CheckboxInput(attrs={'class': ''}),
            'contact_via_email_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'gdpr_post': forms.CheckboxInput(attrs={'class': ''}),
            'gdpr_email': forms.CheckboxInput(attrs={'class': ''}),
            'gdpr_phone': forms.CheckboxInput(attrs={'class': ''}),
        }

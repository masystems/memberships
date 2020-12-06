from .models import MembershipPackage, Member, Equine
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
                   'membership_price_per_month_id',
                   'membership_price_per_year_id',
                   'cloud_lines_account',
                   'enabled')
        help_texts = {
            # 'service': _('If your query is not regarding a service, leave this blank.'),
        }
        widgets = {
            'organisation_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bolton': forms.Select(attrs={'class': 'form-control'}),
            'membership_price_per_month': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '£'}),
            'membership_price_per_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '£'}),
        }


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = '__all__'
        exclude = ('membership_package',
                   'user_account',
                   'stripe_id',
                   'stripe_subscription_id')
        help_texts = {
            # 'service': _('If your query is not regarding a service, leave this blank.'),
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'town': forms.TextInput(attrs={'class': 'form-control'}),
            'county': forms.TextInput(attrs={'class': 'form-control'}),
            'postcode': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.NumberInput(attrs={'class': 'form-control'}),

            'record_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'membership_number': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),

            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'billing_period': forms.Select(attrs={'class': 'form-control'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class EquineForm(forms.ModelForm):
    class Meta:
        model = Equine
        fields = '__all__'
        exclude = ('membership_package',
                   'member')
        widgets = {
            'animal_owner': forms.CheckboxInput(attrs={'class': ''}),
            'badge': forms.CheckboxInput(attrs={'class': ''}),
            'expired': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'actual_renewal': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'standing_order_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '£'}),
            'standing_order_started': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'gift_aid': forms.CheckboxInput(attrs={'class': ''}),
            'signature_given_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),

            'do_not_mail': forms.CheckboxInput(attrs={'class': ''}),
            'want_raffle_tickets': forms.CheckboxInput(attrs={'class': ''}),
            'overseas': forms.CheckboxInput(attrs={'class': ''}),
            'bad_address': forms.CheckboxInput(attrs={'class': ''}),
            'returned_gdpr_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'gdpr_post': forms.CheckboxInput(attrs={'class': ''}),
            'gdpr_email': forms.CheckboxInput(attrs={'class': ''}),
            'gdpr_phone': forms.CheckboxInput(attrs={'class': ''}),

        }

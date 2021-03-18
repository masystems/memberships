from django import forms
from allauth.account.forms import SignupForm
from membership.models import Member, Donation


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=255, label='First Name', widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=255, label='Last Name', widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    address_line_1 = forms.CharField(max_length=255, label='Address Line 1', widget=forms.TextInput(attrs={'placeholder': 'Address Line 1'}))
    address_line_2 = forms.CharField(max_length=255, label='Address Line 2', widget=forms.TextInput(attrs={'placeholder': 'Address Line 2'}), required=False)
    town = forms.CharField(max_length=255, label='Town', widget=forms.TextInput(attrs={'placeholder': 'Town'}), required=False)
    county = forms.CharField(max_length=255, label='County', widget=forms.TextInput(attrs={'placeholder': 'County'}), required=False)
    country = forms.CharField(max_length=255, label='Country', widget=forms.TextInput(attrs={'placeholder': 'Country'}), required=False)
    postcode = forms.CharField(max_length=255, label='Postcode', widget=forms.TextInput(attrs={'placeholder': 'Postcode'}))

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        member = Member(user_account=user)
        member.address_line_1 = self.cleaned_data['address_line_1']
        member.postcode = self.cleaned_data['postcode']
        if self.cleaned_data['address_line_2']:
            member.address_line_2 = self.cleaned_data['address_line_2']
        if self.cleaned_data['town']:
            member.town = self.cleaned_data['town']
        if self.cleaned_data['county']:
            member.county = self.cleaned_data['county']
        if self.cleaned_data['country']:
            member.country = self.cleaned_data['country']
        if self.cleaned_data['postcode']:
            member.postcode = self.cleaned_data['postcode']

        member.save()
        user.save()
        return user


class RegisterForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control','placeholder':'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Password'}))
    password_repeat = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control','placeholder':'Repeat Password'}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Forename'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Surname'}))
    terms = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class':'form-control'}))


# class DonationForm(forms.ModelForm):
#     class Meta:
#         model = Donation
#         fields = '__all__'
#         exclude = ('donator', 'membership_package')
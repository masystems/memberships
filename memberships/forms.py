from django import forms
from allauth.account.forms import SignupForm
from membership.models import Member, Donation


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=255, label='First Name', widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=255, label='Last Name', widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        member = Member(user_account=user)
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
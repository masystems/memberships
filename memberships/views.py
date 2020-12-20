from django.shortcuts import render, redirect, HttpResponseRedirect, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import auth
from django.contrib.auth.models import User
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from membership.models import MembershipPackage, Member
from memberships.functions import generate_username
from .forms import RegisterForm


def login_user(request):
    if request.method == 'POST':
        user = auth.authenticate(request, username=request.POST['email'], password=request.POST['password'])

        if user is not None:
            auth.login(request, user)
            return redirect('dashboard')
        else:
            return render(request, '/accounts/login.html', {'error': 'Username and/or password not recognised.'})
    else:
        return render(request, '/accounts/login.html')


def register(request):
    # if this is a POST request we need to process the form data
    template = 'register.html'

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = RegisterForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            if User.objects.filter(email=form.cleaned_data['email']).exists():
                return render(request, template, {
                    'form': form,
                    'error_message': 'Email already exists.'
                })
            elif not form.cleaned_data['terms']:
                return render(request, template, {
                    'form': form,
                    'error_message': 'Please read and sign the terms'
                })
            elif form.cleaned_data['password'] != form.cleaned_data['password_repeat']:
                return render(request, template, {
                    'form': form,
                    'error_message': 'Passwords do not match.'
                })
            else:
                # Create the user:
                user = User.objects.create_user(
                    generate_username(form.cleaned_data['first_name'], form.cleaned_data['last_name']),
                    form.cleaned_data['email'],
                    form.cleaned_data['password']
                )
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.save()

                # Login the user
                login(request, user)

                # redirect to accounts page:
                return redirect('dashboard')

    # No post data availabe, let's just show the page.
    else:
        form = RegisterForm()

    return render(request, template, {'form': form})


@login_required(login_url='/accounts/login')
def logout_user(request):
    logout(request)
    return redirect('dashboard')


class DashboardBase(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class Dashboard(LoginRequiredMixin, DashboardBase):
    template_name = 'dashboard.html'
    login_url = '/accounts/login'

    def dispatch(self, request, *args, **kwargs):
        """
        if only 1 org account, redirect to org page
        if only 1 membership account, redirect to member profile
        if multiple of anything, return
        :return:
        """
        if not self.request.user.is_authenticated:
            return HttpResponseRedirect('/accounts/login')

        self.context = super().get_context_data(**kwargs)
        self.context['membership_packages'] = MembershipPackage.objects.filter(Q(owner=self.request.user) |
                                                                               Q(admins=self.request.user))
        self.context['memberships'] = Member.objects.filter(user_account=self.request.user)
        if len(self.context['membership_packages']) == 1 and len(self.context['memberships']) == 0:
            return HttpResponseRedirect(
                reverse('membership_package', args=(self.context['membership_packages'][0].organisation_name,)))
        elif len(self.context['memberships']) == 1 and len(self.context['membership_packages']) == 0:
            return HttpResponseRedirect(reverse('member_profile',
                                                args=(self.context['memberships'][0].membership_package.organisation_name,
                                                      self.context['memberships'][0].id)))
        else:
            return super().dispatch(request, *args, **kwargs)

    # def get_context_data(self, **kwargs):
    #     self.context = super().get_context_data(**kwargs)
    #     # check account statuses and redirect as appropriate
    #     #return self.context




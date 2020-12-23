from django.shortcuts import render, redirect, HttpResponseRedirect, reverse
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from membership.models import MembershipPackage, Member


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




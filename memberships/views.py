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

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        # check account statuses and redirect as appropriate
        return self.context

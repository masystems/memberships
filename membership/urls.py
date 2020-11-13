from django.urls import path
from . import views


urlpatterns = [
    path('', views.Membership.as_view(), name="membership"),
    path('create-membership-package', views.CreateMembershipPackageView.as_view(), name="create_membership_package"),
    path('add-member', views.AddMember.as_view(), name="add_member"),
]

from django.urls import path
from . import views


urlpatterns = [
    path('', views.SelectMembershipPackageView.as_view(), name="membership"),
    path('org/<str:title>', views.MembershipPackageView.as_view(), name="membership_package"),
    path('org/select-package', views.SelectMembershipPackageView.as_view(), name="select_package"),
    path('organisation-payment', views.organisation_payment, name='organisation_payment'),
    path('create-package-on-stripe', views.create_package_on_stripe, name='create_package_on_stripe'),
    path('membership-package-settings', views.CreateMembershipPackage.as_view(), name="membership_package_settings"),
    path('member-form/<str:title>', views.MemberRegForm.as_view(), name="member_form"),
    path('member-bolton-form/<str:title>/<int:pk>', views.member_bolton_form, name="member_bolton_form"),
    path('edit-member/<str:title>/<int:pk>', views.UpdateMember.as_view(), name="edit_member"),
    path('member-payment/<str:title>/<int:pk>', views.MemberPaymentView.as_view(), name="member_payment"),
    path('validate-card', views.validate_card, name="validate_card"),
    path('member-profile/<str:title>/<int:pk>', views.MemberProfileView.as_view(), name="member_profile"),
    path('delete-organisation/<str:title>', views.delete_membership_package, name="delete_organisation"),
]

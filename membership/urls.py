from django.urls import path
from . import views


urlpatterns = [
    path('', views.SelectMembershipPackageView.as_view(), name="membership"),
    path('org/<str:title>', views.MembershipPackageView.as_view(), name="membership_package"),
    path('org/select-package', views.SelectMembershipPackageView.as_view(), name="select_package"),
    path('organisation-payment', views.organisation_payment, name='organisation_payment'),
    path('create-package-on-stripe', views.create_package_on_stripe, name='create_package_on_stripe'),
    path('membership-package-settings', views.MembershipPackageSettings.as_view(), name="membership_package_settings"),
    path('add-member/<str:title>', views.AddMember.as_view(), name="add_member"),
    path('edit-member/<str:title>/<int:pk>', views.UpdateMember.as_view(), name="edit_member"),
    path('member-payment/<str:title>/<int:pk>', views.MemberPaymentView.as_view(), name="member_payment"),
    path('validate-card', views.validate_card, name="validate_card"),
]

from django.urls import path
from . import views


urlpatterns = [
    path('', views.SelectMembershipPackageView.as_view(), name="membership"),
    path('org/<str:title>', views.MembershipPackageView.as_view(), name="membership_package"),
    path('org/<str:title>/manage-admins', views.manage_admins, name="manage_admins"),
    path('org/<str:title>/manage-membership-types', views.manage_membership_types, name="manage_membership_types"),
    path('org/<str:title>/manage-payment-methods', views.manage_payment_methods, name="manage_payment_methods"),
    path('org/select-package', views.SelectMembershipPackageView.as_view(), name="select_package"),
    path('get-members/<str:title>', views.get_members, name="get_members"),
    path('get-members-detailed/<str:title>', views.get_members_detailed, name="get_members_detailed"),
    path('organisation-payment', views.organisation_payment, name='organisation_payment'),
    path('create-package-on-stripe', views.create_package_on_stripe, name='create_package_on_stripe'),
    path('membership-package-settings', views.CreateMembershipPackage.as_view(), name="membership_package_settings"),
    path('members-detailed/<str:title>', views.MembersDetailed.as_view(), name="members_detailed"),
    path('member-payments/<str:title>/<int:pk>', views.member_payments, name="member_payments"),
    path('member-payment-form/<str:title>/<int:pk>', views.member_payment_form, name="member_payment_form"),
    path('member-payment-form-edit/<str:title>/<int:pk>/<int:payment_id>', views.member_payment_form_edit, name="member_payment_form_edit"),
    path('get-member-payments/<str:title>/<int:pk>', views.get_member_payments, name="get_member_payments"),
    path('member-form/<str:title>/<int:pk>', views.member_reg_form, name="member_form"),
    path('member-bolton-form/<str:title>/<int:pk>', views.member_bolton_form, name="member_bolton_form"),
    path('edit-sub-comment/<int:id>', views.edit_sub_comment, name="edit_sub_comment"),
    path('member-payment/<str:title>/<int:pk>', views.MemberPaymentView.as_view(), name="member_payment"),
    path('update_membership_type/<str:title>/<int:pk>', views.update_membership_type, name="update_membership_type"),
    path('validate-card', views.validate_card, name="validate_card"),
    path('member-profile/<int:pk>', views.MemberProfileView.as_view(), name="member_profile"),
    path('delete-membership-package/<str:title>', views.delete_membership_package, name="delete_membership_package"),
    path('remove-member/<str:title>/<int:pk>', views.remove_member, name="remove_member"),
    path('update_user/<int:pk>', views.update_user, name='update_user'),
    path('payment-reminder/<str:title>/<int:pk>', views.payment_reminder, name='payment_reminder'),
]

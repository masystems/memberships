from django.urls import path
from . import views
from . import tabledata
from . import reports

urlpatterns = [
    path('', views.SelectMembershipPackageView.as_view(), name="membership"),
    path('org/<str:title>', views.MembershipPackageView.as_view(), name="membership_package"),
    path('org/<str:title>/manage-admins', views.manage_admins, name="manage_admins"),
    path('org/<str:title>/manage-membership-types', views.manage_membership_types, name="manage_membership_types"),
    path('org/<str:title>/manage-payment-methods', views.manage_payment_methods, name="manage_payment_methods"),
    path('org/<str:title>/manage-custom-fields', views.manage_custom_fields, name="manage_custom_fields"),
    path('org/<str:title>/manage-payment-reminder', views.manage_payment_reminder, name="manage_payment_reminder"),
    path('org/<str:title>/manage-reports', views.manage_reports, name="manage_reports"),
    path('org/<str:title>/manage-donation', views.manage_donation, name="manage_donation"),
    path('org/<str:title>/manage-account', views.manage_account, name="manage_account"),
    path('org/<str:title>/report/<str:report>/<str:file_type>', reports.reports, name="reports"),
    path('org/select-package', views.SelectMembershipPackageView.as_view(), name="select_package"),
    path('get-members/<str:title>', tabledata.get_members, name="get_members"),
    path('get-members-detailed/<str:title>', tabledata.get_members_detailed, name="get_members_detailed"),
    path('export_members_detailed/<str:title>', reports.export_members_detailed, name="export_members_detailed"),
    path('export_payments_detailed/<str:title>', reports.export_payments_detailed, name="export_payments_detailed"),
    path('organisation-payment', views.organisation_payment, name='organisation_payment'),
    path('create-package-on-stripe', views.create_package_on_stripe, name='create_package_on_stripe'),
    path('create_stripe_subscription', views.create_stripe_subscription, name='create_stripe_subscription'),
    path('membership-package-settings', views.CreateMembershipPackage.as_view(), name="membership_package_settings"),
    path('members-detailed/<str:title>', views.MembersDetailed.as_view(), name="members_detailed"),
    path('delete-payment/<str:title>/<int:pk>/<int:payment_id>/', views.delete_payment, name="delete_payment"),
    path('payments-detailed/<str:title>', views.payments_detailed, name="payments_detailed"),
    path('member-payments/<str:title>/<int:pk>', views.member_payments, name="member_payments"),
    path('member-payment-form/<str:title>/<int:pk>', views.member_payment_form, name="member_payment_form"),
    path('member-payment-form-edit/<str:title>/<int:pk>/<int:payment_id>/', views.member_payment_form_edit, name="member_payment_form_edit"),
    path('get-member-payments/<str:title>/<int:pk>', tabledata.get_member_payments, name="get_member_payments"),
    path('get-all-member-payments/<str:title>', tabledata.get_all_member_payments, name="get_all_member_payments"),
    path('member-form/<str:title>/<int:pk>', views.member_reg_form, name="member_form"),
    path('member-bolton-form/<str:title>/<int:pk>', views.member_bolton_form, name="member_bolton_form"),
    path('edit-sub-comment/<int:id>', views.edit_sub_comment, name="edit_sub_comment"),
    path('member-payment/<str:title>/<int:pk>', views.MemberPaymentView.as_view(), name="member_payment"),
    path('update_membership_type/<str:title>/<int:pk>', views.update_membership_type, name="update_membership_type"),
    path('validate-card', views.validate_card, name="validate_card"),
    path('member-profile/<int:pk>', views.MemberProfileView.as_view(), name="member_profile"),
    path('delete-membership-package/<str:title>', views.delete_membership_package, name="delete_membership_package"),
    path('remove-member/<str:title>/', views.remove_member, name="remove_member"),
    path('update-membership-status/<int:pk>/<str:status>/<str:title>', views.update_membership_status, name="update_membership_status"),
    path('update_user/<int:pk>', views.update_user, name='update_user'),
    path('payment-reminder/<str:title>/<int:pk>', views.payment_reminder, name='payment_reminder'),
    path('get-donations/<str:title>', tabledata.get_donations, name="get_donations"),
    path('account_deletion', views.account_deletion, name='account_deletion'),
]

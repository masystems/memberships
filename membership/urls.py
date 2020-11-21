from django.urls import path
from . import views


urlpatterns = [
    path('', views.MembershipPackageView.as_view(), name="membership"),
    path('membership-package-settings', views.MembershipPackageSettings.as_view(), name="membership_package_settings"),
    path('add-member', views.AddMember.as_view(), name="add_member"),
    path('edit-member/<int:pk>', views.UpdateMember.as_view(), name="edit_member"),
    path('validate-card', views.validate_card, name="validate_card"),
]

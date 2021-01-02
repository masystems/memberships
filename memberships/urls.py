from django.contrib import admin
from django.urls import path, include
from memberships import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.Dashboard.as_view(), name="dashboard"),
    path('api/', include('api.urls')),
    path('donation-payment', views.donation_payment, name='donation_payment'),
    path('membership/', include('membership.urls')),
    path('accounts/', include('allauth.urls')),
]
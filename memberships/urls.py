from django.contrib import admin
from django.urls import path, include
from memberships import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.HomePage.as_view(), name="homepage"),
    path('dashboard/', views.Dashboard.as_view(), name="dashboard"),
    path('api/', include('api.urls')),
    path('donation-payment', views.donation_payment, name='donation_payment'),
    path('donation/', views.donation, name='donation'),
    path('membership/', include('membership.urls')),
    path('accounts/', include('allauth.urls')),
]
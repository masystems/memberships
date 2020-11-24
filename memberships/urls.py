from django.contrib import admin
from django.urls import path, include
from memberships import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.Dashboard.as_view(), name="dashboard"),
    path('login/', views.login_user, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_user, name='logout'),
    path('membership/', include('membership.urls')),
]

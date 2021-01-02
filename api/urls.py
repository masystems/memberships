from . import views
from rest_framework import routers

router = routers.SimpleRouter()
#router.register('account_admin', views.AccountAdmin, basename='account_admin')
urlpatterns = router.urls

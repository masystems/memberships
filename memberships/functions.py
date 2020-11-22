from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.conf import settings
from random import randint


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_password(password):
                return user
        return None


def generate_username(first_name, last_name):
    return f"{first_name.lower().replace(' ', '')}.{last_name.lower().replace(' ', '')}{randint(1000, 999999)}"


def get_stripe_secret_key(request):
    if request.user.is_superuser:
        return settings.STRIPE_SECRET_TEST_KEY
    else:
        return settings.STRIPE_SECRET_KEY
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend

from emailauth.models import UserEmail


class EmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        try:
            email = UserEmail.objects.get(email=username, verified=True)
            if email.user.check_password(password):
                return email.user
        except UserEmail.DoesNotExist:
            return None


class FallbackBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        try:
            user = User.objects.get(username=username)
            if (user.check_password(password) and
                not UserEmail.objects.filter(user=user).count()):

                return user

        except User.DoesNotExist:
            return None

import re
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from .models import UserProfile

class EmailOrCPFBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        User = get_user_model()
        identifier = username.strip()
        digits = re.sub(r"\D", "", identifier)
        try:
            if "@" in identifier:
                user = User.objects.get(email__iexact=identifier)
            elif len(digits) == 11:
                user = UserProfile.objects.select_related("user").get(cpf=digits).user
            else:
                return None
        except (User.DoesNotExist, UserProfile.DoesNotExist, User.MultipleObjectsReturned):
            return None
        return user if user.check_password(password) and self.user_can_authenticate(user) else None

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q

class EmailBackend(ModelBackend):
    """
    Custom authentication backend to allow users to log in with their email address.
    """
    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        try:
            # If email is provided directly, use it
            if email:
                user = User.objects.get(email=email)
            # Otherwise, try to use the username field as email
            elif username:
                user = User.objects.get(Q(email=username) | Q(username=username))
            else:
                return None
                
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

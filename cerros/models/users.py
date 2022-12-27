from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from .andinists import Andinist

class CustomUserManager(BaseUserManager):

  def create_user(self, email, password=None):
    if not email:
      raise ValueError('Users must have an email address')

    user = self.model(
      email=self.normalize_email(email),
    )

    user.set_password(password)
    user.save(using=self._db)
    return user
      
  def create_superuser(self, email, password=None):
    user = self.create_user(
      email,
      password=password,
    )
    user.is_admin = True
    user.is_superuser = True
    user.is_staff = True
    user.save(using=self._db)
    return user

class CustomUser(AbstractUser):
  username = None
  email = models.EmailField(unique=True)
  andinist = models.ForeignKey(Andinist, on_delete=models.CASCADE, null=True, blank=True)

  objects = CustomUserManager()

  USERNAME_FIELD = 'email'
  REQUIRED_FIELDS = []

  class Meta:
    verbose_name = "Usuario"
    verbose_name_plural = "Usuarios"

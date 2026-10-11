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
  # Linked andinist profile ("reclamar mi perfil", approved by an editor).
  # SET_NULL: deleting an andinist record must not delete the account.
  andinist = models.ForeignKey(Andinist, on_delete=models.SET_NULL, null=True, blank=True)
  # Name shown next to the user's contributions.
  public_name = models.CharField("Nombre público", max_length=80, blank=True, default="")
  privacy_accepted_at = models.DateTimeField("Aceptó la política de privacidad", null=True, blank=True)

  objects = CustomUserManager()

  USERNAME_FIELD = 'email'
  REQUIRED_FIELDS = []

  class Meta:
    verbose_name = "Usuario"
    verbose_name_plural = "Usuarios"


class AndinistClaim(models.Model):
  """A user asks to be linked to an andinist record; an editor approves it."""

  PENDING, APPROVED, REJECTED = 0, 1, 2
  STATUS_CHOICES = ((PENDING, "Pendiente"), (APPROVED, "Aprobado"), (REJECTED, "Rechazado"))

  user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="andinist_claims", verbose_name="Usuario")
  andinist = models.ForeignKey(Andinist, on_delete=models.CASCADE, related_name="claims", verbose_name="Andinista")
  message = models.TextField("Mensaje", blank=True, max_length=1000)
  status = models.IntegerField("Estado", choices=STATUS_CHOICES, default=PENDING)
  created_at = models.DateTimeField("Enviado", auto_now_add=True)
  reviewed_by = models.ForeignKey(
    CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Revisado por"
  )
  reviewed_at = models.DateTimeField("Revisado", null=True, blank=True)

  class Meta:
    verbose_name = "Reclamo de perfil de andinista"
    verbose_name_plural = "Reclamos de perfil de andinista"
    ordering = ["status", "-created_at"]

  def __str__(self):
    return f"{self.user} → {self.andinist}"

from django.db import models

from .users import CustomUser


class Proposal(models.Model):
  """A change proposed by a user to a record (or a new record), applied only
  when an editor approves it. Logic in cerros/proposals.py."""

  MOUNTAIN, ROUTE, ASCENT, ANDINIST = "mountain", "route", "ascent", "andinist"
  TARGET_CHOICES = ((MOUNTAIN, "Cerro"), (ROUTE, "Ruta"), (ASCENT, "Ascenso"), (ANDINIST, "Andinista"))

  PENDING, NEEDS_INFO, APPROVED, REJECTED, WITHDRAWN = 0, 1, 2, 3, 4
  STATUS_CHOICES = (
    (PENDING, "Pendiente"),
    (NEEDS_INFO, "Se pidió más información"),
    (APPROVED, "Aprobada"),
    (REJECTED, "Rechazada"),
    (WITHDRAWN, "Retirada"),
  )
  OPEN = (PENDING, NEEDS_INFO)

  author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="proposals", verbose_name="Autor")
  target_model = models.CharField("Tipo", max_length=20, choices=TARGET_CHOICES)
  target_id = models.PositiveIntegerField("Ficha", null=True, blank=True)  # set on approval for new records
  creates = models.BooleanField("Ficha nueva", default=False)
  target_label = models.CharField("Título", max_length=255, blank=True)
  changes = models.JSONField("Cambios propuestos", default=dict)  # {field: value}
  original = models.JSONField("Valores al proponer", default=dict)  # {field: value} before
  applied = models.JSONField("Valores aplicados", null=True, blank=True)  # if the editor adjusted them
  source = models.TextField("Fuente", max_length=1000)
  comment = models.TextField("Comentario", max_length=2000, blank=True)
  status = models.IntegerField("Estado", choices=STATUS_CHOICES, default=PENDING)
  editor_message = models.TextField("Mensaje del editor", max_length=2000, blank=True)
  reviewed_by = models.ForeignKey(
    CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="Revisada por"
  )
  reviewed_at = models.DateTimeField("Revisada", null=True, blank=True)
  created_at = models.DateTimeField("Enviada", auto_now_add=True)
  updated_at = models.DateTimeField("Actualizada", auto_now=True)

  class Meta:
    verbose_name = "Propuesta"
    verbose_name_plural = "Propuestas"
    ordering = ["status", "-created_at"]
    indexes = [models.Index(fields=["target_model", "target_id", "status"])]

  def __str__(self):
    kind = "Cerro nuevo" if self.creates else self.get_target_model_display()
    return f"#{self.pk} {kind}: {self.target_label}"

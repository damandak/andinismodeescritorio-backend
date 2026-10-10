import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from django.utils.safestring import mark_safe
from PIL import Image as PILImage
from PIL import ImageOps

from .andinists import Andinist
from .base import BaseModel

EXIF_ORIENTATION = 0x0112


def _fit_box(width, height, target_height, min_width):
    """Box for a thumbnail `target_height` tall, but never narrower than
    `min_width` (wide-enough thumbnails for very tall photos)."""
    if height <= target_height:
        return (width, height)
    box_width = int(width * target_height / height)
    box_height = target_height
    if box_width < min_width:
        box_width = min_width
        box_height = int(height * min_width / width)
    return (box_width, box_height)


# name -> (field, file suffix, box function(width, height), JPEG quality)
VARIANTS = {
    # Mountain page and blog cards: 400 px tall (at least 600 wide).
    "cover": ("tb_item_cover", "cover", lambda w, h: _fit_box(w, h, 400, 600), 80),
    # Admin list and small previews: 100 px tall (at least 150 wide).
    "small": ("tb_small", "small", lambda w, h: _fit_box(w, h, 100, 150), 80),
    # Large photos (blog headers, full-width images, high-density screens).
    "medium": ("tb_medium", "medium", lambda w, h: (1600, 1600), 82),
}


def _to_rgb(img):
    """JPEG has no transparency: flatten transparent images on white."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        background = PILImage.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.getchannel("A"))
        return background
    return img.convert("RGB") if img.mode != "RGB" else img


class Image(BaseModel):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="images")
    date_captured = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    author = models.ForeignKey(
        Andinist,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="author",
    )
    tb_item_cover = models.ImageField(upload_to="images", null=True, blank=True)
    tb_small = models.ImageField(upload_to="images", null=True, blank=True)
    tb_medium = models.ImageField(upload_to="images", null=True, blank=True)
    # Size of the original as displayed (after applying the EXIF rotation).
    width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    height = models.PositiveIntegerField(null=True, blank=True, editable=False)

    def __str__(self):
        return self.name

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_image_name = instance.image.name if "image" in field_names else None
        return instance

    def image_tag(self):
        return mark_safe('<img src="%s" width="150" height="150" />' % self.image.url)

    def tb_image_tag(self):
        thumb = self.tb_small or self.image
        return mark_safe('<img src="%s" height="60" />' % thumb.url) if thumb else ""

    tb_image_tag.short_description = "Miniatura"

    def missing_variants(self):
        return (
            self.width is None
            or self.height is None
            or any(not getattr(self, field) for field, *_ in VARIANTS.values())
        )

    def generate_variants(self):
        """(Re)create the cover, small and medium JPEGs from the original.

        - Applies the EXIF rotation, so phone photos are not shown sideways.
        - Flattens transparency (PNG) instead of failing.
        - Decodes large JPEGs at reduced size (draft), so a 24 MP photo does
          not need hundreds of MB of RAM on the server.
        - Deletes the previous thumbnail files instead of leaving them behind.
        """
        with self.image.open("rb") as f, PILImage.open(f) as src:
            raw_width, raw_height = src.size
            rotated = src.getexif().get(EXIF_ORIENTATION) in (5, 6, 7, 8)
            width, height = (raw_height, raw_width) if rotated else (raw_width, raw_height)

            boxes = {name: spec[2](width, height) for name, spec in VARIANTS.items()}
            need = (max(b[0] for b in boxes.values()), max(b[1] for b in boxes.values()))
            if src.format == "JPEG":
                src.draft("RGB", (need[1], need[0]) if rotated else need)
            src.load()
            base = _to_rgb(ImageOps.exif_transpose(src))

        self.width, self.height = width, height
        stem = os.path.splitext(os.path.basename(self.image.name))[0]
        for name, (field, suffix, _, quality) in VARIANTS.items():
            thumb = base.copy()
            thumb.thumbnail(boxes[name], PILImage.Resampling.LANCZOS)
            buffer = BytesIO()
            thumb.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)

            file_field = getattr(self, field)
            old_name = file_field.name if file_field else None
            file_field.save(f"{stem}_{suffix}.jpg", ContentFile(buffer.getvalue()), save=False)
            if old_name and old_name != file_field.name:
                file_field.storage.delete(old_name)

    def save(self, *args, **kwargs):
        image_changed = self.image.name != getattr(self, "_loaded_image_name", None)
        # The original must be stored before it can be read.
        super().save(*args, **kwargs)
        if self.image and (image_changed or self.missing_variants()):
            self.generate_variants()
            super().save(
                update_fields=["tb_item_cover", "tb_small", "tb_medium", "width", "height"]
            )
        self._loaded_image_name = self.image.name

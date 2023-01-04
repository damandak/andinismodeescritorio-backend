from django.db import models
from io import BytesIO
from django.core.files.base import ContentFile
from .base import BaseModel
from django.utils.safestring import mark_safe
from PIL import Image as PILImage

class Image(BaseModel):
  name = models.CharField(max_length=255)
  image = models.ImageField(upload_to='images')
  date_captured = models.DateField(null=True, blank=True)
  location = models.CharField(max_length=255, null=True, blank=True)
  description = models.TextField(null=True, blank=True)
  author = models.ForeignKey('cerros.CustomUser', on_delete=models.CASCADE, related_name='images')
  tb_item_cover = models.ImageField(upload_to='images', null=True, blank=True)
  tb_small = models.ImageField(upload_to='images', null=True, blank=True)

  def __str__(self):
    return self.name

  def image_tag(self):
    return mark_safe('<img src="%s" width="150" height="150" />' % self.image.url)

  def tb_image_tag(self):
    return mark_safe('<img src="%s" width="100" height="100" />' % self.tb_small.url)

  def generate_tb_item_cover(self, img):
    if img and img.height > 400:
      baseheight = 400
      hpercent = (baseheight / float(img.height))
      wsize = int((float(img.width) * float(hpercent)))
      f = open(img.path, 'rb')
      with PILImage.open(f) as image:
        image.load()
        image.thumbnail((wsize, baseheight), PILImage.Resampling.LANCZOS)
        image_io = BytesIO()
        image.save(image_io, format='JPEG', quality=80)
        self.tb_item_cover.save('item_cover.jpg', ContentFile(image_io.getvalue()), save=False)

  def generate_tb_small(self, img):
    if img and img.height > 100:
      baseheight = 100
      hpercent = (baseheight / float(img.height))
      wsize = int((float(img.width) * float(hpercent)))
      f = open(img.path, 'rb')
      with PILImage.open(f) as image:
        image.load()
        image.thumbnail((wsize, baseheight), PILImage.Resampling.LANCZOS)
        image_io = BytesIO()
        image.save(image_io, format='JPEG', quality=80)
        self.tb_small.save('small.jpg', ContentFile(image_io.getvalue()), save=False)

  def save(self, *args, **kwargs):
    super(Image, self).save(*args, **kwargs)
    self.generate_tb_item_cover(self.image)
    self.generate_tb_small(self.image)
    super(Image, self).save(*args, **kwargs)

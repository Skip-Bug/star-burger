from django.db import models


class Location(models.Model):
    address = models.CharField(
        "Адрес",
        max_length=255,
        unique=True,
    )
    lat = models.FloatField("Широта", blank=True, null=True)
    lon = models.FloatField("Долгота", blank=True, null=True)

    class Meta:
        verbose_name = "Локация"
        verbose_name_plural = "Локации"

    def __str__(self):
        return self.address

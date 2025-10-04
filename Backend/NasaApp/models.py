from django.db import models


class Activity(models.Model):
    """
    Каталог активностей (Hiking, Rowing, Running, ...).
    """
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return self.name


class WeatherParam(models.Model):
    """
    Справочник погодных параметров и единиц измерения.
    Примеры code: TEMP_C, WIND_KMH, GUST_KMH, PRECIP_MM, PRECIP_PROB, HUMIDITY, CLOUD, UV_INDEX, PRESSURE_HPA, VIS_KM.
    """
    code = models.CharField(max_length=32, unique=True)
    unit = models.CharField(max_length=16)       # '°C', 'km/h', '%', 'mm', 'hPa', 'km' и т.д.
    description = models.CharField(max_length=160, blank=True)

    class Meta:
        indexes = [models.Index(fields=["code"])]

    def __str__(self) -> str:
        return f"{self.code} ({self.unit})"


class ActivityParam(models.Model):
    """
    M:N — какие параметры важны для конкретной активности.
    Используется, чтобы на фронт отдавать только релевантные поля.
    """
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="params")
    param = models.ForeignKey(WeatherParam, on_delete=models.CASCADE, related_name="activities")

    class Meta:
        unique_together = (("activity", "param"),)
        indexes = [
            models.Index(fields=["activity", "param"]),
        ]

    def __str__(self) -> str:
        return f"{self.activity.name} → {self.param.code}"



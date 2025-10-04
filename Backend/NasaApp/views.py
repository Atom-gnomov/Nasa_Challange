# NasaApp/views.py
from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from rest_framework import serializers, viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Activity, WeatherParam, ActivityParam
from .data_pipeline import (
    ensure_dataset,
    compute_effective_horizon,
    run_arima_and_read_row,
)

# ============================================================================
#                                SERIALIZERS
# ============================================================================

class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ["id", "name", "slug", "is_active"]


class WeatherParamSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherParam
        fields = ["id", "code", "unit", "description"]


class ActivityParamSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(read_only=True)
    activity_id = serializers.PrimaryKeyRelatedField(
        source="activity", queryset=Activity.objects.all(), write_only=True
    )
    param = WeatherParamSerializer(read_only=True)
    param_id = serializers.PrimaryKeyRelatedField(
        source="param", queryset=WeatherParam.objects.all(), write_only=True
    )

    class Meta:
        model = ActivityParam
        fields = ["id", "activity", "activity_id", "param", "param_id"]


# Лёгкий входной сериализатор для предикта (минимум проверок).
class PredictInputSerializerLight(serializers.Serializer):
    activity = serializers.SlugField(min_length=1, max_length=80)
    date = serializers.DateField()
    lat = serializers.DecimalField(max_digits=8, decimal_places=5)
    lon = serializers.DecimalField(max_digits=8, decimal_places=5)
    granularity = serializers.ChoiceField(choices=["daily", "hourly"], default="daily")
    local_tz = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Активность должна существовать и быть активной
        try:
            activity = Activity.objects.get(slug=attrs["activity"], is_active=True)
        except Activity.DoesNotExist:
            raise serializers.ValidationError({"activity": "unknown or inactive"})

        # Простейшая проверка координат
        lat, lon = float(attrs["lat"]), float(attrs["lon"])
        if not (-90.0 <= lat <= 90.0):
            raise serializers.ValidationError({"lat": "[-90, 90]"})
        if not (-180.0 <= lon <= 180.0):
            raise serializers.ValidationError({"lon": "[-180, 180]"})

        # Таймзона (необяз.)
        tz = attrs.get("local_tz") or "UTC"
        try:
            ZoneInfo(tz)
        except Exception:
            tz = "UTC"

        attrs["activity_obj"] = activity
        attrs["local_tz"] = tz
        return attrs


# ============================================================================
#                                  VIEWSETS
# ============================================================================

class ActivityViewSet(viewsets.ModelViewSet):
    """
    CRUD для каталога активностей.
    """
    queryset = Activity.objects.all().order_by("id")
    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]


class WeatherParamViewSet(viewsets.ModelViewSet):
    """
    CRUD для справочника погодных параметров.
    """
    queryset = WeatherParam.objects.all().order_by("code")
    serializer_class = WeatherParamSerializer
    permission_classes = [permissions.AllowAny]


class ActivityParamViewSet(viewsets.ModelViewSet):
    """
    CRUD для связи (какие параметры релевантны активности).
    """
    queryset = ActivityParam.objects.select_related("activity", "param").all().order_by("activity_id", "param_id")
    serializer_class = ActivityParamSerializer
    permission_classes = [permissions.AllowAny]


# ============================================================================
#                        ВСПОМОГАТЕЛЬНЫЕ/ИНФО ЭНДПОИНТЫ
# ============================================================================

class PredictInputView(APIView):
    """
    POST /api/predict/input/
    Предварительная проверка: возвращает, какие WeatherParam требуются выбранной активности.
    Модель НЕ запускается. Этот шаг опционален — можно сразу бить в /api/predict/.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = PredictInputSerializerLight(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        activity = v["activity_obj"]

        required_params = list(
            WeatherParam.objects
            .filter(activities__activity=activity)
            .order_by("code")
            .values("code", "unit", "description")
        )

        return Response(
            {
                "activity": ActivitySerializer(activity).data,
                "date": str(v["date"]),
                "location": {"lat": float(v["lat"]), "lon": float(v["lon"])},
                "granularity": v["granularity"],
                "local_tz": v["local_tz"],
                "required_params": required_params,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================================
#                            СИНХРОННЫЙ ПРЕДИКТ
# ============================================================================

# Соответствие кодов из БД -> колонкам в CSV, который пишет ARIMA.
CSV_MAP = {
    "AIR_TEMP_C": "air_temp_C",
    "PRESSURE_KPA": "pressure_kPa",
    "WIND_SPEED_M_S": "wind_speed_m_s",
    "WATER_TEMP_C": "estimated_water_temp_C",
    "MOON_PHASE": "moon_phase",
}


class PredictView(APIView):
    """
    POST /api/predict/
    Синхронный конвейер:
      1) валидируем минимум входных данных,
      2) учитываем лаг источника (по умолчанию 3 дня): horizon = (target - (today - 3)),
      3) ensure_dataset(...) — если датасета нет локально, докачиваем его,
      4) запускаем ARIMA-скрипт, читаем прогноз на целевую дату,
      5) возвращаем только релевантные параметры выбранной активности.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = PredictInputSerializerLight(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data

        activity = v["activity_obj"]
        target: date = v["date"]
        lat, lon = float(v["lat"]), float(v["lon"])

        # Какие коды нужны активности
        required_codes = list(
            WeatherParam.objects
            .filter(activities__activity=activity)
            .order_by("code")
            .values_list("code", flat=True)
        )

        # Учитываем лаг провайдера (N+3)
        horizon_days, asof = compute_effective_horizon(target=target, lag_days=3)
        if horizon_days <= 0:
            return Response(
                {"detail": f"Запрошенная дата слишком близка к текущей. "
                           f"Источник отдаёт данные максимум до {asof.isoformat()} (today-3)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Гарантируем наличие локального датасета (скачаем через парсер, если нет)
        ddir = ensure_dataset(activity.slug, lat, lon, asof)

        # Запускаем ARIMA и берём ровно одну строку прогноза (на нужную дату)
        row = run_arima_and_read_row(
            activity_slug=activity.slug,
            lat=lat,
            lon=lon,
            target=target,
            lag_days=3,
            dataset_path=ddir,
        )

        # Соберём ответ только по релевантным кодам
        units = {wp.code: wp.unit for wp in WeatherParam.objects.filter(code__in=required_codes)}
        params_out = []
        for code in required_codes:
            csv_col = CSV_MAP.get(code)
            if csv_col and csv_col in row and row[csv_col] is not None:
                val = row[csv_col]
                # фазу луны НЕ кастим в float — это строка
                if code != "MOON_PHASE":
                    try:
                        val = float(val)
                    except (TypeError, ValueError):
                        pass
                params_out.append({"code": code, "value": val, "unit": units.get(code, "")})

        return Response(
            {
                "activity": ActivitySerializer(activity).data,
                "date": target.isoformat(),
                "location": {"lat": lat, "lon": lon},
                "granularity": v["granularity"],
                "local_tz": v["local_tz"],
                "asof": asof.isoformat(),          # последний доступный день источника (today-3)
                "horizon_days": horizon_days,      # это и есть N+3
                "model_version": "arima-merged",
                "params": params_out,
            },
            status=status.HTTP_200_OK,
        )

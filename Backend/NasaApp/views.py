from __future__ import annotations
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Activity, WeatherParam, ActivityParam


# ---- Serializers ----
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


# ---- Open CRUD ViewSets (no auth/permissions) ----
class ActivityViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = ActivitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {"is_active": ["exact"], "slug": ["exact"], "name": ["icontains"]}
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "slug", "id"]
    ordering = ["name"]

    def get_queryset(self):
        # For demo: show only active by default; change if you want all
        return Activity.objects.filter(is_active=True)

    @action(detail=True, methods=["get"], url_path="params")
    def params(self, request, pk=None):
        activity = self.get_object()
        params_qs = WeatherParam.objects.filter(activities__activity=activity).distinct().order_by("code")
        return Response(WeatherParamSerializer(params_qs, many=True).data)


class WeatherParamViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = WeatherParamSerializer
    queryset = WeatherParam.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {"code": ["exact", "icontains"], "unit": ["exact"]}
    search_fields = ["code", "description"]
    ordering_fields = ["code", "id"]
    ordering = ["code"]


class ActivityParamViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = ActivityParamSerializer
    queryset = ActivityParam.objects.select_related("activity", "param")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "activity": ["exact"],
        "activity__slug": ["exact"],
        "param": ["exact"],
        "param__code": ["exact", "icontains"],
    }
    search_fields = ["activity__name", "activity__slug", "param__code", "param__description"]
    ordering_fields = ["activity__name", "param__code", "id"]
    ordering = ["activity__name", "param__code"]


# ---- Prediction INPUT (collect and validate user data only) ----
class PredictInputSerializer(serializers.Serializer):
    activity = serializers.SlugField(min_length=1, max_length=80)
    date = serializers.DateField()
    lat = serializers.DecimalField(max_digits=8, decimal_places=5)
    lon = serializers.DecimalField(max_digits=8, decimal_places=5)
    granularity = serializers.ChoiceField(choices=["daily", "hourly"], default="daily")
    local_tz = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        lat = float(attrs["lat"])
        lon = float(attrs["lon"])
        if not (-90.0 <= lat <= 90.0):
            raise serializers.ValidationError({"lat": "Latitude must be in [-90, 90]."})
        if not (-180.0 <= lon <= 180.0):
            raise serializers.ValidationError({"lon": "Longitude must be in [-180, 180]."})

        try:
            activity = Activity.objects.get(slug=attrs["activity"], is_active=True)
        except Activity.DoesNotExist:
            raise serializers.ValidationError({"activity": "Unknown or inactive activity."})
        attrs["activity_obj"] = activity

        today = date.today()
        if attrs["date"] < today:
            raise serializers.ValidationError({"date": "Date must not be in the past."})
        if attrs["date"] > today + timedelta(days=14):
            raise serializers.ValidationError({"date": "Date must be within 14 days from today."})

        tz = attrs.get("local_tz") or "UTC"
        try:
            ZoneInfo(tz)
        except Exception:
            tz = "UTC"
        attrs["local_tz"] = tz
        return attrs


class PredictInputView(APIView):
    """
    POST /api/predict/input/
    Accepts activity + date + lat/lon, validates, and returns the
    exact list of WeatherParam codes your model should predict.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = PredictInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        activity = v["activity_obj"]

        params_qs = WeatherParam.objects.filter(activities__activity=activity).distinct().order_by("code")
        required = [{"code": p.code, "unit": p.unit, "description": p.description} for p in params_qs]

        return Response({
            "activity": {"id": activity.id, "name": activity.name, "slug": activity.slug},
            "date": str(v["date"]),
            "location": {"lat": float(v["lat"]), "lon": float(v["lon"])},
            "granularity": v["granularity"],
            "local_tz": v["local_tz"],
            "required_params": required
        }, status=status.HTTP_200_OK)



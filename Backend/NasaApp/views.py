# NasaApp/views.py
from __future__ import annotations

from datetime import date
import logging
import traceback

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from .models import Activity, WeatherParam, ActivityParam

from rest_framework import serializers


# ----------------------------
# Serializers
# ----------------------------
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
    param = WeatherParamSerializer(read_only=True)

    # write-only ids so you can POST/PUT easily
    activity_id = serializers.PrimaryKeyRelatedField(
        queryset=Activity.objects.all(), write_only=True, source="activity"
    )
    param_id = serializers.PrimaryKeyRelatedField(
        queryset=WeatherParam.objects.all(), write_only=True, source="param"
    )

    class Meta:
        model = ActivityParam
        fields = ["id", "activity", "param", "activity_id", "param_id"]


# ----------------------------
# ViewSets (CRUD for reference tables)
# ----------------------------
class ActivityViewSet(viewsets.ModelViewSet):
    """
    CRUD for activities (Hiking, Fishing, etc.)
    Demo project => no auth; feel free to toggle to ReadOnlyModelViewSet if needed.
    """
    queryset = Activity.objects.all().order_by("id")
    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["slug", "is_active", "name"]

    @action(detail=True, methods=["get"], permission_classes=[permissions.AllowAny])
    def params(self, request, pk=None):
        """
        GET /api/activities/<id>/params/ → list WeatherParam relevant to this Activity
        """
        activity = get_object_or_404(Activity, pk=pk)
        aps = ActivityParam.objects.filter(activity=activity).select_related("param").order_by("id")
        params = [ap.param for ap in aps]
        return Response(WeatherParamSerializer(params, many=True).data)


class WeatherParamViewSet(viewsets.ModelViewSet):
    queryset = WeatherParam.objects.all().order_by("id")
    serializer_class = WeatherParamSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["code", "unit"]


class ActivityParamViewSet(viewsets.ModelViewSet):
    queryset = ActivityParam.objects.select_related("activity", "param").order_by("id")
    serializer_class = ActivityParamSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activity", "param"]


# ----------------------------
# Utilities / Debug
# ----------------------------
class PingView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"ok": True, "where": "NasaApp.views.PingView"})


# ----------------------------
# Fishing prediction endpoint
# ----------------------------
logger = logging.getLogger(__name__)


class FishingPredictView(APIView):
    """
    POST /api/predict/fishing  (or /api/predict/fishing/)
    Body JSON:
      {
        "lat": 50.4501,     // OR "latitude"
        "lon": 30.5234,     // OR "lng" OR "longitude"
        "date": "2025-10-20"  // optional; if omitted we use static horizon=7 (demo)
      }

    Returns:
      {
        "ok": true,
        "used": { "lat": ..., "lon": ..., "horizon": 7, "target_date": null or ISO date },
        "csv_path": "...",         // where pipeline saved combined CSV
        "rows": [ {...}, {...} ]   // list of per-day results (LLM-enhanced)
      }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            data = request.data or {}

            # Accept common aliases from FE
            lat_raw = data.get("lat") or data.get("latitude")
            lon_raw = data.get("lon") or data.get("lng") or data.get("longitude")

            # Validate coords
            try:
                lat = float(lat_raw)
                lon = float(lon_raw)
            except (TypeError, ValueError):
                return Response(
                    {
                        "ok": False,
                        "error": "BadRequest",
                        "message": "lat/lon (or lat/lng) must be numbers",
                        "received": {"lat": lat_raw, "lon_or_lng": lon_raw},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Optional date; demo uses static horizon=7 regardless
            target_date = None
            if data.get("date"):
                try:
                    target_date = date.fromisoformat(str(data["date"]))
                except Exception:
                    # ignore parse error for demo; just keep horizon
                    target_date = None

            horizon = 7  # demo requirement: fixed horizon

            # Run pipeline
            from NasaApp.ML.main_fishing import run as fishing_run
            out = fishing_run(
                lat=lat,
                lon=lon,
                target_date=target_date,
                horizon=horizon,
                results_dir="results_folder",
            )

            payload = {
                "ok": True,
                "used": {
                    "lat": lat,
                    "lon": lon,
                    "horizon": horizon,
                    "target_date": target_date.isoformat() if target_date else None,
                },
            }

            if isinstance(out, dict):
                payload.update(out)

            return Response(payload, status=status.HTTP_200_OK)

        except Exception as e:
            tb = traceback.format_exc()
            logger.exception("FishingPredictView failed: %s", e)
            # Return JSON so FE can see *why* it failed (instead of blank 500)
            return Response(
                {
                    "ok": False,
                    "error": type(e).__name__,
                    "message": str(e),
                    "trace": tb.splitlines()[-30:],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

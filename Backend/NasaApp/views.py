from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Activity, WeatherParam, ActivityParam


# ===========================
#          SERIALIZERS
# ===========================

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


# ===========================
#        CRUD VIEWSETS
# ===========================

class ActivityViewSet(viewsets.ModelViewSet):
    """
    CRUD for activities (demo: returns active by default).
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ActivitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {"is_active": ["exact"], "slug": ["exact"], "name": ["icontains"]}
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "slug", "id"]
    ordering = ["name"]

    def get_queryset(self):
        return Activity.objects.filter(is_active=True)

    @action(detail=True, methods=["get"], url_path="params")
    def params(self, request, pk=None):
        params_qs = WeatherParam.objects.filter(activities__activity=self.get_object()).distinct().order_by("code")
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


# ===========================
#   FISHING PREDICT (CSV+LLM)
# ===========================

class FishingPredictSerializer(serializers.Serializer):
    """
    Input: lat, lon and either date (YYYY-MM-DD) or horizon (days).
    Optional: results_dir (default 'results_folder').
    """
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    date = serializers.DateField(required=False)
    horizon = serializers.IntegerField(required=False, min_value=1)
    results_dir = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("date") and not attrs.get("horizon"):
            raise serializers.ValidationError("Provide 'date' or 'horizon'.")
        lat, lon = float(attrs["lat"]), float(attrs["lon"])
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            raise serializers.ValidationError("Invalid lat/lon")
        return attrs


class FishingPredictView(APIView):
    """
    POST /api/predict/fishing/
    Runs NasaApp.ML.main_fishing.run(...), reads produced CSV, returns its rows.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = FishingPredictSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data

        lat = float(v["lat"])
        lon = float(v["lon"])
        tgt_date: date | None = v.get("date")
        horizon = v.get("horizon")
        results_dir = v.get("results_dir") or "results_folder"

        # 1) run your pipeline
        from NasaApp.ML.main_fishing import run as fishing_run
        run_result = fishing_run(
            lat=lat,
            lon=lon,
            target_date=tgt_date,
            horizon=horizon+3,
            results_dir=results_dir,
        )

        # 2) resolve CSV path
        csv_path = None
        meta = {}
        if isinstance(run_result, dict):
            csv_path = run_result.get("csv_path")
            for k in ("input_location", "used_location", "location_adjusted", "coord_store"):
                if k in run_result:
                    meta[k] = run_result[k]

        if not csv_path:
            out_dir = Path(results_dir)
            candidates = sorted(out_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not candidates:
                return Response(
                    {"detail": f"No CSV produced in '{out_dir.resolve()}'."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            csv_path = str(candidates[0])

        # 3) read CSV
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            return Response(
                {"detail": f"Failed to read CSV '{csv_path}': {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if "date" in df.columns:
            try:
                df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
            except Exception:
                pass

        rows = df.to_dict(orient="records")
        return Response(
            {
                "csv": csv_path,
                "count": len(rows),
                "results": rows,
                "meta": {"returned_from_csv": True, **meta},
            },
            status=status.HTTP_200_OK,
        )


# ===========================
#   DEBUG: simple ping view
# ===========================

class PingView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        return Response({"ok": True, "where": "NasaApp.views.PingView"})

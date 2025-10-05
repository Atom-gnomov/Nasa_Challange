from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityViewSet,
    WeatherParamViewSet,
    ActivityParamViewSet,
    FishingPredictView,
    PingView,  # debug helper
)

app_name = "NasaApp"
import sys
print("### LOADED NasaApp.urls FROM:", __file__, file=sys.stderr)
router = DefaultRouter()
router.register(r"activities", ActivityViewSet, basename="activity")
router.register(r"weather-params", WeatherParamViewSet, basename="weatherparam")
router.register(r"activity-params", ActivityParamViewSet, basename="activityparam")

urlpatterns = [
    path("", include(router.urls)),
    path("ping/", PingView.as_view(), name="ping"),  # DEBUG: prove this file is loaded
    path("predict/fishing/", FishingPredictView.as_view(), name="predict-fishing"),
]

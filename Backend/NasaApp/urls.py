from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ActivityViewSet, WeatherParamViewSet, ActivityParamViewSet, PredictInputView

app_name = "NasaApp"

router = DefaultRouter()
router.register(r"activities", ActivityViewSet, basename="activity")
router.register(r"weather-params", WeatherParamViewSet, basename="weatherparam")
router.register(r"activity-params", ActivityParamViewSet, basename="activityparam")

urlpatterns = [
    path("", include(router.urls)),
    path("predict/input/", PredictInputView.as_view(), name="predict-input"),
]
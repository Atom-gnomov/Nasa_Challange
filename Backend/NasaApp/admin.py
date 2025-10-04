
from django.contrib import admin


from django.contrib import admin
from .models import Activity, WeatherParam, ActivityParam


# --- Inlines для удобного редактирования связей M:N прямо из родителя ---

class ActivityParamInlineForActivity(admin.TabularInline):
    """
    Строки ActivityParam внутри карточки Activity.
    fk_name обязательно указываем, потому что в ActivityParam два FK.
    """
    model = ActivityParam
    fk_name = "activity"
    extra = 0
    autocomplete_fields = ["param"]       # Работает, т.к. у WeatherParam задан search_fields
    verbose_name = "параметр погоды"
    verbose_name_plural = "нужные параметры погоды"


class ActivityParamInlineForParam(admin.TabularInline):
    """
    Строки ActivityParam внутри карточки WeatherParam.
    """
    model = ActivityParam
    fk_name = "param"
    extra = 0
    autocomplete_fields = ["activity"]    # Работает, т.к. у Activity задан search_fields
    verbose_name = "активность"
    verbose_name_plural = "активности, где нужен этот параметр"


# --- Админы моделей ---

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}  # автозаполнение slug по name
    inlines = [ActivityParamInlineForActivity]


@admin.register(WeatherParam)
class WeatherParamAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "unit", "description")
    search_fields = ("code", "description")
    ordering = ("code",)
    inlines = [ActivityParamInlineForParam]


@admin.register(ActivityParam)
class ActivityParamAdmin(admin.ModelAdmin):
    list_display = ("id", "activity", "param")
    search_fields = (
        "activity__name",
        "activity__slug",
        "param__code",
        "param__description",
    )
    list_select_related = ("activity", "param")
    autocomplete_fields = ["activity", "param"]
    ordering = ("activity__name", "param__code")

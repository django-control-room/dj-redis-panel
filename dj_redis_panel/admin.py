from django.contrib import admin
from dj_control_room_base.core import BasePanelAdmin

from .conf import panel_config
from .models import RedisPanelPlaceholder


@admin.register(RedisPanelPlaceholder)
class RedisPanelPlaceholderAdmin(BasePanelAdmin):
    redirect_url_name = "dj_redis_panel:index"
    panel_config = panel_config

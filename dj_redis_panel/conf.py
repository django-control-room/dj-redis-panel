from dj_control_room_base.core import PanelConfig

panel_config = PanelConfig(
    settings_key="DJ_REDIS_PANEL_SETTINGS",
    defaults={
        "LOAD_DEFAULT_CSS": True,
        "EXTRA_CSS": [],
    },
)

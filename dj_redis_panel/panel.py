from dj_control_room_base.core import PanelPlugin


class RedisPanel(PanelPlugin):
    name = "Redis Panel"
    description = "Monitor Redis connections, memory, and keys"
    icon = "database"
    icon_color = "accent"
    features = [
        "View connection info and server overview",
        "Search and inspect keys with pattern matching",
        "Monitor memory usage, hit rate, and throughput",
        "Inspect key types, TTL, and serialized values",
    ]

    app_name = "dj_redis_panel"
    docs_url = "https://github.com/django-control-room/dj-redis-panel"
    pypi_url = "https://pypi.org/project/dj-redis-panel/"

    def get_url_name(self):
        return "index"

    def get_config(self):
        from .conf import panel_config

        return panel_config

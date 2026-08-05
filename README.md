[![Django Control Room Panel](https://img.shields.io/badge/Django%20Control%20Room-Panel-0c4b33?logo=django)](https://github.com/django-control-room/dj-control-room)
[![Tests](https://github.com/django-control-room/dj-redis-panel/actions/workflows/test.yml/badge.svg)](https://github.com/django-control-room/dj-redis-panel/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/django-control-room/dj-redis-panel/branch/main/graph/badge.svg)](https://codecov.io/gh/django-control-room/dj-redis-panel)
[![PyPI version](https://badge.fury.io/py/dj-redis-panel.svg)](https://badge.fury.io/py/dj-redis-panel)
[![Python versions](https://img.shields.io/pypi/pyversions/dj-redis-panel.svg)](https://pypi.org/project/dj-redis-panel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://img.shields.io/pypi/dm/dj-redis-panel.svg)](https://pypi.org/project/dj-redis-panel/)


# Django Redis Panel

A Django Admin panel for browsing, inspecting, and managing Redis keys. No postgres/mysql models or changes required.

![Django Redis Panel - Instance List](https://raw.githubusercontent.com/django-control-room/dj-redis-panel/main/images/instances_list.png)

**Compatible with [dj-control-room](https://github.com/django-control-room/dj-control-room).** Register this panel in the Control Room to manage it from a centralized dashboard.

- **Official site:** [djangocontrolroom.com](https://djangocontrolroom.com)
- **Project repo:** [dj-control-room](https://github.com/django-control-room/dj-control-room)

## Docs

[https://django-control-room.github.io/dj-redis-panel/](https://django-control-room.github.io/dj-redis-panel/)

## Features

- **Browse Redis Keys**: Search and filter Redis keys with pattern matching
- **Instance Overview**: Monitor Redis instance metrics and database statistics
- **Key Management**: View, edit, and delete Redis keys with support for all data types (String, List, Set, Hash, Sorted Set), including binary data
- **Feature Toggles**: Granular control over operations (delete, edit, TTL updates)
- **Pagination**: Both traditional page-based and cursor-based pagination support
- **Django Admin Integration**: Seamless integration with Django admin styling and dark mode
- **Permission Control**: Respects Django admin permissions and staff-only access
- **Multiple Instances**: Support for multiple Redis instances with different configurations


## Requirements

- Python 3.9+
- Django 4.2+
- Redis 4.0+
- redis-py 4.0+


## Screenshots

### Django Admin Integration
Seamlessly integrated into your Django admin interface. A new section for dj-redis-panel
will appear in the same places where your models appear.

**NOTE:** This application does not actually introduce any model or migrations.

![Admin Home](https://raw.githubusercontent.com/django-control-room/dj-redis-panel/main/images/admin_home.png)

### Instance Overview
Monitor your Redis instances with detailed metrics and database information.

![Instance Overview](https://raw.githubusercontent.com/django-control-room/dj-redis-panel/main/images/instance_overview.png)

### Key Search - Page-based Pagination
Search for keys with traditional page-based navigation.

![Key Search - Page Index](https://raw.githubusercontent.com/django-control-room/dj-redis-panel/main/images/key_search_page_index.png)

### Key Search - Cursor-based Pagination
Efficient cursor-based pagination for large datasets.

![Key Search - Cursor](https://raw.githubusercontent.com/django-control-room/dj-redis-panel/main/images/key_search_cursor.png)

### Key Detail - String Values
View and edit string key values with TTL management.

![Key Detail - String](https://raw.githubusercontent.com/django-control-room/dj-redis-panel/main/images/key_detail_string.png)

### Key Detail - Other data structures
Browse keys with more complex data structures such as hashes, lists, etc.

![Key Detail - Hash](https://raw.githubusercontent.com/django-control-room/dj-redis-panel/main/images/key_detail_hash.png)


## Installation

```bash
pip install dj-redis-panel dj-control-room
```

Add it to `INSTALLED_APPS`, include its URLs, and migrate:

```python
INSTALLED_APPS = [
    # ...
    'dj_control_room_base',
    'dj_redis_panel',
    'dj_control_room',
    # ...
]
```

```python
urlpatterns = [
    path('admin/dj-control-room-base/', include('dj_control_room_base.urls')),
    path('admin/dj-redis-panel/', include('dj_redis_panel.urls')),
    path('admin/dj-control-room/', include('dj_control_room.urls')),
    path('admin/', admin.site.urls),
]
```

You'll also need at least one Redis instance configured under `DJ_REDIS_PANEL_SETTINGS["INSTANCES"]` - see [Configuration](https://django-control-room.github.io/dj-redis-panel/configuration/) for the full settings reference (feature flags, pagination, cluster/SSL connections).

```bash
python manage.py migrate
```

Then visit `/admin/` and look for the "DJ REDIS PANEL" section.

For the full walkthrough and production recommendations, see the [Installation](https://django-control-room.github.io/dj-redis-panel/installation/) and [Configuration](https://django-control-room.github.io/dj-redis-panel/configuration/) docs. See [Scopes](https://django-control-room.github.io/dj-redis-panel/scopes/) for per-view permission scopes.


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Development Setup

Want to contribute or set up the project for local development? See [docs/development.md](docs/development.md) for prerequisites, Docker/virtualenv setup, running the example project, and the test suite.

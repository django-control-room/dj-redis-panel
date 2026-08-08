# Installation

This guide will walk you through installing and setting up Django Redis Panel in your Django project.

## Prerequisites

Before installing Django Redis Panel, make sure you have:

- Python 3.9 or higher
- Django 4.2 or higher
- A running Redis server
- redis-py 4.0 or higher

## Installation Steps

### 1. Install the Package

Install Django Redis Panel along with [Django Control Room](https://github.com/django-control-room/dj-control-room):

```bash
pip install dj-redis-panel dj-control-room
```

`dj-control-room-base` (the shared core library) is pulled in automatically as a dependency.

### 2. Add to Django Settings

Add `dj_control_room_base`, the panel, and `dj_control_room` to your `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dj_control_room_base',  # core lib — required for templates/static
    'dj_redis_panel',
    'dj_control_room',       # hub — registers panels in the Control Room dashboard
    # ... your other apps
]
```

!!! note
    Django Redis Panel doesn't require any database migrations as it doesn't define any Django models. `dj_control_room_base` must still be listed in `INSTALLED_APPS` so Django can discover its template tags and static assets.

### 3. Configure Redis Instances

Add your Redis configuration to your Django settings:

=== "Single Instance"

    ```python
    # settings.py
    DJ_REDIS_PANEL_SETTINGS = {
        "INSTANCES": {
            "default": {
                "description": "Default Redis Instance",
                "host": "127.0.0.1",
                "port": 6379,
            }
        }
    }
    ```

=== "Multiple Instances"

    ```python
    # settings.py
    DJ_REDIS_PANEL_SETTINGS = {
        "INSTANCES": {
            "default": {
                "description": "Default Redis Instance",
                "host": "127.0.0.1",
                "port": 6379,
            },
            "cache": {
                "description": "Cache Redis Instance",
                "host": "127.0.0.1",
                "port": 6379,
            },
            "sessions": {
                "description": "Session Store",
                "url": "redis://127.0.0.1:6379",
            }
        }
    }
    ```

=== "With Authentication"

    ```python
    # settings.py
    DJ_REDIS_PANEL_SETTINGS = {
        "INSTANCES": {
            "secure": {
                "description": "Secure Redis Instance",
                "host": "127.0.0.1",
                "port": 6379,
                "password": "your-redis-password",
            },
            "ssl_instance": {
                "description": "SSL Redis Instance",
                "url": "rediss://user:password@host:6380",
            }
        }
    }
    ```

### 4. Include URLs

Add the Control Room and Redis Panel URLs to your main `urls.py` file (panel URLs must sit under the admin prefix, and before `admin.site.urls`):

```python
# urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/dj-control-room-base/', include('dj_control_room_base.urls')),
    path('admin/dj-redis-panel/', include('dj_redis_panel.urls')),
    path('admin/dj-control-room/', include('dj_control_room.urls')),
    path('admin/', admin.site.urls),
]
```

!!! tip
    You can change the Redis Panel URL path from `admin/dj-redis-panel/` to any path you prefer, such as `admin/redis/`.

### 5. Run Migrations

```bash
python manage.py migrate
```

### 6. Create Admin User (if needed)

If you don't already have a Django admin superuser, create one:

```bash
python manage.py createsuperuser
```

### 7. Start the Development Server

Start your Django development server:

```bash
python manage.py runserver
```

### 8. Access the Panel

1. Navigate to the Django admin at `http://127.0.0.1:8000/admin/`
2. Log in with your admin credentials
3. Look for the **"DJ REDIS PANEL"** section (or open the Control Room dashboard at `/admin/dj-control-room/`)
4. Click through to start browsing your Redis instances

## Verification

To verify that everything is working correctly:

1. Check that you can see the Redis Panel section in your Django admin
2. Click on "Manage Redis keys and values"
3. You should see a list of your configured Redis instances
4. Click on an instance to view its overview and browse keys

## Troubleshooting

### Common Issues

**Redis connection errors**
: Make sure your Redis server is running and accessible at the configured host and port.

**Permission denied**
: Ensure you're logged in as a staff user with admin access.

**Module not found / `'dcr_icons' is not a registered tag library`**
: Make sure `dj_redis_panel`, `dj_control_room_base`, and `dj_control_room` are installed and listed in `INSTALLED_APPS` (base must be present for template tags and static assets).

**URLs not found**
: Verify that you've included the Redis Panel (and Control Room) URLs in your main `urls.py` file.

### Getting Help

If you encounter any issues during installation:

- Check the [Configuration](configuration.md) guide for detailed settings
- Review the [Quick Start](quick-start.md) guide
- [Open an issue on GitHub](https://github.com/django-control-room/dj-redis-panel/issues)

## Next Steps

Now that you have Django Redis Panel installed, learn how to:

- [Configure advanced settings](configuration.md)
- [Follow the quick start guide](quick-start.md)
- [Explore all features](features.md)

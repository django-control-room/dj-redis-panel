# Scopes

Dj Redis Panel splits its permission checks into **scopes**: named checkpoints passed to `@panel_config.permission_required(scope)`. Every scope inherits the panel-wide `ALLOWED_GROUPS`/`REQUIRE_SUPERUSER` rule by default; a scope only behaves differently once you add an entry for it under `SCOPE_PERMISSIONS` in `DJ_REDIS_PANEL_SETTINGS`.

See the [Permissions and Scopes guide](https://djangocontrolroom.com/guides/control-room-permissions-and-scopes) for the full model.

## Reference

| Scope | Type | Protects | Default behavior |
|---|---|---|---|
| `instance_list` | View | `index` view: browse configured Redis instances | Any staff user |
| `instance_overview` | View | `instance_overview` view: a single instance's overview (hero numbers, databases) | Any staff user |
| `key_search` | View | `key_search` view: browse/search keys in a selected DB | Any staff user |
| `key_detail` | View | `KeyDetailView`: view a key's value and (when feature flags allow) edit, delete, or update TTL | Any staff user |
| `key_add` | View | `key_add` view: create a new key | Any staff user |

This panel does not currently register MCP tools, so there are no `agent_*` scopes.

## Example: read-only browsing, restricted writes

Feature flags like `ALLOW_KEY_DELETE` / `ALLOW_KEY_EDIT` hide mutating UI controls, but scopes let you go further and deny access to the write-capable views entirely for some groups:

```python
DJ_REDIS_PANEL_SETTINGS = {
    # Panel-wide default: any staff member can browse instances and keys
    'ALLOWED_GROUPS': [],

    'SCOPE_PERMISSIONS': {
        # Only platform admins may open the key detail page (which is also
        # where edit/delete/TTL updates land) or create new keys.
        'key_detail': {'ALLOWED_GROUPS': ['platform-admins']},
        'key_add': {'ALLOWED_GROUPS': ['platform-admins']},
    },

    # Still recommended in production even when scopes restrict access:
    'ALLOW_KEY_DELETE': False,
    'ALLOW_KEY_EDIT': False,
}
```

Any scope not mentioned in `SCOPE_PERMISSIONS` simply falls back to the panel-wide rule, so you only ever need to write down the exceptions.

See [Configuration](configuration.md) for the rest of the panel's settings, including per-instance feature flags.

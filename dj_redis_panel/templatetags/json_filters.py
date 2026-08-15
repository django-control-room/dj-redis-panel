import json
from django import template

register = template.Library()


@register.filter
def pretty_json(value):
    """
    Format a JSON string with proper indentation for display.
    
    Args:
        value: JSON string to format
        
    Returns:
        Pretty-printed JSON string with 2-space indentation,
        or original value if not valid JSON
    """
    if not value:
        return value
    
    try:
        # Try to parse as JSON string
        if isinstance(value, str):
            parsed = json.loads(value)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        # If already a dict/list, just dump it
        elif isinstance(value, (dict, list)):
            return json.dumps(value, indent=2, ensure_ascii=False)
        else:
            return value
    except (json.JSONDecodeError, TypeError):
        # If not valid JSON, return as-is
        return value

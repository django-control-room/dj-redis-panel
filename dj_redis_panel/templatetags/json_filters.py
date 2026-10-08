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
        Pretty-printed JSON string with 2-space indentation, or input unchanged if not valid JSON.

    Raises:
        TypeError: If value is not a JSON-serializable type.
    """
    # Parse JSON string first, then dump with indentation
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # If input is not valid JSON (e.g., bytes literal from fallback decoding),
            # return it unchanged rather than raising an exception
            return value
    # For other JSON-serializable types, dump directly
    return json.dumps(value, indent=2, ensure_ascii=False)

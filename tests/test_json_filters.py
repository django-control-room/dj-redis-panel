"""
Tests for Django template filters in dj_redis_panel.templatetags.json_filters.
"""

import json
import pytest
from django.test import SimpleTestCase

from dj_redis_panel.templatetags.json_filters import pretty_json


class TestPrettyJsonFilter(SimpleTestCase):
    """Test cases for the pretty_json template filter."""

    def test_pretty_json_with_string_input(self):
        """Test pretty_json with a JSON string input."""
        input_json = '{"name":"John","age":30,"city":"New York"}'
        result = pretty_json(input_json)
        
        expected = '{\n  "name": "John",\n  "age": 30,\n  "city": "New York"\n}'
        assert result == expected

    def test_pretty_json_with_dict_input(self):
        """Test pretty_json with a dict input (non-string JSON-serializable)."""
        input_dict = {"name": "John", "age": 30, "city": "New York"}
        result = pretty_json(input_dict)
        
        expected = '{\n  "name": "John",\n  "age": 30,\n  "city": "New York"\n}'
        assert result == expected

    def test_pretty_json_with_list_input(self):
        """Test pretty_json with a list input."""
        input_list = [1, 2, 3, "four", {"five": 5}]
        result = pretty_json(input_list)
        
        expected = '[\n  1,\n  2,\n  3,\n  "four",\n  {\n    "five": 5\n  }\n]'
        assert result == expected

    def test_pretty_json_with_unicode_characters(self):
        """Test pretty_json preserves unicode characters (ensure_ascii=False)."""
        input_json = '{"name":"José","city":"São Paulo"}'
        result = pretty_json(input_json)
        
        expected = '{\n  "name": "José",\n  "city": "São Paulo"\n}'
        assert result == expected

    def test_pretty_json_with_nested_structure(self):
        """Test pretty_json with nested JSON structure."""
        input_json = '{"user":{"name":"John","address":{"city":"NYC","zip":"10001"}}}'
        result = pretty_json(input_json)
        
        expected = '{\n  "user": {\n    "name": "John",\n    "address": {\n      "city": "NYC",\n      "zip": "10001"\n    }\n  }\n}'
        assert result == expected

    def test_pretty_json_with_invalid_json_string(self):
        """Test pretty_json returns invalid JSON string unchanged."""
        invalid_json = '{"name": "John", "age": 30'
        result = pretty_json(invalid_json)
        
        assert result == invalid_json

    def test_pretty_json_with_non_serializable_type(self):
        """Test pretty_json raises TypeError for non-serializable type."""
        # Using a custom object that is not JSON serializable
        class CustomObject:
            pass
        
        with pytest.raises(TypeError):
            pretty_json(CustomObject())

    def test_pretty_json_with_empty_string(self):
        """Test pretty_json returns empty string unchanged (invalid JSON)."""
        result = pretty_json("")
        assert result == ""

    def test_pretty_json_with_empty_dict(self):
        """Test pretty_json with empty dict."""
        result = pretty_json({})
        assert result == "{}"

    def test_pretty_json_with_empty_list(self):
        """Test pretty_json with empty list."""
        result = pretty_json([])
        assert result == "[]"

    def test_pretty_json_indentation(self):
        """Test that pretty_json uses 2-space indentation."""
        input_json = '{"a":1,"b":2}'
        result = pretty_json(input_json)
        
        # Check that indentation is 2 spaces
        lines = result.split('\n')
        assert lines[1].startswith('  ')  # First level indentation
        assert not lines[1].startswith('    ')  # Not 4 spaces

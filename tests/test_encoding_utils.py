"""
Tests for dj_redis_panel.encoding_utils.RedisValueDecoder.
"""

from django.test import SimpleTestCase

from dj_redis_panel.encoding_utils import RedisValueDecoder


class TestDecodeValue(SimpleTestCase):
    """Test cases for RedisValueDecoder.decode_value."""

    def test_decode_value_none_returns_none(self):
        decoder = RedisValueDecoder()
        self.assertIsNone(decoder.decode_value(None))

    def test_decode_value_str_returned_as_is(self):
        decoder = RedisValueDecoder()
        self.assertEqual(decoder.decode_value("already_a_string"), "already_a_string")

    def test_decode_value_bytes_decoded_with_utf8(self):
        decoder = RedisValueDecoder("utf-8")
        self.assertEqual(decoder.decode_value(b"hello"), "hello")

    def test_decode_value_bytes_unicode_decode_error_falls_back_to_repr(self):
        decoder = RedisValueDecoder("ascii")
        raw = b"\x80\x04\x95binary"
        result = decoder.decode_value(raw)
        self.assertEqual(result, repr(raw))
        self.assertTrue(result.startswith("b'"))

    def test_decode_value_bytes_lookup_error_falls_back_to_repr(self):
        decoder = RedisValueDecoder("not-a-real-encoding")
        raw = b"some bytes"
        result = decoder.decode_value(raw)
        self.assertEqual(result, repr(raw))

    def test_decode_value_other_type_converted_to_str(self):
        decoder = RedisValueDecoder()
        self.assertEqual(decoder.decode_value(42), "42")
        self.assertEqual(decoder.decode_value(3.14), "3.14")


class TestDecodeList(SimpleTestCase):
    def test_decode_list_of_bytes(self):
        decoder = RedisValueDecoder("utf-8")
        result = decoder.decode_list([b"a", b"b", None])
        self.assertEqual(result, ["a", "b", None])


class TestDecodeDict(SimpleTestCase):
    def test_decode_dict_of_bytes(self):
        decoder = RedisValueDecoder("utf-8")
        result = decoder.decode_dict({b"field1": b"value1", b"field2": b"value2"})
        self.assertEqual(result, {"field1": "value1", "field2": "value2"})


class TestDecodeZsetList(SimpleTestCase):
    def test_decode_zset_list_decodes_members_keeps_scores(self):
        decoder = RedisValueDecoder("utf-8")
        result = decoder.decode_zset_list([(b"member1", 1.0), (b"member2", 2.0)])
        self.assertEqual(result, [("member1", 1.0), ("member2", 2.0)])


class TestEncodeForRedis(SimpleTestCase):
    """Test cases for RedisValueDecoder.encode_for_redis."""

    def test_encode_for_redis_non_str_passthrough(self):
        decoder = RedisValueDecoder()
        self.assertEqual(decoder.encode_for_redis(None), None)
        self.assertEqual(decoder.encode_for_redis(123), 123)

    def test_encode_for_redis_regular_string_encoded_with_encoder(self):
        decoder = RedisValueDecoder("utf-8")
        result = decoder.encode_for_redis("hello")
        self.assertEqual(result, b"hello")

    def test_encode_for_redis_bytes_repr_single_quote_parsed_back(self):
        decoder = RedisValueDecoder("utf-8")
        raw = b"\x80\x04\x95binary"
        repr_str = repr(raw)
        self.assertTrue(repr_str.startswith("b'"))
        result = decoder.encode_for_redis(repr_str)
        self.assertEqual(result, raw)

    def test_encode_for_redis_bytes_repr_double_quote_parsed_back(self):
        decoder = RedisValueDecoder("utf-8")
        # Force a double-quoted repr by including a single quote in the bytes
        raw = b"it's binary"
        repr_str = repr(raw)
        self.assertTrue(repr_str.startswith('b"'))
        result = decoder.encode_for_redis(repr_str)
        self.assertEqual(result, raw)

    def test_encode_for_redis_invalid_bytes_repr_returns_original(self):
        decoder = RedisValueDecoder("utf-8")
        # Starts/ends like a bytes repr, but contains an invalid escape
        # sequence that makes ast.literal_eval raise a ValueError.
        value = "b'\\x1'"
        result = decoder.encode_for_redis(value)
        self.assertEqual(result, value)

    def test_encode_for_redis_unicode_encode_error_returns_original_string(self):
        decoder = RedisValueDecoder("ascii")
        value = "héllo"
        result = decoder.encode_for_redis(value)
        self.assertEqual(result, value)

    def test_encode_for_redis_lookup_error_returns_original_string(self):
        decoder = RedisValueDecoder("not-a-real-encoding")
        value = "hello"
        result = decoder.encode_for_redis(value)
        self.assertEqual(result, value)

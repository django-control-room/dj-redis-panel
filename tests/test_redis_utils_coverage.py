"""
Focused unit/integration tests for dj_redis_panel.redis_utils.RedisPanelUtils.

These tests target branches not exercised by the view-level test suite:
config fallbacks, connection-construction edge cases, and the
not-found / wrong-type / exception branches of the key CRUD helpers.
"""

import json
from unittest.mock import MagicMock, patch

import redis
from django.test import SimpleTestCase

from dj_redis_panel.redis_utils import RedisPanelUtils

from .base import RedisTestCase


class TestConfigFallbacks(SimpleTestCase):
    """Pure config-resolution branches that don't need a live Redis server."""

    def setUp(self):
        self.patcher = patch("dj_redis_panel.redis_utils.RedisPanelUtils.get_settings")
        self.mock_get_settings = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_get_decoder_without_instance_alias_uses_global_encoder(self):
        self.mock_get_settings.return_value = {"encoder": "latin-1", "INSTANCES": {}}
        decoder = RedisPanelUtils.get_decoder()
        self.assertEqual(decoder.encoder, "latin-1")

    def test_get_decoder_with_unknown_instance_alias_falls_back_to_global(self):
        self.mock_get_settings.return_value = {"encoder": "utf-8", "INSTANCES": {}}
        decoder = RedisPanelUtils.get_decoder("does_not_exist")
        self.assertEqual(decoder.encoder, "utf-8")

    def test_is_feature_enabled_unknown_instance_returns_false(self):
        self.mock_get_settings.return_value = {"INSTANCES": {}}
        self.assertFalse(
            RedisPanelUtils.is_feature_enabled("does_not_exist", "ALLOW_KEY_DELETE")
        )

    def test_get_max_keys_paginated_scan_unknown_instance_uses_global_default(self):
        self.mock_get_settings.return_value = {
            "INSTANCES": {},
            "MAX_KEYS_PAGINATED_SCAN": 55,
        }
        self.assertEqual(
            RedisPanelUtils.get_max_keys_paginated_scan("does_not_exist"), 55
        )

    def test_get_max_scan_iterations_unknown_instance_uses_global_default(self):
        self.mock_get_settings.return_value = {
            "INSTANCES": {},
            "MAX_SCAN_ITERATIONS": 7,
        }
        self.assertEqual(
            RedisPanelUtils.get_max_scan_iterations("does_not_exist"), 7
        )

    def test_get_redis_connection_unknown_instance_raises_value_error(self):
        self.mock_get_settings.return_value = {"INSTANCES": {}}
        with self.assertRaises(ValueError):
            RedisPanelUtils.get_redis_connection("does_not_exist")


class TestSingleConnectionCreation(SimpleTestCase):
    """_create_single_connection branches (redis.Redis is lazy, so no real I/O)."""

    def setUp(self):
        self.patcher = patch("dj_redis_panel.redis_utils.RedisPanelUtils.get_settings")
        self.mock_get_settings = self.patcher.start()
        self.mock_get_settings.return_value = {}
        self.addCleanup(self.patcher.stop)

    def test_url_with_ssl_scheme_passes_ssl_cert_reqs(self):
        with patch("dj_redis_panel.redis_utils.redis.Redis.from_url") as mock_from_url:
            RedisPanelUtils._create_single_connection(
                {"url": "rediss://localhost:6379/0", "ssl_cert_reqs": "none"}
            )
            mock_from_url.assert_called_once()
            _, kwargs = mock_from_url.call_args
            self.assertEqual(kwargs["ssl_cert_reqs"], "none")

    def test_url_without_ssl_scheme(self):
        with patch("dj_redis_panel.redis_utils.redis.Redis.from_url") as mock_from_url:
            RedisPanelUtils._create_single_connection(
                {"url": "redis://localhost:6379/0"}
            )
            mock_from_url.assert_called_once()

    def test_password_username_ssl_params_applied(self):
        conn = RedisPanelUtils._create_single_connection(
            {
                "host": "127.0.0.1",
                "port": 6379,
                "password": "secret",
                "username": "user1",
                "ssl": True,
                "ssl_cert_reqs": "required",
            }
        )
        kwargs = conn.connection_pool.connection_kwargs
        self.assertEqual(kwargs["password"], "secret")
        self.assertEqual(kwargs["username"], "user1")
        self.assertEqual(kwargs["ssl_cert_reqs"], "required")
        self.assertIn("SSL", conn.connection_pool.connection_class.__name__)


class TestClusterConnectionCreation(SimpleTestCase):
    """_create_cluster_connection branches, mocking RedisCluster to avoid real I/O."""

    def setUp(self):
        self.patcher = patch("dj_redis_panel.redis_utils.RedisPanelUtils.get_settings")
        self.mock_get_settings = self.patcher.start()
        self.mock_get_settings.return_value = {}
        self.addCleanup(self.patcher.stop)

    def test_url_with_ssl_and_ca_certs(self):
        with patch(
            "dj_redis_panel.redis_utils.RedisCluster.from_url"
        ) as mock_from_url:
            RedisPanelUtils._create_cluster_connection(
                {
                    "url": "rediss://localhost:6379",
                    "ssl_cert_reqs": "none",
                    "ssl_ca_certs": "/tmp/ca.pem",
                }
            )
            _, kwargs = mock_from_url.call_args
            self.assertEqual(kwargs["ssl_cert_reqs"], "none")
            self.assertEqual(kwargs["ssl_ca_certs"], "/tmp/ca.pem")

    def test_url_with_ssl_and_no_optional_cert_params(self):
        with patch(
            "dj_redis_panel.redis_utils.RedisCluster.from_url"
        ) as mock_from_url:
            RedisPanelUtils._create_cluster_connection(
                {"url": "rediss://localhost:6379"}
            )
            _, kwargs = mock_from_url.call_args
            self.assertNotIn("ssl_cert_reqs", kwargs)
            self.assertNotIn("ssl_ca_certs", kwargs)

    def test_empty_startup_nodes_raises_value_error(self):
        with self.assertRaises(ValueError):
            RedisPanelUtils._create_cluster_connection({"startup_nodes": []})

    def test_no_url_and_no_startup_nodes_raises(self):
        with self.assertRaises(Exception):
            RedisPanelUtils._create_cluster_connection({})

    def test_startup_nodes_creates_cluster(self):
        with patch("dj_redis_panel.redis_utils.RedisCluster") as mock_cluster_cls:
            RedisPanelUtils._create_cluster_connection(
                {
                    "startup_nodes": [
                        {"host": "node0", "port": 6379},
                        {"host": "node1", "port": 6379},
                    ]
                }
            )
            mock_cluster_cls.assert_called_once()


class TestInstanceMetaDataWithMockedConnection(SimpleTestCase):
    """get_instance_meta_data branches, using a mocked connection to avoid a real cluster."""

    def test_cluster_dbsize_exception_falls_back_to_zero(self):
        mock_conn = MagicMock()
        mock_conn.info.return_value = {"cluster_enabled": 1}
        mock_conn.dbsize.side_effect = Exception("boom")

        with patch.object(
            RedisPanelUtils, "get_redis_connection", return_value=mock_conn
        ):
            result = RedisPanelUtils.get_instance_meta_data("test_cluster")

        self.assertEqual(result["status"], "connected")
        self.assertEqual(result["total_keys"], 0)
        self.assertTrue(result["hero_numbers"]["cluster_enabled"])

    def test_standard_instance_db0_missing_but_inserted(self):
        mock_conn = MagicMock()
        mock_conn.info.return_value = {
            "cluster_enabled": 0,
            "db1": {"keys": 5, "expires": 0, "avg_ttl": 0},
        }

        with patch.object(
            RedisPanelUtils, "get_redis_connection", return_value=mock_conn
        ):
            result = RedisPanelUtils.get_instance_meta_data("test_redis")

        db_numbers = [db["db_number"] for db in result["databases"]]
        self.assertIn(0, db_numbers)
        self.assertEqual(result["databases"][0]["db_number"], 0)
        self.assertEqual(result["databases"][0]["keys"], 0)

    def test_standard_instance_db0_already_present_not_reinserted(self):
        mock_conn = MagicMock()
        mock_conn.info.return_value = {
            "cluster_enabled": 0,
            "db0": {"keys": 5, "expires": 0, "avg_ttl": 0},
        }

        with patch.object(
            RedisPanelUtils, "get_redis_connection", return_value=mock_conn
        ):
            result = RedisPanelUtils.get_instance_meta_data("test_redis")

        self.assertEqual(len(result["databases"]), 1)
        self.assertEqual(result["databases"][0]["keys"], 5)

    def test_standard_instance_skips_empty_non_default_database(self):
        mock_conn = MagicMock()
        mock_conn.info.return_value = {
            "cluster_enabled": 0,
            "db0": {"keys": 1, "expires": 0, "avg_ttl": 0},
            "db1": {"keys": 0, "expires": 0, "avg_ttl": 0},
        }

        with patch.object(
            RedisPanelUtils, "get_redis_connection", return_value=mock_conn
        ):
            result = RedisPanelUtils.get_instance_meta_data("test_redis")

        db_numbers = [db["db_number"] for db in result["databases"]]
        self.assertNotIn(1, db_numbers)

    def test_connection_error_returns_disconnected_status(self):
        with patch.object(
            RedisPanelUtils,
            "get_redis_connection",
            side_effect=redis.ConnectionError("down"),
        ):
            result = RedisPanelUtils.get_instance_meta_data("test_redis")

        self.assertEqual(result["status"], "disconnected")
        self.assertEqual(result["databases"], [])
        self.assertIn("down", result["error"])


class TestKeyOperationsNotFoundAndWrongType(RedisTestCase):
    """Integration tests against a real Redis instance for not-found/wrong-type/exception paths."""

    INVALID_INSTANCE = "does_not_exist_instance"

    def test_get_key_data_nonexistent_key(self):
        result = RedisPanelUtils.get_key_data("test_redis", 15, "no:such:key")
        self.assertFalse(result["exists"])
        self.assertIsNone(result["error"])

    def test_get_key_data_hash_type(self):
        result = RedisPanelUtils.get_key_data("test_redis", 15, "test:hash")
        self.assertEqual(result["type"], "hash")
        self.assertEqual(result["value"]["field1"], "value1")

    def test_get_key_data_stream_type_falls_through_with_zero_size(self):
        self.redis_conn.xadd("test:stream", {"field": "value"})
        result = RedisPanelUtils.get_key_data("test_redis", 15, "test:stream")
        self.assertEqual(result["type"], "stream")
        self.assertEqual(result["size"], 0)
        self.assertIsNone(result["value"])

    def test_get_key_data_rejson_type(self):
        if not self.redis_json_available:
            self.skipTest("RedisJSON module not available")
        self.add_rejson_key("test:rejson", {"a": 1}, db=15)
        result = RedisPanelUtils.get_key_data("test_redis", 15, "test:rejson")
        self.assertEqual(result["type"], "ReJSON-RL")
        self.assertEqual(json.loads(result["value"]), {"a": 1})

    def test_get_key_data_rejson_falls_back_to_root_path_when_dot_returns_none(self):
        if not self.redis_json_available:
            self.skipTest("RedisJSON module not available")
        self.add_rejson_key("test:rejson_fallback", {"a": 1}, db=15)

        original_execute_command = redis.Redis.execute_command

        def fake_execute_command(self_conn, *args, **kwargs):
            if args[:2] == ("JSON.GET", "test:rejson_fallback") and args[2:] == (".",):
                return None
            return original_execute_command(self_conn, *args, **kwargs)

        with patch.object(redis.Redis, "execute_command", new=fake_execute_command):
            result = RedisPanelUtils.get_key_data(
                "test_redis", 15, "test:rejson_fallback"
            )

        self.assertEqual(result["type"], "ReJSON-RL")
        self.assertIsNotNone(result["value"])

    def test_get_key_data_invalid_instance_returns_error(self):
        result = RedisPanelUtils.get_key_data(self.INVALID_INSTANCE, 15, "test:string")
        self.assertFalse(result["exists"])
        self.assertIsNotNone(result["error"])

    def test_get_paginated_key_data_nonexistent_key_cursor_mode(self):
        result = RedisPanelUtils.get_paginated_key_data(
            "test_redis", 15, "no:such:key", cursor=0
        )
        self.assertFalse(result["exists"])
        self.assertEqual(result["cursor"], 0)
        self.assertEqual(result["next_cursor"], 0)

    def test_get_paginated_key_data_small_hash_cursor_mode(self):
        result = RedisPanelUtils.get_paginated_key_data(
            "test_redis", 15, "test:hash", cursor=0
        )
        self.assertFalse(result["is_paginated"])
        self.assertEqual(result["showing_count"], 3)

    def test_get_paginated_key_data_large_hash_cursor_pagination(self):
        for i in range(150):
            self.redis_conn.hset("test:large_hash", f"field{i}", f"value{i}")
        result = RedisPanelUtils.get_paginated_key_data(
            "test_redis", 15, "test:large_hash", cursor=0, per_page=50
        )
        self.assertTrue(result["is_paginated"])
        self.assertEqual(result["pagination_type"], "cursor")
        self.assertIsNone(result["range_start"])
        self.assertIsNone(result["range_end"])

    def test_get_paginated_key_data_large_hash_page_pagination(self):
        for i in range(150):
            self.redis_conn.hset("test:large_hash2", f"field{i}", f"value{i}")
        result = RedisPanelUtils.get_paginated_key_data(
            "test_redis", 15, "test:large_hash2", page=1, per_page=50
        )
        self.assertTrue(result["is_paginated"])
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["showing_count"], 50)

    def test_get_paginated_key_data_large_zset_cursor_pagination(self):
        for i in range(150):
            self.redis_conn.zadd("test:large_zset", {f"member{i}": i})
        result = RedisPanelUtils.get_paginated_key_data(
            "test_redis", 15, "test:large_zset", cursor=0, per_page=50
        )
        self.assertTrue(result["is_paginated"])
        self.assertIsNotNone(result["range_start"])

    def test_get_paginated_key_data_string_cursor_mode_showing_count(self):
        result = RedisPanelUtils.get_paginated_key_data(
            "test_redis", 15, "test:string", cursor=0
        )
        self.assertFalse(result["is_paginated"])
        self.assertEqual(result["showing_count"], len("test_value"))

    def test_get_paginated_key_data_stream_type_small_non_paginated(self):
        self.redis_conn.xadd("test:stream2", {"field": "value"})
        result = RedisPanelUtils.get_paginated_key_data(
            "test_redis", 15, "test:stream2", page=1
        )
        self.assertFalse(result["is_paginated"])
        self.assertEqual(result["type"], "stream")

    def test_get_paginated_key_data_rejson_type(self):
        if not self.redis_json_available:
            self.skipTest("RedisJSON module not available")
        self.add_rejson_key("test:rejson2", {"b": 2}, db=15)
        result = RedisPanelUtils.get_paginated_key_data(
            "test_redis", 15, "test:rejson2", page=1
        )
        self.assertFalse(result["is_paginated"])
        self.assertEqual(result["type"], "ReJSON-RL")

    def test_get_paginated_key_data_rejson_falls_back_to_root_path_when_dot_returns_none(
        self,
    ):
        if not self.redis_json_available:
            self.skipTest("RedisJSON module not available")
        self.add_rejson_key("test:rejson_fallback2", {"b": 2}, db=15)

        original_execute_command = redis.Redis.execute_command

        def fake_execute_command(self_conn, *args, **kwargs):
            if args[:2] == ("JSON.GET", "test:rejson_fallback2") and args[2:] == (
                ".",
            ):
                return None
            return original_execute_command(self_conn, *args, **kwargs)

        with patch.object(redis.Redis, "execute_command", new=fake_execute_command):
            result = RedisPanelUtils.get_paginated_key_data(
                "test_redis", 15, "test:rejson_fallback2", page=1
            )

        self.assertEqual(result["type"], "ReJSON-RL")
        self.assertIsNotNone(result["value"])

    def test_get_paginated_key_data_large_set_page_pagination_multiple_sscan_iterations(
        self,
    ):
        pipe = self.redis_conn.pipeline()
        for i in range(1500):
            pipe.sadd("test:large_set_multi_scan", f"member{i}")
        pipe.execute()

        result = RedisPanelUtils.get_paginated_key_data(
            "test_redis", 15, "test:large_set_multi_scan", page=1, per_page=50
        )
        self.assertTrue(result["is_paginated"])
        self.assertEqual(result["showing_count"], 50)

    def test_get_paginated_key_data_invalid_instance_with_cursor_returns_error(self):
        result = RedisPanelUtils.get_paginated_key_data(
            self.INVALID_INSTANCE, 15, "test:string", cursor=0
        )
        self.assertFalse(result["exists"])
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["cursor"], 0)
        self.assertEqual(result["next_cursor"], 0)

    def test_get_paginated_key_data_invalid_instance_returns_error(self):
        result = RedisPanelUtils.get_paginated_key_data(
            self.INVALID_INSTANCE, 15, "test:string", page=1
        )
        self.assertFalse(result["exists"])
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["total_pages"], 0)

    # --- add_* wrong-type branches ---

    def test_add_list_item_wrong_type(self):
        result = RedisPanelUtils.add_list_item("test_redis", 15, "test:hash", "x")
        self.assertFalse(result["success"])
        self.assertIn("not a list", result["error"])

    def test_add_list_item_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.add_list_item(
            self.INVALID_INSTANCE, 15, "test:list", "x"
        )
        self.assertFalse(result["success"])

    def test_add_set_member_wrong_type(self):
        result = RedisPanelUtils.add_set_member("test_redis", 15, "test:hash", "x")
        self.assertFalse(result["success"])
        self.assertIn("not a set", result["error"])

    def test_add_set_member_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.add_set_member(
            self.INVALID_INSTANCE, 15, "test:set", "x"
        )
        self.assertFalse(result["success"])

    def test_add_zset_member_wrong_type(self):
        result = RedisPanelUtils.add_zset_member(
            "test_redis", 15, "test:hash", 1.0, "x"
        )
        self.assertFalse(result["success"])
        self.assertIn("not a sorted set", result["error"])

    def test_add_zset_member_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.add_zset_member(
            self.INVALID_INSTANCE, 15, "test:zset", 1.0, "x"
        )
        self.assertFalse(result["success"])

    def test_add_hash_field_wrong_type(self):
        result = RedisPanelUtils.add_hash_field(
            "test_redis", 15, "test:list", "field", "x"
        )
        self.assertFalse(result["success"])
        self.assertIn("not a hash", result["error"])

    def test_add_hash_field_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.add_hash_field(
            self.INVALID_INSTANCE, 15, "test:hash", "field", "x"
        )
        self.assertFalse(result["success"])

    # --- delete_* not-found / wrong-type / exception branches ---

    def test_delete_list_item_by_index_key_not_found(self):
        result = RedisPanelUtils.delete_list_item_by_index(
            "test_redis", 15, "no:such:list", 0
        )
        self.assertFalse(result["success"])
        self.assertIn("does not exist", result["error"])

    def test_delete_list_item_by_index_wrong_type(self):
        result = RedisPanelUtils.delete_list_item_by_index(
            "test_redis", 15, "test:hash", 0
        )
        self.assertFalse(result["success"])
        self.assertIn("is not a list", result["error"])

    def test_delete_list_item_by_index_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.delete_list_item_by_index(
            self.INVALID_INSTANCE, 15, "test:list", 0
        )
        self.assertFalse(result["success"])

    def test_delete_set_member_key_not_found(self):
        result = RedisPanelUtils.delete_set_member(
            "test_redis", 15, "no:such:set", "x"
        )
        self.assertFalse(result["success"])
        self.assertIn("does not exist", result["error"])

    def test_delete_set_member_wrong_type(self):
        result = RedisPanelUtils.delete_set_member("test_redis", 15, "test:hash", "x")
        self.assertFalse(result["success"])
        self.assertIn("is not a set", result["error"])

    def test_delete_set_member_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.delete_set_member(
            self.INVALID_INSTANCE, 15, "test:set", "x"
        )
        self.assertFalse(result["success"])

    def test_delete_zset_member_key_not_found(self):
        result = RedisPanelUtils.delete_zset_member(
            "test_redis", 15, "no:such:zset", "x"
        )
        self.assertFalse(result["success"])
        self.assertIn("does not exist", result["error"])

    def test_delete_zset_member_wrong_type(self):
        result = RedisPanelUtils.delete_zset_member(
            "test_redis", 15, "test:hash", "x"
        )
        self.assertFalse(result["success"])
        self.assertIn("is not a sorted set", result["error"])

    def test_delete_zset_member_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.delete_zset_member(
            self.INVALID_INSTANCE, 15, "test:zset", "x"
        )
        self.assertFalse(result["success"])

    def test_delete_hash_field_key_not_found(self):
        result = RedisPanelUtils.delete_hash_field(
            "test_redis", 15, "no:such:hash", "field1"
        )
        self.assertFalse(result["success"])
        self.assertIn("does not exist", result["error"])

    def test_delete_hash_field_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.delete_hash_field(
            self.INVALID_INSTANCE, 15, "test:hash", "field1"
        )
        self.assertFalse(result["success"])

    # --- update_* not-found / wrong-type / exception branches ---

    def test_update_list_item_by_index_key_not_found(self):
        result = RedisPanelUtils.update_list_item_by_index(
            "test_redis", 15, "no:such:list", 0, "new"
        )
        self.assertFalse(result["success"])
        self.assertIn("does not exist", result["error"])

    def test_update_list_item_by_index_wrong_type(self):
        result = RedisPanelUtils.update_list_item_by_index(
            "test_redis", 15, "test:hash", 0, "new"
        )
        self.assertFalse(result["success"])
        self.assertIn("is not a list", result["error"])

    def test_update_list_item_by_index_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.update_list_item_by_index(
            self.INVALID_INSTANCE, 15, "test:list", 0, "new"
        )
        self.assertFalse(result["success"])

    def test_update_hash_field_value_key_not_found(self):
        result = RedisPanelUtils.update_hash_field_value(
            "test_redis", 15, "no:such:hash", "field1", "new"
        )
        self.assertFalse(result["success"])
        self.assertIn("does not exist", result["error"])

    def test_update_hash_field_value_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.update_hash_field_value(
            self.INVALID_INSTANCE, 15, "test:hash", "field1", "new"
        )
        self.assertFalse(result["success"])

    def test_update_string_value_creates_new_key_when_not_existing(self):
        result = RedisPanelUtils.update_string_value(
            "test_redis", 15, "test:brand_new_string", "hello"
        )
        self.assertTrue(result["success"])
        self.assertEqual(self.redis_conn.get("test:brand_new_string"), "hello")

    def test_update_string_value_wrong_type(self):
        result = RedisPanelUtils.update_string_value("test_redis", 15, "test:hash", "x")
        self.assertFalse(result["success"])
        self.assertIn("exists but is not a string", result["error"])

    def test_update_string_value_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.update_string_value(
            self.INVALID_INSTANCE, 15, "test:string", "x"
        )
        self.assertFalse(result["success"])

    def test_update_zset_member_score_key_not_found(self):
        result = RedisPanelUtils.update_zset_member_score(
            "test_redis", 15, "no:such:zset", "member1", 5.0
        )
        self.assertFalse(result["success"])
        self.assertIn("does not exist", result["error"])

    def test_update_zset_member_score_member_not_found(self):
        result = RedisPanelUtils.update_zset_member_score(
            "test_redis", 15, "test:zset", "no_such_member", 5.0
        )
        self.assertFalse(result["success"])
        self.assertIn("does not exist in sorted set", result["error"])

    def test_update_zset_member_score_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.update_zset_member_score(
            self.INVALID_INSTANCE, 15, "test:zset", "member1", 5.0
        )
        self.assertFalse(result["success"])

    def test_create_key_unsupported_type(self):
        result = RedisPanelUtils.create_key(
            "test_redis", 15, "test:new_unsupported", "weird_type"
        )
        self.assertFalse(result["success"])
        self.assertIn("Unsupported key type", result["error"])

    def test_create_key_invalid_instance_exception_branch(self):
        result = RedisPanelUtils.create_key(
            self.INVALID_INSTANCE, 15, "test:new_key", "string"
        )
        self.assertFalse(result["success"])


class TestPaginatedScanBranches(RedisTestCase):
    """paginated_scan / cursor_paginated_scan branches needing a real Redis instance."""

    def test_paginated_scan_includes_hash_type_size(self):
        result = RedisPanelUtils.paginated_scan(
            "test_redis", 15, pattern="test:hash", per_page=10
        )
        hash_entries = [k for k in result["keys_with_details"] if k["key"] == "test:hash"]
        self.assertEqual(len(hash_entries), 1)
        self.assertEqual(hash_entries[0]["type"], "hash")
        self.assertEqual(hash_entries[0]["size"], 3)

    def test_paginated_scan_includes_stream_type_with_zero_size(self):
        self.redis_conn.xadd("test:scan_stream", {"field": "value"})
        result = RedisPanelUtils.paginated_scan(
            "test_redis", 15, pattern="test:scan_stream", per_page=10
        )
        entries = [k for k in result["keys_with_details"] if k["key"] == "test:scan_stream"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["type"], "stream")
        self.assertEqual(entries[0]["size"], 0)

    def test_paginated_scan_rejson_memory_usage_failure_falls_back_to_zero(self):
        if not self.redis_json_available:
            self.skipTest("RedisJSON module not available")
        self.add_rejson_key("test:scan_rejson", {"a": 1}, db=15)

        original_execute_command = redis.Redis.execute_command

        def fake_execute_command(self_conn, *args, **kwargs):
            if args and args[0] == "MEMORY USAGE":
                raise Exception("memory usage boom")
            return original_execute_command(self_conn, *args, **kwargs)

        with patch.object(
            redis.Redis, "execute_command", new=fake_execute_command
        ):
            result = RedisPanelUtils.paginated_scan(
                "test_redis", 15, pattern="test:scan_rejson", per_page=10
            )

        entries = [
            k for k in result["keys_with_details"] if k["key"] == "test:scan_rejson"
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["type"], "ReJSON-RL")
        self.assertEqual(entries[0]["size"], 0)

    def test_paginated_scan_respects_max_keys_limit(self):
        for i in range(10):
            self.redis_conn.set(f"limit:test:{i}", "v")

        with patch.object(
            RedisPanelUtils, "get_max_keys_paginated_scan", return_value=3
        ):
            result = RedisPanelUtils.paginated_scan(
                "test_redis", 15, pattern="limit:test:*", per_page=100, scan_count=1
            )

        self.assertTrue(result["limited_scan"])

    def test_paginated_scan_hits_iteration_limit_without_key_limit(self):
        for i in range(10):
            self.redis_conn.set(f"iter:limit:{i}", "v")

        with patch.object(
            RedisPanelUtils, "get_max_scan_iterations", return_value=1
        ):
            result = RedisPanelUtils.paginated_scan(
                "test_redis", 15, pattern="iter:limit:*", per_page=100, scan_count=1
            )

        self.assertTrue(result["limited_scan"])
        self.assertFalse(result["scan_complete"])

    def test_paginated_scan_invalid_instance_returns_error(self):
        result = RedisPanelUtils.paginated_scan("does_not_exist_instance", 15)
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["keys"], [])

    def test_paginated_scan_skips_key_that_errors_during_detail_fetch(self):
        self.redis_conn.set("skip:me", "value")
        with patch(
            "dj_redis_panel.redis_utils.RedisPanelUtils.get_decoder"
        ) as mock_get_decoder:
            mock_decoder = MagicMock()
            mock_decoder.decode_value.side_effect = Exception("decode boom")
            mock_get_decoder.return_value = mock_decoder

            result = RedisPanelUtils.paginated_scan(
                "test_redis", 15, pattern="skip:me"
            )

        self.assertEqual(result["keys_with_details"], [])

    def test_cursor_paginated_scan_includes_hash_type_size(self):
        # A single SCAN call's COUNT is only a hint on how many hash-table
        # buckets to visit, not a guarantee of finding a specific key, so
        # per_page must be large enough to cover the whole (small) test
        # keyspace in one pass for this assertion to be deterministic.
        result = RedisPanelUtils.cursor_paginated_scan(
            "test_redis", 15, pattern="test:hash", per_page=1000
        )
        hash_entries = [k for k in result["keys_with_details"] if k["key"] == "test:hash"]
        self.assertEqual(len(hash_entries), 1)
        self.assertEqual(hash_entries[0]["size"], 3)

    def test_cursor_paginated_scan_includes_list_set_zset_types(self):
        result = RedisPanelUtils.cursor_paginated_scan(
            "test_redis",
            15,
            pattern="test:*",
            per_page=1000,
        )
        types_seen = {k["type"] for k in result["keys_with_details"]}
        self.assertIn("list", types_seen)
        self.assertIn("set", types_seen)
        self.assertIn("zset", types_seen)

    def test_cursor_paginated_scan_rejson_memory_usage_failure_falls_back_to_zero(self):
        if not self.redis_json_available:
            self.skipTest("RedisJSON module not available")
        self.add_rejson_key("test:cursor_scan_rejson", {"a": 1}, db=15)

        original_execute_command = redis.Redis.execute_command

        def fake_execute_command(self_conn, *args, **kwargs):
            if args and args[0] == "MEMORY USAGE":
                raise Exception("memory usage boom")
            return original_execute_command(self_conn, *args, **kwargs)

        with patch.object(
            redis.Redis, "execute_command", new=fake_execute_command
        ):
            result = RedisPanelUtils.cursor_paginated_scan(
                "test_redis", 15, pattern="test:cursor_scan_rejson", per_page=1000
            )

        entries = [
            k
            for k in result["keys_with_details"]
            if k["key"] == "test:cursor_scan_rejson"
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["size"], 0)

    def test_cursor_paginated_scan_includes_stream_type_with_zero_size(self):
        self.redis_conn.xadd("test:cursor_stream", {"field": "value"})
        result = RedisPanelUtils.cursor_paginated_scan(
            "test_redis", 15, pattern="test:cursor_stream", per_page=1000
        )
        entries = [
            k for k in result["keys_with_details"] if k["key"] == "test:cursor_stream"
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["type"], "stream")
        self.assertEqual(entries[0]["size"], 0)

    def test_cursor_paginated_scan_skips_key_that_errors_during_detail_fetch(self):
        self.redis_conn.set("cursor:skip:me", "value")
        with patch(
            "dj_redis_panel.redis_utils.RedisPanelUtils.get_decoder"
        ) as mock_get_decoder:
            mock_decoder = MagicMock()
            mock_decoder.decode_value.side_effect = Exception("decode boom")
            mock_get_decoder.return_value = mock_decoder

            result = RedisPanelUtils.cursor_paginated_scan(
                "test_redis", 15, pattern="cursor:skip:me", per_page=1000
            )

        self.assertEqual(result["keys_with_details"], [])

    def test_cursor_paginated_scan_invalid_instance_returns_error(self):
        result = RedisPanelUtils.cursor_paginated_scan(
            "does_not_exist_instance", 15
        )
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["keys"], [])

    def test_cursor_paginated_scan_has_more_boosts_estimated_total(self):
        for i in range(20):
            self.redis_conn.set(f"cursor:est:{i}", "v")
        result = RedisPanelUtils.cursor_paginated_scan(
            "test_redis", 15, pattern="cursor:est:*", per_page=5, scan_count=5
        )
        if result["has_more"]:
            self.assertGreaterEqual(result["total_keys"], 5)

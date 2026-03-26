"""
Unit tests for config and logging modules.

Tests cover:
- Settings default values and attribute types
- setup_logging() configuration
- JSONFormatter structured output
- Text format logging
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Request logging middleware (X-Request-ID header)
"""

import json
import logging
import os
import sys
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# Ensure backend package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import Settings
from app.main import JSONFormatter, setup_logging


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestSettingsDefaults:
    """Verify that default values load correctly without any env overrides."""

    def setup_method(self):
        # Build a fresh Settings with no .env file influence
        with patch.dict(os.environ, {}, clear=False):
            self.settings = Settings()

    def test_api_v1_str(self):
        assert self.settings.API_V1_STR == "/api/v1"

    def test_project_name(self):
        assert self.settings.PROJECT_NAME == "Couple Face-Swap API"

    def test_version(self):
        assert self.settings.VERSION == "0.1.0"

    def test_database_url(self):
        assert "postgresql" in self.settings.DATABASE_URL

    def test_redis_url(self):
        assert self.settings.REDIS_URL.startswith("redis://")

    def test_storage_type(self):
        assert self.settings.STORAGE_TYPE == "local"

    def test_max_image_size(self):
        assert self.settings.MAX_IMAGE_SIZE == 4096

    def test_use_gpu(self):
        assert self.settings.USE_GPU is True

    def test_acceleration_provider(self):
        assert self.settings.ACCELERATION_PROVIDER == "auto"

    def test_log_level_default(self):
        assert self.settings.LOG_LEVEL == "INFO"

    def test_log_format_default(self):
        assert self.settings.LOG_FORMAT == "text"


class TestSettingsAttributeTypes:
    """Verify attribute types for every setting."""

    def setup_method(self):
        self.settings = Settings()

    def test_string_fields(self):
        string_fields = [
            "API_V1_STR", "PROJECT_NAME", "VERSION", "DATABASE_URL",
            "REDIS_URL", "STORAGE_TYPE", "STORAGE_PATH", "MINIO_BUCKET",
            "MODELS_PATH", "INSWAPPER_MODEL", "FACE_ANALYSIS_MODEL",
            "ACCELERATION_PROVIDER", "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND", "LOG_LEVEL", "LOG_FORMAT",
            "SECRET_KEY", "ALGORITHM",
        ]
        for field in string_fields:
            assert isinstance(getattr(self.settings, field), str), (
                f"{field} should be str"
            )

    def test_int_fields(self):
        int_fields = [
            "MAX_IMAGE_SIZE", "GPU_DEVICE_ID", "ACCESS_TOKEN_EXPIRE_MINUTES",
        ]
        for field in int_fields:
            assert isinstance(getattr(self.settings, field), int), (
                f"{field} should be int"
            )

    def test_bool_fields(self):
        assert isinstance(self.settings.USE_GPU, bool)

    def test_optional_fields_are_none_or_str(self):
        optional_fields = ["MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"]
        for field in optional_fields:
            val = getattr(self.settings, field)
            assert val is None or isinstance(val, str), (
                f"{field} should be None or str"
            )


class TestSettingsEnvOverride:
    """Verify that environment variables override defaults."""

    def test_override_log_level(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            s = Settings()
            assert s.LOG_LEVEL == "DEBUG"

    def test_override_log_format(self):
        with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
            s = Settings()
            assert s.LOG_FORMAT == "json"

    def test_override_project_name(self):
        with patch.dict(os.environ, {"PROJECT_NAME": "Test App"}):
            s = Settings()
            assert s.PROJECT_NAME == "Test App"

    def test_override_max_image_size(self):
        with patch.dict(os.environ, {"MAX_IMAGE_SIZE": "2048"}):
            s = Settings()
            assert s.MAX_IMAGE_SIZE == 2048


# ---------------------------------------------------------------------------
# Logging tests
# ---------------------------------------------------------------------------

class TestSetupLogging:
    """Verify setup_logging() configures the root logger correctly."""

    def teardown_method(self):
        # Restore root logger to a sane state after each test
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)

    def test_root_logger_level_info(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO", "LOG_FORMAT": "text"}):
            # Rebuild settings so setup_logging picks up the patch
            import app.core.config as cfg
            cfg.settings = Settings()
            setup_logging()

        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_root_logger_level_debug(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "LOG_FORMAT": "text"}):
            new_settings = Settings()
        with patch("app.main.settings", new_settings):
            setup_logging()
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_handler_attached(self):
        import app.core.config as cfg
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO", "LOG_FORMAT": "text"}):
            cfg.settings = Settings()
            setup_logging()

        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)

    def test_json_formatter_selected(self):
        json_settings = Settings(LOG_FORMAT="json", LOG_LEVEL="INFO")
        with patch("app.main.settings", json_settings):
            setup_logging()

        handler = logging.getLogger().handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)
        # Restore
        setup_logging()

    def test_text_formatter_selected(self):
        import app.core.config as cfg
        with patch.dict(os.environ, {"LOG_FORMAT": "text", "LOG_LEVEL": "INFO"}):
            cfg.settings = Settings()
            setup_logging()

        handler = logging.getLogger().handlers[0]
        assert not isinstance(handler.formatter, JSONFormatter)

    def test_noisy_loggers_quieted(self):
        import app.core.config as cfg
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO", "LOG_FORMAT": "text"}):
            cfg.settings = Settings()
            setup_logging()

        assert logging.getLogger("uvicorn.access").level == logging.WARNING
        assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING


class TestJSONFormatter:
    """Verify JSONFormatter produces valid structured JSON."""

    def setup_method(self):
        self.formatter = JSONFormatter()

    def _make_record(self, msg, level=logging.INFO, **extras):
        logger = logging.getLogger("test.json")
        record = logger.makeRecord(
            name="test.json",
            level=level,
            fn="test_file.py",
            lno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )
        for k, v in extras.items():
            setattr(record, k, v)
        return record

    def test_output_is_valid_json(self):
        record = self._make_record("hello world")
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_required_keys_present(self):
        record = self._make_record("check keys")
        parsed = json.loads(self.formatter.format(record))
        for key in ("timestamp", "level", "logger", "message"):
            assert key in parsed, f"Missing key: {key}"

    def test_message_content(self):
        record = self._make_record("my message")
        parsed = json.loads(self.formatter.format(record))
        assert parsed["message"] == "my message"

    def test_level_names(self):
        for level, name in [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
        ]:
            record = self._make_record("lvl test", level=level)
            parsed = json.loads(self.formatter.format(record))
            assert parsed["level"] == name

    def test_extra_fields_included(self):
        extras = {
            "request_id": "abc123",
            "method": "GET",
            "path": "/health",
            "status_code": 200,
            "duration_ms": 3.5,
        }
        record = self._make_record("req", **extras)
        parsed = json.loads(self.formatter.format(record))
        for k, v in extras.items():
            assert parsed[k] == v

    def test_exception_included(self):
        logger = logging.getLogger("test.exc")
        try:
            raise ValueError("boom")
        except ValueError:
            import sys as _sys
            exc_info = _sys.exc_info()

        record = logger.makeRecord(
            name="test.exc",
            level=logging.ERROR,
            fn="test_file.py",
            lno=1,
            msg="err",
            args=(),
            exc_info=exc_info,
        )
        parsed = json.loads(self.formatter.format(record))
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]


class TestTextFormatLogging:
    """Verify text format produces expected output."""

    def test_text_format_contains_level_and_message(self):
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logger = logging.getLogger("test.text")
        record = logger.makeRecord(
            name="test.text",
            level=logging.WARNING,
            fn="test_file.py",
            lno=1,
            msg="some warning",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "WARNING" in output
        assert "some warning" in output
        assert "test.text" in output


# ---------------------------------------------------------------------------
# Middleware tests
# ---------------------------------------------------------------------------

class TestRequestLoggingMiddleware:
    """Test the request logging middleware via a minimal FastAPI app."""

    def setup_method(self):
        import time
        import uuid

        # Build a small app that mirrors the middleware from main.py
        self.app = FastAPI()

        @self.app.middleware("http")
        async def request_logging_middleware(request: Request, call_next):
            request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
            start = time.time()
            response = await call_next(request)
            duration_ms = round((time.time() - start) * 1000, 1)
            response.headers["X-Request-ID"] = request_id
            return response

        @self.app.get("/ping")
        async def ping():
            return {"pong": True}

        self.client = TestClient(self.app)

    def test_x_request_id_generated(self):
        resp = self.client.get("/ping")
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers

    def test_x_request_id_echoed(self):
        resp = self.client.get("/ping", headers={"X-Request-ID": "my-req-42"})
        assert resp.headers["x-request-id"] == "my-req-42"

    def test_generated_id_is_12_hex_chars(self):
        resp = self.client.get("/ping")
        rid = resp.headers["x-request-id"]
        assert len(rid) == 12
        # Should be valid hex
        int(rid, 16)

    def test_response_body_unaffected(self):
        resp = self.client.get("/ping")
        assert resp.json() == {"pong": True}

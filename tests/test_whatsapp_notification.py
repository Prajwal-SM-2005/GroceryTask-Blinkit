#!/usr/bin/env python3
"""
Unit tests for WhatsApp notification script.
All HTTP requests are mocked - no real API calls are made.
"""

import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path
from urllib import error as urllib_error

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from send_whatsapp_notification import (
    load_env_vars,
    load_env_file,
    build_payload,
    send_message,
    HELLO_WORLD_TEMPLATE,
    API_BASE_URL
)


class TestLoadEnvVars(unittest.TestCase):
    """Tests for environment variable loading."""

    def setUp(self):
        # Save original env
        self.original_env = dict(os.environ)

    def tearDown(self):
        # Restore original env
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_load_env_vars_success(self):
        """Test successful loading of all required variables."""
        os.environ["WHATSAPP_ACCESS_TOKEN"] = "test_token"
        os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "123456789"
        os.environ["WHATSAPP_TEST_RECIPIENT"] = "+15551234567"

        token, phone_id, recipient = load_env_vars()

        self.assertEqual(token, "test_token")
        self.assertEqual(phone_id, "123456789")
        self.assertEqual(recipient, "+15551234567")

    def test_load_env_vars_missing_token(self):
        """Test error when access token is missing."""
        os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "123456789"
        os.environ["WHATSAPP_TEST_RECIPIENT"] = "+15551234567"

        with self.assertRaises(ValueError) as ctx:
            load_env_vars()

        self.assertIn("WHATSAPP_ACCESS_TOKEN", str(ctx.exception))

    def test_load_env_vars_missing_phone_id(self):
        """Test error when phone number ID is missing."""
        os.environ["WHATSAPP_ACCESS_TOKEN"] = "test_token"
        os.environ["WHATSAPP_TEST_RECIPIENT"] = "+15551234567"

        with self.assertRaises(ValueError) as ctx:
            load_env_vars()

        self.assertIn("WHATSAPP_PHONE_NUMBER_ID", str(ctx.exception))

    def test_load_env_vars_missing_recipient(self):
        """Test error when test recipient is missing."""
        os.environ["WHATSAPP_ACCESS_TOKEN"] = "test_token"
        os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "123456789"

        with self.assertRaises(ValueError) as ctx:
            load_env_vars()

        self.assertIn("WHATSAPP_TEST_RECIPIENT", str(ctx.exception))

    def test_load_env_vars_missing_multiple(self):
        """Test error when multiple variables are missing."""
        with self.assertRaises(ValueError) as ctx:
            load_env_vars()

        self.assertIn("WHATSAPP_ACCESS_TOKEN", str(ctx.exception))
        self.assertIn("WHATSAPP_PHONE_NUMBER_ID", str(ctx.exception))
        self.assertIn("WHATSAPP_TEST_RECIPIENT", str(ctx.exception))


class TestLoadEnvFile(unittest.TestCase):
    """Tests for .env file loading."""

    def setUp(self):
        self.original_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_load_env_file_basic(self):
        """Test loading basic key=value pairs from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("WHATSAPP_ACCESS_TOKEN=test_token\n")
            f.write("WHATSAPP_PHONE_NUMBER_ID=123456789\n")
            f.write("WHATSAPP_TEST_RECIPIENT=+15551234567\n")
            env_path = Path(f.name)

        try:
            load_env_file(env_path)
            self.assertEqual(os.environ.get("WHATSAPP_ACCESS_TOKEN"), "test_token")
            self.assertEqual(os.environ.get("WHATSAPP_PHONE_NUMBER_ID"), "123456789")
            self.assertEqual(os.environ.get("WHATSAPP_TEST_RECIPIENT"), "+15551234567")
        finally:
            env_path.unlink()

    def test_load_env_file_with_quotes(self):
        """Test loading values with surrounding quotes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write('WHATSAPP_ACCESS_TOKEN="test_token"\n')
            f.write("WHATSAPP_PHONE_NUMBER_ID='123456789'\n")
            env_path = Path(f.name)

        try:
            load_env_file(env_path)
            self.assertEqual(os.environ.get("WHATSAPP_ACCESS_TOKEN"), "test_token")
            self.assertEqual(os.environ.get("WHATSAPP_PHONE_NUMBER_ID"), "123456789")
        finally:
            env_path.unlink()

    def test_load_env_file_skips_comments(self):
        """Test that comments are ignored."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# This is a comment\n")
            f.write("WHATSAPP_ACCESS_TOKEN=test_token\n")
            f.write("# Another comment\n")
            env_path = Path(f.name)

        try:
            load_env_file(env_path)
            self.assertEqual(os.environ.get("WHATSAPP_ACCESS_TOKEN"), "test_token")
        finally:
            env_path.unlink()

    def test_load_env_file_does_not_override_existing(self):
        """Test that existing env vars are not overridden."""
        os.environ["WHATSAPP_ACCESS_TOKEN"] = "existing_token"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("WHATSAPP_ACCESS_TOKEN=new_token\n")
            env_path = Path(f.name)

        try:
            load_env_file(env_path)
            self.assertEqual(os.environ.get("WHATSAPP_ACCESS_TOKEN"), "existing_token")
        finally:
            env_path.unlink()

    def test_load_env_file_missing_file(self):
        """Test that missing .env file is handled gracefully."""
        load_env_file(Path("/nonexistent/path/.env"))
        # Should not raise exception


class TestBuildPayload(unittest.TestCase):
    """Tests for payload building."""

    def test_build_payload_structure(self):
        """Test that payload has correct structure for hello_world template."""
        recipient = "+15551234567"
        payload = build_payload(recipient)

        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["to"], recipient)
        self.assertEqual(payload["type"], "template")
        self.assertEqual(payload["template"]["name"], HELLO_WORLD_TEMPLATE)
        self.assertEqual(payload["template"]["language"]["code"], "en_US")

    def test_build_payload_different_recipients(self):
        """Test payload with different recipient formats."""
        for recipient in ["+15551234567", "+447911123456", "+919876543210"]:
            payload = build_payload(recipient)
            self.assertEqual(payload["to"], recipient)


class TestSendMessage(unittest.TestCase):
    """Tests for send_message function with mocked HTTP."""

    def setUp(self):
        self.access_token = "test_token_123"
        self.phone_number_id = "123456789"
        self.payload = build_payload("+15551234567")

    @patch("send_whatsapp_notification.request.urlopen")
    def test_send_message_success(self, mock_urlopen):
        """Test successful message send."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "messaging_product": "whatsapp",
            "contacts": [{"wa_id": "15551234567"}],
            "messages": [{"id": "wamid.test123"}]
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = mock_response

        result = send_message(self.access_token, self.phone_number_id, self.payload, dry_run=False)

        self.assertTrue(result["success"])
        self.assertTrue(result["api_accepted"])
        self.assertIsNone(result["error"])
        self.assertIn("messages", result["response"])
        self.assertEqual(result["message_id"], "wamid.test123")

    @patch("send_whatsapp_notification.request.urlopen")
    def test_send_message_http_error_400(self, mock_urlopen):
        """Test handling of HTTP 400 error."""
        error_response = {
            "error": {
                "message": "Invalid recipient phone number",
                "type": "OAuthException",
                "code": 400,
                "fbtrace_id": "test123"
            }
        }
        http_error = urllib_error.HTTPError(
            url=f"{API_BASE_URL}/{self.phone_number_id}/messages",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=MagicMock(read=lambda: json.dumps(error_response).encode("utf-8"))
        )
        mock_urlopen.side_effect = http_error

        result = send_message(self.access_token, self.phone_number_id, self.payload, dry_run=False)

        self.assertFalse(result["success"])
        self.assertFalse(result["api_accepted"])
        self.assertIsNotNone(result["error"])
        self.assertIn("400", result["error"])
        self.assertIn("Invalid recipient", result["error"])
        self.assertIsNone(result["message_id"])

    @patch("send_whatsapp_notification.request.urlopen")
    def test_send_message_http_error_401(self, mock_urlopen):
        """Test handling of HTTP 401 (invalid/expired token)."""
        error_response = {
            "error": {
                "message": "Invalid access token",
                "type": "OAuthException",
                "code": 190,
                "fbtrace_id": "test456"
            }
        }
        http_error = urllib_error.HTTPError(
            url=f"{API_BASE_URL}/{self.phone_number_id}/messages",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=MagicMock(read=lambda: json.dumps(error_response).encode("utf-8"))
        )
        mock_urlopen.side_effect = http_error

        result = send_message(self.access_token, self.phone_number_id, self.payload, dry_run=False)

        self.assertFalse(result["success"])
        self.assertFalse(result["api_accepted"])
        self.assertIn("401", result["error"])
        self.assertIn("Invalid access token", result["error"])

    @patch("send_whatsapp_notification.request.urlopen")
    def test_send_message_network_error(self, mock_urlopen):
        """Test handling of network error (URLError)."""
        mock_urlopen.side_effect = urllib_error.URLError("Connection refused")

        result = send_message(self.access_token, self.phone_number_id, self.payload, dry_run=False)

        self.assertFalse(result["success"])
        self.assertFalse(result["api_accepted"])
        self.assertIn("Network error", result["error"])
        self.assertIn("Connection refused", result["error"])

    def test_send_message_dry_run(self):
        """Test dry-run mode makes no network request."""
        with patch("send_whatsapp_notification.request.urlopen") as mock_urlopen:
            result = send_message(self.access_token, self.phone_number_id, self.payload, dry_run=True)

            self.assertTrue(result["success"])
            self.assertFalse(result["api_accepted"])
            self.assertIsNone(result["error"])
            self.assertTrue(result["response"].get("dry_run"))
            self.assertIn("Dry-run mode", result["response"]["message"])
            self.assertIsNone(result["message_id"])
            mock_urlopen.assert_not_called()

    def test_send_message_no_message_id(self):
        """Test handling when API succeeds but returns no message ID."""
        with patch("send_whatsapp_notification.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "messaging_product": "whatsapp",
                "contacts": [{"wa_id": "15551234567"}]
                # No messages array
            }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=None)
            mock_urlopen.return_value = mock_response

            result = send_message(self.access_token, self.phone_number_id, self.payload, dry_run=False)

            self.assertTrue(result["success"])
            self.assertTrue(result["api_accepted"])
            self.assertIsNone(result["message_id"])


class TestMainFunction(unittest.TestCase):
    """Tests for main() function behavior."""

    def setUp(self):
        self.original_env = dict(os.environ)
        self.original_argv = sys.argv

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
        sys.argv = self.original_argv

    @patch("send_whatsapp_notification.send_message")
    @patch("send_whatsapp_notification.load_env_vars")
    def test_main_dry_run(self, mock_load_env, mock_send_message):
        """Test main with --dry-run flag."""
        mock_load_env.return_value = ("token", "123", "+15551234567")
        mock_send_message.return_value = {
            "success": True,
            "api_accepted": False,
            "response": {"dry_run": True, "message": "Dry-run mode"},
            "error": None,
            "message_id": None
        }

        sys.argv = ["send_whatsapp_notification.py", "--dry-run"]

        from send_whatsapp_notification import main
        with self.assertRaises(SystemExit) as ctx:
            main()

        self.assertEqual(ctx.exception.code, 0)
        mock_send_message.assert_called_once()
        call_kwargs = mock_send_message.call_args[1]
        self.assertTrue(call_kwargs["dry_run"])

    @patch("send_whatsapp_notification.send_message")
    @patch("send_whatsapp_notification.load_env_vars")
    def test_main_send_success(self, mock_load_env, mock_send_message):
        """Test main with --send flag and success."""
        mock_load_env.return_value = ("token", "123", "+15551234567")
        mock_send_message.return_value = {
            "success": True,
            "api_accepted": True,
            "response": {"messages": [{"id": "wamid.test"}]},
            "error": None,
            "message_id": "wamid.test"
        }

        sys.argv = ["send_whatsapp_notification.py", "--send"]

        from send_whatsapp_notification import main
        with self.assertRaises(SystemExit) as ctx:
            main()

        self.assertEqual(ctx.exception.code, 0)
        mock_send_message.assert_called_once()
        call_kwargs = mock_send_message.call_args[1]
        self.assertFalse(call_kwargs["dry_run"])

    @patch("send_whatsapp_notification.send_message")
    @patch("send_whatsapp_notification.load_env_vars")
    def test_main_send_failure(self, mock_load_env, mock_send_message):
        """Test main with --send flag and failure."""
        mock_load_env.return_value = ("token", "123", "+15551234567")
        mock_send_message.return_value = {
            "success": False,
            "api_accepted": False,
            "response": {},
            "error": "HTTP 400: Invalid recipient",
            "message_id": None
        }

        sys.argv = ["send_whatsapp_notification.py", "--send"]

        from send_whatsapp_notification import main
        with self.assertRaises(SystemExit) as ctx:
            main()

        self.assertEqual(ctx.exception.code, 1)

    @patch("send_whatsapp_notification.load_env_vars")
    def test_main_missing_args(self, mock_load_env):
        """Test main fails without --dry-run or --send."""
        mock_load_env.return_value = ("token", "123", "+15551234567")

        sys.argv = ["send_whatsapp_notification.py"]

        from send_whatsapp_notification import main
        with self.assertRaises(SystemExit) as ctx:
            main()

        self.assertEqual(ctx.exception.code, 2)

    @patch("send_whatsapp_notification.load_env_vars")
    def test_main_both_flags(self, mock_load_env):
        """Test main fails with both --dry-run and --send."""
        mock_load_env.return_value = ("token", "123", "+15551234567")

        sys.argv = ["send_whatsapp_notification.py", "--dry-run", "--send"]

        from send_whatsapp_notification import main
        with self.assertRaises(SystemExit) as ctx:
            main()

        self.assertEqual(ctx.exception.code, 2)

    @patch("send_whatsapp_notification.load_env_vars")
    def test_main_missing_env(self, mock_load_env):
        """Test main fails with missing environment variables."""
        mock_load_env.side_effect = ValueError("Missing required environment variables: WHATSAPP_ACCESS_TOKEN")

        sys.argv = ["send_whatsapp_notification.py", "--send"]

        from send_whatsapp_notification import main
        with self.assertRaises(SystemExit) as ctx:
            main()

        self.assertEqual(ctx.exception.code, 2)

    @patch("send_whatsapp_notification.load_env_vars")
    def test_main_invalid_recipient(self, mock_load_env):
        """Test main fails with invalid recipient format."""
        mock_load_env.return_value = ("token", "123", "invalid")

        sys.argv = ["send_whatsapp_notification.py", "--send"]

        from send_whatsapp_notification import main
        with self.assertRaises(SystemExit) as ctx:
            main()

        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
#!/usr/bin/env python3
"""
Send a test WhatsApp notification using Meta WhatsApp Cloud API.

This script reads configuration from environment variables and sends
a test message using Meta's built-in `hello_world` template.

Environment variables required:
- WHATSAPP_ACCESS_TOKEN: Meta API access token
- WHATSAPP_PHONE_NUMBER_ID: Meta Business phone number ID
- WHATSAPP_TEST_RECIPIENT: Approved test recipient phone number (E.164 format, e.g., +15551234567)

Optional: Load from .env file (not committed to git)

Usage:
    python scripts/send_whatsapp_notification.py --dry-run
    python scripts/send_whatsapp_notification.py --send
"""

import os
import sys
import json
import argparse
import ssl
from pathlib import Path
from urllib import request, error


API_BASE_URL = "https://graph.facebook.com/v20.0"
HELLO_WORLD_TEMPLATE = "hello_world"


def _create_ssl_context() -> ssl.SSLContext:
    """
    Create an SSL context with proper certificate verification.
    Uses certifi's CA bundle if available, otherwise falls back to system defaults.
    """
    context = ssl.create_default_context()
    # Set minimum TLS version for security
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Try to use certifi's CA bundle for consistent cross-platform behavior
    try:
        import certifi
        context.load_verify_locations(certifi.where())
    except ImportError:
        # certifi not installed - use system default trust store
        # On Windows, this may require manual certificate configuration
        pass
    
    return context


def load_env_file(env_path: Path) -> None:
    """Load environment variables from a .env file if it exists."""
    if not env_path.exists():
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = value


def load_env_vars() -> tuple[str, str, str]:
    """Load required environment variables."""
    access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    test_recipient = os.environ.get("WHATSAPP_TEST_RECIPIENT")

    missing = []
    if not access_token:
        missing.append("WHATSAPP_ACCESS_TOKEN")
    if not phone_number_id:
        missing.append("WHATSAPP_PHONE_NUMBER_ID")
    if not test_recipient:
        missing.append("WHATSAPP_TEST_RECIPIENT")

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return access_token, phone_number_id, test_recipient


def build_payload(recipient: str) -> dict:
    """Build the WhatsApp Cloud API payload for hello_world template."""
    return {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": HELLO_WORLD_TEMPLATE,
            "language": {"code": "en_US"}
        }
    }


def send_message(
    access_token: str,
    phone_number_id: str,
    payload: dict,
    dry_run: bool = False
) -> dict:
    """
    Send a WhatsApp message via Cloud API.

    Args:
        access_token: Meta API access token
        phone_number_id: Meta Business phone number ID
        payload: Message payload
        dry_run: If True, skip network request and return mock response

    Returns:
        Dictionary with keys:
        - success (bool): API call succeeded
        - api_accepted (bool): Message accepted by API (may not be delivered)
        - response (dict): API response
        - error (str or None): Error message if failed
        - message_id (str or None): Message ID if accepted
    """
    url = f"{API_BASE_URL}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = json.dumps(payload).encode("utf-8")

    if dry_run:
        return {
            "success": True,
            "api_accepted": False,
            "response": {"dry_run": True, "message": "Dry-run mode: no network request made"},
            "error": None,
            "message_id": None
        }

    req = request.Request(url, data=data, headers=headers, method="POST")
    
    # Create SSL context with proper certificate verification
    ssl_context = _create_ssl_context()

    try:
        with request.urlopen(req, timeout=30, context=ssl_context) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            message_id = None
            if "messages" in response_data and response_data["messages"]:
                message_id = response_data["messages"][0].get("id")
            return {
                "success": True,
                "api_accepted": True,
                "response": response_data,
                "error": None,
                "message_id": message_id
            }
    except error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No response body"
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get("error", {}).get("message", error_body)
        except json.JSONDecodeError:
            error_msg = error_body
        return {
            "success": False,
            "api_accepted": False,
            "response": {"status": e.code, "body": error_body},
            "error": f"HTTP {e.code}: {error_msg}",
            "message_id": None
        }
    except error.URLError as e:
        return {
            "success": False,
            "api_accepted": False,
            "response": {},
            "error": f"Network error: {e.reason}",
            "message_id": None
        }
    except Exception as e:
        return {
            "success": False,
            "api_accepted": False,
            "response": {},
            "error": f"Unexpected error: {type(e).__name__}: {e}",
            "message_id": None
        }


def log_whatsapp_event(event_type: str, message: str, level: str = "INFO", extra: dict = None) -> None:
    """Log WhatsApp event to execution log (mirrors log_event.py pattern)."""
    log_path = Path(__file__).parent.parent / "output" / "execution_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "level": level.upper(),
        "event_type": event_type,
        "message": message
    }

    if extra:
        safe_extra = {}
        for k, v in extra.items():
            if not any(sensitive in k.lower() for sensitive in ["password", "token", "secret", "cookie", "credential", "access_token"]):
                safe_extra[k] = v
        if safe_extra:
            entry["extra"] = safe_extra

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Send WhatsApp test notification via Meta Cloud API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/send_whatsapp_notification.py --dry-run
  python scripts/send_whatsapp_notification.py --send

Environment variables must be set (or loaded from .env file):
  WHATSAPP_ACCESS_TOKEN     Meta API access token
  WHATSAPP_PHONE_NUMBER_ID  Meta Business phone number ID (default: 1311740252032810)
  WHATSAPP_TEST_RECIPIENT   Approved test recipient (E.164 format, e.g., +15556292158)

Note: Live sending requires explicit --send flag.
"""
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip network request, show what would be sent"
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send live message (required for real API call)"
    )
    args = parser.parse_args()

    # Load .env file from project root
    project_root = Path(__file__).parent.parent
    load_env_file(project_root / ".env")

    try:
        access_token, phone_number_id, test_recipient = load_env_vars()
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Set the required environment variables and try again.", file=sys.stderr)
        print("See docs/whatsapp_cloud_api_setup.md for setup instructions.", file=sys.stderr)
        sys.exit(2)

    # Validate recipient format (basic E.164 check)
    if not test_recipient.startswith("+") or not test_recipient[1:].isdigit():
        print(f"ERROR: WHATSAPP_TEST_RECIPIENT must be in E.164 format (e.g., +15556292158)", file=sys.stderr)
        sys.exit(2)

    # Determine mode
    if args.dry_run and args.send:
        print("ERROR: Cannot use both --dry-run and --send", file=sys.stderr)
        sys.exit(2)
    if not args.dry_run and not args.send:
        print("ERROR: Must specify either --dry-run or --send", file=sys.stderr)
        sys.exit(2)

    payload = build_payload(test_recipient)

    print("WhatsApp Cloud API Test Notification")
    print("=" * 50)
    print(f"Recipient: {test_recipient}")
    print(f"Phone Number ID: {phone_number_id}")
    print(f"Template:  {HELLO_WORLD_TEMPLATE}")
    print(f"Mode:      {'DRY RUN' if args.dry_run else 'LIVE (--send)'}")
    print()

    if args.dry_run:
        print("Payload that would be sent:")
        print(json.dumps(payload, indent=2))
        print()

    # Log start
    if args.dry_run:
        log_whatsapp_event(
            "WHATSAPP_DEMO_STARTED",
            "WhatsApp notification dry-run initiated",
            "INFO",
            {
                "recipient": test_recipient,
                "phone_number_id": phone_number_id,
                "template": HELLO_WORLD_TEMPLATE,
                "mode": "dry_run"
            }
        )
    else:
        log_whatsapp_event(
            "WHATSAPP_API_ACCEPTED",
            "WhatsApp notification live send initiated",
            "INFO",
            {
                "recipient": test_recipient,
                "phone_number_id": phone_number_id,
                "template": HELLO_WORLD_TEMPLATE,
                "mode": "live"
            }
        )

    result = send_message(access_token, phone_number_id, payload, dry_run=args.dry_run)

    if result["success"]:
        if args.dry_run:
            print("SUCCESS: Dry-run completed (no message sent)")
            print(result["response"]["message"])
            # Dry-run: only log DEMO_STARTED (already logged above)
        else:
            print("SUCCESS: Message accepted by WhatsApp API")
            if result["message_id"]:
                print(f"Message ID: {result['message_id']}")
                print("NOTE: Message accepted by API. Delivery confirmation requires webhook.")
            else:
                print("WARNING: No message ID returned by API")

            # Log API acceptance for live send
            log_whatsapp_event(
                "WHATSAPP_API_ACCEPTED",
                "WhatsApp API accepted message",
                "INFO",
                {
                    "message_id": result["message_id"],
                "recipient": test_recipient
            }
        )
        sys.exit(0)
    else:
        print("FAILURE: Message not sent")
        # Sanitize error - don't expose token details
        error_msg = result["error"]
        if "access_token" in error_msg.lower() or "authorization" in error_msg.lower():
            error_msg = "Authentication error (check token validity)"
        print(f"Error: {error_msg}")

        # Log failure
        log_whatsapp_event(
            "WHATSAPP_NOTIFICATION_FAILED",
            f"WhatsApp notification failed: {error_msg}",
            "ERROR",
            {
                "recipient": test_recipient,
                "error": error_msg
            }
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
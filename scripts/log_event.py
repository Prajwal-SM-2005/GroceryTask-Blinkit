#!/usr/bin/env python3
"""
Event logging utility for the grocery shopping assistant.
Writes timestamped events to JSONL format. Does not log credentials or secrets.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


LOG_PATH = Path(__file__).parent.parent / "output" / "execution_log.jsonl"


def log_event(
    event_type: str,
    message: str,
    level: str = "INFO",
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an event to the execution log.
    
    Args:
        event_type: Category of event (e.g., 'validation', 'cart_check', 'summary_generation')
        message: Human-readable description
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        extra: Additional structured data (no secrets/credentials)
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level.upper(),
        "event_type": event_type,
        "message": message
    }
    
    if extra:
        safe_extra = {}
        for k, v in extra.items():
            if not any(sensitive in k.lower() for sensitive in ["password", "token", "secret", "cookie", "credential"]):
                safe_extra[k] = v
        if safe_extra:
            entry["extra"] = safe_extra
    
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    """Test logging functionality."""
    log_event("test", "Log system initialized", "INFO", {"component": "log_event"})
    log_event("validation", "Shopping list validated successfully", "INFO", {"items_count": 3})
    log_event("cart_check", "Cart validation completed", "INFO", {"matched": 3, "unavailable": 0})
    log_event("summary", "Shopping summary generated", "INFO", {"output_files": 2})
    print(f"Test events written to {LOG_PATH}")


if __name__ == "__main__":
    main()
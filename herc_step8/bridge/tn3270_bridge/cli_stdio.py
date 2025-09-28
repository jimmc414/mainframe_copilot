#!/usr/bin/env python3
"""CLI STDIO Interface - JSON input/output via stdin/stdout for LLM integration"""

import json
import sys
import logging
from typing import Dict, Any

from .session import S3270Session

# Configure logging to stderr so it doesn't interfere with JSON output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

def redact_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields"""
    sensitive_keys = ["pwd", "pass", "password", "passwd"]
    redacted = data.copy()

    for key in redacted:
        if any(s in key.lower() for s in sensitive_keys):
            redacted[key] = "***REDACTED***"

    return redacted

def process_command(session: S3270Session, command: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single command and return response"""
    cmd_type = command.get("type", "").lower()

    try:
        if cmd_type == "connect":
            host = command.get("host", "127.0.0.1:3270")
            if not host.startswith(("127.0.0.1:", "localhost:")):
                return {"error": "Only localhost connections allowed"}

            success = session.connect(host)
            return {
                "type": "connect",
                "connected": success,
                "status": "Connected" if success else "Failed",
                "host": host
            }

        elif cmd_type == "disconnect":
            session.disconnect()
            return {
                "type": "disconnect",
                "connected": False,
                "status": "Disconnected"
            }

        elif cmd_type == "screen":
            if not session.connected:
                return {"error": "Not connected"}

            snapshot = session.snapshot()
            return {
                "type": "screen",
                **snapshot
            }

        elif cmd_type == "actions":
            if not session.connected:
                return {"error": "Not connected"}

            actions = command.get("actions", [])
            results = session.execute_actions(actions)
            return {
                "type": "actions",
                "results": results
            }

        elif cmd_type == "fill":
            if not session.connected:
                return {"error": "Not connected"}

            row = command.get("row")
            col = command.get("col")
            text = command.get("text", "")
            enter = command.get("enter", False)

            if row is None or col is None:
                return {"error": "Missing row or col"}

            # Log with redacted text
            log_cmd = redact_sensitive(command)
            logger.info(f"Fill: {log_cmd}")

            session.fill_at(row, col, text, enter)
            return {
                "type": "fill",
                "status": "ok",
                "position": [row, col]
            }

        elif cmd_type == "press":
            if not session.connected:
                return {"error": "Not connected"}

            aid = command.get("aid")
            if not aid:
                return {"error": "Missing aid key"}

            session.press(aid)
            return {
                "type": "press",
                "status": "ok",
                "aid": aid
            }

        elif cmd_type == "fill_by_label":
            if not session.connected:
                return {"error": "Not connected"}

            label = command.get("label")
            offset = command.get("offset", 1)
            text = command.get("text", "")

            if not label:
                return {"error": "Missing label"}

            # Log with redacted text
            log_cmd = redact_sensitive(command)
            logger.info(f"Fill by label: {log_cmd}")

            success = session.fill_by_label(label, offset, text)
            return {
                "type": "fill_by_label",
                "status": "ok" if success else "error",
                "label": label,
                "found": success
            }

        elif cmd_type == "status":
            return {
                "type": "status",
                "connected": session.connected,
                "status": "Connected" if session.connected else "Disconnected"
            }

        elif cmd_type == "help":
            return {
                "type": "help",
                "commands": [
                    {"type": "connect", "params": {"host": "127.0.0.1:3270"}},
                    {"type": "disconnect"},
                    {"type": "screen"},
                    {"type": "actions", "params": {"actions": ["Wait(3270)", "Ascii"]}},
                    {"type": "fill", "params": {"row": 1, "col": 1, "text": "...", "enter": False}},
                    {"type": "press", "params": {"aid": "Enter|PF1-24|PA1-3|Clear"}},
                    {"type": "fill_by_label", "params": {"label": "...", "offset": 1, "text": "..."}},
                    {"type": "status"},
                    {"type": "quit"}
                ]
            }

        elif cmd_type == "quit":
            return {"type": "quit", "status": "Goodbye"}

        else:
            return {"error": f"Unknown command type: {cmd_type}"}

    except Exception as e:
        logger.error(f"Command error: {e}")
        return {"error": str(e)}

def main():
    """Main CLI loop"""
    logger.info("TN3270 Bridge CLI started (JSON stdio mode)")
    print(json.dumps({"status": "ready", "version": "1.0.0"}), flush=True)

    # Create session
    trace = "--trace" in sys.argv
    session = S3270Session(trace_file="/tmp/s3270.trace" if trace else None)
    session.start()

    try:
        while True:
            try:
                # Read JSON command from stdin
                line = sys.stdin.readline()
                if not line:
                    break

                # Parse JSON
                try:
                    command = json.loads(line.strip())
                except json.JSONDecodeError as e:
                    response = {"error": f"Invalid JSON: {e}"}
                    print(json.dumps(response), flush=True)
                    continue

                # Process command
                response = process_command(session, command)

                # Write JSON response to stdout
                print(json.dumps(response), flush=True)

                # Check for quit
                if command.get("type") == "quit":
                    break

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                response = {"error": str(e)}
                print(json.dumps(response), flush=True)

    finally:
        session.stop()
        logger.info("TN3270 Bridge CLI stopped")

if __name__ == "__main__":
    main()
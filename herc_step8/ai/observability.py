#!/usr/bin/env python3
"""Observability module with JSONL logging and metrics"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import threading
from collections import deque

class JSONLLogger:
    """JSONL (JSON Lines) logger for structured logging"""

    def __init__(self, log_dir: Path = None, max_size_mb: int = 100):
        self.log_dir = Path(log_dir or "~/herc/logs/ai").expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024

        # Current log file
        self.current_file = self._get_log_file()

        # Redaction keys
        self.redact_keys = {
            "pwd", "pass", "password", "pin", "secret", "key", "token",
            "credential", "auth", "api_key", "private"
        }

        # Thread-safe writing
        self.lock = threading.Lock()

    def _get_log_file(self) -> Path:
        """Get current log file, rotate if needed"""
        date_str = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"actions_{date_str}.jsonl"

        # Rotate if file is too large
        if log_file.exists() and log_file.stat().st_size > self.max_size_bytes:
            for i in range(1, 100):
                rotated = self.log_dir / f"actions_{date_str}_{i:02d}.jsonl"
                if not rotated.exists():
                    log_file.rename(rotated)
                    break

        return log_file

    def _redact_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive parameters"""
        if not params:
            return {}

        redacted = {}
        for key, value in params.items():
            # Check if key contains sensitive word
            if any(r in key.lower() for r in self.redact_keys):
                redacted[key] = "***REDACTED***"
            elif isinstance(value, dict):
                redacted[key] = self._redact_params(value)
            elif isinstance(value, str):
                # Check if value looks like a credential
                if len(value) > 4 and any(r in key.lower() for r in ["user", "id"]):
                    redacted[key] = value  # Keep usernames
                elif any(r in str(value).lower() for r in self.redact_keys):
                    redacted[key] = "***REDACTED***"
                else:
                    redacted[key] = value
            else:
                redacted[key] = value

        return redacted

    def log_action(self,
                   mode: str,
                   goal: str,
                   step: int,
                   tool: str,
                   params: Dict[str, Any] = None,
                   screen_before: str = None,
                   screen_after: str = None,
                   latency_ms: int = 0,
                   outcome: str = "success",
                   notes: str = None):
        """Log an action in JSONL format"""

        # Calculate screen digests
        digest_before = None
        digest_after = None

        if screen_before:
            digest_before = hashlib.sha256(screen_before.encode()).hexdigest()[:16]
        if screen_after:
            digest_after = hashlib.sha256(screen_after.encode()).hexdigest()[:16]

        # Build log entry
        entry = {
            "ts": datetime.now().isoformat(),
            "mode": mode,
            "goal": goal,
            "step": step,
            "tool": tool,
            "params_redacted": self._redact_params(params or {}),
            "digest_before": digest_before,
            "digest_after": digest_after,
            "latency_ms": latency_ms,
            "outcome": outcome,
            "notes": notes
        }

        # Write to file (thread-safe)
        with self.lock:
            # Check if we need to rotate
            if self.current_file.exists() and \
               self.current_file.stat().st_size > self.max_size_bytes:
                self.current_file = self._get_log_file()

            # Append to log file
            with open(self.current_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')


class TraceLogger:
    """Optional trace logger for screen snapshots"""

    def __init__(self, trace_dir: Path = None, enabled: bool = False, max_traces: int = 1000):
        self.trace_dir = Path(trace_dir or "~/herc/logs/ai/trace").expanduser()
        self.enabled = enabled
        self.max_traces = max_traces

        if self.enabled:
            self.trace_dir.mkdir(parents=True, exist_ok=True)
            self._cleanup_old_traces()

    def _cleanup_old_traces(self):
        """Remove old traces if over limit"""
        traces = sorted(self.trace_dir.glob("*.txt"))
        if len(traces) > self.max_traces:
            for trace in traces[:-self.max_traces]:
                trace.unlink()

    def save_trace(self, screen: str, action: str = None):
        """Save screen trace"""
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"screen_{timestamp}.txt"

        if action:
            filename = f"screen_{timestamp}_{action}.txt"

        trace_file = self.trace_dir / filename

        with open(trace_file, 'w') as f:
            f.write(f"# Timestamp: {datetime.now().isoformat()}\n")
            if action:
                f.write(f"# Action: {action}\n")
            f.write(f"# {'=' * 78}\n")
            f.write(screen)

        # Cleanup if needed
        self._cleanup_old_traces()


class MetricsCollector:
    """Collect and aggregate performance metrics"""

    def __init__(self, metrics_file: Path = None):
        self.metrics_file = Path(metrics_file or "~/herc/logs/ai/metrics.json").expanduser()
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing metrics or initialize
        if self.metrics_file.exists():
            with open(self.metrics_file) as f:
                self.metrics = json.load(f)
        else:
            self.metrics = self._init_metrics()

        # Current session metrics
        self.session_metrics = {
            "start_time": datetime.now().isoformat(),
            "actions": [],
            "errors": 0,
            "fallbacks": 0
        }

        # Thread-safe
        self.lock = threading.Lock()

    def _init_metrics(self) -> Dict[str, Any]:
        """Initialize metrics structure"""
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_actions": 0,
            "total_errors": 0,
            "total_fallbacks": 0,
            "success_rate": 0.0,
            "mean_actions_per_run": 0.0,
            "mean_latency_ms": 0.0,
            "fallback_rate": 0.0,
            "flow_usage_rate": 0.0,
            "last_updated": None,
            "history": []
        }

    def record_action(self, tool: str, latency_ms: int, outcome: str):
        """Record an action"""
        with self.lock:
            self.session_metrics["actions"].append({
                "tool": tool,
                "latency_ms": latency_ms,
                "outcome": outcome,
                "timestamp": datetime.now().isoformat()
            })

            if outcome == "error":
                self.session_metrics["errors"] += 1

    def record_fallback(self):
        """Record a fallback"""
        with self.lock:
            self.session_metrics["fallbacks"] += 1

    def end_session(self, success: bool):
        """End session and update metrics"""
        with self.lock:
            # Calculate session metrics
            action_count = len(self.session_metrics["actions"])
            if action_count > 0:
                latencies = [a["latency_ms"] for a in self.session_metrics["actions"]]
                avg_latency = sum(latencies) / len(latencies)
            else:
                avg_latency = 0

            # Update global metrics
            self.metrics["total_runs"] += 1
            if success:
                self.metrics["successful_runs"] += 1
            else:
                self.metrics["failed_runs"] += 1

            self.metrics["total_actions"] += action_count
            self.metrics["total_errors"] += self.session_metrics["errors"]
            self.metrics["total_fallbacks"] += self.session_metrics["fallbacks"]

            # Calculate rates
            if self.metrics["total_runs"] > 0:
                self.metrics["success_rate"] = \
                    self.metrics["successful_runs"] / self.metrics["total_runs"]
                self.metrics["mean_actions_per_run"] = \
                    self.metrics["total_actions"] / self.metrics["total_runs"]
                self.metrics["fallback_rate"] = \
                    self.metrics["total_fallbacks"] / self.metrics["total_runs"]

            # Update latency
            if avg_latency > 0:
                if self.metrics["mean_latency_ms"] == 0:
                    self.metrics["mean_latency_ms"] = avg_latency
                else:
                    # Rolling average
                    self.metrics["mean_latency_ms"] = \
                        (self.metrics["mean_latency_ms"] + avg_latency) / 2

            # Add to history (keep last 100)
            self.metrics["history"].append({
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "actions": action_count,
                "errors": self.session_metrics["errors"],
                "fallbacks": self.session_metrics["fallbacks"],
                "avg_latency_ms": avg_latency
            })

            if len(self.metrics["history"]) > 100:
                self.metrics["history"] = self.metrics["history"][-100:]

            self.metrics["last_updated"] = datetime.now().isoformat()

            # Save to file
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)

            # Reset session metrics
            self.session_metrics = {
                "start_time": datetime.now().isoformat(),
                "actions": [],
                "errors": 0,
                "fallbacks": 0
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        with self.lock:
            return self.metrics.copy()

    def get_summary(self) -> str:
        """Get metrics summary as string"""
        m = self.get_metrics()
        return f"""
Metrics Summary:
  Total Runs: {m['total_runs']}
  Success Rate: {m['success_rate']:.2%}
  Mean Actions/Run: {m['mean_actions_per_run']:.1f}
  Mean Latency: {m['mean_latency_ms']:.0f}ms
  Fallback Rate: {m['fallback_rate']:.2%}
  Total Errors: {m['total_errors']}
"""


# Global instances
jsonl_logger = JSONLLogger()
trace_logger = TraceLogger()
metrics = MetricsCollector()


def log_action(mode: str, goal: str, step: int, tool: str, **kwargs):
    """Convenience function for logging"""
    jsonl_logger.log_action(mode, goal, step, tool, **kwargs)


def save_trace(screen: str, action: str = None):
    """Convenience function for tracing"""
    trace_logger.save_trace(screen, action)


def record_metric(tool: str, latency_ms: int, outcome: str):
    """Convenience function for metrics"""
    metrics.record_action(tool, latency_ms, outcome)


if __name__ == "__main__":
    # Test logging
    print("Testing observability module...")

    # Test JSONL logging
    log_action(
        mode="test",
        goal="test logging",
        step=1,
        tool="connect",
        params={"host": "127.0.0.1:3270", "password": "secret123"},
        screen_before="LOGON SCREEN",
        screen_after="READY",
        latency_ms=250,
        outcome="success"
    )
    print(f"Log written to: {jsonl_logger.current_file}")

    # Test metrics
    record_metric("connect", 250, "success")
    record_metric("fill", 50, "success")
    record_metric("press", 100, "error")
    metrics.record_fallback()
    metrics.end_session(success=True)
    print(metrics.get_summary())

    print("Test complete!")
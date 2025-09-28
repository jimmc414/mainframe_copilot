#!/usr/bin/env python3
"""Watchdog monitoring system for TN3270 Bridge and Agent"""

import time
import requests
import subprocess
import json
import signal
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import argparse


class ServiceWatchdog:
    """Monitor and manage services"""

    def __init__(self, config_file: Path = None):
        # Load configuration
        self.config = self._load_config(config_file)

        # Setup logging
        self.log_dir = Path("~/herc/logs/watchdog").expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

        # Service URLs (LOCALHOST ONLY)
        self.bridge_health_url = "http://127.0.0.1:8080/healthz"
        self.bridge_reset_url = "http://127.0.0.1:8080/reset_session"

        # State tracking
        self.failures = {"bridge": 0, "hercules": 0}
        self.last_restart = {"bridge": None, "hercules": None}
        self.running = True

        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration"""
        default_config = {
            "check_interval": 10,  # seconds
            "timeout": 5,  # seconds
            "max_failures": 3,
            "restart_delay": 30,  # seconds between restarts
            "services": {
                "bridge": {
                    "enabled": True,
                    "start_cmd": "cd ~/herc/bridge && ./start_api.sh",
                    "stop_cmd": "pkill -f 'uvicorn.*tn3270_bridge'",
                    "health_threshold": 30  # seconds without response
                },
                "hercules": {
                    "enabled": True,
                    "start_cmd": "cd ~/herc && ./start_hercules.sh",
                    "stop_cmd": "pkill hercules",
                    "check_cmd": "pgrep hercules"
                }
            }
        }

        if config_file and config_file.exists():
            with open(config_file) as f:
                user_config = json.load(f)
                # Merge configs
                default_config.update(user_config)

        return default_config

    def _setup_logging(self):
        """Setup logging"""
        log_file = self.log_dir / f"watchdog_{datetime.now().strftime('%Y%m%d')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("watchdog")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)

    def check_bridge_health(self) -> bool:
        """Check TN3270 Bridge health"""
        if not self.config["services"]["bridge"]["enabled"]:
            return True

        try:
            response = requests.get(
                self.bridge_health_url,
                timeout=self.config["timeout"]
            )

            if response.status_code == 200:
                data = response.json()
                # Check if connected and recent activity
                if data.get("connected"):
                    self.logger.debug("Bridge healthy and connected")
                    self.failures["bridge"] = 0
                    return True
                else:
                    self.logger.warning("Bridge not connected to mainframe")
                    # Try to reconnect
                    self._reconnect_bridge()
                    return True

            elif response.status_code == 503:
                # Service degraded
                self.logger.warning("Bridge service degraded")
                self.failures["bridge"] += 1
                return False

        except requests.RequestException as e:
            self.logger.error(f"Bridge health check failed: {e}")
            self.failures["bridge"] += 1
            return False

        return False

    def _reconnect_bridge(self):
        """Try to reconnect bridge to mainframe"""
        try:
            response = requests.post(
                self.bridge_reset_url,
                timeout=self.config["timeout"]
            )
            if response.status_code == 200:
                self.logger.info("Bridge session reset successfully")
            else:
                self.logger.warning(f"Bridge reset returned: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Failed to reset bridge: {e}")

    def check_hercules(self) -> bool:
        """Check if Hercules is running"""
        if not self.config["services"]["hercules"]["enabled"]:
            return True

        try:
            # Use pgrep to check if hercules is running
            result = subprocess.run(
                ["pgrep", "hercules"],
                capture_output=True,
                timeout=self.config["timeout"]
            )

            if result.returncode == 0:
                self.logger.debug("Hercules is running")
                self.failures["hercules"] = 0
                return True
            else:
                self.logger.warning("Hercules not found")
                self.failures["hercules"] += 1
                return False

        except Exception as e:
            self.logger.error(f"Hercules check failed: {e}")
            self.failures["hercules"] += 1
            return False

    def restart_service(self, service: str) -> bool:
        """Restart a service"""
        # Check if we've restarted too recently
        if self.last_restart[service]:
            time_since = datetime.now() - self.last_restart[service]
            if time_since.total_seconds() < self.config["restart_delay"]:
                self.logger.info(
                    f"Skipping {service} restart (too recent: {time_since.total_seconds():.0f}s ago)"
                )
                return False

        self.logger.warning(f"Restarting {service}...")

        try:
            # Stop service
            stop_cmd = self.config["services"][service]["stop_cmd"]
            subprocess.run(stop_cmd, shell=True, timeout=10)
            time.sleep(2)

            # Start service
            start_cmd = self.config["services"][service]["start_cmd"]
            subprocess.Popen(start_cmd, shell=True)
            time.sleep(5)

            # Mark restart time
            self.last_restart[service] = datetime.now()
            self.failures[service] = 0

            self.logger.info(f"{service} restarted successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to restart {service}: {e}")
            return False

    def monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info("Watchdog started - monitoring services")
        self.logger.info(f"Config: {json.dumps(self.config, indent=2)}")

        while self.running:
            try:
                # Check services
                bridge_ok = self.check_bridge_health()
                hercules_ok = self.check_hercules()

                # Restart if needed
                if not bridge_ok and self.failures["bridge"] >= self.config["max_failures"]:
                    self.restart_service("bridge")

                if not hercules_ok and self.failures["hercules"] >= self.config["max_failures"]:
                    self.restart_service("hercules")
                    # Also restart bridge after hercules
                    time.sleep(10)
                    self.restart_service("bridge")

                # Sleep before next check
                time.sleep(self.config["check_interval"])

            except KeyboardInterrupt:
                self.logger.info("Monitoring interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                time.sleep(self.config["check_interval"])

        self.logger.info("Watchdog stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current watchdog status"""
        return {
            "running": self.running,
            "failures": self.failures,
            "last_restart": {
                k: v.isoformat() if v else None
                for k, v in self.last_restart.items()
            },
            "config": self.config
        }

    def test_mode(self):
        """Run tests without restarting services"""
        self.logger.info("Running in test mode...")

        print("\n=== Service Health Checks ===")

        # Check bridge
        print("\n1. TN3270 Bridge:")
        if self.check_bridge_health():
            print("   ✓ Bridge is healthy")
            try:
                response = requests.get(self.bridge_health_url, timeout=2)
                data = response.json()
                print(f"   - Status: {data.get('status')}")
                print(f"   - Connected: {data.get('connected')}")
                print(f"   - Uptime: {data.get('uptime_seconds', 0):.0f}s")
            except:
                pass
        else:
            print("   ✗ Bridge is not healthy")

        # Check Hercules
        print("\n2. Hercules:")
        if self.check_hercules():
            print("   ✓ Hercules is running")
            result = subprocess.run(
                ["pgrep", "-l", "hercules"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(f"   - Process: {result.stdout.strip()}")
        else:
            print("   ✗ Hercules is not running")

        print("\n=== Test Complete ===")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Service watchdog for mainframe automation")

    parser.add_argument("--config", type=Path,
                        help="Configuration file")
    parser.add_argument("--test", action="store_true",
                        help="Run in test mode (no restarts)")
    parser.add_argument("--interval", type=int,
                        help="Check interval in seconds")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose logging")

    args = parser.parse_args()

    # Create watchdog
    watchdog = ServiceWatchdog(config_file=args.config)

    if args.verbose:
        watchdog.logger.setLevel(logging.DEBUG)

    if args.interval:
        watchdog.config["check_interval"] = args.interval

    # Run appropriate mode
    if args.test:
        watchdog.test_mode()
    else:
        print("Starting watchdog monitor...")
        print(f"Check interval: {watchdog.config['check_interval']}s")
        print(f"Max failures before restart: {watchdog.config['max_failures']}")
        print("Press Ctrl+C to stop")
        watchdog.monitor_loop()


if __name__ == "__main__":
    main()
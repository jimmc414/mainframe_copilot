#!/usr/bin/env python3
"""TN3270 client wrapper for AI agent"""

import requests
import json
from typing import Dict, Any, Optional


class TN3270Bridge:
    """Simple wrapper for TN3270 Bridge API"""

    def __init__(self, base_url: str = "http://127.0.0.1:8080"):
        self.base_url = base_url
        self.session = requests.Session()
        self.connected = False

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def connect(self, host: str = "127.0.0.1:3270") -> Dict[str, Any]:
        """Connect to mainframe"""
        result = self._request("POST", "/connect", json={"host": host})
        if result.get("status") == "connected":
            self.connected = True
        return result

    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from mainframe"""
        result = self._request("POST", "/disconnect")
        self.connected = False
        return result

    def get_screen(self) -> Dict[str, Any]:
        """Get current screen snapshot"""
        return self._request("GET", "/screen")

    def fill_at(self, row: int, col: int, text: str, enter: bool = False) -> Dict[str, Any]:
        """Fill text at position"""
        return self._request("POST", "/fill", json={
            "row": row,
            "col": col,
            "text": text,
            "enter": enter
        })

    def fill_by_label(self, label: str, value: str, offset: int = 1) -> Dict[str, Any]:
        """Fill field by label"""
        return self._request("POST", "/fill_by_label", json={
            "label": label,
            "value": value,
            "offset": offset
        })

    def press_key(self, key: str) -> Dict[str, Any]:
        """Press function key"""
        return self._request("POST", "/press", json={"key": key})

    def wait(self, condition: str = "ready", timeout: int = 5000) -> Dict[str, Any]:
        """Wait for condition"""
        return self._request("POST", "/wait", json={
            "condition": condition,
            "timeout": timeout
        })

    def get_status(self) -> Dict[str, Any]:
        """Get connection status"""
        return self._request("GET", "/status")


class FlowRunner:
    """Simple flow runner wrapper"""

    def __init__(self, bridge: TN3270Bridge):
        self.bridge = bridge

    def run(self, flow_path: str) -> bool:
        """Run flow (simplified)"""
        # This is a placeholder - actual flow runner is more complex
        return True
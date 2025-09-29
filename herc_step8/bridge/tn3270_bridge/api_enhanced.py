"""Enhanced HTTP API for TN3270 Bridge with health and recovery"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
import logging
import time
import os
import psutil
from datetime import datetime
from contextlib import asynccontextmanager

from .session import S3270Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global session instance and metadata
session: Optional[S3270Session] = None
session_metadata = {
    "start_time": None,
    "last_action": None,
    "last_action_time": None,
    "action_count": 0,
    "error_count": 0,
    "reconnect_count": 0
}

# Action allowlist for safety
ALLOWED_ACTIONS = [
    "Wait(3270)", "Wait(InputField)", "Ascii()", "ReadBuffer(Ascii)",
    "Query", "MoveCursor", "String", "Enter", "PF", "PA", "Clear",
    "Disconnect", "Connect"
]

def validate_action(action: str) -> bool:
    """Validate action against allowlist"""
    for allowed in ALLOWED_ACTIONS:
        if action.startswith(allowed):
            return True
    return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global session, session_metadata
    # Startup
    session = S3270Session()
    session.start()
    session_metadata["start_time"] = datetime.now().isoformat()
    logger.info("Enhanced S3270 session started")
    yield
    # Shutdown
    if session:
        session.stop()
        logger.info("S3270 session stopped")

# Create FastAPI app
app = FastAPI(
    title="TN3270 Bridge API (Enhanced)",
    description="Production-ready JSON API for s3270 automation",
    version="2.0.0",
    lifespan=lifespan
)

# Request/Response models
class ConnectRequest(BaseModel):
    host: str = Field(default="127.0.0.1:3270", description="Host to connect to")

class ActionsRequest(BaseModel):
    actions: List[str] = Field(description="List of s3270 actions to execute")
    validate: bool = Field(default=True, description="Validate actions against allowlist")

class FillRequest(BaseModel):
    row: int = Field(description="Row position (1-based)")
    col: int = Field(description="Column position (1-based)")
    text: str = Field(description="Text to fill")
    enter: bool = Field(default=False, description="Press Enter after filling")

class PressRequest(BaseModel):
    key: str = Field(description="Key to press (Enter, PF1-PF12, PA1-PA3, Clear)")
    # Also support 'aid' for backward compatibility with flow_runner
    aid: Optional[str] = Field(default=None, description="Alternative to 'key' for compatibility")

class FillByLabelRequest(BaseModel):
    label: str = Field(description="Label to search for on screen")
    value: str = Field(description="Text to fill")
    offset: int = Field(default=1, description="Field offset from label")

class WaitRequest(BaseModel):
    condition: str = Field(default="ready", description="Condition to wait for")
    timeout: int = Field(default=5000, description="Timeout in milliseconds")

# Health check endpoint
@app.get("/healthz")
async def health_check():
    """Health check endpoint with detailed status"""
    global session, session_metadata

    try:
        # Get Hercules process info
        hercules_pid = None
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'hercules' in proc.info['name'].lower():
                hercules_pid = proc.info['pid']
                break

        # Check session status
        connected = False
        if session and session.process and session.process.poll() is None:
            # Try to get status
            try:
                session._send_command("Query(ConnectionState)")
                connected = True
            except:
                connected = False

        health = {
            "status": "healthy" if connected else "degraded",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (
                (datetime.now() - datetime.fromisoformat(session_metadata["start_time"])).total_seconds()
                if session_metadata["start_time"] else 0
            ),
            "hercules_pid": hercules_pid,
            "s3270_pid": session.process.pid if session and session.process else None,
            "connected": connected,
            "host": "127.0.0.1:3270",
            "last_action": session_metadata["last_action"],
            "last_action_time": session_metadata["last_action_time"],
            "action_count": session_metadata["action_count"],
            "error_count": session_metadata["error_count"],
            "reconnect_count": session_metadata["reconnect_count"]
        }

        return JSONResponse(content=health, status_code=200 if connected else 503)

    except Exception as e:
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )

# Session reset endpoint
@app.post("/reset_session")
async def reset_session():
    """Reset the TN3270 session"""
    global session, session_metadata

    try:
        # Disconnect if connected
        if session:
            try:
                session._send_command("Disconnect()")
            except:
                pass

            # Stop and restart session
            session.stop()
            time.sleep(1)
            session = S3270Session()
            session.start()

            # Reconnect
            result = session._send_command("Connect(127.0.0.1:3270)")
            session._send_command("Wait(InputField)")

            # Update metadata
            session_metadata["reconnect_count"] += 1
            session_metadata["last_action"] = "reset_session"
            session_metadata["last_action_time"] = datetime.now().isoformat()

            return {"status": "reset", "message": "Session reset successfully"}

    except Exception as e:
        session_metadata["error_count"] += 1
        raise HTTPException(status_code=500, detail=str(e))

# Connect with retry
@app.post("/connect")
async def connect(request: ConnectRequest):
    """Connect to host with retry logic"""
    global session, session_metadata

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    # Validate host is localhost
    if not request.host.startswith("127.0.0.1"):
        raise HTTPException(status_code=403, detail="Only localhost connections allowed")

    max_retries = 3
    retry_delays = [2, 4, 8]

    for attempt in range(max_retries):
        try:
            result = session._send_command(f"Connect({request.host})")

            # Wait for connection
            session._send_command("Wait(InputField)")

            # Update metadata
            session_metadata["last_action"] = "connect"
            session_metadata["last_action_time"] = datetime.now().isoformat()
            session_metadata["action_count"] += 1

            # Get initial screen
            screen = session.snapshot()

            return {
                "status": "connected",
                "message": f"Connected to {request.host}",
                "screen": screen
            }

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                continue
            else:
                session_metadata["error_count"] += 1
                raise HTTPException(status_code=500, detail=str(e))

# Get screen with keyboard lock detection
@app.get("/screen")
async def get_screen():
    """Get current screen with keyboard lock status"""
    global session, session_metadata

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    try:
        screen = session.snapshot()

        # Check for keyboard lock
        status = screen.get("status", "")
        keyboard_locked = "L" in status or "X" in status

        # Add lock status
        screen["keyboard_locked"] = keyboard_locked

        # Update metadata
        session_metadata["last_action"] = "screen"
        session_metadata["last_action_time"] = datetime.now().isoformat()

        return screen

    except Exception as e:
        session_metadata["error_count"] += 1
        raise HTTPException(status_code=500, detail=str(e))

# Execute actions with validation
@app.post("/actions")
async def execute_actions(request: ActionsRequest):
    """Execute s3270 actions with validation"""
    global session, session_metadata

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    # Validate actions if requested
    if request.validate:
        for action in request.actions:
            if not validate_action(action):
                raise HTTPException(
                    status_code=403,
                    detail=f"Action not allowed: {action}"
                )

    results = []
    for action in request.actions:
        try:
            result = session._send_command(action)
            results.append({"action": action, "result": result, "status": "ok"})

            # Update metadata
            session_metadata["last_action"] = action
            session_metadata["last_action_time"] = datetime.now().isoformat()
            session_metadata["action_count"] += 1

        except Exception as e:
            results.append({"action": action, "error": str(e), "status": "error"})
            session_metadata["error_count"] += 1

            # Check for keyboard lock
            if "keyboard locked" in str(e).lower():
                # Try recovery
                try:
                    session._send_command("Clear()")
                    time.sleep(0.5)
                    session._send_command("Reset()")
                except:
                    pass

    return {"results": results}

# Fill with automatic unlock
@app.post("/fill")
async def fill(request: FillRequest):
    """Fill field with automatic keyboard unlock"""
    global session, session_metadata

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    try:
        # Wait for keyboard unlock first
        session._send_command("Wait(InputField)")

        # Move cursor and fill
        result = session.fill_at(request.row, request.col, request.text, request.enter)

        # Update metadata
        session_metadata["last_action"] = f"fill@{request.row},{request.col}"
        session_metadata["last_action_time"] = datetime.now().isoformat()
        session_metadata["action_count"] += 1

        return result

    except Exception as e:
        session_metadata["error_count"] += 1

        # Try keyboard recovery
        if "keyboard" in str(e).lower():
            try:
                session._send_command("Clear()")
                time.sleep(0.5)
                return {"status": "recovered", "message": "Keyboard unlocked"}
            except:
                pass

        raise HTTPException(status_code=500, detail=str(e))

# Press key with recovery
@app.post("/press")
async def press(request: PressRequest):
    """Press key with automatic recovery"""
    global session, session_metadata

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    # Support both 'key' and 'aid' for backward compatibility
    key_to_press = request.key if request.key else request.aid
    if not key_to_press:
        raise HTTPException(status_code=400, detail="Must provide either 'key' or 'aid'")

    # Validate key
    valid_keys = ["Enter", "Clear"] + [f"PF{i}" for i in range(1, 13)] + [f"PA{i}" for i in range(1, 4)]
    if key_to_press not in valid_keys:
        raise HTTPException(status_code=400, detail=f"Invalid key: {key_to_press}")

    try:
        result = session._send_command(f"{key_to_press}()")

        # Update metadata
        session_metadata["last_action"] = f"press_{key_to_press}"
        session_metadata["last_action_time"] = datetime.now().isoformat()
        session_metadata["action_count"] += 1

        # Wait for screen update
        time.sleep(0.5)

        # Return updated screen
        screen = session.snapshot()
        return {"status": "success", "key": key_to_press, "screen": screen}

    except Exception as e:
        session_metadata["error_count"] += 1
        raise HTTPException(status_code=500, detail=str(e))

# Fill by label endpoint
@app.post("/fill_by_label")
async def fill_by_label(request: FillByLabelRequest):
    """Find label on screen and fill associated field"""
    global session, session_metadata

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    try:
        # Use session's fill_by_label method
        result = session.fill_by_label(request.label, request.offset, request.value)

        # Update metadata
        session_metadata["last_action"] = f"fill_by_label_{request.label}"
        session_metadata["last_action_time"] = datetime.now().isoformat()
        session_metadata["action_count"] += 1

        if result:
            return {"status": "ok", "label": request.label, "value_length": len(request.value)}
        else:
            return {"status": "error", "message": f"Label '{request.label}' not found"}

    except Exception as e:
        session_metadata["error_count"] += 1
        raise HTTPException(status_code=500, detail=str(e))

# Wait with timeout
@app.post("/wait")
async def wait(request: WaitRequest):
    """Wait for condition with timeout"""
    global session, session_metadata

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    try:
        if request.condition == "ready":
            result = session._send_command(f"Wait({request.timeout},InputField)")
        elif request.condition == "change":
            result = session._send_command(f"Wait({request.timeout},Output)")
        else:
            result = session._send_command(f"Wait({request.timeout},{request.condition})")

        # Update metadata
        session_metadata["last_action"] = f"wait_{request.condition}"
        session_metadata["last_action_time"] = datetime.now().isoformat()

        return {"status": "ready", "condition": request.condition}

    except Exception as e:
        if "timed out" in str(e).lower():
            return {"status": "timeout", "condition": request.condition}
        raise HTTPException(status_code=500, detail=str(e))

# Disconnect
@app.post("/disconnect")
async def disconnect():
    """Disconnect from host"""
    global session, session_metadata

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    try:
        result = session._send_command("Disconnect()")

        # Update metadata
        session_metadata["last_action"] = "disconnect"
        session_metadata["last_action_time"] = datetime.now().isoformat()

        return {"status": "disconnected"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get session status
@app.get("/status")
async def get_status():
    """Get session status"""
    global session, session_metadata

    connected = False
    if session and session.process and session.process.poll() is None:
        try:
            session._send_command("Query(ConnectionState)")
            connected = True
        except:
            connected = False

    return {
        "connected": connected,
        "status": "Connected" if connected else "Disconnected",
        "metadata": session_metadata
    }

def main():
    """Main entry point - LOCALHOST ONLY"""
    print("Starting Enhanced TN3270 Bridge API")
    print("Binding to 127.0.0.1:8080 (localhost only)")
    print("Health check: http://127.0.0.1:8080/healthz")
    print("Press Ctrl+C to stop")

    # ENFORCE LOCALHOST BINDING
    uvicorn.run(
        "tn3270_bridge.api_enhanced:app",
        host="127.0.0.1",  # LOCALHOST ONLY
        port=8080,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
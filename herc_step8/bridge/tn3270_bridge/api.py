"""HTTP API for TN3270 Bridge"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
import logging
from contextlib import asynccontextmanager

from .session import S3270Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global session instance
session: Optional[S3270Session] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global session
    # Startup
    session = S3270Session()
    session.start()
    logger.info("S3270 session started")
    yield
    # Shutdown
    if session:
        session.stop()
        logger.info("S3270 session stopped")

# Create FastAPI app
app = FastAPI(
    title="TN3270 Bridge API",
    description="JSON API for s3270 automation",
    version="1.0.0",
    lifespan=lifespan
)

# Request/Response models
class ConnectRequest(BaseModel):
    host: str = Field(default="127.0.0.1:3270", description="Host to connect to")

class DisconnectRequest(BaseModel):
    pass

class ActionsRequest(BaseModel):
    actions: List[str] = Field(description="List of s3270 actions to execute")

class FillRequest(BaseModel):
    row: int = Field(ge=1, le=43, description="Row position (1-based)")
    col: int = Field(ge=1, le=132, description="Column position (1-based)")
    text: str = Field(description="Text to enter")
    enter: bool = Field(default=False, description="Press Enter after filling")

class PressRequest(BaseModel):
    aid: str = Field(description="AID key to press (Enter, PF1-24, PA1-3, Clear)")

class FillByLabelRequest(BaseModel):
    label: str = Field(description="Label text to search for")
    offset: int = Field(default=1, description="Offset from label")
    text: str = Field(description="Text to enter")

class ScreenResponse(BaseModel):
    rows: int
    cols: int
    cursor: List[int]
    ascii: str
    fields: List[Dict[str, Any]]
    digest: str

class StatusResponse(BaseModel):
    connected: bool
    status: str
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    details: Optional[Dict[str, Any]] = None

# Utility function to redact sensitive data
def redact_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields in data"""
    sensitive_keys = ["pwd", "pass", "password", "passwd"]
    redacted = data.copy()

    for key in redacted:
        if any(s in key.lower() for s in sensitive_keys):
            redacted[key] = "***REDACTED***"

    return redacted

# API Endpoints
@app.post("/connect", response_model=StatusResponse)
async def connect(request: ConnectRequest):
    """Connect to TN3270 host"""
    global session

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    # Validate localhost only
    if not request.host.startswith(("127.0.0.1:", "localhost:")):
        raise HTTPException(status_code=400, detail="Only localhost connections allowed")

    try:
        success = session.connect(request.host)
        if success:
            return StatusResponse(connected=True, status="Connected", message=f"Connected to {request.host}")
        else:
            return StatusResponse(connected=False, status="Failed", message="Connection failed")
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/disconnect", response_model=StatusResponse)
async def disconnect():
    """Disconnect from host"""
    global session

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    try:
        session.disconnect()
        return StatusResponse(connected=False, status="Disconnected", message="Disconnected from host")
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/actions")
async def execute_actions(request: ActionsRequest):
    """Execute raw s3270 actions"""
    global session

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    if not session.connected:
        raise HTTPException(status_code=400, detail="Not connected")

    try:
        results = session.execute_actions(request.actions)
        return {"results": results}
    except Exception as e:
        logger.error(f"Action execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/screen", response_model=ScreenResponse)
async def get_screen():
    """Get current screen snapshot"""
    global session

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    if not session.connected:
        raise HTTPException(status_code=400, detail="Not connected")

    try:
        snapshot = session.snapshot()
        return ScreenResponse(**snapshot)
    except Exception as e:
        logger.error(f"Screen capture error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fill")
async def fill_field(request: FillRequest):
    """Fill field at position"""
    global session

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    if not session.connected:
        raise HTTPException(status_code=400, detail="Not connected")

    try:
        # Redact sensitive data from logs
        log_data = redact_sensitive(request.dict())
        logger.info(f"Fill field: {log_data}")

        session.fill_at(request.row, request.col, request.text, request.enter)
        return {"status": "ok", "message": f"Filled at ({request.row},{request.col})"}
    except Exception as e:
        logger.error(f"Fill error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/press")
async def press_key(request: PressRequest):
    """Press AID key"""
    global session

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    if not session.connected:
        raise HTTPException(status_code=400, detail="Not connected")

    try:
        session.press(request.aid)
        return {"status": "ok", "message": f"Pressed {request.aid}"}
    except Exception as e:
        logger.error(f"Press error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fill_by_label")
async def fill_by_label(request: FillByLabelRequest):
    """Fill field by label"""
    global session

    if not session:
        raise HTTPException(status_code=500, detail="Session not initialized")

    if not session.connected:
        raise HTTPException(status_code=400, detail="Not connected")

    try:
        # Redact sensitive data
        log_data = redact_sensitive(request.dict())
        logger.info(f"Fill by label: {log_data}")

        success = session.fill_by_label(request.label, request.offset, request.text)
        if success:
            return {"status": "ok", "message": f"Filled field after '{request.label}'"}
        else:
            return {"status": "error", "message": f"Label '{request.label}' not found"}
    except Exception as e:
        logger.error(f"Fill by label error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get connection status"""
    global session

    if not session:
        return StatusResponse(connected=False, status="No session")

    return StatusResponse(
        connected=session.connected,
        status="Connected" if session.connected else "Disconnected"
    )

@app.get("/")
async def root():
    """API information"""
    return {
        "name": "TN3270 Bridge API",
        "version": "1.0.0",
        "endpoints": [
            {"method": "POST", "path": "/connect", "description": "Connect to host"},
            {"method": "POST", "path": "/disconnect", "description": "Disconnect from host"},
            {"method": "GET", "path": "/screen", "description": "Get screen snapshot"},
            {"method": "POST", "path": "/actions", "description": "Execute raw actions"},
            {"method": "POST", "path": "/fill", "description": "Fill field at position"},
            {"method": "POST", "path": "/press", "description": "Press AID key"},
            {"method": "POST", "path": "/fill_by_label", "description": "Fill field by label"},
            {"method": "GET", "path": "/status", "description": "Get connection status"}
        ]
    }

def run_server(host: str = "127.0.0.1", port: int = 8080, trace: bool = False):
    """Run the API server"""
    global session

    # Configure trace if requested
    if trace:
        import tempfile
        trace_file = tempfile.NamedTemporaryFile(prefix="s3270_", suffix=".trace", delete=False)
        logger.info(f"Trace file: {trace_file.name}")
        session = S3270Session(trace_file=trace_file.name)

    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    import sys
    trace_mode = "--trace" in sys.argv
    run_server(trace=trace_mode)
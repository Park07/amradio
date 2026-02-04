"""
FastAPI Backend for UGL AM Radio Control
=========================================

Thin wrapper around existing model.py - exposes REST endpoints.
Auto-started by Tauri app.

Run standalone: uvicorn api:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from model import Model, ConnectionState, BroadcastState, WatchdogState
from config import Config

app = FastAPI(title="UGL AM Radio Control API")

# CORS - Allow Tauri app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance
model = Model()


# === Request/Response Models ===

class ConnectRequest(BaseModel):
    ip: str = Config.DEFAULT_IP
    port: int = Config.DEFAULT_PORT


class ChannelUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[int] = None  # Hz


class SourceUpdate(BaseModel):
    source: str  # "bram" or "adc"
    message_id: Optional[int] = None


class ChannelState(BaseModel):
    id: int
    enabled: bool
    frequency: int


class AppState(BaseModel):
    connected: bool
    connection_state: str
    broadcast_state: str
    watchdog_state: str
    watchdog_time_remaining: int
    channels: list[ChannelState]
    source: str
    message_id: int
    stale: bool


# === Endpoints ===

@app.get("/api/state")
async def get_state() -> AppState:
    """Get complete application state."""
    channels = [
        ChannelState(
            id=ch.id,
            enabled=ch.enabled,
            frequency=ch.frequency
        )
        for ch in model.device_state.channels
    ]
    
    return AppState(
        connected=model.is_connected(),
        connection_state=model.get_connection_state().name,
        broadcast_state=model.get_broadcast_state().name,
        watchdog_state=model.get_watchdog_state().name,
        watchdog_time_remaining=model.device_state.watchdog_time_remaining,
        channels=channels,
        source="bram" if model.device_state.source == Config.SOURCE_BRAM else "adc",
        message_id=model.device_state.message_id,
        stale=model.device_state.stale
    )


@app.post("/api/connect")
async def connect(req: ConnectRequest):
    """Connect to FPGA."""
    if model.is_connected():
        raise HTTPException(status_code=400, detail="Already connected")
    
    model.connect(req.ip, req.port)
    return {"status": "connecting", "ip": req.ip, "port": req.port}


@app.post("/api/disconnect")
async def disconnect():
    """Disconnect from FPGA."""
    if not model.is_connected():
        raise HTTPException(status_code=400, detail="Not connected")
    
    model.disconnect()
    return {"status": "disconnected"}


@app.post("/api/broadcast/start")
async def start_broadcast():
    """Start broadcasting."""
    if not model.is_connected():
        raise HTTPException(status_code=400, detail="Not connected")
    
    if model.get_broadcast_state() == BroadcastState.BROADCASTING:
        raise HTTPException(status_code=400, detail="Already broadcasting")
    
    active_count = sum(1 for ch in model.device_state.channels if ch.enabled)
    if active_count == 0:
        raise HTTPException(status_code=400, detail="No active channels")
    
    model.set_broadcast(True)
    return {"status": "starting", "active_channels": active_count}


@app.post("/api/broadcast/stop")
async def stop_broadcast():
    """Stop broadcasting."""
    if model.get_broadcast_state() != BroadcastState.BROADCASTING:
        raise HTTPException(status_code=400, detail="Not broadcasting")
    
    model.set_broadcast(False)
    return {"status": "stopping"}


@app.post("/api/channel/{channel_id}")
async def update_channel(channel_id: int, update: ChannelUpdate):
    """Update channel settings."""
    if channel_id < 1 or channel_id > Config.NUM_CHANNELS:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found")
    
    if update.enabled is not None:
        model.set_channel_enabled(channel_id, update.enabled)
    
    if update.frequency is not None:
        if update.frequency < Config.FREQ_MIN or update.frequency > Config.FREQ_MAX:
            raise HTTPException(
                status_code=400, 
                detail=f"Frequency must be between {Config.FREQ_MIN} and {Config.FREQ_MAX} Hz"
            )
        model.set_channel_frequency(channel_id, update.frequency)
    
    return {"status": "updated", "channel": channel_id}


@app.post("/api/channels/preset/{count}")
async def enable_preset_channels(count: int):
    """Enable preset number of channels."""
    valid_presets = [1, 2, 3, 4, 6, 8, 12]
    if count not in valid_presets:
        raise HTTPException(status_code=400, detail=f"Count must be one of {valid_presets}")
    
    distributions = {
        1: [1],
        2: [1, 7],
        3: [12, 4, 8],
        4: [12, 3, 6, 9],
        6: [12, 2, 4, 6, 8, 10],
        8: [12, 1, 3, 4, 6, 7, 9, 10],
        12: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    }
    
    freq_presets = [540000, 900000, 1200000, 1500000]  # Hz
    
    # Disable all first
    for ch_id in range(1, 13):
        model.set_channel_enabled(ch_id, False)
    
    # Enable selected channels
    channels_to_enable = distributions[count]
    for i, ch_id in enumerate(channels_to_enable):
        model.set_channel_enabled(ch_id, True)
        model.set_channel_frequency(ch_id, freq_presets[i % len(freq_presets)])
    
    return {"status": "preset_applied", "count": count, "channels": channels_to_enable}


@app.post("/api/source")
async def set_source(update: SourceUpdate):
    """Set audio source."""
    source = Config.SOURCE_BRAM if update.source.lower() == "bram" else Config.SOURCE_ADC
    model.set_source(source)
    
    if update.message_id is not None:
        model.set_message(update.message_id)
    
    return {"status": "updated", "source": update.source}


@app.post("/api/watchdog/reset")
async def reset_watchdog():
    """Reset watchdog timer."""
    model.reset_watchdog()
    return {"status": "reset"}


@app.get("/api/log")
async def get_log(limit: int = 20):
    """Get recent log entries."""
    entries = model.get_log_entries(limit)
    return {"entries": entries}


@app.on_event("startup")
async def startup():
    model.add_log("API server started")


@app.on_event("shutdown")
async def shutdown():
    if model.is_connected():
        model.disconnect()

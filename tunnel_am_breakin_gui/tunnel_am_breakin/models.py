"""
UGL Tunnel AM Break-In System
Data Models

State management and data structures.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Flag, auto
from typing import Optional
import json
import os


# =============================================================================
# ENUMS
# =============================================================================

class BroadcastState(Flag):
    """System broadcast state."""
    BROADCASTING = True
    STANDBY = False


class ConnectionState(Flag):
    """Red Pitaya connection state."""
    CONNECTED = True
    DISCONNECTED = False


class ChannelStatus:
    """Channel status constants."""
    TRANSMITTING = "transmitting"
    STANDBY = "standby"
    DISABLED = "disabled"
    ERROR = "error"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LogEntry:
    """Single log entry."""
    timestamp: datetime
    level: str
    message: str
    
    def __str__(self) -> str:
        ts = self.timestamp.strftime("%H:%M:%S.%f")[:-3]
        return f"[{ts}] [{self.level}] {self.message}"


@dataclass
class ChannelState:
    """State for a single RF channel."""
    id: int
    enabled: bool = True
    active: bool = False
    rf_level: float = 0.0
    status: str = ChannelStatus.STANDBY


@dataclass
class SpectrumData:
    """Spectrum analyzer data."""
    x: list[float] = field(default_factory=list)  # Frequencies
    y: list[float] = field(default_factory=list)  # Power levels (dB)


@dataclass
class AudioData:
    """Audio waveform data."""
    samples: deque = field(default_factory=lambda: deque([0.0] * 200, maxlen=200))
    level: float = 0.0


# =============================================================================
# MAIN STATE MODEL
# =============================================================================

class SystemModel:
    """
    Central state management for the application.
    All state changes go through this model.
    """
    
    def __init__(self):
        # Connection state
        self.connection_state = ConnectionState.DISCONNECTED
        self.red_pitaya_ip: str = "192.168.1.100"
        
        # Broadcast state
        self.broadcast_state = BroadcastState.STANDBY
        self.broadcast_start_time: Optional[datetime] = None
        self.selected_message: str = "test"
        
        # Channel states
        self.channels: dict[int, ChannelState] = {
            1: ChannelState(id=1),
            2: ChannelState(id=2),
        }
        
        # Display data
        self.spectrum = SpectrumData(
            x=list(range(400, 1200, 2)),  # 400-1200 kHz
            y=[-70.0] * 400
        )
        self.audio = AudioData()
        
        # Log
        self._log: deque[LogEntry] = deque(maxlen=100)
        
        # Persistence
        self._settings_file = "settings.json"
    
    # =========================================================================
    # CONNECTION
    # =========================================================================
    
    def set_connected(self, connected: bool) -> None:
        self.connection_state = ConnectionState.CONNECTED if connected else ConnectionState.DISCONNECTED
        status = "Connected" if connected else "Disconnected"
        self.log(f"Red Pitaya {status}: {self.red_pitaya_ip}", 
                 "SUCCESS" if connected else "WARN")
    
    def is_connected(self) -> bool:
        return bool(self.connection_state)
    
    # =========================================================================
    # BROADCAST
    # =========================================================================
    
    def start_broadcast(self) -> None:
        if self.broadcast_state == BroadcastState.BROADCASTING:
            raise RuntimeError("Already broadcasting")
        
        self.broadcast_state = BroadcastState.BROADCASTING
        self.broadcast_start_time = datetime.now()
        
        # Activate enabled channels
        for ch in self.channels.values():
            if ch.enabled:
                ch.active = True
                ch.status = ChannelStatus.TRANSMITTING
        
        self.log(f"🔴 BROADCAST STARTED - Message: {self.selected_message}", "ALERT")
    
    def stop_broadcast(self) -> None:
        if self.broadcast_state == BroadcastState.STANDBY:
            return
        
        duration = self.get_broadcast_duration()
        
        self.broadcast_state = BroadcastState.STANDBY
        self.broadcast_start_time = None
        
        # Deactivate all channels
        for ch in self.channels.values():
            ch.active = False
            ch.status = ChannelStatus.STANDBY if ch.enabled else ChannelStatus.DISABLED
        
        self.log(f"⬛ BROADCAST STOPPED - Duration: {duration:.1f}s", "ALERT")
    
    def is_broadcasting(self) -> bool:
        return bool(self.broadcast_state)
    
    def get_broadcast_duration(self) -> float:
        if self.broadcast_start_time:
            return (datetime.now() - self.broadcast_start_time).total_seconds()
        return 0.0
    
    # =========================================================================
    # CHANNELS
    # =========================================================================
    
    def set_channel_enabled(self, channel_id: int, enabled: bool) -> None:
        ch = self.channels[channel_id]
        ch.enabled = enabled
        if not enabled:
            ch.active = False
            ch.status = ChannelStatus.DISABLED
        else:
            ch.status = ChannelStatus.STANDBY
        
        status = "enabled" if enabled else "disabled"
        self.log(f"Channel {channel_id} {status}")
    
    def set_channel_level(self, channel_id: int, level: float) -> None:
        self.channels[channel_id].rf_level = max(0.0, min(1.0, level))
    
    def get_active_channels(self) -> list[int]:
        return [ch.id for ch in self.channels.values() if ch.active]
    
    # =========================================================================
    # MESSAGE
    # =========================================================================
    
    def set_message(self, message_id: str) -> None:
        self.selected_message = message_id
        self.log(f"Message selected: {message_id}")
    
    # =========================================================================
    # AUDIO
    # =========================================================================
    
    def update_audio(self, sample: float, level: float) -> None:
        self.audio.samples.append(sample)
        self.audio.level = level
    
    # =========================================================================
    # SPECTRUM
    # =========================================================================
    
    def update_spectrum(self, y_data: list[float]) -> None:
        self.spectrum.y = y_data
    
    # =========================================================================
    # LOGGING
    # =========================================================================
    
    def log(self, message: str, level: str = "INFO") -> None:
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message
        )
        self._log.append(entry)
    
    def get_log_text(self, max_lines: int = 20) -> str:
        recent = list(self._log)[-max_lines:]
        return "\n".join(str(entry) for entry in recent)
    
    def get_log_entries(self) -> list[LogEntry]:
        return list(self._log)
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def save_settings(self) -> None:
        """Save current settings to file."""
        settings = {
            "red_pitaya_ip": self.red_pitaya_ip,
            "selected_message": self.selected_message,
            "channels": {
                ch_id: {"enabled": ch.enabled}
                for ch_id, ch in self.channels.items()
            }
        }
        try:
            with open(self._settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.log(f"Failed to save settings: {e}", "ERROR")
    
    def load_settings(self) -> None:
        """Load settings from file."""
        if not os.path.exists(self._settings_file):
            return
        
        try:
            with open(self._settings_file, 'r') as f:
                settings = json.load(f)
            
            self.red_pitaya_ip = settings.get("red_pitaya_ip", self.red_pitaya_ip)
            self.selected_message = settings.get("selected_message", self.selected_message)
            
            for ch_id, ch_settings in settings.get("channels", {}).items():
                if int(ch_id) in self.channels:
                    self.channels[int(ch_id)].enabled = ch_settings.get("enabled", True)
            
            self.log("Settings loaded")
        except Exception as e:
            self.log(f"Failed to load settings: {e}", "WARN")

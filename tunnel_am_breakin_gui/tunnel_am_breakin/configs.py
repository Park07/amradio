"""
UGL Tunnel AM Break-In System
Configuration Constants

All configurable values in one place.
"""

from dataclasses import dataclass
from typing import Callable


# =============================================================================
# APPLICATION
# =============================================================================

APP_TITLE = "UGL Tunnel AM Break-In System"
APP_VERSION = "1.0.0"
APP_WIDTH = 1200
APP_HEIGHT = 800
APP_MIN_WIDTH = 1000
APP_MIN_HEIGHT = 700


# =============================================================================
# RED PITAYA CONNECTION
# =============================================================================

@dataclass
class RedPitayaConfig:
    DEFAULT_IP: str = "192.168.1.100"
    DEFAULT_PORT: int = 5000
    TIMEOUT: float = 2.0


# =============================================================================
# RF CHANNELS
# =============================================================================

@dataclass(frozen=True)
class Channel:
    id: int
    name: str
    freq_khz: int
    phase_inc: int  # For NCO: (freq × 2^32) / 125MHz


# Default channel configuration
CHANNELS = [
    Channel(id=1, name="Channel 1", freq_khz=531, phase_inc=18253611),
    Channel(id=2, name="Channel 2", freq_khz=702, phase_inc=24120028),
]


# =============================================================================
# BROADCAST MESSAGES
# =============================================================================

@dataclass(frozen=True)
class Message:
    id: str
    name: str
    duration_sec: int
    icon: str = ""


MESSAGES = [
    Message(id="test", name="Test Tone (1kHz)", duration_sec=0, icon="🔊"),
    Message(id="emergency", name="EMERGENCY EVACUATE", duration_sec=15, icon="🔴"),
    Message(id="traffic", name="Traffic Advisory", duration_sec=10, icon="🚗"),
    Message(id="fire", name="FIRE - EXIT NOW", duration_sec=15, icon="🔥"),
]


# =============================================================================
# DISPLAY SETTINGS
# =============================================================================

class Display:
    UPDATE_RATE_HZ: int = 30
    SPECTRUM_MIN_FREQ: int = 400   # kHz
    SPECTRUM_MAX_FREQ: int = 1200  # kHz
    SPECTRUM_MIN_DB: int = -80
    SPECTRUM_MAX_DB: int = 0
    AUDIO_BUFFER_SIZE: int = 200
    LOG_MAX_LINES: int = 100
    LOG_DISPLAY_LINES: int = 20


# =============================================================================
# THEME COLORS (RGBA)
# =============================================================================

class Colors:
    # Background
    WINDOW_BG = (15, 15, 20, 255)
    CHILD_BG = (20, 22, 28, 255)
    POPUP_BG = (25, 28, 35, 255)
    
    # Borders
    BORDER = (50, 55, 65, 255)
    BORDER_ACTIVE = (50, 180, 80, 255)
    
    # Frame
    FRAME_BG = (30, 35, 45, 255)
    FRAME_HOVER = (45, 50, 60, 255)
    FRAME_ACTIVE = (55, 60, 75, 255)
    
    # Title
    TITLE_BG = (15, 18, 25, 255)
    TITLE_ACTIVE = (25, 80, 150, 255)
    
    # Text
    TEXT_PRIMARY = (220, 225, 230, 255)
    TEXT_SECONDARY = (150, 150, 160, 255)
    TEXT_ACCENT = (100, 180, 255, 255)
    
    # Buttons
    BUTTON = (40, 80, 140, 255)
    BUTTON_HOVER = (50, 100, 170, 255)
    BUTTON_ACTIVE = (60, 120, 200, 255)
    
    # Emergency Button
    EMERGENCY_BTN = (180, 30, 30, 255)
    EMERGENCY_BTN_HOVER = (220, 50, 50, 255)
    EMERGENCY_BTN_ACTIVE = (255, 80, 80, 255)
    
    # Stop Button
    STOP_BTN = (60, 60, 70, 255)
    STOP_BTN_HOVER = (80, 80, 90, 255)
    STOP_BTN_ACTIVE = (100, 100, 110, 255)
    
    # Status Colors
    STATUS_OK = (80, 255, 120, 255)
    STATUS_WARN = (255, 200, 80, 255)
    STATUS_ERROR = (255, 80, 80, 255)
    STATUS_OFF = (100, 100, 100, 255)
    
    # Channel Active Background
    CHANNEL_ACTIVE_BG = (20, 50, 30, 255)
    CHANNEL_INACTIVE_BG = (25, 28, 35, 255)
    
    # Log
    LOG_TEXT = (150, 200, 150, 255)


# =============================================================================
# SCPI COMMANDS
# =============================================================================

class SCPICommands:
    """SCPI command templates for Red Pitaya"""
    SET_FREQ = "FREQ:CH{channel} {freq}"          # FREQ:CH1 531000
    SET_MSG = "MSG:SELECT {msg_id}"               # MSG:SELECT emergency
    OUTPUT_ON = "OUTPUT:CH{channel} ON"           # OUTPUT:CH1 ON
    OUTPUT_OFF = "OUTPUT:CH{channel} OFF"         # OUTPUT:CH1 OFF
    OUTPUT_ALL_ON = "OUTPUT:ALL ON"
    OUTPUT_ALL_OFF = "OUTPUT:ALL OFF"
    QUERY_STATUS = "STATUS?"
    QUERY_ID = "*IDN?"


# =============================================================================
# KEYBOARD SHORTCUTS
# =============================================================================

class Shortcuts:
    BROADCAST_TOGGLE = ["F1", "Space"]
    EMERGENCY_STOP = ["Escape"]

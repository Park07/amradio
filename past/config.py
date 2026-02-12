"""
Configuration for UGL AM Radio Control System
==============================================
Author: William Park
Date: January 2026

Architecture based on industry advice from r/FPGA, r/ExperiencedDevs, r/softwarearchitecture

Updated: 12-channel support for stress testing
"""


class Config:
    """Application configuration."""

    # Window settings
    WINDOW_TITLE = "UGL AM Radio Control"
    WINDOW_WIDTH = 600
    WINDOW_HEIGHT = 900  # Taller for 12 channels

    # Connection defaults
    DEFAULT_IP = "192.168.0.100"
    DEFAULT_PORT = 5000
    SOCKET_TIMEOUT = 5.0

    # Polling settings (Reddit advice: alexforencich, exodusTay)
    POLL_INTERVAL = 0.5  # 500ms - fast enough for responsive UI
    HEARTBEAT_INTERVAL = 1.0  # 1 second
    HEARTBEAT_TIMEOUT = 3.0  # 3 seconds = connection lost

    # Watchdog settings (Reddit advice: cannibal_catfish69 - "fail safely")
    WATCHDOG_TIMEOUT = 5  # FPGA will kill RF after 5 sec without heartbeat
    WATCHDOG_WARNING_THRESHOLD = 0.8  # Warn at 80% of timeout

    # Auto-reconnect settings
    AUTO_RECONNECT = True
    RECONNECT_DELAY = 2.0
    MAX_RECONNECT_ATTEMPTS = 5

    # Audio sources
    SOURCE_ADC = "ADC"
    SOURCE_BRAM = "BRAM"

    # Frequency limits (Hz)
    FREQ_MIN = 530_000
    FREQ_MAX = 1_700_000

    # Number of channels (for stress testing)
    NUM_CHANNELS = 12

    # Channel configuration - 12 channels (1-12) spread across AM band
    # Spacing: ~100 kHz apart to avoid interference
    CHANNELS = [
        {"id": 1,  "default_freq": 540_000,  "name": "CH1"},
        {"id": 2,  "default_freq": 640_000,  "name": "CH2"},
        {"id": 3,  "default_freq": 740_000,  "name": "CH3"},
        {"id": 4,  "default_freq": 840_000,  "name": "CH4"},
        {"id": 5,  "default_freq": 940_000,  "name": "CH5"},
        {"id": 6,  "default_freq": 1040_000, "name": "CH6"},
        {"id": 7,  "default_freq": 1140_000, "name": "CH7"},
        {"id": 8,  "default_freq": 1240_000, "name": "CH8"},
        {"id": 9,  "default_freq": 1340_000, "name": "CH9"},
        {"id": 10, "default_freq": 1440_000, "name": "CH10"},
        {"id": 11, "default_freq": 1540_000, "name": "CH11"},
        {"id": 12, "default_freq": 1640_000, "name": "CH12"},
    ]

    # Message presets (original)
    MESSAGES = [
        {"id": 1, "name": "Emergency Evacuation", "duration": "45s"},
        {"id": 2, "name": "Fire Alert", "duration": "30s"},
        {"id": 3, "name": "Traffic Advisory", "duration": "60s"},
        {"id": 4, "name": "Test Tone", "duration": "10s"},
    ]

    # Logging
    LOG_FILE = "audit_log.txt"
    LOG_MAX_LINES = 100
    LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

    # SCPI Commands
    class SCPI:
        QUERY_ID = "*IDN?"
        QUERY_STATUS = "STATUS?"
        SET_SOURCE = "SOURCE:INPUT {}"
        SET_MESSAGE = "SOURCE:MSG {}"
        SET_FREQ = "FREQ:CH{} {}"          # FREQ:CH0 540000
        SET_OUTPUT = "CH{}:OUTPUT {}"       # CH0:OUTPUT ON
        SET_BROADCAST = "OUTPUT:STATE {}"
        SET_ALL_ENABLE = "CH:EN {}"         # CH:EN 0b000000001111 (bitmask)
        # Watchdog commands
        WATCHDOG_ENABLE = "WATCHDOG:ENABLE {}"
        WATCHDOG_RESET = "WATCHDOG:RESET"
        WATCHDOG_STATUS = "WATCHDOG:STATUS?"

    # Colors (Pure black theme with emerald accents)
    class Colors:
        # Backgrounds
        WINDOW_BG = [0, 0, 0, 255]           # Pure black
        PANEL_BG = [23, 23, 23, 255]         # #171717
        FRAME_BG = [38, 38, 38, 255]         # #262626
        FRAME_BG_HOVER = [50, 50, 50, 255]

        # Text
        TEXT_PRIMARY = [255, 255, 255, 230]
        TEXT_SECONDARY = [163, 163, 163, 255]  # #a3a3a3
        TEXT_DIM = [115, 115, 115, 255]        # #737373
        TEXT_DISABLED = [82, 82, 82, 255]

        # Status colors
        CONNECTED = [16, 185, 129, 255]        # emerald-500
        CONNECTED_DIM = [16, 185, 129, 200]
        DISCONNECTED = [239, 68, 68, 255]      # red-500
        DISCONNECTED_DIM = [239, 68, 68, 200]
        WARNING = [245, 158, 11, 255]          # amber-500

        # Buttons
        BTN_HOVER = [50, 50, 50, 255]

        # Broadcast states
        BROADCAST_DISABLED = [38, 38, 38, 255]
        BROADCAST_IDLE = [16, 185, 129, 255]       # emerald-500
        BROADCAST_IDLE_HOVER = [52, 211, 153, 255] # emerald-400
        BROADCAST_ACTIVE = [185, 28, 28, 255]      # red-700
        BROADCAST_ACTIVE_HOVER = [220, 38, 38, 255]
        BROADCAST_ARMING = [245, 158, 11, 255]     # amber-500

        # Watchdog states
        WATCHDOG_OK = [16, 185, 129, 255]      # emerald
        WATCHDOG_WARNING = [245, 158, 11, 255]  # amber
        WATCHDOG_TRIGGERED = [239, 68, 68, 255] # red

        # Channel states
        CHANNEL_ACTIVE = [59, 130, 246, 255]   # blue-500
        CHANNEL_ENABLED = [16, 185, 129, 255]  # emerald
        CHANNEL_DISABLED = [115, 115, 115, 255] # gray

        # Log
        LOG_INFO = [163, 163, 163, 255]
        LOG_WARN = [245, 158, 11, 255]
        LOG_ERROR = [239, 68, 68, 255]

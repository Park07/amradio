"""
Configuration for UGL AM Radio Control System
==============================================
Author: [William Park]
Date: January 2026

"""


class Config:
    """Application configuration."""

    # Window settings
    WINDOW_TITLE = "UGL AM Radio Control"
    WINDOW_WIDTH = 520
    WINDOW_HEIGHT = 820  # Slightly taller for watchdog status

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

    # Channel configuration
    CHANNELS = [
        {"id": 1, "default_freq": 700_000},
        {"id": 2, "default_freq": 900_000},
    ]

    # Message presets
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
        SET_FREQ = "CH{}:FREQ {}"
        SET_OUTPUT = "CH{}:OUTPUT {}"
        SET_BROADCAST = "OUTPUT:STATE {}"
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

        # Channel
        CHANNEL_ACTIVE = [59, 130, 246, 255]   # blue-500

        # Log
        LOG_INFO = [163, 163, 163, 255]
        LOG_WARN = [245, 158, 11, 255]
        LOG_ERROR = [239, 68, 68, 255]

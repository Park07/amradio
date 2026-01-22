"""
Configuration for UGL AM Radio Control System.
All settings centralized here - no hardcoded values elsewhere.
"""


class Config:
    """Application configuration."""

    # === NETWORK ===
    DEFAULT_IP = "192.168.1.100"
    DEFAULT_PORT = 5000
    SOCKET_TIMEOUT = 2.0
    RECONNECT_DELAY = 3.0

    # === CHANNELS ===
    CHANNELS = [
        {"id": 1, "name": "CH1", "default_freq": 531000},
        {"id": 2, "name": "CH2", "default_freq": 702000},
    ]

    # Channel frequency limits (Hz)
    FREQ_MIN = 500000  # 500 kHz
    FREQ_MAX = 1700000  # 1700 kHz

    # === STORED MESSAGES ===
    MESSAGES = [
        {"id": 1, "name": "Emergency Evacuation", "file": "evacuate.wav"},
        {"id": 2, "name": "All Clear", "file": "all_clear.wav"},
        {"id": 3, "name": "Test Broadcast", "file": "test.wav"},
        {"id": 4, "name": "Shelter in Place", "file": "shelter.wav"},
    ]

    # === AUDIO SOURCES ===
    SOURCE_ADC = "ADC"  # Live mic via analog input
    SOURCE_BRAM = "BRAM"  # Stored message from FPGA memory

    # === GUI WINDOW ===
    WINDOW_TITLE = "UGL AM Radio Control"
    WINDOW_WIDTH = 520
    WINDOW_HEIGHT = 700

    # === THEME COLORS (RGBA) ===
    class Colors:
        # Background
        WINDOW_BG = [10, 10, 12, 255]
        PANEL_BG = [18, 20, 26, 255]
        FRAME_BG = [26, 26, 31, 255]
        FRAME_BG_HOVER = [35, 35, 42, 255]

        # Text
        TEXT_PRIMARY = [232, 232, 232, 255]
        TEXT_SECONDARY = [136, 136, 136, 255]
        TEXT_DIM = [102, 102, 102, 255]
        TEXT_DISABLED = [60, 60, 60, 255]

        # Status colors
        CONNECTED = [34, 197, 94, 255]  # Green
        CONNECTED_DIM = [74, 222, 128, 255]
        DISCONNECTED = [239, 68, 68, 255]  # Red
        DISCONNECTED_DIM = [248, 113, 113, 255]
        WARNING = [251, 191, 36, 255]  # Yellow/Amber

        # Buttons
        BTN_BG = [26, 26, 31, 255]
        BTN_HOVER = [40, 40, 48, 255]
        BTN_DISABLED = [20, 20, 24, 255]

        # Broadcast button
        BROADCAST_IDLE = [34, 197, 94, 255]
        BROADCAST_IDLE_HOVER = [22, 163, 74, 255]
        BROADCAST_ACTIVE = [220, 38, 38, 255]
        BROADCAST_ACTIVE_HOVER = [185, 28, 28, 255]
        BROADCAST_DISABLED = [50, 50, 55, 255]

        # Channel
        CHANNEL_ACTIVE = [59, 130, 246, 255]
        CHANNEL_INACTIVE = [51, 51, 51, 255]

        # Log colors
        LOG_BG = [8, 8, 10, 255]
        LOG_ERROR = [248, 113, 113, 255]
        LOG_WARN = [251, 191, 36, 255]
        LOG_INFO = [74, 222, 128, 255]
        LOG_TIME = [85, 85, 85, 255]

    # === SCPI COMMANDS ===
    class SCPI:
        SET_SOURCE = "SOURCE:INPUT {}"
        SET_MESSAGE = "SOURCE:MSG {}"
        SET_FREQ = "CH{}:FREQ {}"
        SET_OUTPUT = "CH{}:OUTPUT {}"
        SET_BROADCAST = "OUTPUT:STATE {}"
        QUERY_ID = "*IDN?"
        QUERY_STATUS = "SYST:STAT?"

    # === LOGGING ===
    LOG_MAX_LINES = 100
    LOG_FILE = "audit_log.txt"
    LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

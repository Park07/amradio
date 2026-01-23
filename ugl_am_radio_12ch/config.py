"""
Configuration for UGL AM Radio Control System.
All settings in one place.

Updated: 12 channels for stress testing
"""


class Config:
    """Application configuration."""

    # === Window ===
    WINDOW_TITLE = "UGL AM Radio Control"
    WINDOW_WIDTH = 520
    WINDOW_HEIGHT = 900  # Increased for 12 channels

    # === Network ===
    DEFAULT_IP = "192.168.1.100"
    DEFAULT_PORT = 5000
    SOCKET_TIMEOUT = 5.0

    # === Audio Source ===
    SOURCE_ADC = "ADC"
    SOURCE_BRAM = "BRAM"

    # === Messages ===
    MESSAGES = [
        {"id": 1, "name": "Emergency Evacuation"},
        {"id": 2, "name": "All Clear"},
        {"id": 3, "name": "Test Broadcast"},
        {"id": 4, "name": "Shelter in Place"},
    ]

    # === Channels (12 for stress testing) ===
    FREQ_MIN = 530_000  # 530 kHz
    FREQ_MAX = 1700_000  # 1700 kHz

    CHANNELS = [
        {"id": 1, "default_freq": 531_000},
        {"id": 2, "default_freq": 600_000},
        {"id": 3, "default_freq": 700_000},
        {"id": 4, "default_freq": 800_000},
        {"id": 5, "default_freq": 900_000},
        {"id": 6, "default_freq": 1000_000},
        {"id": 7, "default_freq": 1100_000},
        {"id": 8, "default_freq": 1200_000},
        {"id": 9, "default_freq": 1300_000},
        {"id": 10, "default_freq": 1400_000},
        {"id": 11, "default_freq": 1500_000},
        {"id": 12, "default_freq": 1600_000},
    ]

    # === Logging ===
    LOG_FILE = "audit_log.txt"
    LOG_MAX_LINES = 100
    LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

    # === SCPI Commands ===
    class SCPI:
        QUERY_ID = "*IDN?"
        SET_FREQ = "CH{0}:FREQ {1}"  # CH1:FREQ 531000
        SET_OUTPUT = "CH{0}:OUTPUT {1}"  # CH1:OUTPUT ON
        SET_SOURCE = "SOURCE:INPUT {0}"  # SOURCE:INPUT ADC
        SET_MESSAGE = "SOURCE:MSG {0}"  # SOURCE:MSG 1
        SET_BROADCAST = "OUTPUT:STATE {0}"  # OUTPUT:STATE ON

    # === Colors ===
    class Colors:
        # Backgrounds
        WINDOW_BG = [18, 18, 22, 255]
        PANEL_BG = [25, 25, 30, 255]
        FRAME_BG = [35, 35, 42, 255]
        FRAME_BG_HOVER = [45, 45, 55, 255]

        # Status
        CONNECTED = [34, 197, 94, 255]
        CONNECTED_DIM = [34, 197, 94, 180]
        DISCONNECTED = [239, 68, 68, 255]
        DISCONNECTED_DIM = [239, 68, 68, 180]

        # Broadcast button states
        BROADCAST_DISABLED = [60, 60, 65, 255]
        BROADCAST_IDLE = [22, 163, 74, 255]
        BROADCAST_IDLE_HOVER = [21, 128, 61, 255]
        BROADCAST_ACTIVE = [220, 38, 38, 255]
        BROADCAST_ACTIVE_HOVER = [185, 28, 28, 255]

        # Text
        TEXT_PRIMARY = [255, 255, 255, 230]
        TEXT_SECONDARY = [160, 160, 170, 255]
        TEXT_DIM = [100, 100, 110, 255]
        TEXT_DISABLED = [80, 80, 85, 255]

        # Buttons
        BTN_HOVER = [50, 50, 60, 255]

        # Channels
        CHANNEL_ACTIVE = [59, 130, 246, 255]

        # Log
        LOG_INFO = [160, 160, 170, 255]

        # Warning
        WARNING = [250, 204, 21, 255]

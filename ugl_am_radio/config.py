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
    FREQ_MIN = 500000    # 500 kHz
    FREQ_MAX = 1700000   # 1700 kHz
    
    # === STORED MESSAGES ===
    MESSAGES = [
        {"id": 1, "name": "Emergency Evacuation", "file": "evacuate.wav"},
        {"id": 2, "name": "All Clear", "file": "all_clear.wav"},
        {"id": 3, "name": "Test Broadcast", "file": "test.wav"},
        {"id": 4, "name": "Custom Message", "file": "custom.wav"},
    ]
    
    # === AUDIO SOURCES ===
    SOURCE_ADC = "ADC"    # Live mic via analog input
    SOURCE_BRAM = "BRAM"  # Stored message from FPGA memory
    
    # === GUI WINDOW ===
    WINDOW_TITLE = "UGL AM Radio Control"
    WINDOW_WIDTH = 450
    WINDOW_HEIGHT = 580
    
    # === THEME COLORS (RGBA) ===
    class Colors:
        # Background
        WINDOW_BG = [25, 25, 30, 255]
        FRAME_BG = [40, 40, 48, 255]
        FRAME_BG_HOVER = [50, 50, 60, 255]
        
        # Text
        TEXT_PRIMARY = [220, 220, 220, 255]
        TEXT_SECONDARY = [140, 140, 140, 255]
        TEXT_HEADER = [180, 180, 180, 255]
        
        # Status
        STATUS_OK = [100, 255, 100, 255]
        STATUS_ERROR = [255, 100, 100, 255]
        STATUS_WARN = [255, 200, 100, 255]
        
        # Buttons
        BTN_NORMAL = [55, 55, 65, 255]
        BTN_HOVER = [70, 70, 80, 255]
        BTN_ACTIVE = [85, 85, 95, 255]
        
        # Broadcast button states
        BROADCAST_IDLE = [40, 130, 40, 255]
        BROADCAST_IDLE_HOVER = [50, 160, 50, 255]
        BROADCAST_ACTIVE = [180, 40, 40, 255]
        BROADCAST_ACTIVE_HOVER = [210, 50, 50, 255]
        
        # Channel indicators
        CHANNEL_ON = [100, 255, 100, 255]
        CHANNEL_OFF = [80, 80, 80, 255]
    
    # === SCPI COMMANDS ===
    class SCPI:
        # Audio source
        SET_SOURCE = "SOURCE:INPUT {}"       # ADC or BRAM
        SET_MESSAGE = "SOURCE:MSG {}"        # Message number (1-4)
        
        # Channel control
        SET_FREQ = "CH{}:FREQ {}"            # Channel, Hz
        SET_OUTPUT = "CH{}:OUTPUT {}"        # Channel, ON/OFF
        
        # Master control
        SET_BROADCAST = "OUTPUT:STATE {}"    # ON/OFF
        
        # Queries
        QUERY_ID = "*IDN?"
        QUERY_STATUS = "SYST:STAT?"
    
    # === LOGGING ===
    LOG_MAX_LINES = 100
    LOG_FILE = "audit_log.txt"
    LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

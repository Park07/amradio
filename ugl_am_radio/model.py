"""
Model layer for UGL AM Radio Control System.
Handles state management, SCPI communication, and audit logging.
"""

import socket
import threading
from datetime import datetime
from typing import Callable, Optional, List
from dataclasses import dataclass, field
from config import Config


@dataclass
class ChannelState:
    """State for a single channel."""
    id: int
    frequency: int
    enabled: bool = False


@dataclass
class AppState:
    """Complete application state."""
    connected: bool = False
    broadcasting: bool = False
    source: str = Config.SOURCE_BRAM
    selected_message: int = 1
    channels: List[ChannelState] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.channels:
            self.channels = [
                ChannelState(id=ch["id"], frequency=ch["default_freq"])
                for ch in Config.CHANNELS
            ]


class AuditLogger:
    """Logs all actions for audit trail."""
    
    def __init__(self, log_file: str = Config.LOG_FILE):
        self.log_file = log_file
        self.listeners: List[Callable[[str], None]] = []
        self._lock = threading.Lock()
    
    def add_listener(self, callback: Callable[[str], None]):
        """Add a callback to receive log messages."""
        self.listeners.append(callback)
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime(Config.LOG_TIMESTAMP_FORMAT)
        entry = f"[{timestamp}] [{level}] {message}"
        
        # Write to file
        with self._lock:
            try:
                with open(self.log_file, "a") as f:
                    f.write(entry + "\n")
            except Exception:
                pass
        
        # Notify listeners
        for listener in self.listeners:
            try:
                listener(entry)
            except Exception:
                pass
        
        # Console output
        print(entry)
        
        return entry


class SCPIClient:
    """Handles SCPI communication with Red Pitaya."""
    
    def __init__(self, logger: AuditLogger):
        self.logger = logger
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self._lock = threading.Lock()
        self.ip = ""
        self.port = 0
    
    def connect(self, ip: str, port: int) -> bool:
        """Connect to Red Pitaya SCPI server."""
        self.ip = ip
        self.port = port
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(Config.SOCKET_TIMEOUT)
            self.socket.connect((ip, port))
            self.connected = True
            self.logger.log(f"Connected to {ip}:{port}")
            return True
        except socket.timeout:
            self.logger.log(f"Connection timeout: {ip}:{port}", "ERROR")
            self.connected = False
            return False
        except Exception as e:
            self.logger.log(f"Connection failed: {e}", "ERROR")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Red Pitaya."""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        self.connected = False
        self.logger.log("Disconnected")
    
    def send(self, command: str) -> Optional[str]:
        """Send SCPI command. Returns response for queries, None otherwise."""
        if not self.connected or not self.socket:
            self.logger.log(f"Not connected. Queued: {command}", "WARN")
            return None
        
        with self._lock:
            try:
                # Send command
                cmd_bytes = (command.strip() + "\n").encode()
                self.socket.sendall(cmd_bytes)
                self.logger.log(f"TX: {command}")
                
                # Read response if query
                if "?" in command:
                    response = self.socket.recv(4096).decode().strip()
                    self.logger.log(f"RX: {response}")
                    return response
                
                return ""
            
            except socket.timeout:
                self.logger.log(f"Timeout sending: {command}", "ERROR")
                return None
            except Exception as e:
                self.logger.log(f"Send error: {e}", "ERROR")
                self.connected = False
                return None
    
    def query_identity(self) -> Optional[str]:
        """Query device identity."""
        return self.send(Config.SCPI.QUERY_ID)


class Model:
    """
    Main model class - coordinates state, communication, and logging.
    Implements observer pattern for state changes.
    """
    
    def __init__(self):
        self.logger = AuditLogger()
        self.scpi = SCPIClient(self.logger)
        self.state = AppState()
        self._state_listeners: List[Callable[[AppState], None]] = []
    
    # === Observer Pattern ===
    
    def add_state_listener(self, callback: Callable[[AppState], None]):
        """Subscribe to state changes."""
        self._state_listeners.append(callback)
    
    def _notify_state_change(self):
        """Notify all listeners of state change."""
        for listener in self._state_listeners:
            try:
                listener(self.state)
            except Exception as e:
                self.logger.log(f"Listener error: {e}", "ERROR")
    
    # === Connection ===
    
    def connect(self, ip: str, port: int) -> bool:
        """Connect to Red Pitaya."""
        success = self.scpi.connect(ip, port)
        self.state.connected = success
        
        if success:
            # Query device ID
            self.scpi.query_identity()
        
        self._notify_state_change()
        return success
    
    def disconnect(self):
        """Disconnect from Red Pitaya."""
        # Stop broadcasting first if active
        if self.state.broadcasting:
            self.set_broadcast(False)
        
        self.scpi.disconnect()
        self.state.connected = False
        self._notify_state_change()
    
    # === Audio Source ===
    
    def set_source(self, source: str):
        """Set audio source (ADC or BRAM)."""
        if source not in [Config.SOURCE_ADC, Config.SOURCE_BRAM]:
            self.logger.log(f"Invalid source: {source}", "ERROR")
            return
        
        self.state.source = source
        cmd = Config.SCPI.SET_SOURCE.format(source)
        self.scpi.send(cmd)
        self._notify_state_change()
    
    def set_message(self, message_id: int):
        """Set stored message to play (1-4)."""
        if not 1 <= message_id <= len(Config.MESSAGES):
            self.logger.log(f"Invalid message ID: {message_id}", "ERROR")
            return
        
        self.state.selected_message = message_id
        cmd = Config.SCPI.SET_MESSAGE.format(message_id)
        self.scpi.send(cmd)
        self._notify_state_change()
    
    # === Channel Control ===
    
    def set_channel_frequency(self, channel_id: int, frequency: int):
        """Set channel frequency in Hz."""
        # Validate
        if not Config.FREQ_MIN <= frequency <= Config.FREQ_MAX:
            self.logger.log(f"Frequency out of range: {frequency}", "WARN")
        
        # Update state
        for ch in self.state.channels:
            if ch.id == channel_id:
                ch.frequency = frequency
                break
        
        # Send command
        cmd = Config.SCPI.SET_FREQ.format(channel_id, frequency)
        self.scpi.send(cmd)
        self._notify_state_change()
    
    def set_channel_enabled(self, channel_id: int, enabled: bool):
        """Enable or disable a channel."""
        # Update state
        for ch in self.state.channels:
            if ch.id == channel_id:
                ch.enabled = enabled
                break
        
        # Send command
        state_str = "ON" if enabled else "OFF"
        cmd = Config.SCPI.SET_OUTPUT.format(channel_id, state_str)
        self.scpi.send(cmd)
        self._notify_state_change()
    
    # === Broadcast Control ===
    
    def set_broadcast(self, active: bool):
        """Start or stop broadcasting."""
        self.state.broadcasting = active
        
        state_str = "ON" if active else "OFF"
        cmd = Config.SCPI.SET_BROADCAST.format(state_str)
        self.scpi.send(cmd)
        
        if active:
            self.logger.log("=== BROADCAST STARTED ===", "INFO")
        else:
            self.logger.log("=== BROADCAST STOPPED ===", "INFO")
        
        self._notify_state_change()
    
    def toggle_broadcast(self):
        """Toggle broadcast state."""
        self.set_broadcast(not self.state.broadcasting)
    
    # === Getters ===
    
    def get_channel(self, channel_id: int) -> Optional[ChannelState]:
        """Get channel state by ID."""
        for ch in self.state.channels:
            if ch.id == channel_id:
                return ch
        return None
    
    def is_connected(self) -> bool:
        return self.state.connected
    
    def is_broadcasting(self) -> bool:
        return self.state.broadcasting

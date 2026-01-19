"""
UGL Tunnel AM Break-In System
SCPI Client

Communication with Red Pitaya via SCPI over TCP.
"""

import socket
import threading
from typing import Optional, Callable
from dataclasses import dataclass

from .configs import RedPitayaConfig, SCPICommands


@dataclass
class SCPIResponse:
    """Response from SCPI command."""
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None


class SCPIClient:
    """
    SCPI client for Red Pitaya communication.
    Thread-safe and handles connection management.
    """
    
    def __init__(self, config: RedPitayaConfig = None):
        self._config = config or RedPitayaConfig()
        self._ip: str = self._config.DEFAULT_IP
        self._port: int = self._config.DEFAULT_PORT
        self._timeout: float = self._config.TIMEOUT
        self._connected: bool = False
        self._lock = threading.Lock()
        self._on_message: Optional[Callable[[str], None]] = None
    
    @property
    def ip(self) -> str:
        return self._ip
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def set_message_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for logging messages."""
        self._on_message = callback
    
    def _log(self, message: str) -> None:
        """Log a message via callback if available."""
        if self._on_message:
            self._on_message(message)
    
    def connect(self, ip: str, port: int = None) -> bool:
        """
        Test connection to Red Pitaya.
        
        Args:
            ip: IP address of Red Pitaya
            port: Port number (default from config)
            
        Returns:
            True if connection successful
        """
        self._ip = ip
        if port:
            self._port = port
        
        try:
            with self._lock:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self._timeout)
                sock.connect((self._ip, self._port))
                
                # Try to get device ID
                sock.send(b"*IDN?\r\n")
                response = sock.recv(1024).decode().strip()
                sock.close()
                
                self._connected = True
                self._log(f"Connected to: {response}")
                return True
                
        except socket.timeout:
            self._log(f"Connection timeout: {self._ip}:{self._port}")
            self._connected = False
            return False
            
        except ConnectionRefusedError:
            self._log(f"Connection refused: {self._ip}:{self._port}")
            self._connected = False
            return False
            
        except Exception as e:
            self._log(f"Connection error: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        """Mark as disconnected."""
        self._connected = False
        self._log("Disconnected from Red Pitaya")
    
    def send(self, command: str) -> SCPIResponse:
        """
        Send SCPI command to Red Pitaya.
        
        Args:
            command: SCPI command string
            
        Returns:
            SCPIResponse with success status and data/error
        """
        with self._lock:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self._timeout)
                sock.connect((self._ip, self._port))
                
                # Send command
                sock.send((command + "\r\n").encode())
                
                # Check if it's a query (ends with ?)
                if command.strip().endswith("?"):
                    response = sock.recv(4096).decode().strip()
                    sock.close()
                    self._log(f"SCPI TX: {command} -> {response}")
                    return SCPIResponse(success=True, data=response)
                else:
                    sock.close()
                    self._log(f"SCPI TX: {command}")
                    return SCPIResponse(success=True)
                    
            except Exception as e:
                self._log(f"SCPI Error: {command} -> {e}")
                return SCPIResponse(success=False, error=str(e))
    
    def query(self, command: str) -> Optional[str]:
        """
        Send query and return response.
        
        Args:
            command: SCPI query (should end with ?)
            
        Returns:
            Response string or None on error
        """
        response = self.send(command)
        return response.data if response.success else None
    
    # =========================================================================
    # HIGH-LEVEL COMMANDS
    # =========================================================================
    
    def set_channel_frequency(self, channel: int, freq_hz: int) -> bool:
        """Set carrier frequency for a channel."""
        cmd = SCPICommands.SET_FREQ.format(channel=channel, freq=freq_hz)
        return self.send(cmd).success
    
    def select_message(self, message_id: str) -> bool:
        """Select broadcast message."""
        cmd = SCPICommands.SET_MSG.format(msg_id=message_id)
        return self.send(cmd).success
    
    def set_output(self, channel: int, enabled: bool) -> bool:
        """Enable/disable channel output."""
        if enabled:
            cmd = SCPICommands.OUTPUT_ON.format(channel=channel)
        else:
            cmd = SCPICommands.OUTPUT_OFF.format(channel=channel)
        return self.send(cmd).success
    
    def set_all_outputs(self, enabled: bool) -> bool:
        """Enable/disable all outputs."""
        cmd = SCPICommands.OUTPUT_ALL_ON if enabled else SCPICommands.OUTPUT_ALL_OFF
        return self.send(cmd).success
    
    def get_status(self) -> Optional[str]:
        """Query system status."""
        return self.query(SCPICommands.QUERY_STATUS)
    
    def get_id(self) -> Optional[str]:
        """Query device identification."""
        return self.query(SCPICommands.QUERY_ID)


# =============================================================================
# MOCK CLIENT FOR TESTING
# =============================================================================

class MockSCPIClient(SCPIClient):
    """
    Mock SCPI client for testing without hardware.
    Simulates responses.
    """
    
    def __init__(self):
        super().__init__()
        self._simulated_connected = False
    
    def connect(self, ip: str, port: int = None) -> bool:
        self._ip = ip
        self._simulated_connected = True
        self._connected = True
        self._log(f"[MOCK] Connected to {ip}")
        return True
    
    def send(self, command: str) -> SCPIResponse:
        if not self._simulated_connected:
            return SCPIResponse(success=False, error="Not connected")
        
        self._log(f"[MOCK] SCPI TX: {command}")
        
        # Simulate query responses
        if command.strip().endswith("?"):
            if "*IDN?" in command:
                return SCPIResponse(success=True, data="Red Pitaya 125-10 MOCK")
            elif "STATUS?" in command:
                return SCPIResponse(success=True, data="READY")
            return SCPIResponse(success=True, data="OK")
        
        return SCPIResponse(success=True)

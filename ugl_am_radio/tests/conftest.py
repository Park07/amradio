"""
Pytest Configuration and Fixtures
=================================
Shared fixtures for all test modules.
"""

import pytest
import socket
import threading
from unittest.mock import Mock, MagicMock, patch
from typing import Generator, Tuple


# =============================================================================
# Mock Server Fixture
# =============================================================================

class MockSCPIServer:
    """Simple mock SCPI server for testing."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.received_commands = []
        self.responses = {
            "*IDN?": "MockRedPitaya,AMRadio,v1.0,TEST",
            "SYST:STAT?": "0x00000006"
        }
        self._thread = None
        
    def start(self) -> int:
        """Start the mock server. Returns assigned port."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.port = self.socket.getsockname()[1]
        self.running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self.port
    
    def _serve(self):
        """Server loop."""
        while self.running:
            try:
                self.socket.settimeout(0.5)
                conn, addr = self.socket.accept()
                self._handle_client(conn)
            except socket.timeout:
                continue
            except Exception:
                break
    
    def _handle_client(self, conn):
        """Handle client connection."""
        while self.running:
            try:
                data = conn.recv(1024).decode().strip()
                if not data:
                    break
                self.received_commands.append(data)
                
                # Send response for queries
                if "?" in data:
                    response = self.responses.get(data, "OK")
                    conn.send((response + "\n").encode())
            except Exception:
                break
        conn.close()
    
    def stop(self):
        """Stop the mock server."""
        self.running = False
        if self.socket:
            self.socket.close()
        if self._thread:
            self._thread.join(timeout=1)
    
    def clear_commands(self):
        """Clear received commands list."""
        self.received_commands.clear()


@pytest.fixture
def mock_server() -> Generator[MockSCPIServer, None, None]:
    """Provide a mock SCPI server for testing."""
    server = MockSCPIServer()
    port = server.start()
    yield server
    server.stop()


# =============================================================================
# Model Fixtures
# =============================================================================

@pytest.fixture
def default_channel_state() -> dict:
    """Default channel state dictionary."""
    return {
        "enabled": False,
        "frequency_khz": 700,
        "frequency_hz": 700000
    }


@pytest.fixture
def default_system_state() -> dict:
    """Default system state dictionary."""
    return {
        "connected": False,
        "broadcasting": False,
        "ip_address": "192.168.0.100",
        "port": 5000,
        "audio_source": "BRAM",
        "selected_message": 1,
        "ch1": {
            "enabled": False,
            "frequency_khz": 700
        },
        "ch2": {
            "enabled": False,
            "frequency_khz": 900
        }
    }


# =============================================================================
# Controller Fixtures
# =============================================================================

@pytest.fixture
def mock_socket():
    """Provide a mock socket for controller testing."""
    with patch('socket.socket') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_model():
    """Provide a mock model for controller testing."""
    model = Mock()
    model.connected = False
    model.broadcasting = False
    model.ch1_enabled = True
    model.ch1_freq = 700000
    model.ch2_enabled = False
    model.ch2_freq = 900000
    model.audio_source = "BRAM"
    return model


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def test_config() -> dict:
    """Test configuration dictionary."""
    return {
        "connection": {
            "default_ip": "127.0.0.1",
            "default_port": 5000,
            "timeout_seconds": 1
        },
        "channels": {
            "ch1": {
                "default_freq_khz": 700,
                "min_freq_khz": 530,
                "max_freq_khz": 1700
            },
            "ch2": {
                "default_freq_khz": 900,
                "min_freq_khz": 530,
                "max_freq_khz": 1700
            }
        }
    }


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def freq_to_phase_inc():
    """Helper function to convert frequency to phase increment."""
    def _convert(freq_hz: int, clk_hz: int = 125000000) -> int:
        return int((freq_hz * (1 << 32)) / clk_hz) & 0xFFFFFFFF
    return _convert

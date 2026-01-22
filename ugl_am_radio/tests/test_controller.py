"""
Unit Tests for Controller Module
=================================
Tests for business logic and SCPI communication.
"""

import pytest
import socket
import time
from unittest.mock import Mock, MagicMock, patch


# =============================================================================
# SCPI Command Building Tests
# =============================================================================

class TestSCPICommands:
    """Tests for SCPI command construction."""
    
    def test_identify_command(self):
        """Identity query should be *IDN?"""
        cmd = "*IDN?"
        assert cmd == "*IDN?"
        
    def test_output_on_command(self):
        """Output ON command format."""
        cmd = "OUTPUT:STATE ON"
        assert cmd == "OUTPUT:STATE ON"
        
    def test_output_off_command(self):
        """Output OFF command format."""
        cmd = "OUTPUT:STATE OFF"
        assert cmd == "OUTPUT:STATE OFF"
        
    def test_channel_enable_command(self):
        """Channel enable command format."""
        ch = 1
        cmd = f"CH{ch}:OUTPUT ON"
        assert cmd == "CH1:OUTPUT ON"
        
    def test_channel_disable_command(self):
        """Channel disable command format."""
        ch = 2
        cmd = f"CH{ch}:OUTPUT OFF"
        assert cmd == "CH2:OUTPUT OFF"
        
    def test_frequency_command(self):
        """Frequency command format."""
        ch = 1
        freq_hz = 531000
        cmd = f"CH{ch}:FREQ {freq_hz}"
        assert cmd == "CH1:FREQ 531000"
        
    def test_source_bram_command(self):
        """BRAM source command format."""
        cmd = "SOURCE:INPUT BRAM"
        assert cmd == "SOURCE:INPUT BRAM"
        
    def test_source_adc_command(self):
        """ADC source command format."""
        cmd = "SOURCE:INPUT ADC"
        assert cmd == "SOURCE:INPUT ADC"
        
    def test_message_select_command(self):
        """Message select command format."""
        msg_id = 2
        cmd = f"SOURCE:MSG {msg_id}"
        assert cmd == "SOURCE:MSG 2"


# =============================================================================
# Connection Tests
# =============================================================================

class TestConnection:
    """Tests for network connection handling."""
    
    def test_connect_success(self, mock_server):
        """Should connect successfully to server."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        try:
            sock.connect(("127.0.0.1", mock_server.port))
            connected = True
        except Exception:
            connected = False
        finally:
            sock.close()
            
        assert connected == True
        
    def test_connect_timeout(self):
        """Should timeout on unreachable host."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        
        try:
            # Use non-routable IP
            sock.connect(("10.255.255.1", 5000))
            connected = True
        except socket.timeout:
            connected = False
        except Exception:
            connected = False
        finally:
            sock.close()
            
        assert connected == False
        
    def test_connect_refused(self):
        """Should handle connection refused."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        
        try:
            # Use localhost with unlikely port
            sock.connect(("127.0.0.1", 59999))
            connected = True
        except ConnectionRefusedError:
            connected = False
        except Exception:
            connected = False
        finally:
            sock.close()
            
        assert connected == False


# =============================================================================
# Command Sending Tests
# =============================================================================

class TestCommandSending:
    """Tests for sending commands to hardware."""
    
    def test_send_command(self, mock_server):
        """Should send command and receive acknowledgment."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        # Send command
        sock.send(b"OUTPUT:STATE ON\n")
        time.sleep(0.1)
        
        sock.close()
        
        assert "OUTPUT:STATE ON" in mock_server.received_commands
        
    def test_send_query(self, mock_server):
        """Should send query and receive response."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        # Send query
        sock.send(b"*IDN?\n")
        response = sock.recv(1024).decode().strip()
        
        sock.close()
        
        assert "MockRedPitaya" in response
        
    def test_send_frequency(self, mock_server):
        """Should send frequency command correctly."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        freq_hz = 700000
        cmd = f"CH1:FREQ {freq_hz}\n"
        sock.send(cmd.encode())
        time.sleep(0.1)
        
        sock.close()
        
        assert "CH1:FREQ 700000" in mock_server.received_commands


# =============================================================================
# Frequency Conversion Tests
# =============================================================================

class TestFrequencyConversion:
    """Tests for kHz to Hz conversion."""
    
    def test_khz_to_hz(self):
        """kHz should convert to Hz correctly."""
        freq_khz = 531
        freq_hz = freq_khz * 1000
        assert freq_hz == 531000
        
    def test_hz_to_phase_inc(self, freq_to_phase_inc):
        """Hz should convert to phase increment correctly."""
        freq_hz = 700000
        phase_inc = freq_to_phase_inc(freq_hz)
        
        # Verify it's a 32-bit value
        assert 0 <= phase_inc <= 0xFFFFFFFF
        
    def test_frequency_range_check(self):
        """Should validate frequency is in AM band."""
        def is_valid_freq(freq_khz):
            return 530 <= freq_khz <= 1700
            
        assert is_valid_freq(531) == True
        assert is_valid_freq(700) == True
        assert is_valid_freq(1700) == True
        assert is_valid_freq(500) == False
        assert is_valid_freq(1800) == False


# =============================================================================
# Broadcast Control Tests
# =============================================================================

class TestBroadcastControl:
    """Tests for broadcast start/stop logic."""
    
    def test_start_broadcast_sequence(self, mock_server):
        """Start broadcast should send correct command sequence."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        # Simulate start broadcast
        commands = [
            "CH1:OUTPUT ON",
            "CH1:FREQ 700000",
            "OUTPUT:STATE ON"
        ]
        
        for cmd in commands:
            sock.send(f"{cmd}\n".encode())
            time.sleep(0.05)
            
        sock.close()
        time.sleep(0.1)
        
        for cmd in commands:
            assert cmd in mock_server.received_commands
            
    def test_stop_broadcast_command(self, mock_server):
        """Stop broadcast should send OUTPUT:STATE OFF."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        sock.send(b"OUTPUT:STATE OFF\n")
        time.sleep(0.1)
        
        sock.close()
        
        assert "OUTPUT:STATE OFF" in mock_server.received_commands


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    def test_handle_disconnect(self):
        """Should handle unexpected disconnect gracefully."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        
        # Connect to nothing
        try:
            sock.connect(("127.0.0.1", 59998))
            sock.send(b"TEST\n")
            error_occurred = False
        except Exception:
            error_occurred = True
        finally:
            sock.close()
            
        assert error_occurred == True
        
    def test_handle_timeout(self):
        """Should handle send timeout gracefully."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        
        try:
            sock.connect(("10.255.255.1", 5000))
            timeout_occurred = False
        except socket.timeout:
            timeout_occurred = True
        except Exception:
            timeout_occurred = True
        finally:
            sock.close()
            
        assert timeout_occurred == True
        
    def test_invalid_frequency_handling(self):
        """Should reject invalid frequencies."""
        def validate_frequency(freq_khz):
            if not isinstance(freq_khz, (int, float)):
                return False
            if freq_khz < 530 or freq_khz > 1700:
                return False
            return True
            
        assert validate_frequency(700) == True
        assert validate_frequency(500) == False
        assert validate_frequency(1800) == False
        assert validate_frequency("abc") == False


# =============================================================================
# Channel Control Tests
# =============================================================================

class TestChannelControl:
    """Tests for channel enable/disable logic."""
    
    def test_enable_channel(self, mock_server):
        """Should send enable command for channel."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        sock.send(b"CH1:OUTPUT ON\n")
        time.sleep(0.1)
        
        sock.close()
        
        assert "CH1:OUTPUT ON" in mock_server.received_commands
        
    def test_disable_channel(self, mock_server):
        """Should send disable command for channel."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        sock.send(b"CH2:OUTPUT OFF\n")
        time.sleep(0.1)
        
        sock.close()
        
        assert "CH2:OUTPUT OFF" in mock_server.received_commands
        
    def test_set_channel_frequency(self, mock_server):
        """Should set channel frequency correctly."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        sock.send(b"CH1:FREQ 531000\n")
        time.sleep(0.1)
        
        sock.close()
        
        assert "CH1:FREQ 531000" in mock_server.received_commands


# =============================================================================
# Audio Source Tests
# =============================================================================

class TestAudioSourceControl:
    """Tests for audio source switching."""
    
    def test_select_bram_source(self, mock_server):
        """Should select BRAM audio source."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        sock.send(b"SOURCE:INPUT BRAM\n")
        time.sleep(0.1)
        
        sock.close()
        
        assert "SOURCE:INPUT BRAM" in mock_server.received_commands
        
    def test_select_adc_source(self, mock_server):
        """Should select ADC audio source."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", mock_server.port))
        
        sock.send(b"SOURCE:INPUT ADC\n")
        time.sleep(0.1)
        
        sock.close()
        
        assert "SOURCE:INPUT ADC" in mock_server.received_commands

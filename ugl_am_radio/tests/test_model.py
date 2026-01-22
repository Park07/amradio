"""
Unit Tests for Model Module
============================
Tests for data models and state management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from model import ChannelState, AppState, AuditLogger, SCPIClient, Model
from config import Config


# =============================================================================
# ChannelState Tests
# =============================================================================

class TestChannelState:
    """Tests for ChannelState dataclass."""

    def test_channel_state_creation(self):
        """ChannelState should be created with required fields."""
        ch = ChannelState(id=1, frequency=700000)
        assert ch.id == 1
        assert ch.frequency == 700000
        assert ch.enabled is False

    def test_channel_state_enabled(self):
        """ChannelState enabled flag should work."""
        ch = ChannelState(id=2, frequency=900000, enabled=True)
        assert ch.enabled is True

    def test_channel_state_modification(self):
        """ChannelState fields should be mutable."""
        ch = ChannelState(id=1, frequency=700000)
        ch.frequency = 531000
        ch.enabled = True
        assert ch.frequency == 531000
        assert ch.enabled is True


# =============================================================================
# AppState Tests
# =============================================================================

class TestAppState:
    """Tests for AppState dataclass."""

    def test_app_state_defaults(self):
        """AppState should have correct defaults."""
        state = AppState()
        assert state.connected is False
        assert state.broadcasting is False
        assert state.source == Config.SOURCE_BRAM
        assert state.selected_message == 1

    def test_app_state_channels_initialized(self):
        """AppState should initialize channels from Config."""
        state = AppState()
        assert len(state.channels) == len(Config.CHANNELS)

    def test_app_state_custom_values(self):
        """AppState should accept custom values."""
        state = AppState(connected=True, broadcasting=True, source="ADC")
        assert state.connected is True
        assert state.broadcasting is True
        assert state.source == "ADC"


# =============================================================================
# AuditLogger Tests
# =============================================================================

class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_logger_creation(self):
        """AuditLogger should be created with default log file."""
        logger = AuditLogger()
        assert logger.log_file == Config.LOG_FILE

    def test_logger_custom_file(self):
        """AuditLogger should accept custom log file."""
        logger = AuditLogger(log_file="custom.log")
        assert logger.log_file == "custom.log"

    def test_logger_log_returns_entry(self):
        """log() should return the formatted entry."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_log = f.name
        try:
            logger = AuditLogger(log_file=temp_log)
            entry = logger.log("Test message")
            assert "Test message" in entry
            assert "[INFO]" in entry
        finally:
            os.unlink(temp_log)

    def test_logger_log_levels(self):
        """log() should include specified level."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_log = f.name
        try:
            logger = AuditLogger(log_file=temp_log)
            entry = logger.log("Error occurred", level="ERROR")
            assert "[ERROR]" in entry
        finally:
            os.unlink(temp_log)

    def test_logger_listener_callback(self):
        """AuditLogger should notify listeners."""
        logger = AuditLogger(log_file="/dev/null")
        received = []
        logger.add_listener(lambda msg: received.append(msg))
        logger.log("Test")
        assert len(received) == 1
        assert "Test" in received[0]

    def test_logger_multiple_listeners(self):
        """AuditLogger should notify all listeners."""
        logger = AuditLogger(log_file="/dev/null")
        received1, received2 = [], []
        logger.add_listener(lambda msg: received1.append(msg))
        logger.add_listener(lambda msg: received2.append(msg))
        logger.log("Multi")
        assert len(received1) == 1
        assert len(received2) == 1


# =============================================================================
# SCPIClient Tests
# =============================================================================

class TestSCPIClient:
    """Tests for SCPIClient class."""

    def test_scpi_client_creation(self):
        """SCPIClient should be created with logger."""
        logger = AuditLogger(log_file="/dev/null")
        client = SCPIClient(logger)
        assert client.connected is False
        assert client.socket is None

    @patch('socket.socket')
    def test_scpi_connect_success(self, mock_socket_class):
        """SCPIClient should connect successfully."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        logger = AuditLogger(log_file="/dev/null")
        client = SCPIClient(logger)
        result = client.connect("127.0.0.1", 5000)

        assert result is True
        assert client.connected is True
        mock_socket.connect.assert_called_once_with(("127.0.0.1", 5000))

    @patch('socket.socket')
    def test_scpi_connect_timeout(self, mock_socket_class):
        """SCPIClient should handle connection timeout."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = TimeoutError()
        mock_socket_class.return_value = mock_socket

        logger = AuditLogger(log_file="/dev/null")
        client = SCPIClient(logger)
        result = client.connect("127.0.0.1", 5000)

        assert result is False
        assert client.connected is False

    @patch('socket.socket')
    def test_scpi_disconnect(self, mock_socket_class):
        """SCPIClient should disconnect cleanly."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        logger = AuditLogger(log_file="/dev/null")
        client = SCPIClient(logger)
        client.connect("127.0.0.1", 5000)
        client.disconnect()

        assert client.connected is False
        assert client.socket is None
        mock_socket.close.assert_called_once()

    @patch('socket.socket')
    def test_scpi_send_command(self, mock_socket_class):
        """SCPIClient should send commands."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        logger = AuditLogger(log_file="/dev/null")
        client = SCPIClient(logger)
        client.connect("127.0.0.1", 5000)
        client.send("OUTPUT:STATE ON")

        mock_socket.sendall.assert_called_with(b"OUTPUT:STATE ON\n")

    @patch('socket.socket')
    def test_scpi_send_query(self, mock_socket_class):
        """SCPIClient should handle queries."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"RedPitaya,v1.0"
        mock_socket_class.return_value = mock_socket

        logger = AuditLogger(log_file="/dev/null")
        client = SCPIClient(logger)
        client.connect("127.0.0.1", 5000)
        response = client.send("*IDN?")

        assert response == "RedPitaya,v1.0"

    def test_scpi_send_not_connected(self):
        """SCPIClient should handle send when not connected."""
        logger = AuditLogger(log_file="/dev/null")
        client = SCPIClient(logger)
        result = client.send("TEST")
        assert result is None


# =============================================================================
# Model Tests
# =============================================================================

class TestModel:
    """Tests for Model class."""

    def test_model_creation(self):
        """Model should be created with components."""
        model = Model()
        assert model.logger is not None
        assert model.scpi is not None
        assert model.state is not None

    def test_model_initial_state(self):
        """Model should have correct initial state."""
        model = Model()
        assert model.is_connected() is False
        assert model.is_broadcasting() is False

    def test_model_state_listener(self):
        """Model should notify state listeners."""
        model = Model()
        received = []
        model.add_state_listener(lambda state: received.append(state))
        model._notify_state_change()
        assert len(received) == 1

    @patch('socket.socket')
    def test_model_connect(self, mock_socket_class):
        """Model should connect and update state."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"RedPitaya"
        mock_socket_class.return_value = mock_socket

        model = Model()
        result = model.connect("127.0.0.1", 5000)

        assert result is True
        assert model.is_connected() is True

    @patch('socket.socket')
    def test_model_disconnect(self, mock_socket_class):
        """Model should disconnect and update state."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"RedPitaya"
        mock_socket_class.return_value = mock_socket

        model = Model()
        model.connect("127.0.0.1", 5000)
        model.disconnect()

        assert model.is_connected() is False

    @patch('socket.socket')
    def test_model_set_source(self, mock_socket_class):
        """Model should set audio source."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        model = Model()
        model.connect("127.0.0.1", 5000)
        model.set_source("ADC")

        assert model.state.source == "ADC"

    @patch('socket.socket')
    def test_model_set_message(self, mock_socket_class):
        """Model should set message ID."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        model = Model()
        model.connect("127.0.0.1", 5000)
        model.set_message(2)

        assert model.state.selected_message == 2

    @patch('socket.socket')
    def test_model_set_channel_frequency(self, mock_socket_class):
        """Model should set channel frequency."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        model = Model()
        model.connect("127.0.0.1", 5000)
        model.set_channel_frequency(1, 531000)

        ch = model.get_channel(1)
        assert ch.frequency == 531000

    @patch('socket.socket')
    def test_model_set_channel_enabled(self, mock_socket_class):
        """Model should enable/disable channel."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        model = Model()
        model.connect("127.0.0.1", 5000)
        model.set_channel_enabled(1, True)

        ch = model.get_channel(1)
        assert ch.enabled is True

    @patch('socket.socket')
    def test_model_set_broadcast(self, mock_socket_class):
        """Model should start/stop broadcast."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        model = Model()
        model.connect("127.0.0.1", 5000)
        model.set_broadcast(True)

        assert model.is_broadcasting() is True

    @patch('socket.socket')
    def test_model_toggle_broadcast(self, mock_socket_class):
        """Model should toggle broadcast state."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        model = Model()
        model.connect("127.0.0.1", 5000)

        model.toggle_broadcast()
        assert model.is_broadcasting() is True

        model.toggle_broadcast()
        assert model.is_broadcasting() is False

    def test_model_get_channel(self):
        """Model should return channel by ID."""
        model = Model()
        ch = model.get_channel(1)
        assert ch is not None
        assert ch.id == 1

    def test_model_get_channel_invalid(self):
        """Model should return None for invalid channel ID."""
        model = Model()
        ch = model.get_channel(99)
        assert ch is None


# =============================================================================
# Phase Increment Tests
# =============================================================================

class TestPhaseIncrement:
    """Tests for NCO phase increment calculation."""

    @pytest.fixture
    def freq_to_phase_inc(self):
        """Helper function to convert frequency to phase increment."""
        def _convert(freq_hz: int, clk_hz: int = 125000000) -> int:
            return int((freq_hz * (1 << 32)) / clk_hz) & 0xFFFFFFFF
        return _convert

    def test_700khz_phase_increment(self, freq_to_phase_inc):
        """700 kHz should produce correct phase increment."""
        phase_inc = freq_to_phase_inc(700000)
        # Expected: 0x016F0069 (approximate)
        assert 0x016F0000 <= phase_inc <= 0x016F00FF

    def test_900khz_phase_increment(self, freq_to_phase_inc):
        """900 kHz should produce correct phase increment."""
        phase_inc = freq_to_phase_inc(900000)
        # Expected: 0x01D7DBF4 (approximate)
        assert 0x01D7DB00 <= phase_inc <= 0x01D7DC00

    def test_531khz_phase_increment(self, freq_to_phase_inc):
        """531 kHz should produce correct phase increment."""
        phase_inc = freq_to_phase_inc(531000)
        expected = int((531000 * (1 << 32)) / 125000000)
        assert phase_inc == expected

    def test_phase_increment_is_32bit(self, freq_to_phase_inc):
        """Phase increment should fit in 32 bits."""
        phase_inc = freq_to_phase_inc(1700000)
        assert 0 <= phase_inc <= 0xFFFFFFFF
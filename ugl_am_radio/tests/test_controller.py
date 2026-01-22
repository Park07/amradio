"""
Unit Tests for Controller Module
=================================
Tests for UI controller and event handling.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys

# Mock dearpygui before importing controller
sys.modules['dearpygui'] = MagicMock()
sys.modules['dearpygui.dearpygui'] = MagicMock()

with patch.dict('sys.modules', {'dearpygui': MagicMock(), 'dearpygui.dearpygui': MagicMock()}):
    from controller import Controller
    from model import Model, AppState, ChannelState
    from config import Config


# =============================================================================
# Controller Creation Tests
# =============================================================================

class TestControllerCreation:
    """Tests for Controller initialization."""

    @patch('controller.dpg')
    def test_controller_creation(self, mock_dpg):
        """Controller should be created with model."""
        model = Model()
        controller = Controller(model)
        assert controller.model is model

    @patch('controller.dpg')
    def test_controller_subscribes_to_model(self, mock_dpg):
        """Controller should subscribe to model state changes."""
        model = Model()
        initial_listeners = len(model._state_listeners)
        controller = Controller(model)
        assert len(model._state_listeners) == initial_listeners + 1

    @patch('controller.dpg')
    def test_controller_subscribes_to_logger(self, mock_dpg):
        """Controller should subscribe to logger messages."""
        model = Model()
        initial_listeners = len(model.logger.listeners)
        controller = Controller(model)
        assert len(model.logger.listeners) == initial_listeners + 1

    @patch('controller.dpg')
    def test_controller_log_entries_empty(self, mock_dpg):
        """Controller should start with empty log entries."""
        model = Model()
        controller = Controller(model)
        assert controller.log_entries == []


# =============================================================================
# Event Handler Tests
# =============================================================================

class TestEventHandlers:
    """Tests for controller event handlers."""

    @patch('controller.dpg')
    def test_on_connect_click_disconnects(self, mock_dpg):
        """Connect click should call model.disconnect when connected."""
        model = Model()
        model.state.connected = True
        model.disconnect = Mock()
        controller = Controller(model)

        controller._on_connect_click()

        model.disconnect.assert_called_once()

    @patch('controller.dpg')
    def test_on_source_change_adc(self, mock_dpg):
        """Source change to ADC should call model.set_source."""
        model = Model()
        model.set_source = Mock()
        controller = Controller(model)

        controller._on_source_change(None, "Live Mic (ADC)")

        model.set_source.assert_called_once_with(Config.SOURCE_ADC)

    @patch('controller.dpg')
    def test_on_source_change_bram(self, mock_dpg):
        """Source change to BRAM should call model.set_source."""
        model = Model()
        model.set_source = Mock()
        controller = Controller(model)

        controller._on_source_change(None, "Stored Message (BRAM)")

        model.set_source.assert_called_once_with(Config.SOURCE_BRAM)

    @patch('controller.dpg')
    def test_on_message_change(self, mock_dpg):
        """Message change should call model.set_message."""
        model = Model()
        model.set_message = Mock()
        controller = Controller(model)

        msg_name = Config.MESSAGES[0]["name"]
        controller._on_message_change(None, msg_name)

        model.set_message.assert_called_once_with(Config.MESSAGES[0]["id"])

    @patch('controller.dpg')
    def test_on_channel_toggle_enable(self, mock_dpg):
        """Channel toggle should call model.set_channel_enabled."""
        model = Model()
        model.set_channel_enabled = Mock()
        controller = Controller(model)

        controller._on_channel_toggle(None, True, 1)

        model.set_channel_enabled.assert_called_once_with(1, True)

    @patch('controller.dpg')
    def test_on_channel_toggle_disable(self, mock_dpg):
        """Channel toggle should disable channel."""
        model = Model()
        model.set_channel_enabled = Mock()
        controller = Controller(model)

        controller._on_channel_toggle(None, False, 2)

        model.set_channel_enabled.assert_called_once_with(2, False)

    @patch('controller.dpg')
    def test_on_freq_change(self, mock_dpg):
        """Frequency change should call model.set_channel_frequency."""
        model = Model()
        model.set_channel_frequency = Mock()
        controller = Controller(model)

        controller._on_freq_change(None, 531, 1)

        model.set_channel_frequency.assert_called_once_with(1, 531000)

    @patch('controller.dpg')
    def test_on_broadcast_click_not_connected(self, mock_dpg):
        """Broadcast click should do nothing when disconnected."""
        model = Model()
        model.set_broadcast = Mock()
        controller = Controller(model)

        controller._on_broadcast_click()

        model.set_broadcast.assert_not_called()

    @patch('controller.dpg')
    def test_on_broadcast_click_stop(self, mock_dpg):
        """Broadcast click should stop when broadcasting."""
        model = Model()
        model.state.connected = True
        model.state.broadcasting = True
        model.set_broadcast = Mock()
        controller = Controller(model)

        controller._on_broadcast_click()

        model.set_broadcast.assert_called_once_with(False)


# =============================================================================
# Log Handler Tests
# =============================================================================

class TestLogHandler:
    """Tests for log message handler."""

    @patch('controller.dpg')
    def test_on_log_message_appends(self, mock_dpg):
        """Log message should be appended to entries."""
        mock_dpg.does_item_exist.return_value = True

        model = Model()
        controller = Controller(model)

        controller._on_log_message("Test log entry")

        assert "Test log entry" in controller.log_entries

    @patch('controller.dpg')
    def test_on_log_message_trims_old(self, mock_dpg):
        """Log should trim old entries when exceeding max."""
        mock_dpg.does_item_exist.return_value = True

        model = Model()
        controller = Controller(model)

        for i in range(Config.LOG_MAX_LINES + 10):
            controller._on_log_message(f"Entry {i}")

        assert len(controller.log_entries) <= Config.LOG_MAX_LINES


# =============================================================================
# Integration Tests
# =============================================================================

class TestControllerIntegration:
    """Integration tests for controller with model."""

    @patch('controller.dpg')
    def test_channel_enable_updates_state(self, mock_dpg):
        """Enabling channel should update model state."""
        model = Model()
        controller = Controller(model)

        controller._on_channel_toggle(None, True, 1)

        ch = model.get_channel(1)
        assert ch.enabled is True

    @patch('controller.dpg')
    def test_frequency_change_updates_state(self, mock_dpg):
        """Changing frequency should update model state."""
        model = Model()
        controller = Controller(model)

        controller._on_freq_change(None, 900, 1)

        ch = model.get_channel(1)
        assert ch.frequency == 900000

    @patch('controller.dpg')
    def test_source_change_updates_state(self, mock_dpg):
        """Changing source should update model state."""
        model = Model()
        controller = Controller(model)

        controller._on_source_change(None, "Live Mic (ADC)")

        assert model.state.source == Config.SOURCE_ADC

    @patch('controller.dpg')
    def test_message_change_updates_state(self, mock_dpg):
        """Changing message should update model state."""
        model = Model()
        controller = Controller(model)

        msg_name = Config.MESSAGES[1]["name"] if len(Config.MESSAGES) > 1 else Config.MESSAGES[0]["name"]
        msg_id = Config.MESSAGES[1]["id"] if len(Config.MESSAGES) > 1 else Config.MESSAGES[0]["id"]
        controller._on_message_change(None, msg_name)

        assert model.state.selected_message == msg_id
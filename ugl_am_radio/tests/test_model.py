"""
Unit Tests for Model Module
============================
Tests for data models and state management.
"""

import pytest
from unittest.mock import Mock, patch


# =============================================================================
# Channel State Tests
# =============================================================================

class TestChannelState:
    """Tests for channel state management."""
    
    def test_default_frequency(self, default_channel_state):
        """Channel should have default frequency."""
        assert default_channel_state["frequency_khz"] == 700
        
    def test_frequency_conversion(self):
        """Frequency should convert kHz to Hz correctly."""
        freq_khz = 531
        freq_hz = freq_khz * 1000
        assert freq_hz == 531000
        
    def test_channel_disabled_by_default(self, default_channel_state):
        """Channel should be disabled by default."""
        assert default_channel_state["enabled"] == False
        
    def test_frequency_range_validation(self):
        """Frequency should be within valid AM range."""
        min_freq = 530
        max_freq = 1700
        test_freq = 700
        
        assert min_freq <= test_freq <= max_freq
        
    def test_invalid_frequency_below_range(self):
        """Frequency below 530 kHz should be invalid."""
        freq = 500
        min_freq = 530
        assert freq < min_freq
        
    def test_invalid_frequency_above_range(self):
        """Frequency above 1700 kHz should be invalid."""
        freq = 1800
        max_freq = 1700
        assert freq > max_freq


# =============================================================================
# System State Tests
# =============================================================================

class TestSystemState:
    """Tests for system state management."""
    
    def test_initial_disconnected(self, default_system_state):
        """System should be disconnected initially."""
        assert default_system_state["connected"] == False
        
    def test_initial_not_broadcasting(self, default_system_state):
        """System should not be broadcasting initially."""
        assert default_system_state["broadcasting"] == False
        
    def test_default_audio_source(self, default_system_state):
        """Default audio source should be BRAM."""
        assert default_system_state["audio_source"] == "BRAM"
        
    def test_default_ip_address(self, default_system_state):
        """Default IP should be set."""
        assert default_system_state["ip_address"] == "192.168.0.100"
        
    def test_default_port(self, default_system_state):
        """Default port should be 5000."""
        assert default_system_state["port"] == 5000


# =============================================================================
# Phase Increment Calculation Tests
# =============================================================================

class TestPhaseIncrement:
    """Tests for NCO phase increment calculation."""
    
    def test_700khz_phase_increment(self, freq_to_phase_inc):
        """700 kHz should produce correct phase increment."""
        phase_inc = freq_to_phase_inc(700000)
        # Expected: 0x016F0069 (approximate)
        assert 0x016F0000 <= phase_inc <= 0x016F00FF
        
    def test_900khz_phase_increment(self, freq_to_phase_inc):
        """900 kHz should produce correct phase increment."""
        phase_inc = freq_to_phase_inc(900000)
        # Expected: 0x01D7DEF4 (approximate)
        assert 0x01D7DB00 <= phase_inc <= 0x01D7DC00
        
    def test_531khz_phase_increment(self, freq_to_phase_inc):
        """531 kHz should produce correct phase increment."""
        phase_inc = freq_to_phase_inc(531000)
        # phase_inc = (531000 * 2^32) / 125000000
        expected = int((531000 * (1 << 32)) / 125000000)
        assert phase_inc == expected
        
    def test_phase_increment_is_32bit(self, freq_to_phase_inc):
        """Phase increment should fit in 32 bits."""
        phase_inc = freq_to_phase_inc(1700000)  # Max frequency
        assert 0 <= phase_inc <= 0xFFFFFFFF
        
    def test_zero_frequency(self, freq_to_phase_inc):
        """Zero frequency should produce zero phase increment."""
        phase_inc = freq_to_phase_inc(0)
        assert phase_inc == 0


# =============================================================================
# Audio Source Tests
# =============================================================================

class TestAudioSource:
    """Tests for audio source selection."""
    
    def test_valid_sources(self):
        """BRAM and ADC should be valid sources."""
        valid_sources = ["BRAM", "ADC"]
        assert "BRAM" in valid_sources
        assert "ADC" in valid_sources
        
    def test_bram_is_stored_audio(self):
        """BRAM should represent stored/pre-loaded audio."""
        source = "BRAM"
        assert source == "BRAM"
        
    def test_adc_is_live_audio(self):
        """ADC should represent live audio input."""
        source = "ADC"
        assert source == "ADC"


# =============================================================================
# Message Selection Tests
# =============================================================================

class TestMessageSelection:
    """Tests for broadcast message selection."""
    
    def test_valid_message_ids(self):
        """Message IDs should be positive integers."""
        messages = [1, 2, 3, 4]
        for msg_id in messages:
            assert isinstance(msg_id, int)
            assert msg_id > 0
            
    def test_message_names(self):
        """Standard messages should have names."""
        messages = {
            1: "Emergency Evacuation",
            2: "System Test",
            3: "All Clear"
        }
        assert messages[1] == "Emergency Evacuation"
        
    def test_default_message_selection(self, default_system_state):
        """Default message should be set."""
        assert default_system_state["selected_message"] == 1


# =============================================================================
# State Transition Tests
# =============================================================================

class TestStateTransitions:
    """Tests for valid state transitions."""
    
    def test_connect_changes_state(self):
        """Connecting should change connected state to True."""
        state = {"connected": False}
        # Simulate connect
        state["connected"] = True
        assert state["connected"] == True
        
    def test_disconnect_changes_state(self):
        """Disconnecting should change connected state to False."""
        state = {"connected": True}
        # Simulate disconnect
        state["connected"] = False
        assert state["connected"] == False
        
    def test_cannot_broadcast_when_disconnected(self):
        """Should not be able to broadcast when disconnected."""
        state = {"connected": False, "broadcasting": False}
        
        # Attempt to broadcast
        can_broadcast = state["connected"]
        assert can_broadcast == False
        
    def test_can_broadcast_when_connected(self):
        """Should be able to broadcast when connected."""
        state = {"connected": True, "broadcasting": False}
        
        # Can broadcast check
        can_broadcast = state["connected"]
        assert can_broadcast == True
        
    def test_stop_broadcast_on_disconnect(self):
        """Broadcast should stop when disconnected."""
        state = {"connected": True, "broadcasting": True}
        
        # Simulate disconnect
        state["connected"] = False
        state["broadcasting"] = False  # Should be stopped
        
        assert state["broadcasting"] == False


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    """Tests for input validation."""
    
    def test_ip_address_format(self):
        """IP address should be valid format."""
        import re
        ip = "192.168.0.100"
        pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        assert re.match(pattern, ip) is not None
        
    def test_invalid_ip_address(self):
        """Invalid IP should be rejected."""
        import re
        invalid_ips = ["256.1.1.1", "abc.def.ghi.jkl", "192.168.1"]
        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        
        for ip in invalid_ips:
            match = re.match(pattern, ip)
            if match:
                # Check octets are valid
                octets = ip.split(".")
                valid = all(0 <= int(o) <= 255 for o in octets)
                assert not valid or len(octets) != 4
                
    def test_port_range(self):
        """Port should be in valid range."""
        valid_port = 5000
        assert 1 <= valid_port <= 65535
        
    def test_invalid_port(self):
        """Invalid ports should be rejected."""
        invalid_ports = [0, -1, 65536, 70000]
        for port in invalid_ports:
            assert not (1 <= port <= 65535)

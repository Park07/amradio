"""
UGL Tunnel AM Break-In System
Controller

Business logic and callback handlers.
Coordinates between Model and View.
"""

from __future__ import annotations
import threading
import time
import math
import random
from datetime import datetime
from typing import Optional

import dearpygui.dearpygui as dpg

from .configs import CHANNELS, MESSAGES, Display, Colors
from .models import SystemModel, BroadcastState
from .views import MainView
from .scpi_client import SCPIClient, MockSCPIClient


class Controller:
    """
    Main controller coordinating Model, View, and SCPI client.
    Handles all user interactions and system updates.
    """
    
    def __init__(
        self,
        model: SystemModel,
        view: MainView,
        scpi: SCPIClient = None,
        use_mock: bool = True
    ):
        self.model = model
        self.view = view
        self.scpi = scpi or (MockSCPIClient() if use_mock else SCPIClient())
        
        # Threading
        self._update_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        
        # Set SCPI message callback
        self.scpi.set_message_callback(self._on_scpi_message)
    
    # =========================================================================
    # LIFECYCLE
    # =========================================================================
    
    def start(self) -> None:
        """Start the controller update loop."""
        self._running = True
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        self.model.log("Controller started", "SUCCESS")
    
    def stop(self) -> None:
        """Stop the controller and cleanup."""
        self._running = False
        
        # Stop any active broadcast
        if self.model.is_broadcasting():
            self._stop_broadcast_internal()
        
        if self._update_thread:
            self._update_thread.join(timeout=1.0)
        
        self.model.log("Controller stopped")
    
    def is_running(self) -> bool:
        return self._running
    
    # =========================================================================
    # UPDATE LOOP
    # =========================================================================
    
    def _update_loop(self) -> None:
        """Main update loop running in background thread."""
        update_interval = 1.0 / Display.UPDATE_RATE_HZ
        
        while self._running and dpg.is_dearpygui_running():
            try:
                self._update_displays()
                time.sleep(update_interval)
            except Exception as e:
                self.model.log(f"Update error: {e}", "ERROR")
    
    def _update_displays(self) -> None:
        """Update all display elements."""
        with self._lock:
            # System clock
            now = datetime.now()
            self.view.set_clock(now.strftime("%H:%M:%S"))
            
            # Broadcast timer
            if self.model.is_broadcasting():
                duration = self.model.get_broadcast_duration()
                mins = int(duration // 60)
                secs = duration % 60
                self.view.set_broadcast_timer(f"⏱ {mins:02d}:{secs:04.1f}")
            else:
                self.view.set_broadcast_timer("⏱ 00:00.0")
            
            # Update spectrum (simulated for now)
            self._update_spectrum_simulated()
            
            # Update audio waveform (simulated)
            self._update_audio_simulated()
            
            # Update channel levels (simulated)
            self._update_channel_levels_simulated()
            
            # Update status LEDs
            self._update_leds()
            
            # Update log display
            self.view.log.update(self.model.get_log_text())
    
    def _update_spectrum_simulated(self) -> None:
        """Update spectrum display with simulated data."""
        # Generate noise floor
        x_data = list(range(Display.SPECTRUM_MIN_FREQ, Display.SPECTRUM_MAX_FREQ, 2))
        y_data = []
        
        for freq in x_data:
            # Base noise floor
            level = -70 + random.gauss(0, 2)
            
            # Add carrier peaks if broadcasting
            if self.model.is_broadcasting():
                for ch in self.model.channels.values():
                    if ch.active:
                        ch_freq = CHANNELS[ch.id - 1].freq_khz
                        distance = abs(freq - ch_freq)
                        
                        # Main carrier
                        if distance < 5:
                            level = max(level, -10 - distance * 2)
                        
                        # Sidebands (1 kHz test tone)
                        for sideband in [-1, 1]:
                            sb_freq = ch_freq + sideband
                            sb_distance = abs(freq - sb_freq)
                            if sb_distance < 3:
                                level = max(level, -25 - sb_distance * 3)
            
            y_data.append(level)
        
        self.view.spectrum.update(x_data, y_data)
    
    def _update_audio_simulated(self) -> None:
        """Update audio display with simulated data."""
        if self.model.is_broadcasting():
            # Generate 1kHz test tone visualization
            t = time.time()
            samples = [math.sin(2 * math.pi * 3 * (t + i/Display.AUDIO_BUFFER_SIZE))
                      for i in range(Display.AUDIO_BUFFER_SIZE)]
            level = 0.7 + random.uniform(-0.1, 0.1)
        else:
            samples = [0.0] * Display.AUDIO_BUFFER_SIZE
            level = 0.0
        
        self.view.audio.update_waveform(samples)
        self.view.audio.update_level(level)
    
    def _update_channel_levels_simulated(self) -> None:
        """Update channel RF levels with simulated data."""
        for ch in self.model.channels.values():
            if ch.active:
                level = 0.8 + random.uniform(-0.1, 0.1)
            elif ch.enabled:
                level = 0.1 + random.uniform(-0.05, 0.05)
            else:
                level = 0.0
            
            ch.rf_level = level
            self.view.channels[ch.id - 1].update_level(level)
    
    def _update_leds(self) -> None:
        """Update status LED indicators."""
        # RF LED - on if any channel transmitting
        rf_on = any(ch.active for ch in self.model.channels.values())
        self._set_led(self.view.tag.led_rf, rf_on)
        
        # MOD LED - on if broadcasting
        self._set_led(self.view.tag.led_mod, self.model.is_broadcasting())
        
        # AUDIO LED - on if broadcasting (would be audio input in production)
        self._set_led(self.view.tag.led_audio, self.model.is_broadcasting())
        
        # NETWORK LED - on if connected
        self._set_led(self.view.tag.led_network, self.model.is_connected())
    
    def _set_led(self, tag: int, on: bool) -> None:
        """Set LED indicator state."""
        if dpg.does_item_exist(tag):
            color = Colors.STATUS_OK if on else Colors.STATUS_OFF
            dpg.configure_item(tag, color=color)
    
    # =========================================================================
    # CALLBACKS
    # =========================================================================
    
    def connect_callback(self, sender, app_data, user_data) -> None:
        """Handle connect button click."""
        ip = self.view.get_ip_address()
        if not ip:
            self.view.popup_error("Invalid IP", "Please enter a valid IP address")
            return
        
        self.model.red_pitaya_ip = ip
        self.model.log(f"Connecting to {ip}...")
        
        # Attempt connection
        if self.scpi.connect(ip):
            self.model.set_connected(True)
            self.view.set_connection_status(True, ip)
        else:
            self.model.set_connected(False)
            self.view.set_connection_status(False)
            self.view.popup_error(
                "Connection Failed",
                f"Could not connect to Red Pitaya at {ip}\n\n"
                "Check that:\n"
                "• Red Pitaya is powered on\n"
                "• Network connection is working\n"
                "• IP address is correct"
            )
    
    def broadcast_callback(self, sender, app_data, user_data) -> None:
        """Handle broadcast button click."""
        if self.model.is_broadcasting():
            self._stop_broadcast()
        else:
            self._start_broadcast_with_confirm()
    
    def _start_broadcast_with_confirm(self) -> None:
        """Show confirmation dialog before broadcasting."""
        # Get selected message
        msg_id = self.view.get_selected_message()
        msg_name = next((m.name for m in MESSAGES if m.id == msg_id), msg_id)
        
        # Get active channels
        active_ch = [f"{ch.freq_khz} kHz" for ch in CHANNELS 
                    if self.model.channels[ch.id].enabled]
        
        self.view.popup_confirm(
            title="⚠️ CONFIRM EMERGENCY BROADCAST",
            message=f"You are about to broadcast:\n\n"
                    f"Message: {msg_name}\n"
                    f"Channels: {', '.join(active_ch)}\n\n"
                    f"This will transmit on all enabled AM frequencies.\n"
                    f"Continue?",
            on_confirm=self._start_broadcast
        )
    
    def _start_broadcast(self) -> None:
        """Start emergency broadcast."""
        with self._lock:
            try:
                # Update model
                msg_id = self.view.get_selected_message()
                self.model.selected_message = msg_id
                self.model.start_broadcast()
                
                # Send SCPI commands
                self.scpi.select_message(msg_id)
                for ch in self.model.channels.values():
                    if ch.enabled:
                        self.scpi.set_output(ch.id, True)
                
                # Update view
                self.view.set_broadcast_button_state(True)
                self.view.set_status("🔴 BROADCASTING", broadcasting=True)
                
                # Update channel views
                for ch in self.model.channels.values():
                    self.view.channels[ch.id - 1].set_active(ch.active)
                    self.view.channels[ch.id - 1].set_status(ch.status)
                
            except Exception as e:
                self.model.log(f"Broadcast start failed: {e}", "ERROR")
                self.view.popup_error("Broadcast Failed", str(e))
    
    def _stop_broadcast(self) -> None:
        """Stop broadcast (public callback version)."""
        self._stop_broadcast_internal()
    
    def _stop_broadcast_internal(self) -> None:
        """Stop emergency broadcast (internal)."""
        with self._lock:
            try:
                # Update model
                self.model.stop_broadcast()
                
                # Send SCPI commands
                self.scpi.set_all_outputs(False)
                
                # Update view
                self.view.set_broadcast_button_state(False)
                self.view.set_status("🟢 SYSTEM READY", broadcasting=False)
                
                # Update channel views
                for ch in self.model.channels.values():
                    self.view.channels[ch.id - 1].set_active(False)
                    self.view.channels[ch.id - 1].set_status(ch.status)
                
            except Exception as e:
                self.model.log(f"Broadcast stop error: {e}", "ERROR")
    
    def channel_toggle_callback(self, sender, app_data, user_data) -> None:
        """Handle channel enable/disable toggle."""
        channel_id = user_data
        enabled = app_data
        
        with self._lock:
            self.model.set_channel_enabled(channel_id, enabled)
            self.view.channels[channel_id - 1].set_status(
                self.model.channels[channel_id].status
            )
    
    def message_select_callback(self, sender, app_data, user_data) -> None:
        """Handle message selection change."""
        # Map display name back to ID
        for msg in MESSAGES:
            if msg.name in app_data:
                self.model.set_message(msg.id)
                break
    
    # =========================================================================
    # KEYBOARD HANDLERS
    # =========================================================================
    
    def handle_key_press(self, key: int) -> None:
        """Handle keyboard shortcuts."""
        # F1 or Space = Toggle broadcast
        if key in [dpg.mvKey_F1, dpg.mvKey_Spacebar]:
            self.broadcast_callback(None, None, None)
        
        # Escape = Stop broadcast
        elif key == dpg.mvKey_Escape:
            if self.model.is_broadcasting():
                self._stop_broadcast()
    
    # =========================================================================
    # SCPI MESSAGE HANDLER
    # =========================================================================
    
    def _on_scpi_message(self, message: str) -> None:
        """Handle messages from SCPI client."""
        self.model.log(message, "SCPI")

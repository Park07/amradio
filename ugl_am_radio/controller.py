"""
Controller - UI Logic with Event Bus Integration (12-Channel Dial Version)
===========================================================================

Fixed:
- ASCII-friendly labels (no Unicode issues)
- Channels 1-12 (not 0-11)
- Channel selector disabled until BRAM checked
- Frequency summary table to track all 12 channels

Author: William Park
Date: January 2026
"""

import dearpygui.dearpygui as dpg
import subprocess
from typing import Optional
from datetime import datetime

from config import Config
from model import Model, ConnectionState, BroadcastState, WatchdogState
from event_bus import EventBus, Event, EventType, event_bus


class Controller:
    """Controller with event bus integration and rotary channel selector."""

    def __init__(self, model: Model):
        self.model = model
        self.tags = {}
        self.version_hash = self._get_version_hash()

        # Current selected channel index (0-11 internally, display as 1-12)
        self.selected_channel_idx = 0

        self._subscribe_to_events()

    def _get_version_hash(self) -> str:
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "dev"

    def _subscribe_to_events(self):
        event_bus.subscribe(EventType.CONNECT_SUCCESS, self._on_connect_success)
        event_bus.subscribe(EventType.CONNECT_FAILED, self._on_connect_failed)
        event_bus.subscribe(EventType.DISCONNECTED, self._on_disconnected)
        event_bus.subscribe(EventType.RECONNECT_ATTEMPT, self._on_reconnect_attempt)
        event_bus.subscribe(EventType.DEVICE_STATE_UPDATED, self._on_state_updated)
        event_bus.subscribe(EventType.DEVICE_HEARTBEAT_LOST, self._on_heartbeat_lost)
        event_bus.subscribe(EventType.BROADCAST_ARMING, self._on_broadcast_arming)
        event_bus.subscribe(EventType.BROADCAST_STARTED, self._on_broadcast_started)
        event_bus.subscribe(EventType.BROADCAST_STOPPED, self._on_broadcast_stopped)
        event_bus.subscribe(EventType.WATCHDOG_WARNING, self._on_watchdog_warning)
        event_bus.subscribe(EventType.WATCHDOG_TRIGGERED, self._on_watchdog_triggered)
        event_bus.subscribe(EventType.WATCHDOG_RESET, self._on_watchdog_reset)
        event_bus.subscribe(EventType.ERROR_OCCURRED, self._on_error)

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_connect_success(self, event: Event):
        self._update_connection_ui(True)
        self._hide_warning_banner()
        self._update_log()

    def _on_connect_failed(self, event: Event):
        self._update_connection_ui(False)
        reason = event.data.get("reason", "Unknown error")
        self._show_warning_banner(f"Connection failed: {reason}")
        self._update_log()

    def _on_disconnected(self, event: Event):
        self._update_connection_ui(False)
        self._update_broadcast_ui()
        self._update_log()

    def _on_reconnect_attempt(self, event: Event):
        attempt = event.data.get("attempt", 0)
        max_attempts = Config.MAX_RECONNECT_ATTEMPTS
        self._show_warning_banner(f"Reconnecting... ({attempt}/{max_attempts})")
        dpg.set_value(self.tags["connect_btn"], "RECONNECTING...")
        self._update_log()

    def _on_state_updated(self, event: Event):
        self._update_broadcast_ui()
        self._update_selected_channel_ui()
        self._update_channel_indicators()
        self._update_freq_summary()
        self._update_watchdog_ui()
        self._update_log()

        if not self.model.device_state.stale:
            if not self.model.device_state.watchdog_triggered:
                self._hide_warning_banner()

    def _on_heartbeat_lost(self, event: Event):
        self._show_warning_banner("STALE DATA - Device not responding")

    def _on_broadcast_arming(self, event: Event):
        dpg.set_value(self.tags["broadcast_btn"], "ARMING...")
        dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
        self._update_log()

    def _on_broadcast_started(self, event: Event):
        self._update_broadcast_ui()
        self._update_log()

    def _on_broadcast_stopped(self, event: Event):
        self._update_broadcast_ui()
        self._update_log()

    def _on_watchdog_warning(self, event: Event):
        self._show_warning_banner("WATCHDOG WARNING - Heartbeat delayed")
        self._update_watchdog_ui()

    def _on_watchdog_triggered(self, event: Event):
        self._show_warning_banner("FAIL-SAFE ACTIVATED - RF output disabled!")
        self._update_broadcast_ui()
        self._update_watchdog_ui()
        self._update_log()

    def _on_watchdog_reset(self, event: Event):
        self._hide_warning_banner()
        self._update_watchdog_ui()
        self._update_log()

    def _on_error(self, event: Event):
        message = event.data.get("message", "Unknown error")
        self._show_warning_banner(f"ERROR: {message}")
        self._update_log()

    # =========================================================================
    # UI Update Methods
    # =========================================================================

    def _update_connection_ui(self, connected: bool):
        if connected:
            dpg.set_value(self.tags["connect_btn"], "DISCONNECT")
            dpg.set_value(self.tags["status_text"], "[CONNECTED]")
            dpg.configure_item(self.tags["status_text"], color=Config.Colors.CONNECTED)
            dpg.configure_item(self.tags["ip_input"], enabled=False)
            dpg.configure_item(self.tags["port_input"], enabled=False)
            dpg.configure_item(self.tags["broadcast_btn"], enabled=True)
        else:
            dpg.set_value(self.tags["connect_btn"], "CONNECT")
            dpg.set_value(self.tags["status_text"], "[DISCONNECTED]")
            dpg.configure_item(self.tags["status_text"], color=Config.Colors.DISCONNECTED)
            dpg.configure_item(self.tags["ip_input"], enabled=True)
            dpg.configure_item(self.tags["port_input"], enabled=True)
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
            dpg.set_value(self.tags["broadcast_btn"], "START BROADCAST")

    def _update_broadcast_ui(self):
        state = self.model.get_broadcast_state()
        connected = self.model.is_connected()
        watchdog_triggered = self.model.is_watchdog_triggered()

        if not connected:
            dpg.set_value(self.tags["broadcast_btn"], "START BROADCAST")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
            return

        if watchdog_triggered:
            dpg.set_value(self.tags["broadcast_btn"], "!! WATCHDOG TRIGGERED !!")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
            return

        if state == BroadcastState.BROADCASTING:
            dpg.set_value(self.tags["broadcast_btn"], "[LIVE] STOP BROADCAST")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=True)
        elif state == BroadcastState.ARMING:
            dpg.set_value(self.tags["broadcast_btn"], "ARMING...")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
        elif state == BroadcastState.STOPPING:
            dpg.set_value(self.tags["broadcast_btn"], "STOPPING...")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
        else:
            dpg.set_value(self.tags["broadcast_btn"], "START BROADCAST")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=True)

    def _update_selected_channel_ui(self):
        """Update the currently selected channel's display."""
        if self.selected_channel_idx < len(self.model.device_state.channels):
            ch = self.model.device_state.channels[self.selected_channel_idx]
            ch_num = ch.id  # 1-12

            dpg.set_value(self.tags["channel_num"], f"CH{ch_num}")
            dpg.set_value(self.tags["ch_enable"], ch.enabled)
            dpg.set_value(self.tags["ch_freq_slider"], ch.frequency / 1000)
            dpg.set_value(self.tags["ch_freq_input"], ch.frequency / 1000)

            if ch.enabled:
                dpg.set_value(self.tags["ch_status"], f"[ON] {ch.frequency/1000:.0f} kHz")
                dpg.configure_item(self.tags["ch_status"], color=Config.Colors.CHANNEL_ENABLED)
            else:
                dpg.set_value(self.tags["ch_status"], "[OFF]")
                dpg.configure_item(self.tags["ch_status"], color=Config.Colors.CHANNEL_DISABLED)

    def _update_channel_indicators(self):
        """Update the circular channel indicator buttons."""
        enabled_count = 0

        for idx in range(Config.NUM_CHANNELS):
            tag = f"ch_ind_{idx}"
            if tag in self.tags and idx < len(self.model.device_state.channels):
                ch = self.model.device_state.channels[idx]
                ch_num = ch.id  # 1-12

                if ch.enabled:
                    enabled_count += 1
                    dpg.configure_item(self.tags[tag], label=f"*{ch_num}")
                else:
                    dpg.configure_item(self.tags[tag], label=f" {ch_num}")

                # Highlight selected
                if idx == self.selected_channel_idx:
                    dpg.bind_item_theme(self.tags[tag], self.tags["selected_theme"])
                else:
                    dpg.bind_item_theme(self.tags[tag], self.tags["normal_theme"])

        dpg.set_value(self.tags["channel_count"], f"Active: {enabled_count}/12")

    def _update_freq_summary(self):
        """Update the frequency summary table - only show freq for enabled channels."""
        summary_lines = []
        for idx, ch in enumerate(self.model.device_state.channels):
            if ch.enabled:
                freq_khz = ch.frequency / 1000
                summary_lines.append(f"CH{ch.id:2d}: ON  {freq_khz:6.0f} kHz")
            else:
                summary_lines.append(f"CH{ch.id:2d}: --          ")

        # Split into two columns
        left = summary_lines[:6]
        right = summary_lines[6:]

        combined = []
        for i in range(6):
            l = left[i] if i < len(left) else ""
            r = right[i] if i < len(right) else ""
            combined.append(f"{l}   {r}")

        dpg.set_value(self.tags["freq_summary"], "\n".join(combined))

    def _update_watchdog_ui(self):
        state = self.model.get_watchdog_state()
        time_remaining = self.model.device_state.watchdog_time_remaining

        if state == WatchdogState.OK:
            dpg.set_value(self.tags["watchdog_status"], f"[OK] ({time_remaining}s)")
            dpg.configure_item(self.tags["watchdog_status"], color=Config.Colors.WATCHDOG_OK)
            dpg.configure_item(self.tags["watchdog_reset_btn"], enabled=False)
        elif state == WatchdogState.WARNING:
            dpg.set_value(self.tags["watchdog_status"], f"[WARN] ({time_remaining}s)")
            dpg.configure_item(self.tags["watchdog_status"], color=Config.Colors.WATCHDOG_WARNING)
            dpg.configure_item(self.tags["watchdog_reset_btn"], enabled=True)
        elif state == WatchdogState.TRIGGERED:
            dpg.set_value(self.tags["watchdog_status"], "[TRIGGERED!]")
            dpg.configure_item(self.tags["watchdog_status"], color=Config.Colors.WATCHDOG_TRIGGERED)
            dpg.configure_item(self.tags["watchdog_reset_btn"], enabled=True)

    def _update_log(self):
        entries = self.model.get_log_entries(10)
        dpg.set_value(self.tags["log_text"], "\n".join(entries))

    def _show_warning_banner(self, message: str):
        dpg.set_value(self.tags["warning_text"], message)
        dpg.configure_item(self.tags["warning_banner"], show=True)

    def _hide_warning_banner(self):
        dpg.configure_item(self.tags["warning_banner"], show=False)

    def _update_channel_selector_enabled(self):
        """Enable/disable channel selector based on BRAM checkbox."""
        bram_enabled = dpg.get_value(self.tags["source_toggle"])

        # Enable/disable all channel indicator buttons
        for idx in range(Config.NUM_CHANNELS):
            tag = f"ch_ind_{idx}"
            if tag in self.tags:
                dpg.configure_item(self.tags[tag], enabled=bram_enabled)

        # Enable/disable dial buttons
        dpg.configure_item(self.tags["dial_left"], enabled=bram_enabled)
        dpg.configure_item(self.tags["dial_right"], enabled=bram_enabled)

        # Enable/disable channel controls
        dpg.configure_item(self.tags["ch_enable"], enabled=bram_enabled)
        dpg.configure_item(self.tags["ch_freq_slider"], enabled=bram_enabled)
        dpg.configure_item(self.tags["ch_freq_input"], enabled=bram_enabled)

        # Enable/disable quick buttons
        for n in [1, 2, 3, 4, 6, 8, 12]:
            tag = f"quick_{n}"
            if tag in self.tags:
                dpg.configure_item(self.tags[tag], enabled=bram_enabled)
        dpg.configure_item(self.tags["quick_none"], enabled=bram_enabled)

    # =========================================================================
    # UI Callbacks
    # =========================================================================

    def _on_connect_click(self):
        if self.model.is_connected():
            self.model.disconnect()
        else:
            ip = dpg.get_value(self.tags["ip_input"])
            port = dpg.get_value(self.tags["port_input"])
            dpg.set_value(self.tags["connect_btn"], "CONNECTING...")
            dpg.configure_item(self.tags["connect_btn"], enabled=False)
            self.model.connect(ip, port)

    def _on_broadcast_click(self):
        if self.model.get_broadcast_state() == BroadcastState.BROADCASTING:
            self.model.set_broadcast(False)
        else:
            self.model.set_broadcast(True)

    def _on_watchdog_reset_click(self):
        self.model.reset_watchdog()

    def _on_source_change(self, sender, app_data, user_data):
        source = Config.SOURCE_BRAM if app_data else Config.SOURCE_ADC
        self.model.set_source(source)
        self._update_channel_selector_enabled()

    def _on_message_change(self, sender, app_data, user_data):
        for msg in Config.MESSAGES:
            if msg["name"] == app_data:
                self.model.set_message(msg["id"])
                break

    def _on_dial_left(self):
        self.selected_channel_idx = (self.selected_channel_idx - 1) % Config.NUM_CHANNELS
        self._update_selected_channel_ui()
        self._update_channel_indicators()

    def _on_dial_right(self):
        self.selected_channel_idx = (self.selected_channel_idx + 1) % Config.NUM_CHANNELS
        self._update_selected_channel_ui()
        self._update_channel_indicators()

    def _on_channel_indicator_click(self, sender, app_data, user_data):
        self.selected_channel_idx = user_data  # 0-11 index
        self._update_selected_channel_ui()
        self._update_channel_indicators()

    def _on_channel_enable(self, sender, app_data, user_data):
        ch_id = self.model.device_state.channels[self.selected_channel_idx].id
        self.model.set_channel_enabled(ch_id, app_data)
        # Immediate visual feedback for testing (device will overwrite when connected)
        self.model.device_state.channels[self.selected_channel_idx].enabled = app_data
        self._update_selected_channel_ui()
        self._update_channel_indicators()
        self._update_freq_summary()

    def _on_freq_slider_change(self, sender, app_data, user_data):
        ch_id = self.model.device_state.channels[self.selected_channel_idx].id
        freq_hz = int(app_data * 1000)
        self.model.set_channel_frequency(ch_id, freq_hz)
        # Immediate visual feedback
        self.model.device_state.channels[self.selected_channel_idx].frequency = freq_hz
        dpg.set_value(self.tags["ch_freq_input"], app_data)
        self._update_freq_summary()

    def _on_freq_input_change(self, sender, app_data, user_data):
        ch_id = self.model.device_state.channels[self.selected_channel_idx].id
        freq_hz = int(app_data * 1000)
        self.model.set_channel_frequency(ch_id, freq_hz)
        # Immediate visual feedback
        self.model.device_state.channels[self.selected_channel_idx].frequency = freq_hz
        dpg.set_value(self.tags["ch_freq_slider"], app_data)
        self._update_freq_summary()

    def _on_enable_n_channels(self, sender, app_data, user_data):
        n = user_data
        for i, ch in enumerate(Config.CHANNELS):
            enabled = i < n
            self.model.set_channel_enabled(ch["id"], enabled)
            # Immediate visual feedback
            self.model.device_state.channels[i].enabled = enabled
        self._update_selected_channel_ui()
        self._update_channel_indicators()
        self._update_freq_summary()

    def _on_disable_all_channels(self):
        for i, ch in enumerate(Config.CHANNELS):
            self.model.set_channel_enabled(ch["id"], False)
            # Immediate visual feedback
            self.model.device_state.channels[i].enabled = False
        self._update_selected_channel_ui()
        self._update_channel_indicators()
        self._update_freq_summary()

    # =========================================================================
    # Build UI
    # =========================================================================

    def build_ui(self):
        """Build the complete UI."""

        # Themes
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, Config.Colors.WINDOW_BG)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, Config.Colors.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, Config.Colors.FRAME_BG_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_Text, Config.Colors.TEXT_PRIMARY)
                dpg.add_theme_color(dpg.mvThemeCol_Button, Config.Colors.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, Config.Colors.BTN_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, Config.Colors.PANEL_BG)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 6)

        dpg.bind_theme(global_theme)

        # Theme for selected channel
        with dpg.theme() as selected_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, Config.Colors.CHANNEL_ACTIVE)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, Config.Colors.CHANNEL_ACTIVE)
        self.tags["selected_theme"] = selected_theme

        # Theme for normal channel
        with dpg.theme() as normal_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, Config.Colors.FRAME_BG)
        self.tags["normal_theme"] = normal_theme

        # Main window
        with dpg.window(tag="main_window"):

            # Warning banner
            with dpg.group(tag="warning_banner_group", show=False) as banner:
                self.tags["warning_banner"] = banner
                dpg.add_text("", tag="warning_text_tag", color=Config.Colors.WARNING)
                self.tags["warning_text"] = "warning_text_tag"
                dpg.add_separator()

            # Header
            with dpg.group(horizontal=True):
                dpg.add_text("UGL AM Radio Control", color=Config.Colors.TEXT_PRIMARY)
                dpg.add_spacer(width=20)
                dpg.add_text(f"v{self.version_hash}", color=Config.Colors.TEXT_DIM)

            dpg.add_spacer(height=10)

            # === Connection Section ===
            dpg.add_text("CONNECTION", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="ip_input", default_value=Config.DEFAULT_IP, width=150)
                self.tags["ip_input"] = "ip_input"
                dpg.add_input_int(tag="port_input", default_value=Config.DEFAULT_PORT, width=100)
                self.tags["port_input"] = "port_input"
                dpg.add_button(tag="connect_btn", label="CONNECT", width=120, callback=lambda: self._on_connect_click())
                self.tags["connect_btn"] = "connect_btn"
                dpg.add_text("[DISCONNECTED]", tag="status_text", color=Config.Colors.DISCONNECTED)
                self.tags["status_text"] = "status_text"

            dpg.add_spacer(height=10)

            # === Watchdog Section ===
            with dpg.group(horizontal=True):
                dpg.add_text("WATCHDOG:", color=Config.Colors.TEXT_SECONDARY)
                dpg.add_text("[OK] (5s)", tag="watchdog_status", color=Config.Colors.WATCHDOG_OK)
                self.tags["watchdog_status"] = "watchdog_status"
                dpg.add_button(tag="watchdog_reset_btn", label="Reset", width=60, enabled=False, callback=lambda: self._on_watchdog_reset_click())
                self.tags["watchdog_reset_btn"] = "watchdog_reset_btn"

            dpg.add_spacer(height=10)

            # === Source Section ===
            with dpg.group(horizontal=True):
                dpg.add_text("SOURCE:", color=Config.Colors.TEXT_SECONDARY)
                dpg.add_checkbox(tag="source_toggle", label="BRAM", default_value=False, callback=self._on_source_change)
                self.tags["source_toggle"] = "source_toggle"
                dpg.add_combo(tag="message_select", items=[m["name"] for m in Config.MESSAGES], default_value=Config.MESSAGES[0]["name"], width=200, callback=self._on_message_change)
                self.tags["message_select"] = "message_select"

            dpg.add_spacer(height=15)

            # === Channel Selector (Clock Layout) ===
            dpg.add_text("CHANNEL SELECTOR (enable BRAM first)", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()

            # Clock positions for 12 channels (index 0-11, display 1-12)
            # Positions: 12=1, 1=2, 2=3, 3=4, 4=5, 5=6, 6=7, 7=8, 8=9, 9=10, 10=11, 11=12

            # Row 1: positions 11, 0, 1 (CH12, CH1, CH2)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=95)
                for idx in [11, 0, 1]:
                    ch_num = Config.CHANNELS[idx]["id"]
                    btn = dpg.add_button(label=f" {ch_num}", width=40, enabled=False, callback=self._on_channel_indicator_click, user_data=idx)
                    self.tags[f"ch_ind_{idx}"] = btn

            # Row 2: 10, space, 2 (CH11, CH3)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=55)
                btn = dpg.add_button(label=" 11", width=40, enabled=False, callback=self._on_channel_indicator_click, user_data=10)
                self.tags["ch_ind_10"] = btn
                dpg.add_spacer(width=100)
                btn = dpg.add_button(label=" 3", width=40, enabled=False, callback=self._on_channel_indicator_click, user_data=2)
                self.tags["ch_ind_2"] = btn

            # Row 3: 9, dial, 3 (CH10, CH4)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=35)
                btn = dpg.add_button(label=" 10", width=40, enabled=False, callback=self._on_channel_indicator_click, user_data=9)
                self.tags["ch_ind_9"] = btn
                dpg.add_spacer(width=15)
                btn_left = dpg.add_button(label="<", width=35, enabled=False, callback=lambda: self._on_dial_left())
                self.tags["dial_left"] = btn_left
                dpg.add_text("CH1", tag="channel_num", color=Config.Colors.TEXT_PRIMARY)
                self.tags["channel_num"] = "channel_num"
                btn_right = dpg.add_button(label=">", width=35, enabled=False, callback=lambda: self._on_dial_right())
                self.tags["dial_right"] = btn_right
                dpg.add_spacer(width=15)
                btn = dpg.add_button(label=" 4", width=40, enabled=False, callback=self._on_channel_indicator_click, user_data=3)
                self.tags["ch_ind_3"] = btn

            # Row 4: 8, space, 4 (CH9, CH5)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=55)
                btn = dpg.add_button(label=" 9", width=40, enabled=False, callback=self._on_channel_indicator_click, user_data=8)
                self.tags["ch_ind_8"] = btn
                dpg.add_spacer(width=100)
                btn = dpg.add_button(label=" 5", width=40, enabled=False, callback=self._on_channel_indicator_click, user_data=4)
                self.tags["ch_ind_4"] = btn
            
            # Row 5: 7, 6, 5 (CH8, CH7, CH6)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=95)
                for idx in [7, 6, 5]:
                    ch_num = Config.CHANNELS[idx]["id"]
                    btn = dpg.add_button(label=f" {ch_num}", width=40, enabled=False, callback=self._on_channel_indicator_click, user_data=idx)
                    self.tags[f"ch_ind_{idx}"] = btn

            with dpg.group(horizontal=True):
                dpg.add_spacer(width=120)
                dpg.add_text("Active: 0/12", tag="channel_count", color=Config.Colors.TEXT_DIM)
                self.tags["channel_count"] = "channel_count"

            dpg.add_spacer(height=10)

            # === Selected Channel Controls ===
            dpg.add_text("SELECTED CHANNEL", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()

            with dpg.child_window(height=100, border=True):
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(tag="ch_enable", label="Enable", default_value=False, enabled=False, callback=self._on_channel_enable)
                    self.tags["ch_enable"] = "ch_enable"
                    dpg.add_spacer(width=20)
                    dpg.add_text("[OFF]", tag="ch_status", color=Config.Colors.CHANNEL_DISABLED)
                    self.tags["ch_status"] = "ch_status"

                dpg.add_text("Frequency:", color=Config.Colors.TEXT_DIM)
                with dpg.group(horizontal=True):
                    dpg.add_slider_float(tag="ch_freq_slider", default_value=540, min_value=Config.FREQ_MIN/1000, max_value=Config.FREQ_MAX/1000, format="%.0f kHz", width=250, enabled=False, callback=self._on_freq_slider_change)
                    self.tags["ch_freq_slider"] = "ch_freq_slider"
                    dpg.add_input_float(tag="ch_freq_input", default_value=540, width=120, format="%.0f", enabled=False, callback=self._on_freq_input_change)
                    self.tags["ch_freq_input"] = "ch_freq_input"

            dpg.add_spacer(height=5)

            # Quick enable buttons
            with dpg.group(horizontal=True):
                dpg.add_text("Quick:", color=Config.Colors.TEXT_DIM)
                for n in [1, 2, 3, 4, 6, 8, 12]:
                    btn = dpg.add_button(label=str(n), width=28, enabled=False, callback=self._on_enable_n_channels, user_data=n)
                    self.tags[f"quick_{n}"] = btn
                btn = dpg.add_button(label="None", width=45, enabled=False, callback=lambda: self._on_disable_all_channels())
                self.tags["quick_none"] = btn

            dpg.add_spacer(height=10)

            # === Frequency Summary ===
            dpg.add_text("ALL CHANNELS SUMMARY", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()

            # Two-column summary (starts blank)
            dpg.add_input_text(tag="freq_summary", default_value="", multiline=True, readonly=True, width=-1, height=110)
            self.tags["freq_summary"] = "freq_summary"

            dpg.add_spacer(height=10)

            # === Broadcast Button ===
            dpg.add_button(tag="broadcast_btn", label="START BROADCAST", width=-1, height=50, enabled=False, callback=lambda: self._on_broadcast_click())
            self.tags["broadcast_btn"] = "broadcast_btn"

            dpg.add_spacer(height=10)

            # === Log ===
            dpg.add_text("LOG", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()
            dpg.add_input_text(tag="log_text", multiline=True, readonly=True, width=-1, height=80, default_value="System ready.\n")
            self.tags["log_text"] = "log_text"

        # Initialize
        self._update_channel_indicators()
        self._update_freq_summary()

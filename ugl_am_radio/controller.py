"""
Controller - UI Logic with Event Bus Integration (12-Channel Dial Version)
===========================================================================

v4 - Properly sized:
- Larger viewport (1200x900)
- All cards increased by ~15%
- Proper spacing throughout

Author: William Park
Date: January 2026
"""

import dearpygui.dearpygui as dpg
import subprocess
import os
from typing import Optional
from datetime import datetime

from config import Config
from model import Model, ConnectionState, BroadcastState, WatchdogState
from event_bus import EventBus, Event, EventType, event_bus


class Controller:
    """Controller with event bus integration and rotary channel selector."""

    # === Color Palette ===
    class Colors:
        WINDOW_BG = (18, 18, 22)
        PANEL_BG = (28, 28, 35)
        CARD_BG = (35, 35, 45)
        FRAME_BG = (45, 45, 55)

        TEXT_PRIMARY = (240, 240, 245)
        TEXT_SECONDARY = (160, 165, 180)
        TEXT_DIM = (100, 105, 120)

        GREEN_ACTIVE = (50, 205, 100)
        GREEN_DARK = (30, 80, 50)
        GREEN_HOVER = (40, 100, 60)

        AMBER_STANDBY = (255, 180, 50)
        AMBER_DARK = (80, 60, 20)

        RED_ERROR = (255, 80, 80)
        RED_DARK = (100, 30, 30)
        RED_HOVER = (120, 40, 40)

        BLUE_SELECTED = (70, 130, 220)
        BLUE_DARK = (35, 55, 90)

        CH_ENABLED = (50, 205, 100)
        CH_DISABLED = (80, 80, 90)

    def __init__(self, model: Model):
        self.model = model
        self.tags = {}
        self.version_hash = self._get_version_hash()
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
            dpg.configure_item(self.tags["status_text"], color=self.Colors.GREEN_ACTIVE)
            dpg.configure_item(self.tags["ip_input"], enabled=False)
            dpg.configure_item(self.tags["port_input"], enabled=False)
            dpg.configure_item(self.tags["broadcast_btn"], enabled=True)
        else:
            dpg.set_value(self.tags["connect_btn"], "CONNECT")
            dpg.set_value(self.tags["status_text"], "[DISCONNECTED]")
            dpg.configure_item(self.tags["status_text"], color=self.Colors.RED_ERROR)
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
            dpg.bind_item_theme(self.tags["broadcast_btn"], self.tags["broadcast_disabled_theme"])
            return

        if watchdog_triggered:
            dpg.set_value(self.tags["broadcast_btn"], "!! WATCHDOG TRIGGERED !!")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
            dpg.bind_item_theme(self.tags["broadcast_btn"], self.tags["broadcast_error_theme"])
            return

        if state == BroadcastState.BROADCASTING:
            dpg.set_value(self.tags["broadcast_btn"], ">>> LIVE <<< STOP")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=True)
            dpg.bind_item_theme(self.tags["broadcast_btn"], self.tags["broadcast_live_theme"])
        elif state == BroadcastState.ARMING:
            dpg.set_value(self.tags["broadcast_btn"], "ARMING...")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
            dpg.bind_item_theme(self.tags["broadcast_btn"], self.tags["broadcast_standby_theme"])
        elif state == BroadcastState.STOPPING:
            dpg.set_value(self.tags["broadcast_btn"], "STOPPING...")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
            dpg.bind_item_theme(self.tags["broadcast_btn"], self.tags["broadcast_standby_theme"])
        else:
            dpg.set_value(self.tags["broadcast_btn"], "START BROADCAST")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=True)
            dpg.bind_item_theme(self.tags["broadcast_btn"], self.tags["broadcast_ready_theme"])

    def _update_selected_channel_ui(self):
        if self.selected_channel_idx < len(self.model.device_state.channels):
            ch = self.model.device_state.channels[self.selected_channel_idx]
            ch_num = ch.id

            dpg.set_value(self.tags["channel_num"], f"CH{ch_num}")
            dpg.set_value(self.tags["ch_enable"], ch.enabled)
            dpg.set_value(self.tags["ch_freq_slider"], ch.frequency / 1000)
            dpg.set_value(self.tags["ch_freq_input"], ch.frequency / 1000)

            if ch.enabled:
                dpg.set_value(self.tags["ch_status"], f"[ON] {ch.frequency/1000:.0f} kHz")
                dpg.configure_item(self.tags["ch_status"], color=self.Colors.GREEN_ACTIVE)
            else:
                dpg.set_value(self.tags["ch_status"], "[OFF]")
                dpg.configure_item(self.tags["ch_status"], color=self.Colors.CH_DISABLED)

    def _update_channel_indicators(self):
        enabled_count = 0

        for idx in range(Config.NUM_CHANNELS):
            tag = f"ch_ind_{idx}"
            if tag in self.tags and idx < len(self.model.device_state.channels):
                ch = self.model.device_state.channels[idx]
                ch_num = ch.id

                if ch.enabled:
                    enabled_count += 1
                    freq_khz = int(ch.frequency / 1000)
                    dpg.configure_item(self.tags[tag], label=f"{ch_num}\n{freq_khz}")
                    dpg.bind_item_theme(self.tags[tag], self.tags["ch_enabled_theme"])
                else:
                    dpg.configure_item(self.tags[tag], label=f"{ch_num}")
                    dpg.bind_item_theme(self.tags[tag], self.tags["ch_disabled_theme"])

                if idx == self.selected_channel_idx:
                    dpg.bind_item_theme(self.tags[tag], self.tags["ch_selected_theme"])

        dpg.set_value(self.tags["channel_count"], f"Active: {enabled_count}/12")

        if enabled_count == 0:
            dpg.configure_item(self.tags["channel_count"], color=self.Colors.TEXT_DIM)
        elif enabled_count == 12:
            dpg.configure_item(self.tags["channel_count"], color=self.Colors.GREEN_ACTIVE)
        else:
            dpg.configure_item(self.tags["channel_count"], color=self.Colors.AMBER_STANDBY)

    def _update_freq_summary(self):
        for idx, ch in enumerate(self.model.device_state.channels):
            freq_tag = f"summary_freq_{idx}"
            status_tag = f"summary_status_{idx}"

            if freq_tag in self.tags:
                if ch.enabled:
                    freq_khz = ch.frequency / 1000
                    dpg.set_value(self.tags[freq_tag], f"{freq_khz:.0f} kHz")
                    dpg.configure_item(self.tags[freq_tag], color=self.Colors.TEXT_PRIMARY)
                    dpg.set_value(self.tags[status_tag], "ON")
                    dpg.configure_item(self.tags[status_tag], color=self.Colors.GREEN_ACTIVE)
                else:
                    dpg.set_value(self.tags[freq_tag], "---")
                    dpg.configure_item(self.tags[freq_tag], color=self.Colors.TEXT_DIM)
                    dpg.set_value(self.tags[status_tag], "--")
                    dpg.configure_item(self.tags[status_tag], color=self.Colors.CH_DISABLED)

    def _update_watchdog_ui(self):
        state = self.model.get_watchdog_state()
        time_remaining = self.model.device_state.watchdog_time_remaining

        if state == WatchdogState.OK:
            dpg.set_value(self.tags["watchdog_status"], f"OK ({time_remaining}s)")
            dpg.configure_item(self.tags["watchdog_status"], color=self.Colors.GREEN_ACTIVE)
            dpg.configure_item(self.tags["watchdog_reset_btn"], enabled=False)
        elif state == WatchdogState.WARNING:
            dpg.set_value(self.tags["watchdog_status"], f"WARN ({time_remaining}s)")
            dpg.configure_item(self.tags["watchdog_status"], color=self.Colors.AMBER_STANDBY)
            dpg.configure_item(self.tags["watchdog_reset_btn"], enabled=True)
        elif state == WatchdogState.TRIGGERED:
            dpg.set_value(self.tags["watchdog_status"], "TRIGGERED!")
            dpg.configure_item(self.tags["watchdog_status"], color=self.Colors.RED_ERROR)
            dpg.configure_item(self.tags["watchdog_reset_btn"], enabled=True)

    def _update_log(self):
        entries = self.model.get_log_entries(6)
        dpg.set_value(self.tags["log_text"], "\n".join(entries))

    def _show_warning_banner(self, message: str):
        dpg.set_value(self.tags["warning_text"], f"WARNING: {message}")
        dpg.configure_item(self.tags["warning_banner"], show=True)

    def _hide_warning_banner(self):
        dpg.configure_item(self.tags["warning_banner"], show=False)

    def _update_channel_selector_enabled(self):
        bram_enabled = dpg.get_value(self.tags["source_toggle"])

        for idx in range(Config.NUM_CHANNELS):
            tag = f"ch_ind_{idx}"
            if tag in self.tags:
                dpg.configure_item(self.tags[tag], enabled=bram_enabled)

        dpg.configure_item(self.tags["dial_left"], enabled=bram_enabled)
        dpg.configure_item(self.tags["dial_right"], enabled=bram_enabled)
        dpg.configure_item(self.tags["ch_enable"], enabled=bram_enabled)
        dpg.configure_item(self.tags["ch_freq_slider"], enabled=bram_enabled)
        dpg.configure_item(self.tags["ch_freq_input"], enabled=bram_enabled)

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
        self.selected_channel_idx = user_data
        self._update_selected_channel_ui()
        self._update_channel_indicators()

    def _on_channel_enable(self, sender, app_data, user_data):
        ch_id = self.model.device_state.channels[self.selected_channel_idx].id
        self.model.set_channel_enabled(ch_id, app_data)
        self.model.device_state.channels[self.selected_channel_idx].enabled = app_data
        self._update_selected_channel_ui()
        self._update_channel_indicators()
        self._update_freq_summary()

    def _on_freq_slider_change(self, sender, app_data, user_data):
        ch_id = self.model.device_state.channels[self.selected_channel_idx].id
        freq_hz = int(app_data * 1000)
        self.model.set_channel_frequency(ch_id, freq_hz)
        self.model.device_state.channels[self.selected_channel_idx].frequency = freq_hz
        dpg.set_value(self.tags["ch_freq_input"], app_data)
        self._update_channel_indicators()
        self._update_freq_summary()

    def _on_freq_input_change(self, sender, app_data, user_data):
        ch_id = self.model.device_state.channels[self.selected_channel_idx].id
        freq_hz = int(app_data * 1000)
        self.model.set_channel_frequency(ch_id, freq_hz)
        self.model.device_state.channels[self.selected_channel_idx].frequency = freq_hz
        dpg.set_value(self.tags["ch_freq_slider"], app_data)
        self._update_channel_indicators()
        self._update_freq_summary()

    def _on_enable_n_channels(self, sender, app_data, user_data):
        n = user_data
        for i, ch in enumerate(Config.CHANNELS):
            enabled = i < n
            self.model.set_channel_enabled(ch["id"], enabled)
            self.model.device_state.channels[i].enabled = enabled
        self._update_selected_channel_ui()
        self._update_channel_indicators()
        self._update_freq_summary()

    def _on_disable_all_channels(self):
        for i, ch in enumerate(Config.CHANNELS):
            self.model.set_channel_enabled(ch["id"], False)
            self.model.device_state.channels[i].enabled = False
        self._update_selected_channel_ui()
        self._update_channel_indicators()
        self._update_freq_summary()

    # =========================================================================
    # Build UI
    # =========================================================================

    def build_ui(self):
        """Build the complete UI."""

        # === FONT ===
        with dpg.font_registry():
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/SFNS.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            font_loaded = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        default_font = dpg.add_font(font_path, 18)
                        font_loaded = True
                        print(f"[Font] Loaded: {font_path} @ 18px")
                        break
                    except:
                        continue

            if not font_loaded:
                print("[Font] Using default font")
                default_font = None

        if font_loaded and default_font:
            dpg.bind_font(default_font)

        # === THEMES ===
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, self.Colors.WINDOW_BG)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, self.Colors.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (55, 55, 70))
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.Colors.TEXT_PRIMARY)
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.Colors.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (60, 60, 75))
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, self.Colors.PANEL_BG)
                dpg.add_theme_color(dpg.mvThemeCol_Border, (50, 50, 65))
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 8)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12, 10)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
        dpg.bind_theme(global_theme)

        # Channel themes
        with dpg.theme() as ch_selected_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.Colors.BLUE_DARK)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (45, 65, 110))
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.Colors.BLUE_SELECTED)
        self.tags["ch_selected_theme"] = ch_selected_theme

        with dpg.theme() as ch_enabled_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.Colors.GREEN_DARK)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, self.Colors.GREEN_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.Colors.GREEN_ACTIVE)
        self.tags["ch_enabled_theme"] = ch_enabled_theme

        with dpg.theme() as ch_disabled_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.Colors.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.Colors.TEXT_DIM)
        self.tags["ch_disabled_theme"] = ch_disabled_theme

        # Broadcast themes
        with dpg.theme() as broadcast_ready_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.Colors.GREEN_DARK)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, self.Colors.GREEN_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.Colors.GREEN_ACTIVE)
        self.tags["broadcast_ready_theme"] = broadcast_ready_theme

        with dpg.theme() as broadcast_live_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (20, 140, 60))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (25, 160, 70))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
        self.tags["broadcast_live_theme"] = broadcast_live_theme

        with dpg.theme() as broadcast_standby_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.Colors.AMBER_DARK)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (90, 70, 25))
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.Colors.AMBER_STANDBY)
        self.tags["broadcast_standby_theme"] = broadcast_standby_theme

        with dpg.theme() as broadcast_error_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.Colors.RED_DARK)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, self.Colors.RED_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.Colors.RED_ERROR)
        self.tags["broadcast_error_theme"] = broadcast_error_theme

        with dpg.theme() as broadcast_disabled_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (35, 35, 40))
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.Colors.TEXT_DIM)
        self.tags["broadcast_disabled_theme"] = broadcast_disabled_theme

        with dpg.theme() as card_theme:
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, self.Colors.CARD_BG)
                dpg.add_theme_color(dpg.mvThemeCol_Border, (55, 55, 70))
        self.tags["card_theme"] = card_theme

        # === MAIN WINDOW ===
        with dpg.window(tag="main_window"):

            # Warning banner
            with dpg.group(tag="warning_banner_group", show=False) as banner:
                self.tags["warning_banner"] = banner
                dpg.add_text("", tag="warning_text_tag", color=self.Colors.AMBER_STANDBY)
                self.tags["warning_text"] = "warning_text_tag"
                dpg.add_spacer(height=8)

            # Header
            with dpg.group(horizontal=True):
                dpg.add_text("UGL AM Radio Control", color=self.Colors.TEXT_PRIMARY)
                dpg.add_spacer(width=30)
                dpg.add_text(f"v{self.version_hash}", color=self.Colors.TEXT_DIM)

            dpg.add_spacer(height=10)

            # === CONNECTION CARD ===
            with dpg.child_window(height=95, border=True, no_scrollbar=True) as conn_card:
                dpg.bind_item_theme(conn_card, self.tags["card_theme"])

                with dpg.group(horizontal=True):
                    dpg.add_text("CONNECTION", color=self.Colors.TEXT_SECONDARY)
                    dpg.add_spacer(width=40)
                    dpg.add_text("[DISCONNECTED]", tag="status_text", color=self.Colors.RED_ERROR)
                    self.tags["status_text"] = "status_text"

                dpg.add_spacer(height=12)

                with dpg.group(horizontal=True):
                    dpg.add_input_text(tag="ip_input", default_value=Config.DEFAULT_IP, width=160)
                    self.tags["ip_input"] = "ip_input"
                    dpg.add_input_int(tag="port_input", default_value=Config.DEFAULT_PORT, width=100, step=0)
                    self.tags["port_input"] = "port_input"
                    dpg.add_button(tag="connect_btn", label="CONNECT", width=130, callback=lambda: self._on_connect_click())
                    self.tags["connect_btn"] = "connect_btn"
                    dpg.add_spacer(width=40)
                    dpg.add_text("WATCHDOG:", color=self.Colors.TEXT_SECONDARY)
                    dpg.add_text("OK (5s)", tag="watchdog_status", color=self.Colors.GREEN_ACTIVE)
                    self.tags["watchdog_status"] = "watchdog_status"
                    dpg.add_button(tag="watchdog_reset_btn", label="Reset", width=80, enabled=False, callback=lambda: self._on_watchdog_reset_click())
                    self.tags["watchdog_reset_btn"] = "watchdog_reset_btn"

            dpg.add_spacer(height=10)

            # === SOURCE CARD ===
            with dpg.child_window(height=55, border=True, no_scrollbar=True) as source_card:
                dpg.bind_item_theme(source_card, self.tags["card_theme"])

                with dpg.group(horizontal=True):
                    dpg.add_text("SOURCE:", color=self.Colors.TEXT_SECONDARY)
                    dpg.add_checkbox(tag="source_toggle", label="BRAM", default_value=False, callback=self._on_source_change)
                    self.tags["source_toggle"] = "source_toggle"
                    dpg.add_spacer(width=15)
                    dpg.add_combo(tag="message_select", items=[m["name"] for m in Config.MESSAGES], default_value=Config.MESSAGES[0]["name"], width=220, callback=self._on_message_change)
                    self.tags["message_select"] = "message_select"
                    dpg.add_spacer(width=40)
                    dpg.add_text("Quick:", color=self.Colors.TEXT_DIM)
                    for n in [1, 2, 3, 4, 6, 8, 12]:
                        btn = dpg.add_button(label=str(n), width=40, enabled=False, callback=self._on_enable_n_channels, user_data=n)
                        self.tags[f"quick_{n}"] = btn
                    btn = dpg.add_button(label="None", width=60, enabled=False, callback=lambda: self._on_disable_all_channels())
                    self.tags["quick_none"] = btn

            dpg.add_spacer(height=10)

            # === MAIN CONTROL AREA ===
            with dpg.group(horizontal=True):

                # LEFT: Channel Selector
                with dpg.child_window(width=340, height=330, border=True, no_scrollbar=True) as ch_card:
                    dpg.bind_item_theme(ch_card, self.tags["card_theme"])

                    with dpg.group(horizontal=True):
                        dpg.add_text("CHANNELS", color=self.Colors.TEXT_SECONDARY)
                        dpg.add_spacer(width=100)
                        dpg.add_text("Active: 0/12", tag="channel_count", color=self.Colors.TEXT_DIM)
                        self.tags["channel_count"] = "channel_count"

                    dpg.add_spacer(height=10)

                    # Clock layout - Row 1: 12, 1, 2
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=80)
                        for idx in [11, 0, 1]:
                            ch_num = Config.CHANNELS[idx]["id"]
                            btn = dpg.add_button(label=f"{ch_num}", width=55, height=42, enabled=False, callback=self._on_channel_indicator_click, user_data=idx)
                            self.tags[f"ch_ind_{idx}"] = btn

                    # Row 2: 11, 3
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=35)
                        btn = dpg.add_button(label="11", width=55, height=42, enabled=False, callback=self._on_channel_indicator_click, user_data=10)
                        self.tags["ch_ind_10"] = btn
                        dpg.add_spacer(width=115)
                        btn = dpg.add_button(label="3", width=55, height=42, enabled=False, callback=self._on_channel_indicator_click, user_data=2)
                        self.tags["ch_ind_2"] = btn

                    # Row 3: 10, dial, 4
                    with dpg.group(horizontal=True):
                        btn = dpg.add_button(label="10", width=55, height=42, enabled=False, callback=self._on_channel_indicator_click, user_data=9)
                        self.tags["ch_ind_9"] = btn
                        dpg.add_spacer(width=15)
                        btn_left = dpg.add_button(label="<", width=40, enabled=False, callback=lambda: self._on_dial_left())
                        self.tags["dial_left"] = btn_left
                        dpg.add_text("CH1", tag="channel_num", color=self.Colors.BLUE_SELECTED)
                        self.tags["channel_num"] = "channel_num"
                        btn_right = dpg.add_button(label=">", width=40, enabled=False, callback=lambda: self._on_dial_right())
                        self.tags["dial_right"] = btn_right
                        dpg.add_spacer(width=15)
                        btn = dpg.add_button(label="4", width=55, height=42, enabled=False, callback=self._on_channel_indicator_click, user_data=3)
                        self.tags["ch_ind_3"] = btn

                    # Row 4: 9, 5
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=35)
                        btn = dpg.add_button(label="9", width=55, height=42, enabled=False, callback=self._on_channel_indicator_click, user_data=8)
                        self.tags["ch_ind_8"] = btn
                        dpg.add_spacer(width=115)
                        btn = dpg.add_button(label="5", width=55, height=42, enabled=False, callback=self._on_channel_indicator_click, user_data=4)
                        self.tags["ch_ind_4"] = btn

                    # Row 5: 8, 7, 6
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=80)
                        for idx in [7, 6, 5]:
                            ch_num = Config.CHANNELS[idx]["id"]
                            btn = dpg.add_button(label=f"{ch_num}", width=55, height=42, enabled=False, callback=self._on_channel_indicator_click, user_data=idx)
                            self.tags[f"ch_ind_{idx}"] = btn

                dpg.add_spacer(width=12)

                # MIDDLE: Broadcast Control
                with dpg.child_window(width=300, height=330, border=True, no_scrollbar=True) as bc_card:
                    dpg.bind_item_theme(bc_card, self.tags["card_theme"])

                    dpg.add_text("BROADCAST CONTROL", color=self.Colors.TEXT_SECONDARY)
                    dpg.add_spacer(height=15)

                    dpg.add_button(
                        tag="broadcast_btn",
                        label="START BROADCAST",
                        width=-1,
                        height=250,
                        enabled=False,
                        callback=lambda: self._on_broadcast_click()
                    )
                    self.tags["broadcast_btn"] = "broadcast_btn"
                    dpg.bind_item_theme("broadcast_btn", self.tags["broadcast_disabled_theme"])

                dpg.add_spacer(width=12)

                # RIGHT: Selected Channel
                with dpg.child_window(width=-1, height=330, border=True, no_scrollbar=True) as sel_card:
                    dpg.bind_item_theme(sel_card, self.tags["card_theme"])

                    with dpg.group(horizontal=True):
                        dpg.add_text("SELECTED CHANNEL", color=self.Colors.TEXT_SECONDARY)
                        dpg.add_spacer(width=40)
                        dpg.add_text("[OFF]", tag="ch_status", color=self.Colors.CH_DISABLED)
                        self.tags["ch_status"] = "ch_status"

                    dpg.add_spacer(height=20)

                    dpg.add_checkbox(tag="ch_enable", label="Enable Channel", default_value=False, enabled=False, callback=self._on_channel_enable)
                    self.tags["ch_enable"] = "ch_enable"

                    dpg.add_spacer(height=25)
                    dpg.add_text("Frequency:", color=self.Colors.TEXT_DIM)
                    dpg.add_spacer(height=8)

                    dpg.add_slider_float(tag="ch_freq_slider", default_value=540, min_value=Config.FREQ_MIN/1000, max_value=Config.FREQ_MAX/1000, format="%.0f kHz", width=-1, enabled=False, callback=self._on_freq_slider_change)
                    self.tags["ch_freq_slider"] = "ch_freq_slider"

                    dpg.add_spacer(height=15)
                    with dpg.group(horizontal=True):
                        dpg.add_input_float(tag="ch_freq_input", default_value=540, width=140, format="%.0f", enabled=False, callback=self._on_freq_input_change)
                        self.tags["ch_freq_input"] = "ch_freq_input"
                        dpg.add_text("kHz", color=self.Colors.TEXT_DIM)

            dpg.add_spacer(height=10)

            # === BOTTOM ROW: Summary + Log (fills remaining space) ===
            with dpg.group(horizontal=True):

                # LEFT: Channel Summary Grid
                with dpg.child_window(width=650, height=-1, border=True, no_scrollbar=True) as sum_card:
                    dpg.bind_item_theme(sum_card, self.tags["card_theme"])

                    dpg.add_text("ALL CHANNELS", color=self.Colors.TEXT_SECONDARY)
                    dpg.add_spacer(height=15)

                    # Row 1: CH1-6
                    with dpg.group(horizontal=True):
                        for idx in range(6):
                            ch_num = idx + 1
                            with dpg.group():
                                with dpg.group(horizontal=True):
                                    dpg.add_text(f"CH{ch_num}", color=self.Colors.TEXT_SECONDARY)
                                    dpg.add_text("--", tag=f"summary_status_{idx}", color=self.Colors.CH_DISABLED)
                                    self.tags[f"summary_status_{idx}"] = f"summary_status_{idx}"
                                dpg.add_text("---", tag=f"summary_freq_{idx}", color=self.Colors.TEXT_DIM)
                                self.tags[f"summary_freq_{idx}"] = f"summary_freq_{idx}"
                            dpg.add_spacer(width=30)

                    dpg.add_spacer(height=20)

                    # Row 2: CH7-12
                    with dpg.group(horizontal=True):
                        for idx in range(6, 12):
                            ch_num = idx + 1
                            with dpg.group():
                                with dpg.group(horizontal=True):
                                    dpg.add_text(f"CH{ch_num}", color=self.Colors.TEXT_SECONDARY)
                                    dpg.add_text("--", tag=f"summary_status_{idx}", color=self.Colors.CH_DISABLED)
                                    self.tags[f"summary_status_{idx}"] = f"summary_status_{idx}"
                                dpg.add_text("---", tag=f"summary_freq_{idx}", color=self.Colors.TEXT_DIM)
                                self.tags[f"summary_freq_{idx}"] = f"summary_freq_{idx}"
                            dpg.add_spacer(width=30)

                dpg.add_spacer(width=12)

                # RIGHT: Log
                with dpg.child_window(width=-1, height=-1, border=True, no_scrollbar=True) as log_card:
                    dpg.bind_item_theme(log_card, self.tags["card_theme"])

                    dpg.add_text("LOG", color=self.Colors.TEXT_SECONDARY)
                    dpg.add_spacer(height=10)
                    dpg.add_input_text(tag="log_text", multiline=True, readonly=True, width=-1, height=-1, default_value="System ready.\n")
                    self.tags["log_text"] = "log_text"

        # Initialize
        self._update_channel_indicators()
        self._update_freq_summary()
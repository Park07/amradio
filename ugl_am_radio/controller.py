"""
Controller - UI Logic with Event Bus Integration
=================================================

- Stateless UI: Only updates from device state, never assumes
- Event Bus: Subscribes to events instead of direct callbacks
- Intermediate States: Shows "CONNECTING...", "ARMING..." etc.
- Stale Warning: Shows banner when device state is uncertain
- Watchdog Status: Shows fail-safe state prominently

Author: [William Park]
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
    """
    Controller with event bus integration.

    Reddit advice (kubrador, 5 upvotes):
    "Throw an event bus in there so hardware state changes and UI events
    talk through a neutral medium."
    """

    def __init__(self, model: Model):
        self.model = model

        # UI element tags
        self.tags = {}

        # Get version hash for display
        self.version_hash = self._get_version_hash()

        # Subscribe to events
        self._subscribe_to_events()

    def _get_version_hash(self) -> str:
        """Get git commit hash for version display."""
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
        """Subscribe to all relevant events."""
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
        """Handle successful connection."""
        self._update_connection_ui(True)
        self._hide_warning_banner()
        self._update_log()

    def _on_connect_failed(self, event: Event):
        """Handle failed connection."""
        self._update_connection_ui(False)
        reason = event.data.get("reason", "Unknown error")
        self._show_warning_banner(f"Connection failed: {reason}")
        self._update_log()

    def _on_disconnected(self, event: Event):
        """Handle disconnection."""
        self._update_connection_ui(False)
        self._update_broadcast_ui()
        self._update_log()

    def _on_reconnect_attempt(self, event: Event):
        """Handle reconnection attempt."""
        attempt = event.data.get("attempt", 0)
        max_attempts = Config.MAX_RECONNECT_ATTEMPTS
        self._show_warning_banner(f"Reconnecting... ({attempt}/{max_attempts})")
        dpg.set_value(self.tags["connect_btn"], "RECONNECTING...")
        self._update_log()

    def _on_state_updated(self, event: Event):
        """Handle device state update from polling."""
        self._update_broadcast_ui()
        self._update_channel_ui()
        self._update_watchdog_ui()
        self._update_log()

        # Clear stale warning if we got fresh data
        if not self.model.device_state.stale:
            if not self.model.device_state.watchdog_triggered:
                self._hide_warning_banner()

    def _on_heartbeat_lost(self, event: Event):
        """Handle heartbeat loss - show stale data warning."""
        self._show_warning_banner("⚠️ STALE DATA - Device not responding")

    def _on_broadcast_arming(self, event: Event):
        """Handle broadcast arming state."""
        dpg.set_value(self.tags["broadcast_btn"], "⏳ ARMING...")
        dpg.configure_item(self.tags["broadcast_btn"],
                          enabled=False)
        self._update_log()

    def _on_broadcast_started(self, event: Event):
        """Handle broadcast started (confirmed from device)."""
        self._update_broadcast_ui()
        self._update_log()

    def _on_broadcast_stopped(self, event: Event):
        """Handle broadcast stopped (confirmed from device)."""
        self._update_broadcast_ui()
        self._update_log()

    def _on_watchdog_warning(self, event: Event):
        """Handle watchdog warning (80% of timeout)."""
        self._show_warning_banner("⚠️ WATCHDOG WARNING - Heartbeat delayed")
        self._update_watchdog_ui()

    def _on_watchdog_triggered(self, event: Event):
        """Handle watchdog trigger - CRITICAL SAFETY EVENT."""
        self._show_warning_banner("🚨 FAIL-SAFE ACTIVATED - RF output disabled!")
        self._update_broadcast_ui()
        self._update_watchdog_ui()
        self._update_log()

    def _on_watchdog_reset(self, event: Event):
        """Handle watchdog reset."""
        self._hide_warning_banner()
        self._update_watchdog_ui()
        self._update_log()

    def _on_error(self, event: Event):
        """Handle error events."""
        message = event.data.get("message", "Unknown error")
        self._show_warning_banner(f"❌ {message}")
        self._update_log()

    # =========================================================================
    # UI Update Methods
    # =========================================================================

    def _update_connection_ui(self, connected: bool):
        """Update connection-related UI elements."""
        if connected:
            dpg.set_value(self.tags["connect_btn"], "DISCONNECT")
            dpg.set_value(self.tags["status_text"], "● CONNECTED")
            dpg.configure_item(self.tags["status_text"],
                             color=Config.Colors.CONNECTED)
            dpg.configure_item(self.tags["ip_input"], enabled=False)
            dpg.configure_item(self.tags["port_input"], enabled=False)
            dpg.configure_item(self.tags["broadcast_btn"], enabled=True)
        else:
            dpg.set_value(self.tags["connect_btn"], "CONNECT")
            dpg.set_value(self.tags["status_text"], "○ DISCONNECTED")
            dpg.configure_item(self.tags["status_text"],
                             color=Config.Colors.DISCONNECTED)
            dpg.configure_item(self.tags["ip_input"], enabled=True)
            dpg.configure_item(self.tags["port_input"], enabled=True)
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
            dpg.set_value(self.tags["broadcast_btn"], "START BROADCAST")

    def _update_broadcast_ui(self):
        """Update broadcast button based on device state."""
        state = self.model.get_broadcast_state()
        connected = self.model.is_connected()
        watchdog_triggered = self.model.is_watchdog_triggered()

        if not connected:
            dpg.set_value(self.tags["broadcast_btn"], "START BROADCAST")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
            return

        if watchdog_triggered:
            dpg.set_value(self.tags["broadcast_btn"], "🚨 WATCHDOG TRIGGERED")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
            return

        if state == BroadcastState.BROADCASTING:
            dpg.set_value(self.tags["broadcast_btn"], "🔴 STOP BROADCAST")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=True)
        elif state == BroadcastState.ARMING:
            dpg.set_value(self.tags["broadcast_btn"], "⏳ ARMING...")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
        elif state == BroadcastState.STOPPING:
            dpg.set_value(self.tags["broadcast_btn"], "⏳ STOPPING...")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=False)
        else:
            dpg.set_value(self.tags["broadcast_btn"], "START BROADCAST")
            dpg.configure_item(self.tags["broadcast_btn"], enabled=True)

    def _update_channel_ui(self):
        """Update channel displays from device state."""
        for ch in self.model.device_state.channels:
            freq_tag = self.tags.get(f"ch{ch.id}_freq")
            enable_tag = self.tags.get(f"ch{ch.id}_enable")
            status_tag = self.tags.get(f"ch{ch.id}_status")

            if freq_tag:
                dpg.set_value(freq_tag, ch.frequency / 1000)  # Hz to kHz

            if enable_tag:
                dpg.set_value(enable_tag, ch.enabled)

            if status_tag:
                if ch.confirmed:
                    status = "✓" if ch.enabled else "○"
                else:
                    status = "⏳"
                dpg.set_value(status_tag, status)

    def _update_watchdog_ui(self):
        """Update watchdog status display."""
        state = self.model.get_watchdog_state()
        time_remaining = self.model.device_state.watchdog_time_remaining

        watchdog_tag = self.tags.get("watchdog_status")
        if not watchdog_tag:
            return

        if state == WatchdogState.TRIGGERED:
            dpg.set_value(watchdog_tag, "🚨 TRIGGERED - Reset Required")
            dpg.configure_item(watchdog_tag, color=Config.Colors.WATCHDOG_TRIGGERED)
            dpg.configure_item(self.tags["watchdog_reset_btn"], enabled=True)
        elif state == WatchdogState.WARNING:
            dpg.set_value(watchdog_tag, f"⚠️ WARNING ({time_remaining}s)")
            dpg.configure_item(watchdog_tag, color=Config.Colors.WATCHDOG_WARNING)
            dpg.configure_item(self.tags["watchdog_reset_btn"], enabled=False)
        else:
            dpg.set_value(watchdog_tag, f"● OK ({time_remaining}s)")
            dpg.configure_item(watchdog_tag, color=Config.Colors.WATCHDOG_OK)
            dpg.configure_item(self.tags["watchdog_reset_btn"], enabled=False)

    def _update_log(self):
        """Update log display."""
        log_tag = self.tags.get("log_text")
        if not log_tag:
            return

        entries = self.model.get_log_entries(15)
        log_text = "\n".join(entries[-15:])  # Most recent at bottom
        dpg.set_value(log_tag, log_text)

    def _show_warning_banner(self, message: str):
        """Show warning banner at top of window."""
        banner_tag = self.tags.get("warning_banner")
        banner_text_tag = self.tags.get("warning_text")
        if banner_tag and banner_text_tag:
            dpg.set_value(banner_text_tag, message)
            dpg.show_item(banner_tag)

    def _hide_warning_banner(self):
        """Hide warning banner."""
        banner_tag = self.tags.get("warning_banner")
        if banner_tag:
            dpg.hide_item(banner_tag)

    # =========================================================================
    # UI Callbacks
    # =========================================================================

    def _on_connect_click(self):
        """Handle connect/disconnect button click."""
        if self.model.is_connected():
            self.model.disconnect()
        else:
            ip = dpg.get_value(self.tags["ip_input"])
            port = dpg.get_value(self.tags["port_input"])

            dpg.set_value(self.tags["connect_btn"], "CONNECTING...")
            dpg.configure_item(self.tags["connect_btn"], enabled=False)

            self.model.connect(ip, int(port))

            # Re-enable button after short delay (connection is async)
            dpg.configure_item(self.tags["connect_btn"], enabled=True)

    def _on_broadcast_click(self):
        """Handle broadcast button click."""
        if self.model.is_broadcasting():
            self.model.set_broadcast(False)
        else:
            self.model.set_broadcast(True)

    def _on_source_change(self, sender, app_data):
        """Handle source selection change."""
        source = Config.SOURCE_BRAM if app_data else Config.SOURCE_ADC
        self.model.set_source(source)

    def _on_message_change(self, sender, app_data):
        """Handle message selection change."""
        # Find message ID from name
        for msg in Config.MESSAGES:
            if msg["name"] == app_data:
                self.model.set_message(msg["id"])
                break

    def _on_freq_change(self, sender, app_data, user_data):
        """Handle frequency slider OR input change."""
        channel_id = user_data
        frequency = int(app_data * 1000)  # kHz to Hz
        self.model.set_channel_frequency(channel_id, frequency)

        # Sync slider and input field
        slider_tag = f"ch{channel_id}_freq"
        input_tag = f"ch{channel_id}_freq_input"

        # Update whichever one WASN'T changed
        if sender == slider_tag:
            dpg.set_value(input_tag, app_data)
        else:
            dpg.set_value(slider_tag, app_data)
    def _on_channel_enable(self, sender, app_data, user_data):
        """Handle channel enable checkbox."""
        channel_id = user_data
        self.model.set_channel_enabled(channel_id, app_data)

    def _on_watchdog_reset_click(self):
        """Handle watchdog reset button click."""
        self.model.reset_watchdog()

    # =========================================================================
    # Build UI
    # =========================================================================

    def build_ui(self):
        """Build the complete UI."""


        # Theme
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, Config.Colors.WINDOW_BG)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, Config.Colors.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, Config.Colors.FRAME_BG_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_Text, Config.Colors.TEXT_PRIMARY)
                dpg.add_theme_color(dpg.mvThemeCol_Button, Config.Colors.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, Config.Colors.BTN_HOVER)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 8)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12, 8)

        dpg.bind_theme(global_theme)

        # Main window
        with dpg.window(tag="main_window"):

            # Warning banner (hidden by default)
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

            # Connection section
            dpg.add_text("CONNECTION", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag="ip_input",
                    default_value=Config.DEFAULT_IP,
                    width=180,
                    hint="IP Address"
                )
                self.tags["ip_input"] = "ip_input"

                dpg.add_input_int(
                    tag="port_input",
                    default_value=Config.DEFAULT_PORT,
                    width=130,
                    min_value=1,
                    max_value=65535
                )
                self.tags["port_input"] = "port_input"

            with dpg.group(horizontal=True):
                dpg.add_button(
                    tag="connect_btn",
                    label="CONNECT",
                    width=150,
                    callback=lambda: self._on_connect_click()
                )
                self.tags["connect_btn"] = "connect_btn"

                dpg.add_text(
                    "○ DISCONNECTED",
                    tag="status_text",
                    color=Config.Colors.DISCONNECTED
                )
                self.tags["status_text"] = "status_text"

            dpg.add_spacer(height=15)

            # Watchdog section
            dpg.add_text("FAIL-SAFE WATCHDOG", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_text(
                    "● OK (5s)",
                    tag="watchdog_status",
                    color=Config.Colors.WATCHDOG_OK
                )
                self.tags["watchdog_status"] = "watchdog_status"

                dpg.add_spacer(width=20)

                dpg.add_button(
                    tag="watchdog_reset_btn",
                    label="Reset Watchdog",
                    width=120,
                    enabled=False,
                    callback=lambda: self._on_watchdog_reset_click()
                )
                self.tags["watchdog_reset_btn"] = "watchdog_reset_btn"

            dpg.add_spacer(height=15)

            # Source section
            dpg.add_text("AUDIO SOURCE", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_checkbox(
                    tag="source_toggle",
                    label="Use Pre-recorded (BRAM)",
                    default_value=False,
                    callback=self._on_source_change
                )
                self.tags["source_toggle"] = "source_toggle"

            # Message selection (only for BRAM)
            dpg.add_combo(
                tag="message_select",
                items=[m["name"] for m in Config.MESSAGES],
                default_value=Config.MESSAGES[0]["name"],
                width=300,
                callback=self._on_message_change
            )
            self.tags["message_select"] = "message_select"

            dpg.add_spacer(height=15)

            # Channels section
            dpg.add_text("CHANNELS", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()

            for ch in Config.CHANNELS:
                ch_id = ch["id"]
                default_freq = ch["default_freq"] / 1000  # Hz to kHz

                with dpg.group():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(
                            tag=f"ch{ch_id}_enable",
                            label=f"CH{ch_id}",
                            default_value=False,
                            callback=self._on_channel_enable,
                            user_data=ch_id
                        )
                        self.tags[f"ch{ch_id}_enable"] = f"ch{ch_id}_enable"

                        dpg.add_text("", tag=f"ch{ch_id}_status", color=Config.Colors.TEXT_DIM)
                        self.tags[f"ch{ch_id}_status"] = f"ch{ch_id}_status"

                    with dpg.group(horizontal=True):
                        dpg.add_slider_float(
                            tag=f"ch{ch_id}_freq",
                            default_value=default_freq,
                            min_value=Config.FREQ_MIN / 1000,
                            max_value=Config.FREQ_MAX / 1000,
                            format="%.0f kHz",
                            width=300,
                            callback=self._on_freq_change,
                            user_data=ch_id
                        )
                        self.tags[f"ch{ch_id}_freq"] = f"ch{ch_id}_freq"

                        dpg.add_input_float(
                            tag=f"ch{ch_id}_freq_input",
                            default_value=default_freq,
                            width=130,
                            format="%.0f",
                            callback=self._on_freq_change,
                            user_data=ch_id
                        )

                dpg.add_spacer(height=5)

            dpg.add_spacer(height=15)

            # Broadcast button
            dpg.add_button(
                tag="broadcast_btn",
                label="START BROADCAST",
                width=-1,
                height=60,
                enabled=False,
                callback=lambda: self._on_broadcast_click()
            )
            self.tags["broadcast_btn"] = "broadcast_btn"

            dpg.add_spacer(height=15)

            # Log section
            dpg.add_text("AUDIT LOG", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_separator()

            dpg.add_input_text(
                tag="log_text",
                multiline=True,
                readonly=True,
                width=-1,
                height=200,
                default_value="System ready.\n"
            )
            self.tags["log_text"] = "log_text"

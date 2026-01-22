"""
Controller layer for UGL AM Radio Control System.
Handles UI construction, event binding, and view updates.

FIXES APPLIED:
- Broadcast button disabled when disconnected
- Dynamic button label: "Connect to Broadcast" → "Start Broadcast" → "Stop Broadcast"
- Channel controls greyed out when channel disabled
"""

import dearpygui.dearpygui as dpg
from typing import Optional
from config import Config
from model import Model, AppState


class Controller:
    """
    Controller class - builds UI, handles events, updates view.
    """

    def __init__(self, model: Model):
        self.model = model

        # Subscribe to model changes
        self.model.add_state_listener(self._on_state_change)
        self.model.logger.add_listener(self._on_log_message)

        # Track log entries
        self.log_entries = []

    # =========================================================================
    # THEMES
    # =========================================================================

    def _create_themes(self):
        """Create all UI themes."""
        C = Config.Colors

        # Main dark theme
        with dpg.theme(tag="main_theme"):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, C.WINDOW_BG)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, C.PANEL_BG)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, C.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, C.FRAME_BG_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, C.FRAME_BG_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_Button, C.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C.BTN_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, C.BTN_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_Text, C.TEXT_PRIMARY)
                dpg.add_theme_color(dpg.mvThemeCol_Border, [255, 255, 255, 25])
                dpg.add_theme_color(dpg.mvThemeCol_Separator, [255, 255, 255, 20])
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, C.CONNECTED)
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, C.CHANNEL_ACTIVE)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 8)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 8)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 20, 20)

        # Broadcast button - disabled (grey)
        with dpg.theme(tag="broadcast_disabled"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, C.BROADCAST_DISABLED)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C.BROADCAST_DISABLED)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, C.BROADCAST_DISABLED)
                dpg.add_theme_color(dpg.mvThemeCol_Text, C.TEXT_DISABLED)

        # Broadcast button - idle/ready (green)
        with dpg.theme(tag="broadcast_idle"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, C.BROADCAST_IDLE)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C.BROADCAST_IDLE_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [20, 140, 60, 255])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 255])

        # Broadcast button - active/broadcasting (red)
        with dpg.theme(tag="broadcast_active"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, C.BROADCAST_ACTIVE)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C.BROADCAST_ACTIVE_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [160, 25, 25, 255])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 255])

        # Connect button
        with dpg.theme(tag="connect_btn_theme"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [34, 197, 94, 50])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [34, 197, 94, 80])
                dpg.add_theme_color(dpg.mvThemeCol_Text, C.CONNECTED_DIM)
                dpg.add_theme_color(dpg.mvThemeCol_Border, [34, 197, 94, 100])

        # Disconnect button
        with dpg.theme(tag="disconnect_btn_theme"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [239, 68, 68, 50])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [239, 68, 68, 80])
                dpg.add_theme_color(dpg.mvThemeCol_Text, C.DISCONNECTED_DIM)
                dpg.add_theme_color(dpg.mvThemeCol_Border, [239, 68, 68, 100])

        # Status connected
        with dpg.theme(tag="status_connected"):
            with dpg.theme_component(dpg.mvText):
                dpg.add_theme_color(dpg.mvThemeCol_Text, C.CONNECTED_DIM)

        # Status disconnected
        with dpg.theme(tag="status_disconnected"):
            with dpg.theme_component(dpg.mvText):
                dpg.add_theme_color(dpg.mvThemeCol_Text, C.DISCONNECTED_DIM)

        # Channel enabled theme
        with dpg.theme(tag="channel_on"):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [59, 130, 246, 20])
                dpg.add_theme_color(dpg.mvThemeCol_Border, [59, 130, 246, 75])
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, C.CHANNEL_ACTIVE)

        # Channel disabled theme (greyed out)
        with dpg.theme(tag="channel_off"):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [30, 30, 35, 255])
                dpg.add_theme_color(dpg.mvThemeCol_Border, [50, 50, 55, 255])
                dpg.add_theme_color(dpg.mvThemeCol_Text, C.TEXT_DIM)

    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================

    def build_ui(self):
        """Build the complete UI."""
        self._create_themes()

        with dpg.window(tag="main_window", label=""):

            # Header with status
            self._build_header()

            dpg.add_spacer(height=8)
            dpg.add_separator()
            dpg.add_spacer(height=16)

            # Connection section
            self._build_connection_section()
            dpg.add_spacer(height=20)

            # Audio source section
            self._build_source_section()
            dpg.add_spacer(height=20)

            # Channels section
            self._build_channels_section()
            dpg.add_spacer(height=24)

            # Broadcast button
            self._build_broadcast_section()
            dpg.add_spacer(height=16)

            # Status bar
            self._build_status_bar()
            dpg.add_spacer(height=16)

            # Log section
            self._build_log_section()

        # Confirmation popup
        self._build_confirm_popup()

        # Apply main theme
        dpg.bind_theme("main_theme")

    def _build_header(self):
        """Build header with title and status badge."""
        with dpg.group(horizontal=True):
            # Status indicator dot
            dpg.add_text("*", tag="status_dot", color=Config.Colors.DISCONNECTED)
            dpg.add_spacer(width=8)

            # Title
            dpg.add_text("UGL AM RADIO CONTROL", color=[255, 255, 255, 255])

            dpg.add_spacer(width=20)

            # Status badge
            dpg.add_text("DISCONNECTED", tag="status_badge")
            dpg.bind_item_theme("status_badge", "status_disconnected")

    def _build_connection_section(self):
        """Build connection controls."""
        dpg.add_text("CONNECTION", color=Config.Colors.TEXT_DIM)
        dpg.add_spacer(height=8)

        with dpg.group(horizontal=True):
            # IP Address
            with dpg.group():
                dpg.add_text("IP ADDRESS", color=Config.Colors.TEXT_DIM)
                dpg.add_spacer(height=4)
                dpg.add_input_text(
                    tag="ip_input", default_value=Config.DEFAULT_IP, width=150, no_spaces=True
                )

            dpg.add_spacer(width=16)

            # Port
            with dpg.group():
                dpg.add_text("PORT", color=Config.Colors.TEXT_DIM)
                dpg.add_spacer(height=4)
                dpg.add_input_int(
                    tag="port_input",
                    default_value=Config.DEFAULT_PORT,
                    width=100,
                    min_value=1,
                    max_value=65535,
                    step=0,  # Remove stepper arrows
                )

            dpg.add_spacer(width=20)

            # Connect button
            with dpg.group():
                dpg.add_text(" ", color=Config.Colors.TEXT_DIM)
                dpg.add_spacer(height=4)
                dpg.add_button(
                    tag="connect_btn", label="Connect", callback=self._on_connect_click, width=100
                )
                dpg.bind_item_theme("connect_btn", "connect_btn_theme")

    def _build_source_section(self):
        """Build audio source selection."""
        dpg.add_text("AUDIO SOURCE", color=Config.Colors.TEXT_DIM)
        dpg.add_spacer(height=8)

        dpg.add_radio_button(
            tag="source_radio",
            items=["Live Mic (ADC)", "Stored Message (BRAM)"],
            default_value="Stored Message (BRAM)",
            horizontal=True,
            callback=self._on_source_change,
        )

        dpg.add_spacer(height=4)
        dpg.add_text(
            "ADC = PA Console analog input  |  BRAM = Pre-loaded audio",
            color=Config.Colors.TEXT_DIM,
        )

        dpg.add_spacer(height=12)

        # Message selector
        with dpg.group(tag="msg_group"):
            with dpg.child_window(height=70, border=True):
                dpg.add_spacer(height=8)
                dpg.add_text("SELECT MESSAGE", color=Config.Colors.TEXT_DIM)
                dpg.add_spacer(height=6)
                msg_names = [m["name"] for m in Config.MESSAGES]
                dpg.add_combo(
                    tag="msg_combo",
                    items=msg_names,
                    default_value=msg_names[0],
                    width=-1,
                    callback=self._on_message_change,
                )

    def _build_channels_section(self):
        """Build channel controls."""
        dpg.add_text("BROADCAST CHANNELS", color=Config.Colors.TEXT_DIM)
        dpg.add_spacer(height=8)

        for ch_config in Config.CHANNELS:
            ch_id = ch_config["id"]
            default_freq = ch_config["default_freq"]

            with dpg.child_window(tag=f"ch{ch_id}_panel", height=50, border=True):
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=8)

                    # Enable checkbox
                    dpg.add_checkbox(
                        tag=f"ch{ch_id}_enable",
                        label="",
                        callback=self._on_channel_toggle,
                        user_data=ch_id,
                    )

                    dpg.add_spacer(width=8)

                    # Channel label
                    dpg.add_text(f"CH{ch_id}", tag=f"ch{ch_id}_label", color=Config.Colors.TEXT_DIM)

                    dpg.add_spacer(width=20)

                    # Frequency input
                    dpg.add_input_int(
                        tag=f"ch{ch_id}_freq",
                        default_value=int(default_freq / 1000),
                        width=80,
                        min_value=int(Config.FREQ_MIN / 1000),
                        max_value=int(Config.FREQ_MAX / 1000),
                        callback=self._on_freq_change,
                        user_data=ch_id,
                        step=0,  # Remove stepper
                    )

                    dpg.add_text("kHz", tag=f"ch{ch_id}_khz", color=Config.Colors.TEXT_SECONDARY)

                    dpg.add_spacer(width=20)

                    # Status indicator
                    dpg.add_text("OFF", tag=f"ch{ch_id}_status", color=Config.Colors.TEXT_DIM)

            dpg.add_spacer(height=8)

    def _build_broadcast_section(self):
        """Build broadcast button."""
        # Button starts disabled until connected
        dpg.add_button(
            tag="broadcast_btn",
            label="Connect to Broadcast",
            width=-1,
            height=60,
            callback=self._on_broadcast_click,
            enabled=False,  # Disabled until connected
        )
        dpg.bind_item_theme("broadcast_btn", "broadcast_disabled")

    def _build_status_bar(self):
        """Build status bar showing current state in plain English."""
        with dpg.group(horizontal=True):
            dpg.add_text("Status:", color=Config.Colors.TEXT_DIM)
            dpg.add_spacer(width=8)
            dpg.add_text(
                "Disconnected - Connect to Red Pitaya to enable broadcast",
                tag="status_bar_text",
                color=Config.Colors.TEXT_SECONDARY,
            )

    def _build_log_section(self):
        """Build log display."""
        dpg.add_text("SYSTEM LOG", color=Config.Colors.TEXT_DIM)
        dpg.add_spacer(height=8)

        with dpg.child_window(tag="log_window", height=140, border=True):
            dpg.add_text("System ready.", tag="log_text", color=Config.Colors.LOG_INFO, wrap=460)

    def _build_confirm_popup(self):
        """Build confirmation popup for broadcast."""
        with dpg.window(
            tag="confirm_popup",
            label="Confirm Broadcast",
            modal=True,
            show=False,
            no_title_bar=False,
            width=380,
            height=220,
            pos=[70, 240],
        ):
            dpg.add_spacer(height=10)
            dpg.add_text("WARNING: You are about to broadcast", color=Config.Colors.WARNING)
            dpg.add_spacer(height=12)

            dpg.add_text("Message:", color=Config.Colors.TEXT_SECONDARY)
            dpg.add_text("", tag="confirm_message", color=Config.Colors.WARNING)

            dpg.add_spacer(height=8)
            dpg.add_text("", tag="confirm_channels", color=Config.Colors.TEXT_DIM)

            dpg.add_spacer(height=20)

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Cancel",
                    width=140,
                    callback=lambda: dpg.configure_item("confirm_popup", show=False),
                )
                dpg.add_spacer(width=20)
                dpg.add_button(
                    tag="confirm_btn",
                    label="Confirm & Broadcast",
                    width=160,
                    callback=self._on_confirm_broadcast,
                )
                dpg.bind_item_theme("confirm_btn", "broadcast_active")

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _on_connect_click(self):
        """Handle connect/disconnect button click."""
        if self.model.is_connected():
            self.model.disconnect()
        else:
            ip = dpg.get_value("ip_input")
            port = dpg.get_value("port_input")
            self.model.connect(ip, port)

    def _on_source_change(self, sender, app_data):
        """Handle audio source radio button change."""
        if "ADC" in app_data:
            self.model.set_source(Config.SOURCE_ADC)
        else:
            self.model.set_source(Config.SOURCE_BRAM)

    def _on_message_change(self, sender, app_data):
        """Handle message dropdown change."""
        for msg in Config.MESSAGES:
            if msg["name"] == app_data:
                self.model.set_message(msg["id"])
                break

    def _on_channel_toggle(self, sender, app_data, user_data):
        """Handle channel enable checkbox."""
        channel_id = user_data
        enabled = app_data
        self.model.set_channel_enabled(channel_id, enabled)

    def _on_freq_change(self, sender, app_data, user_data):
        """Handle frequency input change."""
        channel_id = user_data
        freq_hz = int(app_data * 1000)
        self.model.set_channel_frequency(channel_id, freq_hz)

    def _on_broadcast_click(self):
        """Handle broadcast button click."""
        if not self.model.is_connected():
            return  # Safety check

        if self.model.is_broadcasting():
            # Stop immediately
            self.model.set_broadcast(False)
        else:
            # Show confirmation popup
            msg_name = dpg.get_value("msg_combo")
            dpg.set_value("confirm_message", msg_name)

            # Show active channels
            active_chs = []
            for ch in self.model.state.channels:
                if ch.enabled:
                    active_chs.append(f"{ch.frequency // 1000} kHz")
            ch_text = "Active channels: " + (", ".join(active_chs) if active_chs else "None")
            dpg.set_value("confirm_channels", ch_text)

            dpg.configure_item("confirm_popup", show=True)

    def _on_confirm_broadcast(self):
        """Handle confirmed broadcast."""
        dpg.configure_item("confirm_popup", show=False)
        self.model.set_broadcast(True)

    # =========================================================================
    # VIEW UPDATES (Observer callbacks)
    # =========================================================================

    def _on_state_change(self, state: AppState):
        """Update UI when model state changes."""
        C = Config.Colors

        # === CONNECTION STATUS ===
        if state.connected:
            dpg.configure_item("status_dot", color=C.CONNECTED)
            dpg.set_value("status_badge", "CONNECTED")
            dpg.bind_item_theme("status_badge", "status_connected")
            dpg.configure_item("connect_btn", label="Disconnect")
            dpg.bind_item_theme("connect_btn", "disconnect_btn_theme")
        else:
            dpg.configure_item("status_dot", color=C.DISCONNECTED)
            dpg.set_value("status_badge", "DISCONNECTED")
            dpg.bind_item_theme("status_badge", "status_disconnected")
            dpg.configure_item("connect_btn", label="Connect")
            dpg.bind_item_theme("connect_btn", "connect_btn_theme")

        # === SOURCE SELECTION ===
        is_bram = state.source == Config.SOURCE_BRAM
        dpg.configure_item("msg_group", show=is_bram)

        # === CHANNEL STATUS ===
        for ch in state.channels:
            panel_tag = f"ch{ch.id}_panel"
            label_tag = f"ch{ch.id}_label"
            freq_tag = f"ch{ch.id}_freq"
            khz_tag = f"ch{ch.id}_khz"
            status_tag = f"ch{ch.id}_status"

            if ch.enabled:
                # Channel ON - highlight
                dpg.set_value(status_tag, "ON")
                dpg.configure_item(status_tag, color=C.CONNECTED)
                dpg.configure_item(label_tag, color=[255, 255, 255, 255])
                dpg.configure_item(khz_tag, color=C.TEXT_PRIMARY)
                dpg.configure_item(freq_tag, enabled=True)
                dpg.bind_item_theme(panel_tag, "channel_on")
            else:
                # Channel OFF - grey out
                dpg.set_value(status_tag, "OFF")
                dpg.configure_item(status_tag, color=C.TEXT_DIM)
                dpg.configure_item(label_tag, color=C.TEXT_DIM)
                dpg.configure_item(khz_tag, color=C.TEXT_DIM)
                dpg.configure_item(freq_tag, enabled=False)
                dpg.bind_item_theme(panel_tag, "channel_off")

        # === BROADCAST BUTTON - Dynamic label + enabled state ===
        if not state.connected:
            # Disconnected: disabled, grey
            dpg.configure_item("broadcast_btn", label="Connect to Broadcast", enabled=False)
            dpg.bind_item_theme("broadcast_btn", "broadcast_disabled")
            dpg.set_value(
                "status_bar_text", "Disconnected - Connect to Red Pitaya to enable broadcast"
            )
            dpg.configure_item("status_bar_text", color=C.TEXT_SECONDARY)
        elif state.broadcasting:
            # Broadcasting: enabled, red, STOP label
            dpg.configure_item("broadcast_btn", label="STOP BROADCAST", enabled=True)
            dpg.bind_item_theme("broadcast_btn", "broadcast_active")
            dpg.set_value("status_bar_text", "BROADCASTING - RF output is ACTIVE")
            dpg.configure_item("status_bar_text", color=C.BROADCAST_ACTIVE)
        else:
            # Connected but not broadcasting: enabled, green, START label
            dpg.configure_item("broadcast_btn", label="Start Broadcast", enabled=True)
            dpg.bind_item_theme("broadcast_btn", "broadcast_idle")
            dpg.set_value("status_bar_text", "Ready - Click Start Broadcast when ready")
            dpg.configure_item("status_bar_text", color=C.CONNECTED)

    def _on_log_message(self, message: str):
        """Append message to log display."""
        if not dpg.does_item_exist("log_text"):
            return

        self.log_entries.append(message)
        if len(self.log_entries) > Config.LOG_MAX_LINES:
            self.log_entries = self.log_entries[-Config.LOG_MAX_LINES :]

        # Show last 15 entries
        display_text = "\n".join(self.log_entries[-15:])
        dpg.set_value("log_text", display_text)

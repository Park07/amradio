"""
Controller layer for UGL AM Radio Control System.
Handles UI construction, event binding, and view updates.
"""

import dearpygui.dearpygui as dpg
from typing import Optional
from config import Config
from model import Model, AppState


class Controller:
    """
    Controller class - builds UI, handles events, updates view.
    Bridges Model and DearPyGui view layer.
    """
    
    def __init__(self, model: Model):
        self.model = model
        
        # Subscribe to model changes
        self.model.add_state_listener(self._on_state_change)
        self.model.logger.add_listener(self._on_log_message)
        
        # UI element tags
        self.tags = {
            "main_window": "main_window",
            "ip_input": "ip_input",
            "port_input": "port_input",
            "connect_btn": "connect_btn",
            "status_text": "status_text",
            "source_radio": "source_radio",
            "msg_group": "msg_group",
            "msg_combo": "msg_combo",
            "broadcast_btn": "broadcast_btn",
            "log_text": "log_text",
        }
    
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
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, C.FRAME_BG)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, C.FRAME_BG_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_Button, C.BTN_NORMAL)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C.BTN_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, C.BTN_ACTIVE)
                dpg.add_theme_color(dpg.mvThemeCol_Text, C.TEXT_PRIMARY)
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, C.STATUS_OK)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
        
        # Broadcast button - idle (green)
        with dpg.theme(tag="broadcast_idle"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, C.BROADCAST_IDLE)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C.BROADCAST_IDLE_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [60, 180, 60, 255])
        
        # Broadcast button - active (red pulsing)
        with dpg.theme(tag="broadcast_active"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, C.BROADCAST_ACTIVE)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C.BROADCAST_ACTIVE_HOVER)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [230, 60, 60, 255])
        
        # Section header text
        with dpg.theme(tag="header_theme"):
            with dpg.theme_component(dpg.mvText):
                dpg.add_theme_color(dpg.mvThemeCol_Text, C.TEXT_HEADER)
    
    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================
    
    def build_ui(self):
        """Build the complete UI."""
        self._create_themes()
        
        with dpg.window(tag=self.tags["main_window"], label=Config.WINDOW_TITLE):
            self._build_connection_section()
            dpg.add_spacer(height=10)
            self._build_source_section()
            dpg.add_spacer(height=10)
            self._build_channels_section()
            dpg.add_spacer(height=15)
            self._build_broadcast_section()
            dpg.add_spacer(height=10)
            self._build_log_section()
        
        # Apply main theme
        dpg.bind_theme("main_theme")
    
    def _build_connection_section(self):
        """Build connection controls."""
        self._section_header("CONNECTION")
        
        with dpg.group(horizontal=True):
            dpg.add_input_text(
                tag=self.tags["ip_input"],
                label="IP",
                default_value=Config.DEFAULT_IP,
                width=130
            )
            dpg.add_input_int(
                tag=self.tags["port_input"],
                label="Port",
                default_value=Config.DEFAULT_PORT,
                width=80,
                min_value=1,
                max_value=65535
            )
            dpg.add_button(
                tag=self.tags["connect_btn"],
                label="Connect",
                callback=self._on_connect_click,
                width=80
            )
        
        with dpg.group(horizontal=True):
            dpg.add_text("Status:")
            dpg.add_text(
                tag=self.tags["status_text"],
                default_value="Disconnected",
                color=Config.Colors.STATUS_ERROR
            )
    
    def _build_source_section(self):
        """Build audio source selection."""
        self._section_header("AUDIO SOURCE")
        
        dpg.add_radio_button(
            tag=self.tags["source_radio"],
            items=["Live Mic (ADC)", "Stored Message (BRAM)"],
            default_value="Stored Message (BRAM)",
            horizontal=True,
            callback=self._on_source_change
        )
        
        dpg.add_text(
            "ADC = PA Console analog input  |  BRAM = Pre-loaded audio",
            color=Config.Colors.TEXT_SECONDARY
        )
        
        # Message selector (shown only when BRAM selected)
        with dpg.group(tag=self.tags["msg_group"]):
            dpg.add_spacer(height=5)
            msg_names = [m["name"] for m in Config.MESSAGES]
            dpg.add_combo(
                tag=self.tags["msg_combo"],
                items=msg_names,
                default_value=msg_names[0],
                label="Message",
                width=200,
                callback=self._on_message_change
            )
    
    def _build_channels_section(self):
        """Build channel controls."""
        self._section_header("CHANNELS")
        
        for ch_config in Config.CHANNELS:
            ch_id = ch_config["id"]
            ch_name = ch_config["name"]
            default_freq = ch_config["default_freq"]
            
            with dpg.group(horizontal=True):
                dpg.add_checkbox(
                    tag=f"ch{ch_id}_enable",
                    label=ch_name,
                    callback=self._on_channel_toggle,
                    user_data=ch_id
                )
                dpg.add_input_float(
                    tag=f"ch{ch_id}_freq",
                    label="kHz",
                    default_value=default_freq / 1000,
                    width=100,
                    format="%.0f",
                    min_value=Config.FREQ_MIN / 1000,
                    max_value=Config.FREQ_MAX / 1000,
                    callback=self._on_freq_change,
                    user_data=ch_id
                )
                dpg.add_text(
                    tag=f"ch{ch_id}_status",
                    default_value="●",
                    color=Config.Colors.CHANNEL_OFF
                )
    
    def _build_broadcast_section(self):
        """Build broadcast button."""
        dpg.add_button(
            tag=self.tags["broadcast_btn"],
            label="● BROADCAST",
            width=-1,
            height=60,
            callback=self._on_broadcast_click
        )
        dpg.bind_item_theme(self.tags["broadcast_btn"], "broadcast_idle")
    
    def _build_log_section(self):
        """Build log display."""
        self._section_header("LOG")
        
        dpg.add_input_text(
            tag=self.tags["log_text"],
            multiline=True,
            readonly=True,
            default_value="System ready.\n",
            width=-1,
            height=130,
            tab_input=False
        )
    
    def _section_header(self, title: str):
        """Add a section header with separator."""
        dpg.add_text(title, color=Config.Colors.TEXT_HEADER)
        dpg.add_separator()
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _on_connect_click(self):
        """Handle connect/disconnect button click."""
        if self.model.is_connected():
            self.model.disconnect()
        else:
            ip = dpg.get_value(self.tags["ip_input"])
            port = dpg.get_value(self.tags["port_input"])
            self.model.connect(ip, port)
    
    def _on_source_change(self, sender, app_data):
        """Handle audio source radio button change."""
        if "ADC" in app_data:
            self.model.set_source(Config.SOURCE_ADC)
        else:
            self.model.set_source(Config.SOURCE_BRAM)
    
    def _on_message_change(self, sender, app_data):
        """Handle message dropdown change."""
        # Find message ID by name
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
        freq_hz = int(app_data * 1000)  # Convert kHz to Hz
        self.model.set_channel_frequency(channel_id, freq_hz)
    
    def _on_broadcast_click(self):
        """Handle broadcast button click."""
        self.model.toggle_broadcast()
    
    # =========================================================================
    # VIEW UPDATES (Observer callbacks)
    # =========================================================================
    
    def _on_state_change(self, state: AppState):
        """Update UI when model state changes."""
        # Connection status
        if state.connected:
            dpg.configure_item(self.tags["connect_btn"], label="Disconnect")
            dpg.configure_item(
                self.tags["status_text"],
                default_value="Connected",
                color=Config.Colors.STATUS_OK
            )
        else:
            dpg.configure_item(self.tags["connect_btn"], label="Connect")
            dpg.configure_item(
                self.tags["status_text"],
                default_value="Disconnected",
                color=Config.Colors.STATUS_ERROR
            )
        
        # Source selection - show/hide message dropdown
        is_bram = state.source == Config.SOURCE_BRAM
        dpg.configure_item(self.tags["msg_group"], show=is_bram)
        
        # Channel status indicators
        for ch in state.channels:
            status_tag = f"ch{ch.id}_status"
            if dpg.does_item_exist(status_tag):
                color = Config.Colors.CHANNEL_ON if ch.enabled else Config.Colors.CHANNEL_OFF
                dpg.configure_item(status_tag, color=color)
        
        # Broadcast button
        if state.broadcasting:
            dpg.configure_item(self.tags["broadcast_btn"], label="■ STOP BROADCAST")
            dpg.bind_item_theme(self.tags["broadcast_btn"], "broadcast_active")
        else:
            dpg.configure_item(self.tags["broadcast_btn"], label="● BROADCAST")
            dpg.bind_item_theme(self.tags["broadcast_btn"], "broadcast_idle")
    
    def _on_log_message(self, message: str):
        """Append message to log display."""
        if not dpg.does_item_exist(self.tags["log_text"]):
            return
        
        current = dpg.get_value(self.tags["log_text"])
        lines = current.split("\n")
        
        # Keep last N lines
        if len(lines) > Config.LOG_MAX_LINES:
            lines = lines[-Config.LOG_MAX_LINES:]
        
        lines.append(message)
        dpg.set_value(self.tags["log_text"], "\n".join(lines))
        
        # Auto-scroll to bottom (by setting cursor to end)
        # Note: DearPyGui doesn't have direct scroll control for input_text

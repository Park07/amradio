"""
UGL Tunnel AM Break-In System
View Components

Separated view classes for each UI section.
"""

from __future__ import annotations
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

import dearpygui.dearpygui as dpg

from .configs import Colors, CHANNELS, MESSAGES
from .tags import Tag, ChannelTags

if TYPE_CHECKING:
    from .themes import ThemeCollection


class ChannelView:
    """View for a single RF channel panel."""
    
    def __init__(self, parent: MainView, channel_id: int):
        self._parent = parent
        self._channel_id = channel_id
        self._tags = ChannelTags(parent.tag)
    
    @property
    def tag(self) -> Tag:
        return self._parent.tag
    
    @property
    def themes(self) -> ThemeCollection:
        return self._parent.themes
    
    def update_level(self, level: float) -> None:
        """Update RF level bar."""
        tag = self._tags.get(self._channel_id, 'level_bar')
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, level)
    
    def set_status(self, status: str) -> None:
        """Set channel status text and color."""
        tag = self._tags.get(self._channel_id, 'status')
        if not dpg.does_item_exist(tag):
            return
        
        status_config = {
            "transmitting": ("🟢 TRANSMITTING", Colors.STATUS_OK),
            "standby": ("🟡 STANDBY", Colors.STATUS_WARN),
            "disabled": ("⚫ DISABLED", Colors.STATUS_OFF),
            "error": ("🔴 ERROR", Colors.STATUS_ERROR),
        }
        
        text, color = status_config.get(status, ("UNKNOWN", Colors.STATUS_OFF))
        dpg.set_value(tag, text)
        dpg.configure_item(tag, color=color)
    
    def set_active(self, active: bool) -> None:
        """Set channel panel active/inactive theme."""
        panel_tag = self._tags.get(self._channel_id, 'panel')
        if dpg.does_item_exist(panel_tag):
            theme = self.themes.channel_active if active else self.themes.channel_inactive
            dpg.bind_item_theme(panel_tag, theme)
    
    def is_enabled(self) -> bool:
        """Check if channel checkbox is enabled."""
        tag = self._tags.get(self._channel_id, 'checkbox')
        if dpg.does_item_exist(tag):
            return dpg.get_value(tag)
        return True


class SpectrumView:
    """View for spectrum analyzer display."""
    
    def __init__(self, parent: MainView):
        self._parent = parent
    
    @property
    def tag(self) -> Tag:
        return self._parent.tag
    
    def update(self, x_data: list, y_data: list) -> None:
        """Update spectrum plot data."""
        if dpg.does_item_exist(self.tag.spectrum_series):
            dpg.set_value(self.tag.spectrum_series, [x_data, y_data])


class AudioView:
    """View for audio display."""
    
    def __init__(self, parent: MainView):
        self._parent = parent
    
    @property
    def tag(self) -> Tag:
        return self._parent.tag
    
    def update_waveform(self, samples: list) -> None:
        """Update audio waveform plot."""
        if dpg.does_item_exist(self.tag.audio_series):
            x_data = list(range(len(samples)))
            dpg.set_value(self.tag.audio_series, [x_data, list(samples)])
    
    def update_level(self, level: float) -> None:
        """Update audio level bar."""
        if dpg.does_item_exist(self.tag.audio_level_bar):
            dpg.set_value(self.tag.audio_level_bar, level)


class LogView:
    """View for system log display."""
    
    def __init__(self, parent: MainView):
        self._parent = parent
    
    @property
    def tag(self) -> Tag:
        return self._parent.tag
    
    def update(self, log_text: str) -> None:
        """Update log display text."""
        if dpg.does_item_exist(self.tag.log_text):
            dpg.set_value(self.tag.log_text, log_text)


class MainView:
    """
    Main view coordinator.
    Contains all sub-views and theme references.
    """
    
    def __init__(self, tags: Tag = None, themes: ThemeCollection = None):
        self.tag = tags or Tag()
        self.themes: Optional[ThemeCollection] = themes
        
        # Sub-views
        self.channels = [ChannelView(self, ch.id) for ch in CHANNELS]
        self.spectrum = SpectrumView(self)
        self.audio = AudioView(self)
        self.log = LogView(self)
        
        # UI Builder reference (set during build)
        self.ui = None
    
    def set_themes(self, themes: ThemeCollection) -> None:
        """Set theme collection after creation."""
        self.themes = themes
    
    # =========================================================================
    # HEADER
    # =========================================================================
    
    def set_status(self, text: str, broadcasting: bool = False) -> None:
        """Set main status text."""
        if dpg.does_item_exist(self.tag.status_text):
            dpg.set_value(self.tag.status_text, text)
            color = Colors.STATUS_ERROR if broadcasting else Colors.STATUS_OK
            dpg.configure_item(self.tag.status_text, color=color)
    
    def set_clock(self, time_str: str) -> None:
        """Set system clock display."""
        if dpg.does_item_exist(self.tag.system_clock):
            dpg.set_value(self.tag.system_clock, time_str)
    
    def set_broadcast_timer(self, text: str) -> None:
        """Set broadcast duration timer."""
        if dpg.does_item_exist(self.tag.broadcast_timer):
            dpg.set_value(self.tag.broadcast_timer, text)
    
    # =========================================================================
    # CONNECTION
    # =========================================================================
    
    def get_ip_address(self) -> str:
        """Get IP address from input field."""
        if dpg.does_item_exist(self.tag.ip_input):
            return dpg.get_value(self.tag.ip_input)
        return ""
    
    def set_connection_status(self, connected: bool, ip: str = "") -> None:
        """Set connection status display."""
        if dpg.does_item_exist(self.tag.connection_status):
            if connected:
                text = f"🟢 Connected: {ip}"
                color = Colors.STATUS_OK
            else:
                text = "🔴 Disconnected"
                color = Colors.STATUS_ERROR
            dpg.set_value(self.tag.connection_status, text)
            dpg.configure_item(self.tag.connection_status, color=color)
    
    # =========================================================================
    # BROADCAST BUTTON
    # =========================================================================
    
    def set_broadcast_button_state(self, broadcasting: bool) -> None:
        """Update broadcast button appearance."""
        if not dpg.does_item_exist(self.tag.broadcast_btn):
            return
        
        if broadcasting:
            dpg.configure_item(self.tag.broadcast_btn, label="⬛  STOP BROADCAST  ⬛")
            dpg.bind_item_theme(self.tag.broadcast_btn, self.themes.stop_button)
        else:
            dpg.configure_item(self.tag.broadcast_btn, label="🔴  EMERGENCY BROADCAST  🔴")
            dpg.bind_item_theme(self.tag.broadcast_btn, self.themes.emergency_button)
    
    def set_broadcast_callback(self, callback: Callable) -> None:
        """Set broadcast button callback."""
        if dpg.does_item_exist(self.tag.broadcast_btn):
            dpg.configure_item(self.tag.broadcast_btn, callback=callback)
    
    # =========================================================================
    # MESSAGE SELECTION
    # =========================================================================
    
    def get_selected_message(self) -> str:
        """Get selected message ID from radio buttons."""
        if dpg.does_item_exist(self.tag.message_radio):
            selected_name = dpg.get_value(self.tag.message_radio)
            # Map name back to ID
            for msg in MESSAGES:
                if msg.name in selected_name or selected_name in msg.name:
                    return msg.id
        return "test"
    
    def set_message_callback(self, callback: Callable) -> None:
        """Set message selection callback."""
        if dpg.does_item_exist(self.tag.message_radio):
            dpg.configure_item(self.tag.message_radio, callback=callback)
    
    # =========================================================================
    # CALLBACKS
    # =========================================================================
    
    def set_connect_callback(self, callback: Callable) -> None:
        """Set connect button callback."""
        if dpg.does_item_exist(self.tag.connect_btn):
            dpg.configure_item(self.tag.connect_btn, callback=callback)
    
    def set_channel_callback(self, channel_id: int, callback: Callable) -> None:
        """Set channel checkbox callback."""
        tags = ChannelTags(self.tag)
        checkbox_tag = tags.get(channel_id, 'checkbox')
        if dpg.does_item_exist(checkbox_tag):
            dpg.configure_item(checkbox_tag, callback=callback, user_data=channel_id)
    
    # =========================================================================
    # DIALOGS
    # =========================================================================
    
    def popup_error(self, title: str, message: str) -> None:
        """Show error popup dialog."""
        with dpg.mutex():
            viewport_width = dpg.get_viewport_client_width()
            viewport_height = dpg.get_viewport_client_height()
            
            with dpg.window(
                label="ERROR",
                modal=True,
                no_close=True,
                no_resize=True,
            ) as modal_id:
                dpg.add_text(title, color=Colors.STATUS_ERROR)
                dpg.add_separator()
                dpg.add_spacer(height=10)
                dpg.add_text(message, wrap=400)
                dpg.add_spacer(height=10)
                dpg.add_button(
                    label="Close",
                    width=-1,
                    height=30,
                    callback=lambda: dpg.delete_item(modal_id)
                )
        
        dpg.split_frame()
        width = dpg.get_item_width(modal_id)
        height = dpg.get_item_height(modal_id)
        dpg.set_item_pos(modal_id, [
            viewport_width // 2 - width // 2,
            viewport_height // 2 - height // 2
        ])
    
    def popup_confirm(
        self,
        title: str,
        message: str,
        on_confirm: Callable,
        on_cancel: Callable = None
    ) -> None:
        """Show confirmation popup dialog."""
        with dpg.mutex():
            viewport_width = dpg.get_viewport_client_width()
            viewport_height = dpg.get_viewport_client_height()
            
            def confirm_callback():
                dpg.delete_item(modal_id)
                on_confirm()
            
            def cancel_callback():
                dpg.delete_item(modal_id)
                if on_cancel:
                    on_cancel()
            
            with dpg.window(
                label="CONFIRM",
                modal=True,
                no_close=True,
                no_resize=True,
            ) as modal_id:
                dpg.add_text(title, color=Colors.STATUS_WARN)
                dpg.add_separator()
                dpg.add_spacer(height=10)
                dpg.add_text(message, wrap=400)
                dpg.add_spacer(height=15)
                
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="✓ Confirm",
                        width=150,
                        height=35,
                        callback=confirm_callback
                    )
                    dpg.add_button(
                        label="Cancel",
                        width=100,
                        height=35,
                        callback=cancel_callback
                    )
        
        dpg.split_frame()
        width = dpg.get_item_width(modal_id)
        height = dpg.get_item_height(modal_id)
        dpg.set_item_pos(modal_id, [
            viewport_width // 2 - width // 2,
            viewport_height // 2 - height // 2
        ])
    
    # =========================================================================
    # RESIZE
    # =========================================================================
    
    def resize(self) -> None:
        """Handle viewport resize."""
        # Update any dynamic sizing here
        pass

"""
UGL Tunnel AM Break-In System
UI Builder

Constructs all UI components using DearPyGui.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass

import dearpygui.dearpygui as dpg

from .configs import (
    APP_TITLE, APP_VERSION, Colors, Display,
    CHANNELS, MESSAGES
)
from .tags import Tag

if TYPE_CHECKING:
    from .views import MainView
    from .themes import ThemeCollection


@dataclass
class Font:
    """Font collection."""
    default: int
    large: int
    mono: int


class UIBuilder:
    """
    Builds the entire UI structure.
    Separated from view logic for maintainability.
    """
    
    def __init__(self, parent: MainView):
        self._parent = parent
        self.font: Font = None
    
    @property
    def tag(self) -> Tag:
        return self._parent.tag
    
    @property
    def themes(self) -> ThemeCollection:
        return self._parent.themes
    
    def build(self) -> int:
        """Build and return the main window."""
        self._create_fonts()
        
        with dpg.window(tag=self.tag.main_window) as window:
            self._create_header()
            self._create_body()
        
        return window
    
    def _create_fonts(self) -> None:
        """Create and register fonts."""
        # DearPyGui uses built-in fonts when none specified
        # We'll use the default fonts by not specifying custom ones
        self.font = Font(
            default=None,  # Use DPG default
            large=None,
            mono=None,
        )
        # Font binding not needed - DPG uses default
    
    def _create_header(self) -> None:
        """Create header bar with status indicators."""
        with dpg.group(horizontal=True, tag=self.tag.header_group):
            # Title
            dpg.add_text(f"⚡ {APP_TITLE}", color=Colors.TEXT_ACCENT)
            
            dpg.add_spacer(width=30)
            
            # Status LEDs
            self._create_status_leds()
            
            dpg.add_spacer(width=30)
            
            # Main Status
            dpg.add_text("🟢 SYSTEM READY", tag=self.tag.status_text, color=Colors.STATUS_OK)
            
            dpg.add_spacer(width=30)
            
            # Broadcast Timer
            dpg.add_text("⏱ 00:00.0", tag=self.tag.broadcast_timer, color=Colors.TEXT_SECONDARY)
            
            # Push clock to right
            dpg.add_spacer(width=-1)
            
            # System Clock
            dpg.add_text("--:--:--", tag=self.tag.system_clock, color=Colors.TEXT_SECONDARY)
        
        dpg.add_separator()
        dpg.add_spacer(height=5)
    
    def _create_status_leds(self) -> None:
        """Create status LED indicators."""
        with dpg.group(horizontal=True):
            # RF LED
            dpg.add_text("●", tag=self.tag.led_rf, color=Colors.STATUS_OFF)
            dpg.add_text("RF", color=Colors.TEXT_SECONDARY)
            dpg.add_spacer(width=10)
            
            # MOD LED
            dpg.add_text("●", tag=self.tag.led_mod, color=Colors.STATUS_OFF)
            dpg.add_text("MOD", color=Colors.TEXT_SECONDARY)
            dpg.add_spacer(width=10)
            
            # AUDIO LED
            dpg.add_text("●", tag=self.tag.led_audio, color=Colors.STATUS_OFF)
            dpg.add_text("AUD", color=Colors.TEXT_SECONDARY)
            dpg.add_spacer(width=10)
            
            # NETWORK LED
            dpg.add_text("●", tag=self.tag.led_network, color=Colors.STATUS_OFF)
            dpg.add_text("NET", color=Colors.TEXT_SECONDARY)
    
    def _create_body(self) -> None:
        """Create main body with left and right panels."""
        with dpg.group(horizontal=True):
            # Left Panel - Controls
            self._create_left_panel()
            
            dpg.add_spacer(width=10)
            
            # Right Panel - Displays
            self._create_right_panel()
    
    def _create_left_panel(self) -> None:
        """Create left control panel."""
        with dpg.child_window(tag=self.tag.left_panel, width=350, border=True):
            self._create_connection_section()
            dpg.add_spacer(height=10)
            
            self._create_channel_panels()
            dpg.add_spacer(height=10)
            
            self._create_audio_section()
            dpg.add_spacer(height=10)
            
            self._create_message_section()
    
    def _create_connection_section(self) -> None:
        """Create Red Pitaya connection section."""
        with dpg.collapsing_header(label="🔌 Red Pitaya Connection", default_open=True):
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag=self.tag.ip_input,
                    default_value="192.168.1.100",
                    width=200,
                    hint="IP Address"
                )
                dpg.add_button(
                    tag=self.tag.connect_btn,
                    label="Connect",
                    width=-1
                )
            
            dpg.add_spacer(height=5)
            dpg.add_text(
                "🔴 Disconnected",
                tag=self.tag.connection_status,
                color=Colors.STATUS_ERROR
            )
    
    def _create_channel_panels(self) -> None:
        """Create channel control panels."""
        for i, channel in enumerate(CHANNELS):
            panel_tag = self.tag.ch1_panel if channel.id == 1 else self.tag.ch2_panel
            checkbox_tag = self.tag.ch1_checkbox if channel.id == 1 else self.tag.ch2_checkbox
            freq_tag = self.tag.ch1_freq_label if channel.id == 1 else self.tag.ch2_freq_label
            level_tag = self.tag.ch1_level_bar if channel.id == 1 else self.tag.ch2_level_bar
            status_tag = self.tag.ch1_status if channel.id == 1 else self.tag.ch2_status
            
            with dpg.child_window(tag=panel_tag, height=100, border=True):
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(
                        tag=checkbox_tag,
                        default_value=True
                    )
                    dpg.add_text(
                        f"📻 {channel.name}",
                        color=Colors.TEXT_ACCENT
                    )
                    dpg.add_spacer(width=-1)
                    dpg.add_text(
                        f"{channel.freq_khz} kHz",
                        tag=freq_tag,
                        color=Colors.TEXT_PRIMARY
                    )
                
                dpg.add_spacer(height=5)
                
                # RF Level Bar
                with dpg.group(horizontal=True):
                    dpg.add_text("RF:", color=Colors.TEXT_SECONDARY)
                    dpg.add_progress_bar(
                        tag=level_tag,
                        default_value=0.0,
                        width=-1,
                        overlay="0 dB"
                    )
                
                dpg.add_spacer(height=5)
                
                # Status
                dpg.add_text(
                    "🟡 STANDBY",
                    tag=status_tag,
                    color=Colors.STATUS_WARN
                )
            
            if i < len(CHANNELS) - 1:
                dpg.add_spacer(height=5)
    
    def _create_audio_section(self) -> None:
        """Create audio input section."""
        with dpg.collapsing_header(label="🎤 Audio Input", default_open=True):
            dpg.add_text(
                "Source: Pre-loaded BRAM",
                tag=self.tag.audio_source_label,
                color=Colors.TEXT_SECONDARY
            )
            
            dpg.add_spacer(height=5)
            
            with dpg.group(horizontal=True):
                dpg.add_text("Level:", color=Colors.TEXT_SECONDARY)
                dpg.add_progress_bar(
                    tag=self.tag.audio_level_bar,
                    default_value=0.0,
                    width=-1
                )
    
    def _create_message_section(self) -> None:
        """Create message selection section."""
        with dpg.collapsing_header(label="📝 Message Selection", default_open=True):
            # Create radio button options
            message_names = [f"{msg.icon} {msg.name}" for msg in MESSAGES]
            
            dpg.add_radio_button(
                items=message_names,
                tag=self.tag.message_radio,
                default_value=message_names[0]
            )
    
    def _create_right_panel(self) -> None:
        """Create right display panel."""
        with dpg.child_window(tag=self.tag.right_panel, border=True):
            self._create_spectrum_display()
            dpg.add_spacer(height=10)
            
            self._create_audio_waveform()
            dpg.add_spacer(height=10)
            
            self._create_broadcast_button()
            dpg.add_spacer(height=10)
            
            self._create_log_section()
    
    def _create_spectrum_display(self) -> None:
        """Create spectrum analyzer display."""
        dpg.add_text("📊 RF Spectrum", color=Colors.TEXT_ACCENT)
        
        with dpg.plot(
            tag=self.tag.spectrum_plot,
            height=180,
            width=-1,
            no_menus=True,
            no_box_select=True,
            no_mouse_pos=True
        ):
            # X Axis
            dpg.add_plot_axis(
                dpg.mvXAxis,
                tag=self.tag.spectrum_x_axis,
                label="Frequency (kHz)"
            )
            dpg.set_axis_limits(self.tag.spectrum_x_axis, Display.SPECTRUM_MIN_FREQ, Display.SPECTRUM_MAX_FREQ)
            
            # Y Axis
            dpg.add_plot_axis(
                dpg.mvYAxis,
                tag=self.tag.spectrum_y_axis,
                label="Power (dB)"
            )
            dpg.set_axis_limits(self.tag.spectrum_y_axis, Display.SPECTRUM_MIN_DB, Display.SPECTRUM_MAX_DB)
            
            # Spectrum Series
            dpg.add_line_series(
                x=[],
                y=[],
                tag=self.tag.spectrum_series,
                parent=self.tag.spectrum_y_axis
            )
            
            # Channel markers (vertical lines)
            for channel in CHANNELS:
                marker_tag = self.tag.spectrum_marker_ch1 if channel.id == 1 else self.tag.spectrum_marker_ch2
                dpg.add_vline_series(
                    x=[channel.freq_khz],
                    tag=marker_tag,
                    parent=self.tag.spectrum_y_axis
                )
    
    def _create_audio_waveform(self) -> None:
        """Create audio waveform display."""
        dpg.add_text("🔊 Audio Waveform", color=Colors.TEXT_ACCENT)
        
        with dpg.plot(
            tag=self.tag.audio_plot,
            height=120,
            width=-1,
            no_menus=True,
            no_box_select=True,
            no_mouse_pos=True,
            no_title=True
        ):
            # X Axis
            dpg.add_plot_axis(
                dpg.mvXAxis,
                tag=self.tag.audio_x_axis,
                no_tick_labels=True
            )
            dpg.set_axis_limits(self.tag.audio_x_axis, 0, Display.AUDIO_BUFFER_SIZE)
            
            # Y Axis
            dpg.add_plot_axis(
                dpg.mvYAxis,
                tag=self.tag.audio_y_axis,
                no_tick_labels=True
            )
            dpg.set_axis_limits(self.tag.audio_y_axis, -1.0, 1.0)
            
            # Audio Series
            dpg.add_line_series(
                x=[],
                y=[],
                tag=self.tag.audio_series,
                parent=self.tag.audio_y_axis
            )
    
    def _create_broadcast_button(self) -> None:
        """Create main broadcast button."""
        with dpg.group(tag=self.tag.broadcast_section):
            dpg.add_button(
                tag=self.tag.broadcast_btn,
                label="🔴  EMERGENCY BROADCAST  🔴",
                width=-1,
                height=80
            )
            
            # Keyboard shortcut hint
            dpg.add_text(
                "Keyboard: F1 or SPACE to toggle | ESC to stop",
                color=Colors.TEXT_SECONDARY
            )
    
    def _create_log_section(self) -> None:
        """Create system log section."""
        dpg.add_text("📋 System Log", color=Colors.TEXT_ACCENT)
        
        with dpg.child_window(
            tag=self.tag.log_window,
            height=-1,
            border=True,
            horizontal_scrollbar=True
        ):
            dpg.add_text(
                "",
                tag=self.tag.log_text,
                color=Colors.LOG_TEXT,
                wrap=0
            )

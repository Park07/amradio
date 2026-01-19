"""
UGL Tunnel AM Break-In System
Tag Management

Immutable tag references for all UI widgets.
No more magic strings scattered throughout the code.
"""

import uuid
from dataclasses import dataclass


def generate_tag() -> int:
    """Generate a random, unique tag."""
    return hash(uuid.uuid4())


@dataclass(frozen=True, slots=True)
class Tag:
    """
    Creates immutable tag references for all widgets.
    Once instantiated, tag values cannot be modified.
    
    Usage:
        tags = Tag()
        dpg.add_button(tag=tags.broadcast_btn, ...)
        dpg.set_value(tags.status_text, "Ready")
    """
    
    # === Main Window ===
    main_window: int
    
    # === Header ===
    header_group: int
    status_text: int
    broadcast_timer: int
    system_clock: int
    
    # === Left Panel ===
    left_panel: int
    
    # Connection Section
    connection_section: int
    ip_input: int
    connect_btn: int
    connection_status: int
    
    # Channel 1
    ch1_panel: int
    ch1_checkbox: int
    ch1_freq_label: int
    ch1_level_bar: int
    ch1_status: int
    
    # Channel 2
    ch2_panel: int
    ch2_checkbox: int
    ch2_freq_label: int
    ch2_level_bar: int
    ch2_status: int
    
    # Audio Section
    audio_section: int
    audio_level_bar: int
    audio_source_label: int
    
    # Message Selection
    message_section: int
    message_radio: int
    
    # === Right Panel ===
    right_panel: int
    
    # Spectrum Display
    spectrum_section: int
    spectrum_plot: int
    spectrum_x_axis: int
    spectrum_y_axis: int
    spectrum_series: int
    spectrum_marker_ch1: int
    spectrum_marker_ch2: int
    
    # Audio Waveform
    audio_waveform_section: int
    audio_plot: int
    audio_x_axis: int
    audio_y_axis: int
    audio_series: int
    
    # Broadcast Button
    broadcast_section: int
    broadcast_btn: int
    
    # Log Section
    log_section: int
    log_window: int
    log_text: int
    
    # === Dialogs ===
    confirm_dialog: int
    confirm_message: int
    confirm_yes_btn: int
    confirm_no_btn: int
    
    error_dialog: int
    error_title: int
    error_message: int
    error_close_btn: int
    
    # === Status LEDs ===
    led_rf: int
    led_mod: int
    led_audio: int
    led_network: int
    
    def __init__(self) -> None:
        """Generate unique tags for all slots."""
        for tag_name in self.__slots__:
            object.__setattr__(self, tag_name, generate_tag())


# Channel-specific tag helper
class ChannelTags:
    """Helper to access channel-specific tags by index."""
    
    def __init__(self, tags: Tag):
        self._tags = tags
        self._channel_attrs = {
            1: {
                'panel': 'ch1_panel',
                'checkbox': 'ch1_checkbox',
                'freq_label': 'ch1_freq_label',
                'level_bar': 'ch1_level_bar',
                'status': 'ch1_status',
            },
            2: {
                'panel': 'ch2_panel',
                'checkbox': 'ch2_checkbox',
                'freq_label': 'ch2_freq_label',
                'level_bar': 'ch2_level_bar',
                'status': 'ch2_status',
            }
        }
    
    def get(self, channel_id: int, attr: str) -> int:
        """Get tag for a specific channel attribute."""
        attr_name = self._channel_attrs[channel_id][attr]
        return getattr(self._tags, attr_name)

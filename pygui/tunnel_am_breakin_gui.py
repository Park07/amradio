"""
UGL TUNNEL AM BREAK-IN SYSTEM
Industrial Control Panel GUI

Hardware: Red Pitaya 125-10
Project: UNSW EPI x UGL
Author: William Park
Version: 1.0.0

Requirements:
    pip install dearpygui
"""

import dearpygui.dearpygui as dpg
import socket
import threading
import time
import math
import random
from datetime import datetime
from collections import deque

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    # Red Pitaya Connection
    RP_IP = "192.168.1.100"
    RP_PORT = 5000

    # RF Channels
    CHANNELS = [
        {"id": 1, "freq_khz": 531, "name": "Channel 1", "phase_inc": 18253611},
        {"id": 2, "freq_khz": 702, "name": "Channel 2", "phase_inc": 24120028},
    ]

    # Pre-recorded Messages
    MESSAGES = [
        {"id": "test", "name": "Test Tone (1kHz)", "duration": 0},
        {"id": "emergency", "name": "🔴 EMERGENCY EVACUATE", "duration": 15},
        {"id": "traffic", "name": "Traffic Advisory", "duration": 10},
        {"id": "fire", "name": "🔥 FIRE - EXIT NOW", "duration": 15},
    ]

    # GUI Settings
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    UPDATE_RATE = 30  # Hz

# ============================================================================
# THEME - INDUSTRIAL DARK
# ============================================================================

def create_industrial_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Dark industrial colors
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (15, 15, 20, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (20, 22, 28, 255))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (25, 28, 35, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (50, 55, 65, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (30, 35, 45, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (45, 50, 60, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (55, 60, 75, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (15, 18, 25, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (25, 80, 150, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (220, 225, 230, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (40, 80, 140, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (50, 100, 170, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (60, 120, 200, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Header, (40, 80, 140, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (50, 100, 170, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (60, 120, 200, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (80, 140, 220, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (100, 160, 240, 255))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (100, 200, 100, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 8)
    return global_theme

def create_emergency_button_theme():
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (180, 30, 30, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (220, 50, 50, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 80, 80, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 20, 20)
    return theme

def create_stop_button_theme():
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 60, 70, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 80, 90, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (100, 100, 110, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 20, 20)
    return theme

def create_active_channel_theme():
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (20, 50, 30, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (50, 180, 80, 255))
    return theme

def create_inactive_channel_theme():
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (25, 28, 35, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (50, 55, 65, 255))
    return theme

# ============================================================================
# SYSTEM STATE
# ============================================================================

class SystemState:
    def __init__(self):
        self.connected = False
        self.broadcasting = False
        self.selected_message = "test"
        self.channels_active = {ch["id"]: False for ch in Config.CHANNELS}
        self.channels_enabled = {ch["id"]: True for ch in Config.CHANNELS}
        self.audio_level = 0.0
        self.rf_levels = {ch["id"]: 0.0 for ch in Config.CHANNELS}
        self.broadcast_start_time = None
        self.log_messages = deque(maxlen=100)

        # Spectrum data (simulated for demo)
        self.spectrum_x = list(range(400, 1200, 2))  # 400-1200 kHz
        self.spectrum_y = [0.0] * len(self.spectrum_x)

        # Audio waveform buffer
        self.audio_buffer = deque([0.0] * 200, maxlen=200)

state = SystemState()

# ============================================================================
# COMMUNICATION
# ============================================================================

def send_scpi(command: str) -> bool:
    """Send SCPI command to Red Pitaya"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((Config.RP_IP, Config.RP_PORT))
        sock.send((command + "\r\n").encode())
        sock.close()
        log_message(f"SCPI: {command}", "DEBUG")
        return True
    except Exception as e:
        log_message(f"SCPI Error: {e}", "ERROR")
        return False

def check_connection() -> bool:
    """Check Red Pitaya connection"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((Config.RP_IP, Config.RP_PORT))
        sock.close()
        return True
    except:
        return False

# ============================================================================
# LOGGING
# ============================================================================

def log_message(message: str, level: str = "INFO"):
    """Add message to log"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    entry = f"[{timestamp}] [{level}] {message}"
    state.log_messages.append(entry)

    # Update log display if it exists
    if dpg.does_item_exist("log_text"):
        log_text = "\n".join(list(state.log_messages)[-20:])
        dpg.set_value("log_text", log_text)

# ============================================================================
# CALLBACKS
# ============================================================================

def on_broadcast_click():
    """Handle broadcast button click"""
    if not state.broadcasting:
        start_broadcast()
    else:
        stop_broadcast()

def start_broadcast():
    """Start emergency broadcast"""
    state.broadcasting = True
    state.broadcast_start_time = time.time()

    # Activate enabled channels
    for ch in Config.CHANNELS:
        if state.channels_enabled[ch["id"]]:
            state.channels_active[ch["id"]] = True
            send_scpi(f"CHANNEL{ch['id']}:FREQ {ch['freq_khz']}000")
            send_scpi(f"CHANNEL{ch['id']}:STATE ON")

    # Set message
    send_scpi(f"MSG:SELECT {state.selected_message}")
    send_scpi("OUTPUT:STATE ON")

    log_message(f"🔴 BROADCAST STARTED - Message: {state.selected_message}", "ALERT")

    # Update UI
    dpg.configure_item("broadcast_btn", label="⬛  STOP BROADCAST  ⬛")
    dpg.bind_item_theme("broadcast_btn", stop_button_theme)
    dpg.set_value("status_text", "🔴 BROADCASTING")
    dpg.configure_item("status_text", color=(255, 80, 80, 255))

def stop_broadcast():
    """Stop broadcast"""
    state.broadcasting = False

    # Deactivate all channels
    for ch in Config.CHANNELS:
        state.channels_active[ch["id"]] = False
        send_scpi(f"CHANNEL{ch['id']}:STATE OFF")

    send_scpi("OUTPUT:STATE OFF")

    duration = time.time() - state.broadcast_start_time if state.broadcast_start_time else 0
    log_message(f"⬛ BROADCAST STOPPED - Duration: {duration:.1f}s", "ALERT")

    # Update UI
    dpg.configure_item("broadcast_btn", label="🔴  EMERGENCY BROADCAST  🔴")
    dpg.bind_item_theme("broadcast_btn", emergency_button_theme)
    dpg.set_value("status_text", "🟢 SYSTEM READY")
    dpg.configure_item("status_text", color=(80, 255, 120, 255))

def on_message_select(sender, app_data, user_data):
    """Handle message selection"""
    state.selected_message = user_data
    log_message(f"Message selected: {user_data}")

def on_message_radio_select(sender, app_data):
    """Handle message radio button selection"""
    # Map display name back to message ID
    for msg in Config.MESSAGES:
        if msg["name"] == app_data:
            state.selected_message = msg["id"]
            log_message(f"Message selected: {msg['name']}")
            break

def on_channel_toggle(sender, app_data, user_data):
    """Handle channel enable/disable"""
    channel_id = user_data
    state.channels_enabled[channel_id] = app_data
    status = "enabled" if app_data else "disabled"
    log_message(f"Channel {channel_id} {status}")

def on_connect_click():
    """Handle connect button click"""
    log_message(f"Connecting to Red Pitaya at {Config.RP_IP}...")
    state.connected = check_connection()
    if state.connected:
        log_message("✅ Connected to Red Pitaya", "SUCCESS")
        dpg.set_value("connection_status", f"🟢 Connected: {Config.RP_IP}")
        dpg.configure_item("connection_status", color=(80, 255, 120, 255))
    else:
        log_message("❌ Connection failed", "ERROR")
        dpg.set_value("connection_status", f"🔴 Disconnected")
        dpg.configure_item("connection_status", color=(255, 80, 80, 255))

def on_ip_change(sender, app_data):
    """Handle IP address change"""
    Config.RP_IP = app_data

def keyboard_handler(sender, app_data):
    """Handle keyboard shortcuts"""
    key = app_data
    # F1 or Space for emergency broadcast toggle
    if key == dpg.mvKey_F1 or key == dpg.mvKey_Spacebar:
        on_broadcast_click()
    # Escape to stop broadcast
    elif key == dpg.mvKey_Escape and state.broadcasting:
        stop_broadcast()

# ============================================================================
# REAL-TIME UPDATE LOOP
# ============================================================================

def update_displays():
    """Update all real-time displays"""
    while dpg.is_dearpygui_running():
        # Simulate data for demo (replace with real Red Pitaya data)
        if state.broadcasting:
            # Simulate audio level
            state.audio_level = 0.6 + random.uniform(-0.2, 0.2)

            # Simulate RF output levels
            for ch in Config.CHANNELS:
                if state.channels_active[ch["id"]]:
                    state.rf_levels[ch["id"]] = 0.8 + random.uniform(-0.1, 0.1)
                else:
                    state.rf_levels[ch["id"]] = 0.0

            # Update spectrum (simulated)
            update_spectrum_data()

            # Update audio waveform
            t = time.time() * 1000  # 1kHz test tone simulation
            state.audio_buffer.append(math.sin(t * 2 * math.pi / 1000) * state.audio_level)
        else:
            state.audio_level = 0.0
            for ch in Config.CHANNELS:
                state.rf_levels[ch["id"]] = max(0, state.rf_levels[ch["id"]] - 0.05)
            state.audio_buffer.append(0.0)

        # Update UI elements
        update_channel_displays()
        update_spectrum_plot()
        update_audio_plot()
        update_broadcast_timer()

        time.sleep(1.0 / Config.UPDATE_RATE)

def update_spectrum_data():
    """Update spectrum display data"""
    # Clear spectrum
    state.spectrum_y = [random.uniform(-80, -70) for _ in state.spectrum_x]

    # Add peaks at active frequencies
    for ch in Config.CHANNELS:
        if state.channels_active[ch["id"]]:
            freq = ch["freq_khz"]
            for i, x in enumerate(state.spectrum_x):
                # Create peak with sidebands (AM modulation)
                distance = abs(x - freq)
                if distance < 20:
                    peak = -10 - distance * 0.5
                    state.spectrum_y[i] = max(state.spectrum_y[i], peak)
                elif distance < 10:
                    # Sidebands
                    state.spectrum_y[i] = max(state.spectrum_y[i], -25)

def update_channel_displays():
    """Update channel status displays"""
    for ch in Config.CHANNELS:
        ch_id = ch["id"]

        # Update level bar
        if dpg.does_item_exist(f"ch{ch_id}_level"):
            level = state.rf_levels[ch_id]
            dpg.set_value(f"ch{ch_id}_level", level)

        # Update status indicator
        if dpg.does_item_exist(f"ch{ch_id}_status"):
            if state.channels_active[ch_id]:
                dpg.set_value(f"ch{ch_id}_status", "🟢 TRANSMITTING")
                dpg.configure_item(f"ch{ch_id}_status", color=(80, 255, 120, 255))
            elif state.channels_enabled[ch_id]:
                dpg.set_value(f"ch{ch_id}_status", "🟡 STANDBY")
                dpg.configure_item(f"ch{ch_id}_status", color=(255, 200, 80, 255))
            else:
                dpg.set_value(f"ch{ch_id}_status", "⚫ DISABLED")
                dpg.configure_item(f"ch{ch_id}_status", color=(120, 120, 120, 255))

        # Update channel panel theme
        if dpg.does_item_exist(f"ch{ch_id}_panel"):
            if state.channels_active[ch_id]:
                dpg.bind_item_theme(f"ch{ch_id}_panel", active_channel_theme)
            else:
                dpg.bind_item_theme(f"ch{ch_id}_panel", inactive_channel_theme)

def update_spectrum_plot():
    """Update spectrum analyzer plot"""
    if dpg.does_item_exist("spectrum_series"):
        dpg.set_value("spectrum_series", [state.spectrum_x, state.spectrum_y])

def update_audio_plot():
    """Update audio waveform plot"""
    if dpg.does_item_exist("audio_series"):
        x_data = list(range(len(state.audio_buffer)))
        y_data = list(state.audio_buffer)
        dpg.set_value("audio_series", [x_data, y_data])

    # Update audio level bar
    if dpg.does_item_exist("audio_level_bar"):
        dpg.set_value("audio_level_bar", state.audio_level)

def update_broadcast_timer():
    """Update broadcast duration timer and system clock"""
    # System clock
    if dpg.does_item_exist("system_clock"):
        current_time = datetime.now().strftime("%H:%M:%S")
        dpg.set_value("system_clock", current_time)

    # Broadcast timer
    if state.broadcasting and state.broadcast_start_time:
        duration = time.time() - state.broadcast_start_time
        mins = int(duration // 60)
        secs = int(duration % 60)
        if dpg.does_item_exist("broadcast_timer"):
            dpg.set_value("broadcast_timer", f"🔴 TX Duration: {mins:02d}:{secs:02d}")
    else:
        if dpg.does_item_exist("broadcast_timer"):
            dpg.set_value("broadcast_timer", "")

# ============================================================================
# GUI LAYOUT
# ============================================================================

def create_gui():
    dpg.create_context()
    dpg.create_viewport(
        title="UGL Tunnel AM Break-In System",
        width=Config.WINDOW_WIDTH,
        height=Config.WINDOW_HEIGHT,
        min_width=1000,
        min_height=700
    )

    # Create themes
    global emergency_button_theme, stop_button_theme
    global active_channel_theme, inactive_channel_theme

    industrial_theme = create_industrial_theme()
    emergency_button_theme = create_emergency_button_theme()
    stop_button_theme = create_stop_button_theme()
    active_channel_theme = create_active_channel_theme()
    inactive_channel_theme = create_inactive_channel_theme()

    dpg.bind_theme(industrial_theme)

    # Main window
    with dpg.window(tag="main_window"):

        # ===== HEADER =====
        with dpg.group(horizontal=True):
            dpg.add_text("████  UGL TUNNEL AM BREAK-IN SYSTEM  ████",
                        color=(100, 180, 255, 255))
            dpg.add_spacer(width=20)
            dpg.add_text("🟢 SYSTEM READY", tag="status_text",
                        color=(80, 255, 120, 255))

            dpg.add_spacer(width=50)
            dpg.add_text("", tag="broadcast_timer", color=(255, 200, 80, 255))

            dpg.add_spacer(width=-1)  # Push to right
            dpg.add_text("", tag="system_clock", color=(150, 150, 160, 255))

        dpg.add_separator()
        dpg.add_spacer(height=10)

        # ===== MAIN CONTENT =====
        with dpg.group(horizontal=True):

            # ----- LEFT PANEL: Channels & Controls -----
            with dpg.child_window(width=350, height=-1, border=True):

                # Connection
                dpg.add_text("CONNECTION", color=(150, 150, 160, 255))
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_input_text(default_value=Config.RP_IP, width=150,
                                      callback=on_ip_change)
                    dpg.add_button(label="Connect", callback=on_connect_click)
                dpg.add_text("🔴 Disconnected", tag="connection_status",
                            color=(255, 80, 80, 255))

                dpg.add_spacer(height=15)

                # Channel panels
                dpg.add_text("RF CHANNELS", color=(150, 150, 160, 255))
                dpg.add_separator()

                for ch in Config.CHANNELS:
                    with dpg.child_window(height=100, border=True,
                                         tag=f"ch{ch['id']}_panel"):
                        with dpg.group(horizontal=True):
                            dpg.add_checkbox(label="", default_value=True,
                                           callback=on_channel_toggle,
                                           user_data=ch["id"])
                            dpg.add_text(f"{ch['name']}", color=(200, 200, 210, 255))

                        dpg.add_text(f"{ch['freq_khz']} kHz",
                                    color=(100, 180, 255, 255))

                        # Level bar
                        dpg.add_progress_bar(default_value=0,
                                            tag=f"ch{ch['id']}_level",
                                            overlay="RF Level")

                        dpg.add_text("🟡 STANDBY", tag=f"ch{ch['id']}_status",
                                    color=(255, 200, 80, 255))

                    dpg.add_spacer(height=5)

                dpg.add_spacer(height=15)

                # Audio input
                dpg.add_text("AUDIO INPUT", color=(150, 150, 160, 255))
                dpg.add_separator()
                with dpg.child_window(height=80, border=True):
                    dpg.add_progress_bar(default_value=0, tag="audio_level_bar",
                                        overlay="Input Level")
                    dpg.add_text("Source: Pre-recorded", color=(150, 150, 160, 255))

                dpg.add_spacer(height=15)

                # Message selection
                dpg.add_text("BROADCAST MESSAGE", color=(150, 150, 160, 255))
                dpg.add_separator()

                message_names = [msg["name"] for msg in Config.MESSAGES]
                dpg.add_radio_button(
                    items=message_names,
                    default_value=message_names[0],
                    callback=on_message_radio_select,
                    tag="message_radio",
                    horizontal=False
                )

            dpg.add_spacer(width=10)

            # ----- RIGHT PANEL: Displays & Broadcast -----
            with dpg.child_window(width=-1, height=-1, border=False):

                # Spectrum Analyzer
                dpg.add_text("RF OUTPUT SPECTRUM", color=(150, 150, 160, 255))
                with dpg.plot(height=200, width=-1, tag="spectrum_plot"):
                    dpg.add_plot_legend()

                    x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Frequency (kHz)")
                    dpg.set_axis_limits(x_axis, 400, 1200)

                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Power (dB)")
                    dpg.set_axis_limits(y_axis, -80, 0)

                    dpg.add_line_series(state.spectrum_x, state.spectrum_y,
                                       label="RF Spectrum",
                                       parent=y_axis,
                                       tag="spectrum_series")

                    # Add frequency markers
                    for ch in Config.CHANNELS:
                        dpg.add_vline_series([ch["freq_khz"]],
                                            parent=y_axis,
                                            label=f"{ch['freq_khz']} kHz")

                dpg.add_spacer(height=10)

                # Audio Waveform
                dpg.add_text("AUDIO WAVEFORM", color=(150, 150, 160, 255))
                with dpg.plot(height=120, width=-1, tag="audio_plot"):
                    x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="", no_tick_labels=True)
                    dpg.set_axis_limits(x_axis, 0, 200)

                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="")
                    dpg.set_axis_limits(y_axis, -1, 1)

                    dpg.add_line_series(list(range(200)), [0]*200,
                                       parent=y_axis,
                                       tag="audio_series")

                dpg.add_spacer(height=20)

                # BROADCAST BUTTON
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=50)
                    btn = dpg.add_button(
                        label="🔴  EMERGENCY BROADCAST  🔴",
                        tag="broadcast_btn",
                        width=-100,
                        height=80,
                        callback=on_broadcast_click
                    )
                    dpg.bind_item_theme(btn, emergency_button_theme)

                dpg.add_spacer(height=20)

                # Log
                dpg.add_text("SYSTEM LOG", color=(150, 150, 160, 255))
                with dpg.child_window(height=-1, border=True):
                    dpg.add_text("", tag="log_text", wrap=0,
                                color=(150, 200, 150, 255))

    # Initialize
    log_message("System initialized")
    log_message(f"Channels configured: {len(Config.CHANNELS)}")
    for ch in Config.CHANNELS:
        log_message(f"  - {ch['name']}: {ch['freq_khz']} kHz")
    log_message("Keyboard shortcuts: F1/SPACE = Toggle Broadcast, ESC = Stop")
    log_message("Ready for operation")

    # Register keyboard handler
    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=keyboard_handler)

    dpg.set_primary_window("main_window", True)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Start update thread
    update_thread = threading.Thread(target=update_displays, daemon=True)
    update_thread.start()

    dpg.start_dearpygui()
    dpg.destroy_context()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  UGL TUNNEL AM BREAK-IN SYSTEM")
    print("  Industrial Control Panel")
    print("=" * 60)
    print(f"  Red Pitaya IP: {Config.RP_IP}")
    print(f"  Channels: {len(Config.CHANNELS)}")
    print("=" * 60)
    print()

    create_gui()
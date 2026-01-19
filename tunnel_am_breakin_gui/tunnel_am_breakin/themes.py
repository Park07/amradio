"""
UGL Tunnel AM Break-In System
Theme Definitions

Industrial dark theme for control room aesthetic.
"""

import dearpygui.dearpygui as dpg
from dataclasses import dataclass

from .configs import Colors


@dataclass
class ThemeCollection:
    """Collection of all application themes."""
    default: int
    emergency_button: int
    stop_button: int
    channel_active: int
    channel_inactive: int
    led_on: int
    led_off: int


def create_themes() -> ThemeCollection:
    """Create and return all application themes."""

    # =========================================================================
    # DEFAULT INDUSTRIAL THEME
    # =========================================================================
    with dpg.theme() as default_theme:
        with dpg.theme_component(dpg.mvAll):
            # Window backgrounds
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, Colors.WINDOW_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, Colors.CHILD_BG)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, Colors.POPUP_BG)

            # Borders
            dpg.add_theme_color(dpg.mvThemeCol_Border, Colors.BORDER)

            # Frame (input fields, sliders, etc.)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, Colors.FRAME_BG)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, Colors.FRAME_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, Colors.FRAME_ACTIVE)

            # Title bar
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, Colors.TITLE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, Colors.TITLE_ACTIVE)

            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text, Colors.TEXT_PRIMARY)

            # Buttons
            dpg.add_theme_color(dpg.mvThemeCol_Button, Colors.BUTTON)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, Colors.BUTTON_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, Colors.BUTTON_ACTIVE)

            # Headers
            dpg.add_theme_color(dpg.mvThemeCol_Header, Colors.BUTTON)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, Colors.BUTTON_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, Colors.BUTTON_ACTIVE)

            # Sliders
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (80, 140, 220, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (100, 160, 240, 255))

            # Checkmarks
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, Colors.STATUS_OK)

            # Separators
            dpg.add_theme_color(dpg.mvThemeCol_Separator, Colors.BORDER)

            # Plot styling - use mvPlotCol for plot-specific colors
            # Note: Plot colors use mvPlotCol_ prefix in DearPyGui 2.x
            try:
                dpg.add_theme_color(dpg.mvPlotCol_PlotBg, (15, 15, 20, 255), category=dpg.mvThemeCat_Plots)
                dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, Colors.BORDER, category=dpg.mvThemeCat_Plots)
            except AttributeError:
                pass  # Skip if not available in this DPG version

            # Style variables
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 12)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 4)

    # =========================================================================
    # EMERGENCY BROADCAST BUTTON
    # =========================================================================
    with dpg.theme() as emergency_button_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, Colors.EMERGENCY_BTN)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, Colors.EMERGENCY_BTN_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, Colors.EMERGENCY_BTN_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 20, 20)

    # =========================================================================
    # STOP BUTTON
    # =========================================================================
    with dpg.theme() as stop_button_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, Colors.STOP_BTN)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, Colors.STOP_BTN_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, Colors.STOP_BTN_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 20, 20)

    # =========================================================================
    # CHANNEL PANEL - ACTIVE (Transmitting)
    # =========================================================================
    with dpg.theme() as channel_active_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, Colors.CHANNEL_ACTIVE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Border, Colors.BORDER_ACTIVE)

    # =========================================================================
    # CHANNEL PANEL - INACTIVE
    # =========================================================================
    with dpg.theme() as channel_inactive_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, Colors.CHANNEL_INACTIVE_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Border, Colors.BORDER)

    # =========================================================================
    # LED INDICATOR - ON
    # =========================================================================
    with dpg.theme() as led_on_theme:
        with dpg.theme_component(dpg.mvText):
            dpg.add_theme_color(dpg.mvThemeCol_Text, Colors.STATUS_OK)

    # =========================================================================
    # LED INDICATOR - OFF
    # =========================================================================
    with dpg.theme() as led_off_theme:
        with dpg.theme_component(dpg.mvText):
            dpg.add_theme_color(dpg.mvThemeCol_Text, Colors.STATUS_OFF)

    return ThemeCollection(
        default=default_theme,
        emergency_button=emergency_button_theme,
        stop_button=stop_button_theme,
        channel_active=channel_active_theme,
        channel_inactive=channel_inactive_theme,
        led_on=led_on_theme,
        led_off=led_off_theme,
    )
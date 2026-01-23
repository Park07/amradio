#!/usr/bin/env python3
"""
UGL Tunnel AM Radio Control System - 12 Channel Stress Test Version
====================================================================
Entry point for the GUI application.

Usage:
    python main.py

Requirements:
    pip install dearpygui
"""
import dearpygui.dearpygui as dpg
from config import Config
from model import Model
from controller import Controller


def main():
    """Main entry point."""
    # Initialize DearPyGui
    dpg.create_context()

    # Create MVC components
    model = Model()
    controller = Controller(model)

    # Build UI
    controller.build_ui()

    # Setup viewport
    dpg.create_viewport(
        title=Config.WINDOW_TITLE + " (12-Channel Stress Test)",
        width=Config.WINDOW_WIDTH,
        height=Config.WINDOW_HEIGHT,
        resizable=True,
        vsync=True,
    )

    # Configure
    dpg.setup_dearpygui()
    dpg.set_primary_window("main_window", True)

    # Run
    dpg.show_viewport()
    dpg.start_dearpygui()

    # Cleanup
    if model.is_connected():
        model.disconnect()

    dpg.destroy_context()


if __name__ == "__main__":
    main()

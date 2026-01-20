#!/usr/bin/env python3
"""
UGL Tunnel AM Radio Control System
===================================

Entry point for the GUI application.

Architecture (from Rob's whiteboard):
    
    MODE A: Live Mic (ADC)
    ┌─────────────┐     ┌─────────┐     ┌──────────────┐     ┌────────┐
    │ Microphone  │ ──► │   PA    │ ──► │ Red Pitaya   │ ──► │ RF OUT │
    │ (operator)  │     │ Console │     │ ADC → FPGA   │     │        │
    └─────────────┘     └─────────┘     └──────────────┘     └────────┘
                              │                 ▲
                              │                 │
                         Analog Cable      SCPI Control
                                                │
                                          ┌─────┴─────┐
                                          │  This GUI │
                                          └───────────┘
    
    MODE B: Stored Message (BRAM)
    ┌─────────────────────────────────────────────────────┐
    │                   Red Pitaya                        │
    │  BRAM (pre-loaded audio) → FPGA → DAC → RF OUT     │
    └─────────────────────────────────────────────────────┘
                              ▲
                              │ SCPI: "SOURCE:MSG 2"
                        ┌─────┴─────┐
                        │  This GUI │
                        └───────────┘

SCPI Commands:
    SOURCE:INPUT ADC|BRAM   - Select audio source
    SOURCE:MSG <n>          - Select stored message (1-4)
    CH<n>:FREQ <hz>         - Set carrier frequency
    CH<n>:OUTPUT ON|OFF     - Enable/disable channel
    OUTPUT:STATE ON|OFF     - Master broadcast on/off
    *IDN?                   - Identity query

Usage:
    python main.py
    
Requirements:
    pip install dearpygui

Author: William (UGL EPI Team)
Date: January 2026
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
    
    # Setup viewport (main window)
    dpg.create_viewport(
        title=Config.WINDOW_TITLE,
        width=Config.WINDOW_WIDTH,
        height=Config.WINDOW_HEIGHT,
        resizable=True,
        vsync=True
    )
    
    # Configure
    dpg.setup_dearpygui()
    dpg.set_primary_window(controller.tags["main_window"], True)
    
    # Run
    dpg.show_viewport()
    dpg.start_dearpygui()
    
    # Cleanup
    if model.is_connected():
        model.disconnect()
    
    dpg.destroy_context()


if __name__ == "__main__":
    main()

"""
UGL AM Radio Control - Main Entry Point
========================================
Sets up DearPyGui viewport with proper sizing.
"""
import dearpygui.dearpygui as dpg
from model import Model
from controller import Controller

def main():
    dpg.create_context()

    # Create model and controller
    model = Model()
    controller = Controller(model)

    # Build the UI
    controller.build_ui()

    # Create viewport with proper size
    dpg.create_viewport(
        title="UGL AM Radio Control",
        width=1200,
        height=900,
        min_width=1100,
        min_height=800
    )

    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Set main window as primary
    dpg.set_primary_window("main_window", True)

    # Main loop
    dpg.start_dearpygui()
    dpg.destroy_context()

if __name__ == "__main__":
    main()
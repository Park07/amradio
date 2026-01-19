"""
UGL Tunnel AM Break-In System
Main Application

Application orchestration and lifecycle management.
"""

from __future__ import annotations
import sys
import logging
from typing import Optional, Callable

import dearpygui.dearpygui as dpg

from .configs import APP_TITLE, APP_VERSION, APP_WIDTH, APP_HEIGHT
from .tags import Tag
from .models import SystemModel
from .views import MainView
from .ui_builder import UIBuilder
from .controllers import Controller
from .themes import create_themes
from .scpi_client import SCPIClient, MockSCPIClient


class TunnelAMBreakIn:
    """
    Main application class.
    
    Orchestrates the Model-View-Controller architecture
    and handles application lifecycle.
    
    Usage:
        app = TunnelAMBreakIn()
        app.run()
    
    Or with custom components:
        model = SystemModel()
        view = MainView()
        scpi = SCPIClient()
        app = TunnelAMBreakIn(model=model, view=view, scpi=scpi)
        app.run()
    """
    
    def __init__(
        self,
        model: SystemModel = None,
        view: MainView = None,
        controller: Controller = None,
        scpi: SCPIClient = None,
        tags: Tag = None,
        use_mock: bool = True
    ):
        """
        Initialize the application.
        
        Args:
            model: Custom SystemModel instance
            view: Custom MainView instance
            controller: Custom Controller instance (overrides model/view)
            scpi: Custom SCPI client
            tags: Custom Tag instance
            use_mock: Use mock SCPI client for testing
        """
        if controller and any([model, view]):
            raise RuntimeError(
                "Cannot provide both controller and model/view. "
                "Either provide a controller OR model and view separately."
            )
        
        # Create tags first (needed by view)
        self.tags = tags or Tag()
        
        # Create or use provided components
        if controller:
            self.model = controller.model
            self.view = controller.view
            self.controller = controller
        else:
            self.model = model or SystemModel()
            self.view = view or MainView(tags=self.tags)
            self.scpi = scpi or (MockSCPIClient() if use_mock else SCPIClient())
            self.controller = Controller(
                model=self.model,
                view=self.view,
                scpi=self.scpi,
                use_mock=use_mock
            )
        
        # UI Builder reference
        self.ui_builder: Optional[UIBuilder] = None
        
        # Themes reference
        self.themes = None
    
    def setup(self) -> None:
        """
        Initialize DearPyGui and build the UI.
        Called automatically by run().
        """
        # Create DearPyGui context
        dpg.create_context()
        
        # Create themes
        self.themes = create_themes()
        self.view.set_themes(self.themes)
        
        # Build UI
        self.ui_builder = UIBuilder(self.view)
        self.view.ui = self.ui_builder
        main_window = self.ui_builder.build()
        
        # Apply default theme
        dpg.bind_theme(self.themes.default)
        
        # Apply special themes
        dpg.bind_item_theme(
            self.view.tag.broadcast_btn,
            self.themes.emergency_button
        )
        
        # Wire up callbacks
        self._setup_callbacks()
        
        # Setup keyboard handler
        self._setup_keyboard_handler()
        
        # Create viewport
        dpg.create_viewport(
            title=f"{APP_TITLE} v{APP_VERSION}",
            width=APP_WIDTH,
            height=APP_HEIGHT,
            resizable=True
        )
        
        # Setup resize callback
        dpg.set_viewport_resize_callback(self._on_resize)
        
        # Finish setup
        dpg.setup_dearpygui()
        dpg.set_primary_window(main_window, True)
        
        # Load saved settings
        self.model.load_settings()
        
        # Log startup
        self.model.log(f"{APP_TITLE} v{APP_VERSION} started", "SUCCESS")
        self.model.log("Ready for operation")
    
    def _setup_callbacks(self) -> None:
        """Wire up all UI callbacks to controller methods."""
        # Connect button
        self.view.set_connect_callback(self.controller.connect_callback)
        
        # Broadcast button
        self.view.set_broadcast_callback(self.controller.broadcast_callback)
        
        # Channel checkboxes
        for ch_id in [1, 2]:
            self.view.set_channel_callback(ch_id, self.controller.channel_toggle_callback)
        
        # Message selection
        self.view.set_message_callback(self.controller.message_select_callback)
    
    def _setup_keyboard_handler(self) -> None:
        """Setup global keyboard shortcuts."""
        with dpg.handler_registry():
            dpg.add_key_press_handler(callback=self._on_key_press)
    
    def _on_key_press(self, sender, key) -> None:
        """Handle key press events."""
        self.controller.handle_key_press(key)
    
    def _on_resize(self) -> None:
        """Handle viewport resize."""
        self.view.resize()
    
    def teardown(self) -> None:
        """
        Cleanup and shutdown.
        Called automatically when main loop exits.
        """
        # Stop controller
        self.controller.stop()
        
        # Save settings
        self.model.save_settings()
        
        # Destroy DearPyGui context
        dpg.destroy_context()
        
        self.model.log("Application shutdown complete")
    
    def exception_handler(self, exc_type, exc_value, exc_traceback) -> None:
        """
        Global exception handler.
        Catches unhandled exceptions and displays error dialog.
        """
        logging.error(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Show error popup
        self.view.popup_error(
            title=f"Error: {exc_type.__name__}",
            message=str(exc_value)
        )
    
    def run(
        self,
        demo_mode: bool = False,
        show: bool = True,
        test_callback: Callable = None
    ) -> None:
        """
        Run the application.
        
        Args:
            demo_mode: Run with simulated data
            show: Show viewport (False for testing)
            test_callback: Optional callback for testing
        """
        self.setup()
        
        # Start controller update loop
        self.controller.start()
        
        # Run test callback if provided
        if test_callback:
            test_callback(self)
        
        # Set global exception handler
        sys.excepthook = self.exception_handler
        
        # Show viewport and run main loop
        if show:
            dpg.show_viewport()
        
        dpg.start_dearpygui()
        
        # Cleanup
        self.teardown()


def create_app(**kwargs) -> TunnelAMBreakIn:
    """
    Factory function to create application instance.
    
    Args:
        **kwargs: Arguments passed to TunnelAMBreakIn
        
    Returns:
        Configured TunnelAMBreakIn instance
    """
    return TunnelAMBreakIn(**kwargs)

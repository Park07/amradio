"""
UGL Tunnel AM Break-In System

A professional control panel for emergency AM broadcast
in road tunnels using Red Pitaya FPGA.

UNSW EPI Project for UGL

Usage:
    from tunnel_am_breakin import TunnelAMBreakIn
    
    app = TunnelAMBreakIn()
    app.run()

Or run directly:
    python -m tunnel_am_breakin
    python -m tunnel_am_breakin --demo
"""

__version__ = "1.0.0"
__author__ = "UNSW EPI Team"

from .app import TunnelAMBreakIn, create_app
from .configs import CHANNELS, MESSAGES
from .models import SystemModel
from .views import MainView
from .controllers import Controller
from .scpi_client import SCPIClient, MockSCPIClient
from .tags import Tag

__all__ = [
    "TunnelAMBreakIn",
    "create_app",
    "SystemModel",
    "MainView",
    "Controller",
    "SCPIClient",
    "MockSCPIClient",
    "Tag",
    "CHANNELS",
    "MESSAGES",
]

#!/usr/bin/env python3
"""
UGL Tunnel AM Break-In System
Quick Start Script

Run this script from the project root directory:
    python run.py
    python run.py --demo
    python run.py --help
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tunnel_am_breakin.__main__ import main

if __name__ == "__main__":
    sys.exit(main())

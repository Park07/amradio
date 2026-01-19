"""
UGL Tunnel AM Break-In System
Entry Point

Run with:
    python -m tunnel_am_breakin
    python -m tunnel_am_breakin --demo
    python -m tunnel_am_breakin --help
"""

import argparse
import sys

from .app import TunnelAMBreakIn


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="UGL Tunnel AM Break-In System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m tunnel_am_breakin           Run with mock SCPI client
    python -m tunnel_am_breakin --demo    Run in demo mode
    python -m tunnel_am_breakin --real    Use real SCPI client (requires Red Pitaya)
    
Keyboard Shortcuts:
    F1 / Space    Toggle broadcast
    Escape        Emergency stop
"""
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with simulated data"
    )
    
    parser.add_argument(
        "--real",
        action="store_true",
        help="Use real SCPI client (default is mock)"
    )
    
    parser.add_argument(
        "--ip",
        type=str,
        default="192.168.1.100",
        help="Red Pitaya IP address (default: 192.168.1.100)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    args = parser.parse_args()
    
    # Create and run application
    use_mock = not args.real
    
    app = TunnelAMBreakIn(use_mock=use_mock)
    
    # Set IP if provided
    if args.ip:
        app.model.red_pitaya_ip = args.ip
    
    # Run
    app.run(demo_mode=args.demo)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

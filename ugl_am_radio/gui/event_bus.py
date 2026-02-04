"""
Event Bus - Central Event Dispatcher
=====================================
Author: William
Date: January 2026



This allows:
- Hardware events and UI events go through same channel
- Components don't call each other directly
- Easy to add logging, replay, testing
"""

from enum import Enum, auto
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import threading


class EventType(Enum):
    """All possible events in the system."""

    # Connection events
    CONNECT_REQUESTED = auto()
    CONNECT_SUCCESS = auto()
    CONNECT_FAILED = auto()
    DISCONNECT_REQUESTED = auto()
    DISCONNECTED = auto()
    CONNECTION_LOST = auto()
    RECONNECT_ATTEMPT = auto()

    # Command events
    COMMAND_SENT = auto()
    COMMAND_SUCCESS = auto()
    COMMAND_FAILED = auto()
    COMMAND_TIMEOUT = auto()

    # Broadcast events
    BROADCAST_REQUESTED = auto()
    BROADCAST_ARMING = auto()
    BROADCAST_STARTED = auto()
    BROADCAST_STOPPED = auto()
    BROADCAST_FAILED = auto()

    # Channel events
    CHANNEL_ENABLED = auto()
    CHANNEL_DISABLED = auto()
    CHANNEL_FREQ_CHANGED = auto()
    CHANNEL_PENDING = auto()
    CHANNEL_CONFIRMED = auto()

    # State events (from device polling)
    DEVICE_STATE_UPDATED = auto()
    DEVICE_HEARTBEAT = auto()
    DEVICE_HEARTBEAT_LOST = auto()

    # Source events
    SOURCE_CHANGED = auto()
    MESSAGE_CHANGED = auto()

    # UI events
    UI_REFRESH_REQUESTED = auto()

    # Error events
    ERROR_OCCURRED = auto()

    # Watchdog events (Reddit: cannibal_catfish69 - "fail safely")
    WATCHDOG_HEARTBEAT_SENT = auto()  # GUI sent heartbeat to FPGA
    WATCHDOG_WARNING = auto()          # 80% of timeout reached
    WATCHDOG_TRIGGERED = auto()        # FAIL-SAFE ACTIVATED!
    WATCHDOG_RESET = auto()            # Watchdog manually reset
    WATCHDOG_ENABLED = auto()          # Watchdog turned on
    WATCHDOG_DISABLED = auto()         # Watchdog turned off


@dataclass
class Event:
    """Event object carrying type and data."""
    type: EventType
    data: Dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.data is None:
            self.data = {}


class EventBus:
    """
    Central event dispatcher.

    Usage:
        bus = EventBus()
        bus.subscribe(EventType.CONNECT_SUCCESS, my_callback)
        bus.publish(Event(EventType.CONNECT_SUCCESS, {"ip": "192.168.0.100"}))
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern - one bus for entire app."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._event_log: List[Event] = []
        self._log_enabled = True
        self._max_log_size = 1000
        self._lock = threading.Lock()
        self._initialized = True

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribe to an event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Unsubscribe from an event type."""
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)

    def publish(self, event: Event):
        """Publish an event to all subscribers."""
        # Log event
        if self._log_enabled:
            self._event_log.append(event)
            if len(self._event_log) > self._max_log_size:
                self._event_log = self._event_log[-self._max_log_size:]

        # Notify subscribers
        with self._lock:
            subscribers = self._subscribers.get(event.type, []).copy()

        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"[EventBus] Error in subscriber: {e}")

    def publish_async(self, event: Event):
        """Publish event in a separate thread (non-blocking)."""
        thread = threading.Thread(target=self.publish, args=(event,), daemon=True)
        thread.start()

    def get_event_log(self, event_type: EventType = None, limit: int = 100) -> List[Event]:
        """Get recent events, optionally filtered by type."""
        if event_type:
            filtered = [e for e in self._event_log if e.type == event_type]
            return filtered[-limit:]
        return self._event_log[-limit:]

    def clear_log(self):
        """Clear event log."""
        self._event_log = []


# Global instance
event_bus = EventBus()

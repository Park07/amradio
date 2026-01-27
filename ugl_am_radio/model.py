"""
Model Layer - Stateless Design with Fail-Safe Watchdog
=======================================================
Author: William Park
Date: January 2026

- Stateless UI: State comes from device polling only
- Polling thread: Background thread for TCP, UI never blocks
- Fail-safe: Hardware watchdog for safety
- Auto-reconnect: Automatic recovery on connection loss
- State machines: Proper connection/broadcast/watchdog states
"""

import socket
import threading
import time
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from config import Config
from event_bus import EventBus, Event, EventType, event_bus


class ConnectionState(Enum):
    """Connection state machine states."""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    ERROR = auto()


class BroadcastState(Enum):
    """Broadcast state machine states."""
    IDLE = auto()
    ARMING = auto()        # Command sent, waiting for confirmation
    BROADCASTING = auto()  # Confirmed from device
    STOPPING = auto()      # Stop command sent, waiting for confirmation
    ERROR = auto()


class WatchdogState(Enum):
    """Watchdog states for fail-safe monitoring."""
    OK = auto()
    WARNING = auto()      # 80% of timeout reached
    TRIGGERED = auto()    # FAIL-SAFE ACTIVATED!
    DISABLED = auto()


@dataclass
class ChannelState:
    """State for a single channel - from device, not assumed."""
    id: int
    frequency: int = 0
    enabled: bool = False
    confirmed: bool = False  # True if state confirmed from device


@dataclass
class DeviceState:
    """
    Actual device state - populated ONLY from polling.
    This is the source of truth, not local assumptions.

    Reddit (alexforencich, 7 upvotes):
    "Stateless user interfaces. Push a button to send a command,
    GUI doesn't change until it gets a state update from the hardware."
    """
    connected: bool = False
    broadcasting: bool = False
    source: str = ""
    channels: List[ChannelState] = field(default_factory=list)
    last_update: datetime = None
    stale: bool = True  # True if we haven't polled recently

    # Watchdog state
    watchdog_enabled: bool = True
    watchdog_triggered: bool = False
    watchdog_warning: bool = False
    watchdog_time_remaining: int = 5

    def __post_init__(self):
        if not self.channels:
            self.channels = [
                ChannelState(id=ch["id"], frequency=ch["default_freq"])
                for ch in Config.CHANNELS
            ]


@dataclass
class PendingCommand:
    """Tracks commands waiting for confirmation."""
    command: str
    sent_at: datetime
    timeout: float = 2.0
    retries: int = 0
    max_retries: int = 3


class AuditLogger:
    """Thread-safe audit logger."""

    def __init__(self, log_file: str = Config.LOG_FILE):
        self.log_file = log_file
        self._lock = threading.Lock()
        self._log_entries = []

    def log(self, message: str, level: str = "INFO") -> str:
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime(Config.LOG_TIMESTAMP_FORMAT)
        entry = f"[{timestamp}] [{level}] {message}"

        with self._lock:
            self._log_entries.append(entry)
            if len(self._log_entries) > Config.LOG_MAX_LINES:
                self._log_entries = self._log_entries[-Config.LOG_MAX_LINES:]

            try:
                with open(self.log_file, "a") as f:
                    f.write(entry + "\n")
            except Exception:
                pass

        print(entry)
        return entry

    def get_entries(self, limit: int = 15) -> List[str]:
        """Get recent log entries."""
        with self._lock:
            return self._log_entries[-limit:]


class NetworkManager:
    """
    Handles all network operations in background thread.

    Reddit advice (exodusTay, 3 upvotes):
    "Create a separate thread that polls the device and UI is updated
    from this thread using signal/slots (thread-safe callbacks)."
    """

    def __init__(self, logger: AuditLogger):
        self.logger = logger
        self.socket: Optional[socket.socket] = None
        self._lock = threading.Lock()

        # Connection state machine
        self.connection_state = ConnectionState.DISCONNECTED
        self.ip = ""
        self.port = 0

        # Threading
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None

        # Polling settings
        self.poll_interval = Config.POLL_INTERVAL
        self.heartbeat_interval = Config.HEARTBEAT_INTERVAL
        self.heartbeat_timeout = Config.HEARTBEAT_TIMEOUT
        self._last_heartbeat = None

        # Auto-reconnect
        self.auto_reconnect = Config.AUTO_RECONNECT
        self.reconnect_delay = Config.RECONNECT_DELAY
        self.max_reconnect_attempts = Config.MAX_RECONNECT_ATTEMPTS
        self._reconnect_count = 0

    def connect(self, ip: str, port: int) -> bool:
        """Initiate connection (non-blocking, starts background threads)."""
        self.ip = ip
        self.port = port
        self.connection_state = ConnectionState.CONNECTING
        self.auto_reconnect = Config.AUTO_RECONNECT

        event_bus.publish(Event(EventType.CONNECT_REQUESTED, {"ip": ip, "port": port}))

        # Start connection in background
        thread = threading.Thread(target=self._connect_async, daemon=True)
        thread.start()
        return True

    def _connect_async(self):
        """Actual connection logic (runs in background)."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(Config.SOCKET_TIMEOUT)
            self.socket.connect((self.ip, self.port))

            self.connection_state = ConnectionState.CONNECTED
            self._reconnect_count = 0
            self._last_heartbeat = datetime.now()
            self.logger.log(f"Connected to {self.ip}:{self.port}")

            event_bus.publish(Event(EventType.CONNECT_SUCCESS, {"ip": self.ip, "port": self.port}))

            # Start background threads
            self._start_background_threads()

        except socket.timeout:
            self.connection_state = ConnectionState.ERROR
            self.logger.log(f"Connection timeout: {self.ip}:{self.port}", "ERROR")
            event_bus.publish(Event(EventType.CONNECT_FAILED, {"reason": "timeout"}))
            self._handle_connection_failure()

        except Exception as e:
            self.connection_state = ConnectionState.ERROR
            self.logger.log(f"Connection failed: {e}", "ERROR")
            event_bus.publish(Event(EventType.CONNECT_FAILED, {"reason": str(e)}))
            self._handle_connection_failure()

    def _start_background_threads(self):
        """Start polling and heartbeat threads."""
        self._running = True

        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _poll_loop(self):
        """
        Background polling loop.

        CRITICAL: Sends WATCHDOG:RESET before STATUS? to keep FPGA fail-safe alive.
        If this loop stops (GUI crash, network issue), FPGA will auto-stop broadcast.

        Reddit advice (alexforencich, 7 upvotes):
        "Stateless user interfaces. Push a button to send a command,
        GUI doesn't change until it gets a state update from the hardware."
        """
        while self._running and self.connection_state == ConnectionState.CONNECTED:
            try:
                # WATCHDOG HEARTBEAT - Must come first!
                # This keeps the FPGA fail-safe timer from triggering
                self.send_command(Config.SCPI.WATCHDOG_RESET, log=False)

                # Poll device status
                status = self.send_command(Config.SCPI.QUERY_STATUS)
                if status:
                    self._parse_and_publish_status(status)

                time.sleep(self.poll_interval)

            except Exception as e:
                self.logger.log(f"Poll error: {e}", "ERROR")
                time.sleep(self.poll_interval)

    def _heartbeat_loop(self):
        """Background heartbeat to detect connection loss."""
        while self._running and self.connection_state == ConnectionState.CONNECTED:
            try:
                response = self.send_command(Config.SCPI.QUERY_ID, log=False)
                if response:
                    self._last_heartbeat = datetime.now()
                    event_bus.publish(Event(EventType.DEVICE_HEARTBEAT))
                else:
                    self._check_heartbeat_timeout()

                time.sleep(self.heartbeat_interval)

            except Exception as e:
                self.logger.log(f"Heartbeat error: {e}", "ERROR")
                self._check_heartbeat_timeout()
                time.sleep(self.heartbeat_interval)

    def _check_heartbeat_timeout(self):
        """Check if heartbeat has timed out."""
        if self._last_heartbeat:
            elapsed = (datetime.now() - self._last_heartbeat).total_seconds()
            if elapsed > self.heartbeat_timeout:
                self.logger.log("Heartbeat lost - connection may be down", "WARN")
                event_bus.publish(Event(EventType.DEVICE_HEARTBEAT_LOST))
                self._handle_connection_failure()

    def _handle_connection_failure(self):
        """Handle connection failure with auto-reconnect."""
        self._running = False

        if not self.auto_reconnect:
            self.connection_state = ConnectionState.DISCONNECTED
            event_bus.publish(Event(EventType.DISCONNECTED))
            return

        if self._reconnect_count >= self.max_reconnect_attempts:
            self.logger.log("Max reconnect attempts reached", "ERROR")
            self.connection_state = ConnectionState.DISCONNECTED
            event_bus.publish(Event(EventType.DISCONNECTED, {"reason": "max_retries"}))
            return

        self._reconnect_count += 1
        self.connection_state = ConnectionState.RECONNECTING
        self.logger.log(f"Reconnecting... attempt {self._reconnect_count}/{self.max_reconnect_attempts}")
        event_bus.publish(Event(EventType.RECONNECT_ATTEMPT, {"attempt": self._reconnect_count}))

        # Close old socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        time.sleep(self.reconnect_delay)
        self._connect_async()

    def _parse_and_publish_status(self, status: str):
        """Parse status response and publish structured data."""
        try:
            data = {}
            for part in status.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    data[key.strip()] = value.strip()

            # Check for watchdog trigger - critical safety event!
            if data.get("watchdog_triggered") == "1":
                self.logger.log("⚠️ WATCHDOG TRIGGERED - FPGA fail-safe activated!", "ERROR")
                event_bus.publish(Event(EventType.WATCHDOG_TRIGGERED, data))
            elif data.get("watchdog_warning") == "1":
                event_bus.publish(Event(EventType.WATCHDOG_WARNING, data))

            event_bus.publish(Event(EventType.DEVICE_STATE_UPDATED, data))

        except Exception as e:
            self.logger.log(f"Status parse error: {e}", "WARN")

    def disconnect(self):
        """Disconnect and stop background threads."""
        self._running = False
        self.auto_reconnect = False  # Don't reconnect on intentional disconnect

        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

        self.connection_state = ConnectionState.DISCONNECTED
        self.logger.log("Disconnected")
        event_bus.publish(Event(EventType.DISCONNECTED))

    def send_command(self, command: str, log: bool = True) -> Optional[str]:
        """Send command (thread-safe)."""
        if self.connection_state != ConnectionState.CONNECTED or not self.socket:
            return None

        with self._lock:
            try:
                cmd_bytes = (command.strip() + "\n").encode()
                self.socket.sendall(cmd_bytes)

                if log:
                    self.logger.log(f"TX: {command}")

                if "?" in command:
                    response = self.socket.recv(4096).decode().strip()
                    if log:
                        self.logger.log(f"RX: {response}")
                    return response

                return ""

            except socket.timeout:
                self.logger.log(f"Timeout: {command}", "ERROR")
                event_bus.publish(Event(EventType.COMMAND_TIMEOUT, {"command": command}))
                return None
            except Exception as e:
                self.logger.log(f"Send error: {e}", "ERROR")
                event_bus.publish(Event(EventType.COMMAND_FAILED, {"command": command, "error": str(e)}))
                return None

    @property
    def is_connected(self) -> bool:
        return self.connection_state == ConnectionState.CONNECTED


class Model:
    """
    Main model - STATELESS design with fail-safe watchdog.

    Reddit advice (alexforencich, 7 upvotes):
    "Never keep state in UI, poll device, use last known state"

    Key principle: self.device_state is ONLY updated from device polling,
    never from local assumptions after sending commands.
    """

    def __init__(self):
        self.logger = AuditLogger()
        self.network = NetworkManager(self.logger)

        # Device state - source of truth, only from polling
        self.device_state = DeviceState()

        # Pending state - what we've requested but not confirmed
        self.pending_state: Dict[str, Any] = {}

        # State machines
        self.connection_state = ConnectionState.DISCONNECTED
        self.broadcast_state = BroadcastState.IDLE
        self.watchdog_state = WatchdogState.OK

        # Subscribe to network events
        event_bus.subscribe(EventType.CONNECT_SUCCESS, self._on_connect_success)
        event_bus.subscribe(EventType.CONNECT_FAILED, self._on_connect_failed)
        event_bus.subscribe(EventType.DISCONNECTED, self._on_disconnected)
        event_bus.subscribe(EventType.RECONNECT_ATTEMPT, self._on_reconnect_attempt)
        event_bus.subscribe(EventType.DEVICE_STATE_UPDATED, self._on_device_state_updated)
        event_bus.subscribe(EventType.DEVICE_HEARTBEAT_LOST, self._on_heartbeat_lost)
        event_bus.subscribe(EventType.WATCHDOG_TRIGGERED, self._on_watchdog_triggered)
        event_bus.subscribe(EventType.WATCHDOG_WARNING, self._on_watchdog_warning)

    # === Event Handlers ===

    def _on_connect_success(self, event: Event):
        """Handle successful connection."""
        self.connection_state = ConnectionState.CONNECTED
        self.device_state.connected = True
        self.device_state.stale = True  # Will be updated by first poll

    def _on_connect_failed(self, event: Event):
        """Handle failed connection."""
        self.connection_state = ConnectionState.ERROR
        self.device_state.connected = False

    def _on_disconnected(self, event: Event):
        """Handle disconnection."""
        self.connection_state = ConnectionState.DISCONNECTED
        self.device_state.connected = False
        self.device_state.stale = True
        self.broadcast_state = BroadcastState.IDLE

    def _on_reconnect_attempt(self, event: Event):
        """Handle reconnection attempt."""
        self.connection_state = ConnectionState.RECONNECTING

    def _on_heartbeat_lost(self, event: Event):
        """Handle heartbeat loss."""
        self.device_state.stale = True

    def _on_watchdog_triggered(self, event: Event):
        """
        Handle watchdog trigger - FPGA has auto-stopped broadcast!

        Reddit (cannibal_catfish69): "Controllers should fail safely"
        """
        self.watchdog_state = WatchdogState.TRIGGERED
        self.device_state.watchdog_triggered = True
        self.broadcast_state = BroadcastState.IDLE  # FPGA killed broadcast

        self.logger.log("🚨 FAIL-SAFE ACTIVATED: RF output disabled!", "ERROR")

    def _on_watchdog_warning(self, event: Event):
        """Handle watchdog warning (80% of timeout)."""
        self.watchdog_state = WatchdogState.WARNING
        self.device_state.watchdog_warning = True

    def _on_device_state_updated(self, event: Event):
        """
        Update local state from device polling.
        THIS IS THE ONLY PLACE device_state gets updated.
        """
        data = event.data

        # Update watchdog state
        if "watchdog_triggered" in data:
            triggered = data["watchdog_triggered"] in ["1", "true", "True", True]
            self.device_state.watchdog_triggered = triggered
            if triggered:
                self.watchdog_state = WatchdogState.TRIGGERED
            elif data.get("watchdog_warning") in ["1", "true", "True", True]:
                self.watchdog_state = WatchdogState.WARNING
                self.device_state.watchdog_warning = True
            else:
                self.watchdog_state = WatchdogState.OK
                self.device_state.watchdog_warning = False

        if "watchdog_time" in data:
            try:
                self.device_state.watchdog_time_remaining = int(data["watchdog_time"])
            except ValueError:
                pass

        if "watchdog_enabled" in data:
            self.device_state.watchdog_enabled = data["watchdog_enabled"] in ["1", "true", "True", True]

        # Update broadcast state from DEVICE (not from our request)
        if "broadcasting" in data:
            was_broadcasting = self.device_state.broadcasting
            self.device_state.broadcasting = data["broadcasting"] in ["1", "true", "True", True]

            # Update broadcast state machine based on DEVICE state
            if self.device_state.broadcasting and not was_broadcasting:
                self.broadcast_state = BroadcastState.BROADCASTING
                event_bus.publish(Event(EventType.BROADCAST_STARTED))
            elif not self.device_state.broadcasting and was_broadcasting:
                self.broadcast_state = BroadcastState.IDLE
                event_bus.publish(Event(EventType.BROADCAST_STOPPED))

        # Update channel states from device
        for ch in self.device_state.channels:
            key_enabled = f"ch{ch.id}_enabled"
            key_freq = f"ch{ch.id}_freq"

            if key_enabled in data:
                ch.enabled = data[key_enabled] in ["1", "true", "True", True]
                ch.confirmed = True

            if key_freq in data:
                try:
                    ch.frequency = int(data[key_freq])
                    ch.confirmed = True
                except ValueError:
                    pass

        # Update source
        if "source" in data:
            self.device_state.source = data["source"]

        self.device_state.last_update = datetime.now()
        self.device_state.stale = False

        # Clear pending state for confirmed items
        self.pending_state.clear()

    # === Public API ===

    def connect(self, ip: str, port: int):
        """Request connection (async, non-blocking)."""
        self.connection_state = ConnectionState.CONNECTING
        self.network.connect(ip, port)

    def disconnect(self):
        """Request disconnection."""
        if self.device_state.broadcasting:
            self.set_broadcast(False)
        self.network.disconnect()

    def set_source(self, source: str):
        """Request source change - won't update UI until confirmed."""
        if source not in [Config.SOURCE_ADC, Config.SOURCE_BRAM]:
            return

        self.pending_state["source"] = source
        cmd = Config.SCPI.SET_SOURCE.format(source)
        self.network.send_command(cmd)

        event_bus.publish(Event(EventType.SOURCE_CHANGED, {"source": source, "pending": True}))

    def set_message(self, message_id: int):
        """Request message change."""
        self.pending_state["message"] = message_id
        cmd = Config.SCPI.SET_MESSAGE.format(message_id)
        self.network.send_command(cmd)

        event_bus.publish(Event(EventType.MESSAGE_CHANGED, {"message_id": message_id, "pending": True}))

    def set_channel_frequency(self, channel_id: int, frequency: int):
        """Request frequency change - won't update UI until confirmed."""
        self.pending_state[f"ch{channel_id}_freq"] = frequency
        cmd = Config.SCPI.SET_FREQ.format(channel_id, frequency)
        self.network.send_command(cmd)

        event_bus.publish(Event(EventType.CHANNEL_FREQ_CHANGED, {
            "channel_id": channel_id,
            "frequency": frequency,
            "pending": True
        }))

    def set_channel_enabled(self, channel_id: int, enabled: bool):
        """Request channel enable/disable - won't update UI until confirmed."""
        self.pending_state[f"ch{channel_id}_enabled"] = enabled
        state_str = "ON" if enabled else "OFF"
        cmd = Config.SCPI.SET_OUTPUT.format(channel_id, state_str)
        self.network.send_command(cmd)

        event_type = EventType.CHANNEL_ENABLED if enabled else EventType.CHANNEL_DISABLED
        event_bus.publish(Event(event_type, {"channel_id": channel_id, "pending": True}))

    def set_broadcast(self, active: bool):
        """
        Request broadcast start/stop.

        Reddit advice: UI shows intermediate state until device confirms.
        """
        # Check watchdog before allowing broadcast
        if active and self.device_state.watchdog_triggered:
            self.logger.log("Cannot start broadcast - watchdog triggered!", "ERROR")
            event_bus.publish(Event(EventType.ERROR_OCCURRED, {
                "message": "Reset watchdog before broadcast"
            }))
            return

        if active:
            self.broadcast_state = BroadcastState.ARMING  # Intermediate state
            event_bus.publish(Event(EventType.BROADCAST_ARMING))
        else:
            self.broadcast_state = BroadcastState.STOPPING

        state_str = "ON" if active else "OFF"
        cmd = Config.SCPI.SET_BROADCAST.format(state_str)
        self.network.send_command(cmd)

        # Note: We DON'T set device_state.broadcasting here
        # It will be updated when we poll and device confirms

    def reset_watchdog(self):
        """Manually reset watchdog after a trigger."""
        self.network.send_command(Config.SCPI.WATCHDOG_RESET)
        self.watchdog_state = WatchdogState.OK
        self.device_state.watchdog_triggered = False
        self.device_state.watchdog_warning = False
        event_bus.publish(Event(EventType.WATCHDOG_RESET))

    def set_watchdog_enabled(self, enabled: bool):
        """Enable or disable the fail-safe watchdog."""
        state = "ON" if enabled else "OFF"
        self.network.send_command(Config.SCPI.WATCHDOG_ENABLE.format(state))

    # === Getters (return device state, not pending) ===

    def is_connected(self) -> bool:
        return self.network.is_connected

    def is_broadcasting(self) -> bool:
        return self.device_state.broadcasting

    def is_state_stale(self) -> bool:
        return self.device_state.stale

    def is_watchdog_triggered(self) -> bool:
        return self.device_state.watchdog_triggered

    def get_broadcast_state(self) -> BroadcastState:
        return self.broadcast_state

    def get_connection_state(self) -> ConnectionState:
        return self.connection_state

    def get_watchdog_state(self) -> WatchdogState:
        return self.watchdog_state

    def get_log_entries(self, limit: int = 15) -> List[str]:
        return self.logger.get_entries(limit)

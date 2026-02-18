#![allow(dead_code)]
// event_bus.rs - FULL EVENT SYSTEM
// Pub/sub pattern using tokio broadcast channels

use tokio::sync::broadcast;

use crate::state_machine::{ConnectionState, SourceMode};

// EVENT TYPES
#[derive(Clone, Debug)]
pub enum EventType {
    // CONNECTION EVENTS
    ConnectSuccess,
    ConnectFailed(String),
    Disconnected,
    ConnectionLost,
    ConnectionStateChanged(ConnectionState),

    // RECONNECTION EVENTS
    ReconnectAttempt(u8),  // Attempt number
    ReconnectSuccess,
    ReconnectFailed,

    // BROADCAST EVENTS
    BroadcastStarted,
    BroadcastStopped,

    // WATCHDOG EVENTS (CRITICAL FOR SAFETY)
    WatchdogOk,
    WatchdogWarning,
    WatchdogTriggered,  // FPGA killed output - this is serious!
    WatchdogReset,

    // CHANNEL EVENTS
    ChannelUpdated(u8),      // Channel ID
    ChannelEnabled(u8),
    ChannelDisabled(u8),
    FrequencyChanged(u8, u32),  // Channel ID, new frequency

    // SOURCE EVENTS
    SourceChanged(SourceMode),

    // STATE EVENTS
    DeviceStateUpdated,

    // ERROR EVENTS
    CommandFailed(String),
    NetworkError(String),
}

// EVENT BUS
pub struct EventBus {
    sender: broadcast::Sender<EventType>,
}

impl EventBus {
    /// Create new event bus with buffer capacity
    pub fn new() -> Self {
        let (sender, _) = broadcast::channel(256);
        Self { sender }
    }

    /// Emit an event to all subscribers
    pub fn emit(&self, event: EventType) {
        // Log significant events
        match &event {
            EventType::ConnectSuccess => println!("[EVENT] Connect success"),
            EventType::Disconnected => println!("[EVENT] Disconnected"),
            EventType::BroadcastStarted => println!("[EVENT] Broadcast started"),
            EventType::BroadcastStopped => println!("[EVENT] Broadcast stopped"),
            EventType::WatchdogTriggered => println!("[EVENT] ⚠️  WATCHDOG TRIGGERED!"),
            EventType::ConnectionLost => println!("[EVENT] Connection lost"),
            _ => {}
        }

        // Send to all subscribers (ignore if no subscribers)
        let _ = self.sender.send(event);
    }

    /// Subscribe to receive events
    pub fn subscribe(&self) -> broadcast::Receiver<EventType> {
        self.sender.subscribe()
    }

    /// Get a clone of the sender (for passing to other threads/tasks)
    pub fn get_sender(&self) -> broadcast::Sender<EventType> {
        self.sender.clone()
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new()
    }
}

// EVENT LISTENER EXAMPLE
/// Example of how to listen for events in a background task
pub async fn example_event_listener(mut rx: broadcast::Receiver<EventType>) {
    loop {
        match rx.recv().await {
            Ok(event) => {
                match event {
                    EventType::WatchdogTriggered => {
                        // CRITICAL: Handle watchdog trigger
                        eprintln!("⚠️  WATCHDOG TRIGGERED - FPGA STOPPED OUTPUT!");
                        // In real code: notify UI, log, maybe try to recover
                    }
                    EventType::ConnectionLost => {
                        eprintln!("Connection lost - attempting reconnect...");
                    }
                    EventType::BroadcastStarted => {
                        println!("📡 Broadcast is now LIVE");
                    }
                    EventType::BroadcastStopped => {
                        println!("📡 Broadcast stopped");
                    }
                    EventType::ChannelUpdated(ch) => {
                        println!("Channel {} updated", ch);
                    }
                    EventType::DeviceStateUpdated => {
                        // This fires every 500ms - usually just update UI
                    }
                    _ => {}
                }
            }
            Err(broadcast::error::RecvError::Lagged(n)) => {
                eprintln!("Event listener lagged by {} events", n);
            }
            Err(broadcast::error::RecvError::Closed) => {
                println!("Event bus closed");
                break;
            }
        }
    }
}

// TAURI EVENT BRIDGE
/// Bridge events to Tauri window for UI updates

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_event_bus() {
        let bus = EventBus::new();
        let mut rx = bus.subscribe();

        bus.emit(EventType::ConnectSuccess);

        let event = rx.recv().await.unwrap();
        assert!(matches!(event, EventType::ConnectSuccess));
    }

    #[tokio::test]
    async fn test_multiple_subscribers() {
        let bus = EventBus::new();
        let mut rx1 = bus.subscribe();
        let mut rx2 = bus.subscribe();

        bus.emit(EventType::BroadcastStarted);

        // Both should receive the event
        assert!(matches!(rx1.recv().await.unwrap(), EventType::BroadcastStarted));
        assert!(matches!(rx2.recv().await.unwrap(), EventType::BroadcastStarted));
    }
}

#[cfg(test)]
mod additional_tests {
    use super::*;

    #[tokio::test]
    async fn test_watchdog_event_types() {
        let bus = EventBus::new();
        let mut rx = bus.subscribe();

        bus.emit(EventType::WatchdogTriggered);
        assert!(matches!(rx.recv().await.unwrap(), EventType::WatchdogTriggered));

        bus.emit(EventType::WatchdogWarning);
        assert!(matches!(rx.recv().await.unwrap(), EventType::WatchdogWarning));
    }

    #[tokio::test]
    async fn test_event_ordering() {
        let bus = EventBus::new();
        let mut rx = bus.subscribe();

        bus.emit(EventType::ConnectSuccess);
        bus.emit(EventType::BroadcastStarted);
        bus.emit(EventType::WatchdogTriggered);

        assert!(matches!(rx.recv().await.unwrap(), EventType::ConnectSuccess));
        assert!(matches!(rx.recv().await.unwrap(), EventType::BroadcastStarted));
        assert!(matches!(rx.recv().await.unwrap(), EventType::WatchdogTriggered));
    }

    #[test]
    fn test_no_subscribers_doesnt_panic() {
        let bus = EventBus::new();
        bus.emit(EventType::ConnectSuccess);
        bus.emit(EventType::WatchdogTriggered);
    }
}

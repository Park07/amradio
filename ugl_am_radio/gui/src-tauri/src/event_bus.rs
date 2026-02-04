//! Event Bus - Central Event Dispatcher
//! 
//! Direct port from Python event_bus.py using tokio broadcast channels
//! Author: William Park

use chrono::{DateTime, Utc};
use once_cell::sync::Lazy;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::broadcast;

/// All possible events in the system
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EventType {
    // Connection events
    ConnectRequested,
    ConnectSuccess,
    ConnectFailed,
    DisconnectRequested,
    Disconnected,
    ConnectionLost,
    ReconnectAttempt,

    // Command events
    CommandSent,
    CommandSuccess,
    CommandFailed,
    CommandTimeout,

    // Broadcast events
    BroadcastRequested,
    BroadcastArming,
    BroadcastStarted,
    BroadcastStopped,
    BroadcastFailed,

    // Channel events
    ChannelEnabled,
    ChannelDisabled,
    ChannelFreqChanged,
    ChannelPending,
    ChannelConfirmed,

    // State events (from device polling)
    DeviceStateUpdated,
    DeviceHeartbeat,
    DeviceHeartbeatLost,

    // Source events
    SourceChanged,
    MessageChanged,

    // UI events
    UiRefreshRequested,

    // Error events
    ErrorOccurred,

    // Watchdog events
    WatchdogHeartbeatSent,
    WatchdogWarning,
    WatchdogTriggered,
    WatchdogReset,
    WatchdogEnabled,
    WatchdogDisabled,
}

/// Event object carrying type and data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub event_type: EventType,
    pub data: HashMap<String, serde_json::Value>,
    pub timestamp: DateTime<Utc>,
}

impl Event {
    pub fn new(event_type: EventType) -> Self {
        Self {
            event_type,
            data: HashMap::new(),
            timestamp: Utc::now(),
        }
    }

    pub fn with_data(event_type: EventType, data: HashMap<String, serde_json::Value>) -> Self {
        Self {
            event_type,
            data,
            timestamp: Utc::now(),
        }
    }

    /// Helper to create data map from key-value pairs
    pub fn data_from<const N: usize>(pairs: [(&str, serde_json::Value); N]) -> HashMap<String, serde_json::Value> {
        pairs.into_iter().map(|(k, v)| (k.to_string(), v)).collect()
    }
}

/// Central event dispatcher using tokio broadcast
pub struct EventBus {
    sender: broadcast::Sender<Event>,
    event_log: RwLock<Vec<Event>>,
    max_log_size: usize,
}

impl EventBus {
    fn new() -> Self {
        let (sender, _) = broadcast::channel(256);
        Self {
            sender,
            event_log: RwLock::new(Vec::new()),
            max_log_size: 1000,
        }
    }

    /// Subscribe to events - returns a receiver
    pub fn subscribe(&self) -> broadcast::Receiver<Event> {
        self.sender.subscribe()
    }

    /// Publish an event to all subscribers
    pub fn publish(&self, event: Event) {
        // Log event
        {
            let mut log = self.event_log.write();
            log.push(event.clone());
            if log.len() > self.max_log_size {
                let drain_count = log.len() - self.max_log_size;
                log.drain(0..drain_count);
            }
        }

        // Send to subscribers (ignore if no receivers)
        let _ = self.sender.send(event);
    }

    /// Convenience method to publish a simple event
    pub fn emit(&self, event_type: EventType) {
        self.publish(Event::new(event_type));
    }

    /// Convenience method to publish event with data
    pub fn emit_with_data(&self, event_type: EventType, data: HashMap<String, serde_json::Value>) {
        self.publish(Event::with_data(event_type, data));
    }

    /// Get recent events, optionally filtered by type
    pub fn get_event_log(&self, event_type: Option<EventType>, limit: usize) -> Vec<Event> {
        let log = self.event_log.read();
        let filtered: Vec<Event> = if let Some(et) = event_type {
            log.iter().filter(|e| e.event_type == et).cloned().collect()
        } else {
            log.clone()
        };
        filtered.into_iter().rev().take(limit).collect()
    }

    /// Clear event log
    pub fn clear_log(&self) {
        self.event_log.write().clear();
    }
}

// Global singleton instance
pub static EVENT_BUS: Lazy<Arc<EventBus>> = Lazy::new(|| Arc::new(EventBus::new()));

/// Get the global event bus instance
pub fn event_bus() -> &'static Arc<EventBus> {
    &EVENT_BUS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_event_bus_publish_subscribe() {
        let bus = EventBus::new();
        let mut rx = bus.subscribe();

        bus.emit(EventType::ConnectSuccess);

        let event = rx.recv().await.unwrap();
        assert_eq!(event.event_type, EventType::ConnectSuccess);
    }
}

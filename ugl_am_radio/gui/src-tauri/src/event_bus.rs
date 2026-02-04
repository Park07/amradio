// ============================================================
// event_bus.rs - PUB/SUB EVENT SYSTEM
// Same concept as Python's event_bus.py
// ============================================================

use tokio::sync::broadcast;

// ============================================================
// EVENT TYPES
// Same events as Python had
// ============================================================
#[derive(Clone, Debug)]
pub enum EventType {
    // Connection events
    ConnectSuccess,
    ConnectFailed(String),
    Disconnected,
    ReconnectAttempt(u8),

    // Broadcast events
    BroadcastStarted,
    BroadcastStopped,

    // Watchdog events (CRITICAL for safety)
    WatchdogOk,
    WatchdogWarning,
    WatchdogTriggered,  // FPGA stopped all output!

    // State events
    DeviceStateUpdated,
    ChannelUpdated(u8),
    SourceChanged(String),
}

// ============================================================
// EVENT BUS
// Python used callbacks, Rust uses broadcast channels
// ============================================================
pub struct EventBus {
    // Sender can be cloned to multiple producers
    sender: broadcast::Sender<EventType>,
}

impl EventBus {
    pub fn new() -> Self {
        // Create channel with buffer of 100 events
        let (sender, _) = broadcast::channel(100);
        Self { sender }
    }

    // ----------------------------------------------------------
    // EMIT EVENT (Same as Python's emit())
    // ----------------------------------------------------------
    pub fn emit(&self, event: EventType) {
        // Send to all subscribers
        let _ = self.sender.send(event);
    }

    // ----------------------------------------------------------
    // SUBSCRIBE (Same as Python's subscribe())
    // ----------------------------------------------------------
    pub fn subscribe(&self) -> broadcast::Receiver<EventType> {
        self.sender.subscribe()
    }

    // ----------------------------------------------------------
    // GET SENDER (For passing to other threads/tasks)
    // ----------------------------------------------------------
    pub fn get_sender(&self) -> broadcast::Sender<EventType> {
        self.sender.clone()
    }
}

// ============================================================
// USAGE EXAMPLE
// ============================================================
//
// // In model.rs - emit events
// event_bus.emit(EventType::BroadcastStarted);
//
// // In another task - subscribe and handle
// let mut rx = event_bus.subscribe();
// loop {
//     match rx.recv().await {
//         Ok(EventType::WatchdogTriggered) => {
//             // CRITICAL: Stop broadcast immediately!
//             stop_broadcast().await;
//             log_error("WATCHDOG TRIGGERED!");
//         }
//         Ok(EventType::DeviceStateUpdated) => {
//             // Update UI via Tauri event
//             window.emit("state-updated", &state).unwrap();
//         }
//         _ => {}
//     }
// }

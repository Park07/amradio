// state_machine.rs
// Enforces valid state transitions for broadcast control

use serde::{Deserialize, Serialize};

/// Broadcast state machine
/// Transitions: IDLE → ARMED → BROADCASTING → IDLE
///              Any state → EMERGENCY → IDLE
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BroadcastState {
    Idle,
    Arming,       // Intermediate: arm requested, waiting for confirmation
    Armed,
    Starting,     // Intermediate: start requested, waiting for confirmation
    Broadcasting,
    Stopping,     // Intermediate: stop requested, waiting for confirmation
    Emergency,
}

impl Default for BroadcastState {
    fn default() -> Self {
        Self::Idle
    }
}

impl BroadcastState {
    /// Request to arm - returns intermediate state
    pub fn request_arm(&self) -> Result<BroadcastState, &'static str> {
        match self {
            BroadcastState::Idle => Ok(BroadcastState::Arming),
            BroadcastState::Arming => Err("Already arming"),
            BroadcastState::Armed => Err("Already armed"),
            BroadcastState::Starting => Err("Cannot arm while starting"),
            BroadcastState::Broadcasting => Err("Cannot arm while broadcasting"),
            BroadcastState::Stopping => Err("Cannot arm while stopping"),
            BroadcastState::Emergency => Err("Cannot arm during emergency"),
        }
    }

    /// Confirm armed (from polling)
    pub fn confirm_armed(&self) -> BroadcastState {
        match self {
            BroadcastState::Arming => BroadcastState::Armed,
            other => *other,
        }
    }

    /// Request to start broadcast
    pub fn request_start(&self) -> Result<BroadcastState, &'static str> {
        match self {
            BroadcastState::Idle => Err("Must arm before broadcasting"),
            BroadcastState::Arming => Err("Still arming, please wait"),
            BroadcastState::Armed => Ok(BroadcastState::Starting),
            BroadcastState::Starting => Err("Already starting"),
            BroadcastState::Broadcasting => Err("Already broadcasting"),
            BroadcastState::Stopping => Err("Currently stopping"),
            BroadcastState::Emergency => Err("Already in emergency mode"),
        }
    }

    /// Confirm broadcasting (from polling)
    pub fn confirm_broadcasting(&self) -> BroadcastState {
        match self {
            BroadcastState::Starting => BroadcastState::Broadcasting,
            other => *other,
        }
    }

    /// Request to stop
    pub fn request_stop(&self) -> Result<BroadcastState, &'static str> {
        match self {
            BroadcastState::Idle => Err("Not broadcasting"),
            BroadcastState::Arming => Ok(BroadcastState::Idle), // Cancel arm
            BroadcastState::Armed => Ok(BroadcastState::Idle),  // Disarm
            BroadcastState::Starting => Ok(BroadcastState::Stopping),
            BroadcastState::Broadcasting => Ok(BroadcastState::Stopping),
            BroadcastState::Stopping => Err("Already stopping"),
            BroadcastState::Emergency => Err("Use stop_emergency for emergency"),
        }
    }

    /// Confirm stopped (from polling)
    pub fn confirm_stopped(&self) -> BroadcastState {
        match self {
            BroadcastState::Stopping => BroadcastState::Idle,
            other => *other,
        }
    }

    /// Emergency broadcast - from ANY state
    pub fn request_emergency(&self) -> Result<BroadcastState, &'static str> {
        match self {
            BroadcastState::Emergency => Err("Already in emergency mode"),
            _ => Ok(BroadcastState::Emergency),
        }
    }

    /// Stop emergency
    pub fn request_stop_emergency(&self) -> Result<BroadcastState, &'static str> {
        match self {
            BroadcastState::Emergency => Ok(BroadcastState::Idle),
            _ => Err("Not in emergency mode"),
        }
    }

    /// Check if actively broadcasting
    pub fn is_broadcasting(&self) -> bool {
        matches!(self, BroadcastState::Broadcasting | BroadcastState::Emergency)
    }

    /// Check if in intermediate state
    pub fn is_transitioning(&self) -> bool {
        matches!(self, BroadcastState::Arming | BroadcastState::Starting | BroadcastState::Stopping)
    }

    /// Get display string for UI
    pub fn display(&self) -> &'static str {
        match self {
            BroadcastState::Idle => "IDLE",
            BroadcastState::Arming => "ARMING...",
            BroadcastState::Armed => "ARMED",
            BroadcastState::Starting => "STARTING...",
            BroadcastState::Broadcasting => "BROADCASTING",
            BroadcastState::Stopping => "STOPPING...",
            BroadcastState::Emergency => "EMERGENCY",
        }
    }
}

/// Connection state machine
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ConnectionState {
    #[default]
    Disconnected,
    Connecting,
    Connected,
    Reconnecting,
}

impl ConnectionState {
    pub fn display(&self) -> &'static str {
        match self {
            ConnectionState::Disconnected => "DISCONNECTED",
            ConnectionState::Connecting => "CONNECTING...",
            ConnectionState::Connected => "CONNECTED",
            ConnectionState::Reconnecting => "RECONNECTING...",
        }
    }
}

/// Watchdog state
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum WatchdogState {
    #[default]
    Ok,
    Warning,
    Triggered,
}

impl WatchdogState {
    pub fn from_status(value: &str) -> Self {
        match value.to_uppercase().as_str() {
            "0" | "OK" => WatchdogState::Ok,
            "1" | "WARNING" => WatchdogState::Warning,
            "2" | "TRIGGERED" => WatchdogState::Triggered,
            _ => WatchdogState::Ok,
        }
    }

    pub fn display(&self) -> &'static str {
        match self {
            WatchdogState::Ok => "OK",
            WatchdogState::Warning => "WARNING",
            WatchdogState::Triggered => "TRIGGERED",
        }
    }
}

/// Audio source
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum SourceMode {
    #[default]
    Bram,
    Adc,
}

impl SourceMode {
    pub fn as_str(&self) -> &'static str {
        match self {
            SourceMode::Bram => "BRAM",
            SourceMode::Adc => "ADC",
        }
    }

    pub fn from_str(s: &str) -> Self {
        match s.to_uppercase().as_str() {
            "ADC" => SourceMode::Adc,
            _ => SourceMode::Bram,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normal_flow() {
        let mut state = BroadcastState::Idle;

        // Arm
        state = state.request_arm().unwrap();
        assert_eq!(state, BroadcastState::Arming);
        state = state.confirm_armed();
        assert_eq!(state, BroadcastState::Armed);

        // Start
        state = state.request_start().unwrap();
        assert_eq!(state, BroadcastState::Starting);
        state = state.confirm_broadcasting();
        assert_eq!(state, BroadcastState::Broadcasting);

        // Stop
        state = state.request_stop().unwrap();
        assert_eq!(state, BroadcastState::Stopping);
        state = state.confirm_stopped();
        assert_eq!(state, BroadcastState::Idle);
    }

    #[test]
    fn test_cannot_broadcast_without_arm() {
        let state = BroadcastState::Idle;
        assert!(state.request_start().is_err());
    }

    #[test]
    fn test_emergency_from_any_state() {
        assert!(BroadcastState::Idle.request_emergency().is_ok());
        assert!(BroadcastState::Armed.request_emergency().is_ok());
        assert!(BroadcastState::Broadcasting.request_emergency().is_ok());
    }
}

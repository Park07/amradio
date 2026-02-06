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

#[cfg(test)]
mod additional_tests {
    use super::*;

    #[test]
    fn test_cannot_double_arm() {
        assert!(BroadcastState::Arming.request_arm().is_err());
        assert!(BroadcastState::Armed.request_arm().is_err());
    }

    #[test]
    fn test_cannot_start_while_stopping() {
        assert!(BroadcastState::Stopping.request_start().is_err());
    }

    #[test]
    fn test_stop_cancels_arming() {
        assert_eq!(BroadcastState::Arming.request_stop().unwrap(), BroadcastState::Idle);
    }

    #[test]
    fn test_stop_disarms() {
        assert_eq!(BroadcastState::Armed.request_stop().unwrap(), BroadcastState::Idle);
    }

    #[test]
    fn test_emergency_stops_correctly() {
        assert_eq!(BroadcastState::Emergency.request_stop_emergency().unwrap(), BroadcastState::Idle);
    }

    #[test]
    fn test_cannot_stop_emergency_from_normal() {
        assert!(BroadcastState::Idle.request_stop_emergency().is_err());
        assert!(BroadcastState::Broadcasting.request_stop_emergency().is_err());
    }

    #[test]
    fn test_is_broadcasting() {
        assert!(!BroadcastState::Idle.is_broadcasting());
        assert!(!BroadcastState::Armed.is_broadcasting());
        assert!(BroadcastState::Broadcasting.is_broadcasting());
        assert!(BroadcastState::Emergency.is_broadcasting());
    }

    #[test]
    fn test_is_transitioning() {
        assert!(BroadcastState::Arming.is_transitioning());
        assert!(BroadcastState::Starting.is_transitioning());
        assert!(BroadcastState::Stopping.is_transitioning());
        assert!(!BroadcastState::Idle.is_transitioning());
        assert!(!BroadcastState::Broadcasting.is_transitioning());
    }

    #[test]
    fn test_display_strings() {
        assert_eq!(BroadcastState::Idle.display(), "IDLE");
        assert_eq!(BroadcastState::Broadcasting.display(), "BROADCASTING");
        assert_eq!(BroadcastState::Emergency.display(), "EMERGENCY");
        assert_eq!(ConnectionState::Disconnected.display(), "DISCONNECTED");
        assert_eq!(ConnectionState::Connected.display(), "CONNECTED");
    }

    #[test]
    fn test_watchdog_from_status() {
        assert_eq!(WatchdogState::from_status("OK"), WatchdogState::Ok);
        assert_eq!(WatchdogState::from_status("0"), WatchdogState::Ok);
        assert_eq!(WatchdogState::from_status("WARNING"), WatchdogState::Warning);
        assert_eq!(WatchdogState::from_status("1"), WatchdogState::Warning);
        assert_eq!(WatchdogState::from_status("TRIGGERED"), WatchdogState::Triggered);
        assert_eq!(WatchdogState::from_status("garbage"), WatchdogState::Ok);
    }

    #[test]
    fn test_source_mode_roundtrip() {
        assert_eq!(SourceMode::from_str("BRAM"), SourceMode::Bram);
        assert_eq!(SourceMode::from_str("ADC"), SourceMode::Adc);
        assert_eq!(SourceMode::from_str("bram"), SourceMode::Bram);
        assert_eq!(SourceMode::from_str("garbage"), SourceMode::Bram);
        assert_eq!(SourceMode::from_str(SourceMode::Bram.as_str()), SourceMode::Bram);
        assert_eq!(SourceMode::from_str(SourceMode::Adc.as_str()), SourceMode::Adc);
    }

    #[test]
    fn test_default_states() {
        assert_eq!(BroadcastState::default(), BroadcastState::Idle);
        assert_eq!(ConnectionState::default(), ConnectionState::Disconnected);
        assert_eq!(WatchdogState::default(), WatchdogState::Ok);
        assert_eq!(SourceMode::default(), SourceMode::Bram);
    }

    #[test]
    fn test_confirm_noop_wrong_state() {
        assert_eq!(BroadcastState::Idle.confirm_armed(), BroadcastState::Idle);
        assert_eq!(BroadcastState::Idle.confirm_broadcasting(), BroadcastState::Idle);
        assert_eq!(BroadcastState::Idle.confirm_stopped(), BroadcastState::Idle);
        assert_eq!(BroadcastState::Broadcasting.confirm_armed(), BroadcastState::Broadcasting);
    }
}

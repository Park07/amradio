//! Configuration for UGL AM Radio Control System
//! 
//! Direct port from Python config.py
//! Author: William Park

use serde::{Deserialize, Serialize};

/// Application configuration constants
pub struct Config;

impl Config {
    // Connection defaults
    pub const DEFAULT_IP: &'static str = "192.168.0.100";
    pub const DEFAULT_PORT: u16 = 5000;
    pub const SOCKET_TIMEOUT_SECS: u64 = 5;

    // Polling settings
    pub const POLL_INTERVAL_MS: u64 = 500;
    pub const HEARTBEAT_INTERVAL_MS: u64 = 1000;
    pub const HEARTBEAT_TIMEOUT_SECS: u64 = 3;

    // Watchdog settings
    pub const WATCHDOG_TIMEOUT_SECS: u64 = 5;
    pub const WATCHDOG_WARNING_THRESHOLD: f64 = 0.8;

    // Auto-reconnect settings
    pub const AUTO_RECONNECT: bool = true;
    pub const RECONNECT_DELAY_MS: u64 = 2000;
    pub const MAX_RECONNECT_ATTEMPTS: u32 = 5;

    // Audio sources
    pub const SOURCE_ADC: &'static str = "ADC";
    pub const SOURCE_BRAM: &'static str = "BRAM";

    // Frequency limits (Hz)
    pub const FREQ_MIN: u32 = 530_000;
    pub const FREQ_MAX: u32 = 1_700_000;

    // Number of channels
    pub const NUM_CHANNELS: usize = 12;
}

/// Channel configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChannelConfig {
    pub id: u8,
    pub default_freq: u32,
    pub name: String,
}

/// Get default channel configurations
pub fn get_default_channels() -> Vec<ChannelConfig> {
    vec![
        ChannelConfig { id: 1,  default_freq: 540_000,  name: "CH1".into() },
        ChannelConfig { id: 2,  default_freq: 640_000,  name: "CH2".into() },
        ChannelConfig { id: 3,  default_freq: 740_000,  name: "CH3".into() },
        ChannelConfig { id: 4,  default_freq: 840_000,  name: "CH4".into() },
        ChannelConfig { id: 5,  default_freq: 940_000,  name: "CH5".into() },
        ChannelConfig { id: 6,  default_freq: 1_040_000, name: "CH6".into() },
        ChannelConfig { id: 7,  default_freq: 1_140_000, name: "CH7".into() },
        ChannelConfig { id: 8,  default_freq: 1_240_000, name: "CH8".into() },
        ChannelConfig { id: 9,  default_freq: 1_340_000, name: "CH9".into() },
        ChannelConfig { id: 10, default_freq: 1_440_000, name: "CH10".into() },
        ChannelConfig { id: 11, default_freq: 1_540_000, name: "CH11".into() },
        ChannelConfig { id: 12, default_freq: 1_640_000, name: "CH12".into() },
    ]
}

/// Message presets
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessagePreset {
    pub id: u8,
    pub name: String,
    pub duration: String,
}

pub fn get_message_presets() -> Vec<MessagePreset> {
    vec![
        MessagePreset { id: 1, name: "Emergency Evacuation".into(), duration: "45s".into() },
        MessagePreset { id: 2, name: "Fire Alert".into(), duration: "30s".into() },
        MessagePreset { id: 3, name: "Traffic Advisory".into(), duration: "60s".into() },
        MessagePreset { id: 4, name: "Test Tone".into(), duration: "10s".into() },
    ]
}

/// SCPI command templates
pub struct ScpiCommands;

impl ScpiCommands {
    pub const QUERY_ID: &'static str = "*IDN?";
    pub const QUERY_STATUS: &'static str = "STATUS?";
    
    pub fn set_source(source: &str) -> String {
        format!("SOURCE:INPUT {}", source)
    }
    
    pub fn set_message(id: u8) -> String {
        format!("SOURCE:MSG {}", id)
    }
    
    pub fn set_freq(channel_id: u8, freq_hz: u32) -> String {
        format!("FREQ:CH{} {}", channel_id, freq_hz)
    }
    
    pub fn set_output(channel_id: u8, enabled: bool) -> String {
        let state = if enabled { "ON" } else { "OFF" };
        format!("CH{}:OUTPUT {}", channel_id, state)
    }
    
    pub fn set_broadcast(active: bool) -> String {
        let state = if active { "ON" } else { "OFF" };
        format!("OUTPUT:STATE {}", state)
    }
    
    pub const WATCHDOG_RESET: &'static str = "WATCHDOG:RESET";
    
    pub fn watchdog_enable(enabled: bool) -> String {
        let state = if enabled { "ON" } else { "OFF" };
        format!("WATCHDOG:ENABLE {}", state)
    }
}

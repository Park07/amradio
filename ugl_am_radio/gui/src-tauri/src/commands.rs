//! Tauri Commands - Exposed to Frontend
//!
//! These replace the FastAPI endpoints

use crate::config::{Config, get_default_channels, get_message_presets};
use crate::model::{model, DeviceState, ConnectionState, BroadcastState, WatchdogState, ChannelState};
use serde::{Deserialize, Serialize};
use tauri::command;

/// Response for state queries
#[derive(Debug, Serialize)]
pub struct AppStateResponse {
    pub connected: bool,
    pub connection_state: ConnectionState,
    pub broadcast_state: BroadcastState,
    pub watchdog_state: WatchdogState,
    pub watchdog_time_remaining: u32,
    pub channels: Vec<ChannelState>,
    pub source: String,
    pub message_id: u8,
    pub stale: bool,
}

#[command]
pub fn get_state() -> AppStateResponse {
    let m = model();
    let device = m.get_device_state();
    
    AppStateResponse {
        connected: m.is_connected(),
        connection_state: m.get_connection_state(),
        broadcast_state: m.get_broadcast_state(),
        watchdog_state: m.get_watchdog_state(),
        watchdog_time_remaining: device.watchdog_time_remaining,
        channels: device.channels,
        source: device.source,
        message_id: device.message_id,
        stale: device.stale,
    }
}

#[command]
pub async fn connect(ip: String, port: u16) -> Result<String, String> {
    if model().is_connected() {
        return Err("Already connected".into());
    }
    
    model().connect(&ip, port).await;
    Ok(format!("Connecting to {}:{}", ip, port))
}

#[command]
pub async fn disconnect() -> Result<String, String> {
    if !model().is_connected() {
        return Err("Not connected".into());
    }
    
    model().disconnect().await;
    Ok("Disconnected".into())
}

#[command]
pub async fn start_broadcast() -> Result<String, String> {
    if !model().is_connected() {
        return Err("Not connected".into());
    }
    
    if model().get_broadcast_state() == BroadcastState::Broadcasting {
        return Err("Already broadcasting".into());
    }
    
    let active_count = model().get_device_state().channels.iter()
        .filter(|c| c.enabled).count();
    
    if active_count == 0 {
        return Err("No active channels".into());
    }
    
    model().set_broadcast(true).await;
    Ok(format!("Starting broadcast on {} channels", active_count))
}

#[command]
pub async fn stop_broadcast() -> Result<String, String> {
    if model().get_broadcast_state() != BroadcastState::Broadcasting {
        return Err("Not broadcasting".into());
    }
    
    model().set_broadcast(false).await;
    Ok("Stopping broadcast".into())
}

#[derive(Debug, Deserialize)]
pub struct ChannelUpdate {
    pub enabled: Option<bool>,
    pub frequency: Option<u32>,
}

#[command]
pub async fn update_channel(channel_id: u8, update: ChannelUpdate) -> Result<String, String> {
    if channel_id < 1 || channel_id > Config::NUM_CHANNELS as u8 {
        return Err(format!("Channel {} not found", channel_id));
    }
    
    if let Some(enabled) = update.enabled {
        model().set_channel_enabled(channel_id, enabled).await;
    }
    
    if let Some(freq) = update.frequency {
        if freq < Config::FREQ_MIN || freq > Config::FREQ_MAX {
            return Err(format!("Frequency must be between {} and {} Hz", Config::FREQ_MIN, Config::FREQ_MAX));
        }
        model().set_channel_frequency(channel_id, freq).await;
    }
    
    Ok(format!("Updated channel {}", channel_id))
}

#[command]
pub async fn enable_preset_channels(count: u8) -> Result<String, String> {
    let valid = [1, 2, 3, 4, 6, 8, 12];
    if !valid.contains(&count) {
        return Err(format!("Count must be one of {:?}", valid));
    }
    
    let distributions: std::collections::HashMap<u8, Vec<u8>> = [
        (1, vec![1]),
        (2, vec![1, 7]),
        (3, vec![12, 4, 8]),
        (4, vec![12, 3, 6, 9]),
        (6, vec![12, 2, 4, 6, 8, 10]),
        (8, vec![12, 1, 3, 4, 6, 7, 9, 10]),
        (12, vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
    ].into_iter().collect();
    
    let freq_presets = [540_000u32, 900_000, 1_200_000, 1_500_000];
    
    // Disable all first
    for ch_id in 1..=12 {
        model().set_channel_enabled(ch_id, false).await;
    }
    
    // Enable selected channels
    if let Some(channels) = distributions.get(&count) {
        for (i, &ch_id) in channels.iter().enumerate() {
            model().set_channel_enabled(ch_id, true).await;
            model().set_channel_frequency(ch_id, freq_presets[i % freq_presets.len()]).await;
        }
    }
    
    Ok(format!("Enabled {} channels", count))
}

#[command]
pub async fn set_source(source: String) -> Result<String, String> {
    model().set_source(&source).await;
    Ok(format!("Source set to {}", source))
}

#[command]
pub async fn set_message(message_id: u8) -> Result<String, String> {
    model().set_message(message_id).await;
    Ok(format!("Message set to {}", message_id))
}

#[command]
pub async fn reset_watchdog() -> Result<String, String> {
    model().reset_watchdog().await;
    Ok("Watchdog reset".into())
}

#[command]
pub fn get_log(limit: usize) -> Vec<String> {
    model().get_log_entries(limit)
}

#[command]
pub fn get_config() -> serde_json::Value {
    serde_json::json!({
        "default_ip": Config::DEFAULT_IP,
        "default_port": Config::DEFAULT_PORT,
        "num_channels": Config::NUM_CHANNELS,
        "freq_min": Config::FREQ_MIN,
        "freq_max": Config::FREQ_MAX,
        "channels": get_default_channels(),
        "messages": get_message_presets(),
    })
}

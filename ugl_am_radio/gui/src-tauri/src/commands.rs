// commands.rs
// Tauri commands - API between JS and Rust
// Updated with state machine support

use std::sync::Arc;
use tauri::State;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};

use crate::model::NetworkManager;
use crate::state_machine::{BroadcastState, ConnectionState, WatchdogState, SourceMode};

pub type AppState = Arc<RwLock<NetworkManager>>;

// ==================== RESPONSE TYPES ====================

#[derive(Serialize)]
pub struct StateResponse {
    pub connection: String,
    pub broadcast: String,
    pub watchdog: String,
    pub source: String,
    pub channels: Vec<ChannelResponse>,
    pub fpga_temperature: Option<f32>,
    pub error_count: u32,

    // State machine helpers for UI
    pub can_arm: bool,
    pub can_broadcast: bool,
    pub can_stop: bool,
    pub is_emergency: bool,
    pub is_transitioning: bool,
}

#[derive(Serialize)]
pub struct ChannelResponse {
    pub id: u8,
    pub enabled: bool,
    pub frequency: u32,
    pub amplitude: f32,
}

#[derive(Deserialize)]
pub struct ChannelUpdate {
    pub enabled: Option<bool>,
    pub frequency: Option<u32>,
}

// ==================== CONNECTION ====================

#[tauri::command]
pub async fn connect(
    ip: String,
    port: u16,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = state.read().await;
    manager.connect(&ip, port).await?;
    Ok(format!("Connected to {}:{}", ip, port))
}

#[tauri::command]
pub async fn disconnect(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.read().await;
    manager.disconnect().await?;
    Ok("Disconnected".to_string())
}

// ==================== BROADCAST STATE MACHINE ====================

/// Arm the system for broadcast
#[tauri::command]
pub async fn arm(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.read().await;
    manager.arm().await?;
    Ok("System armed".to_string())
}

/// Start broadcasting (must be armed first)
#[tauri::command]
pub async fn start_broadcast(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.read().await;
    manager.start_broadcast().await?;
    Ok("Broadcast started".to_string())
}

/// Stop broadcasting
#[tauri::command]
pub async fn stop_broadcast(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.read().await;
    manager.stop_broadcast().await?;
    Ok("Broadcast stopped".to_string())
}

/// Start emergency broadcast (bypasses arm requirement)
#[tauri::command]
pub async fn start_emergency(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.read().await;
    manager.start_emergency().await?;
    Ok("Emergency broadcast started".to_string())
}

/// Stop emergency broadcast
#[tauri::command]
pub async fn stop_emergency(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.read().await;
    manager.stop_emergency().await?;
    Ok("Emergency broadcast stopped".to_string())
}

// ==================== CHANNEL CONTROL ====================

#[tauri::command]
pub async fn update_channel(
    channel_id: u8,
    update: ChannelUpdate,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = state.read().await;
    let device_state = manager.get_state().await;

    let current = device_state
        .channels
        .iter()
        .find(|c| c.id == channel_id)
        .ok_or_else(|| format!("Channel {} not found", channel_id))?;

    let enabled = update.enabled.unwrap_or(current.enabled);
    let frequency = update.frequency.unwrap_or(current.frequency);

    manager.set_channel(channel_id, frequency, enabled).await?;
    Ok(format!("Channel {} updated", channel_id))
}

#[tauri::command]
pub async fn enable_preset_channels(
    count: u8,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = state.read().await;
    manager.enable_preset(count).await?;
    Ok(format!("Enabled {} channels", count))
}

// ==================== SOURCE CONTROL ====================

#[tauri::command]
pub async fn set_source(source: String, state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.read().await;

    let mode = match source.to_uppercase().as_str() {
        "BRAM" => SourceMode::Bram,
        "ADC" => SourceMode::Adc,
        _ => return Err(format!("Invalid source: {}", source)),
    };

    manager.set_source(mode).await?;
    Ok(format!("Source set to {}", source))
}

// ==================== STATE QUERY ====================

#[tauri::command]
pub async fn get_state(state: State<'_, AppState>) -> Result<StateResponse, String> {
    let manager = state.read().await;
    let device_state = manager.get_state().await;

    let broadcast = &device_state.broadcast;

    Ok(StateResponse {
        connection: device_state.connection.display().to_string(),
        broadcast: broadcast.display().to_string(),
        watchdog: device_state.watchdog.display().to_string(),
        source: device_state.source.as_str().to_string(),

        channels: device_state
            .channels
            .iter()
            .map(|c| ChannelResponse {
                id: c.id,
                enabled: c.enabled,
                frequency: c.frequency,
                amplitude: c.amplitude,
            })
            .collect(),

        fpga_temperature: device_state.fpga_temperature,
        error_count: device_state.error_count,

        // State machine helpers
        can_arm: matches!(broadcast, BroadcastState::Idle),
        can_broadcast: matches!(broadcast, BroadcastState::Armed),
        can_stop: broadcast.is_broadcasting(),
        is_emergency: matches!(broadcast, BroadcastState::Emergency),
        is_transitioning: broadcast.is_transitioning(),
    })
}

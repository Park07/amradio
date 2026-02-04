use tauri::State;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::model::{NetworkManager, ConnectionState, BroadcastState, WatchdogState, SourceMode};

// Make this PUBLIC so main.rs can use it
pub type AppState = Arc<Mutex<NetworkManager>>;

#[derive(Serialize)]
pub struct ConnectResponse {
    pub success: bool,
    pub message: String,
}

#[derive(Serialize)]
pub struct StateResponse {
    pub connection_state: String,
    pub broadcast_state: String,
    pub watchdog_state: String,
    pub channels: Vec<ChannelResponse>,
    pub source: String,
    pub fpga_temperature: Option<f32>,
    pub error_count: u32,
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

// CONNECT
#[tauri::command]
pub async fn connect(
    ip: String,
    port: u16,
    state: State<'_, AppState>,
) -> Result<ConnectResponse, String> {
    let manager = state.lock().await;
    
    match manager.connect(&ip, port).await {
        Ok(_) => Ok(ConnectResponse {
            success: true,
            message: format!("Connected to {}:{}", ip, port),
        }),
        Err(e) => Err(e),
    }
}

// DISCONNECT
#[tauri::command]
pub async fn disconnect(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.lock().await;
    manager.disconnect().await?;
    Ok("Disconnected".to_string())
}

// START BROADCAST
#[tauri::command]
pub async fn start_broadcast(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.lock().await;
    manager.start_broadcast().await?;
    Ok("Broadcast started".to_string())
}

// STOP BROADCAST
#[tauri::command]
pub async fn stop_broadcast(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.lock().await;
    manager.stop_broadcast().await?;
    Ok("Broadcast stopped".to_string())
}

// UPDATE CHANNEL
#[tauri::command]
pub async fn update_channel(
    channel_id: u8,
    update: ChannelUpdate,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = state.lock().await;
    let device_state = manager.get_state().await;
    
    let current = device_state.channels
        .iter()
        .find(|c| c.id == channel_id)
        .ok_or_else(|| format!("Channel {} not found", channel_id))?;
    
    let enabled = update.enabled.unwrap_or(current.enabled);
    let frequency = update.frequency.unwrap_or(current.frequency);
    
    manager.set_channel(channel_id, frequency, enabled).await?;
    Ok(format!("Channel {} updated", channel_id))
}

// SET SOURCE
#[tauri::command]
pub async fn set_source(
    source: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = state.lock().await;
    
    let mode = match source.to_uppercase().as_str() {
        "BRAM" => SourceMode::Bram,
        "ADC" => SourceMode::Adc,
        _ => return Err(format!("Invalid source: {}", source)),
    };
    
    manager.set_source(mode).await?;
    Ok(format!("Source set to {}", source))
}

// ENABLE PRESET CHANNELS
#[tauri::command]
pub async fn enable_preset_channels(
    count: u8,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = state.lock().await;
    manager.enable_preset(count).await?;
    Ok(format!("Enabled {} channels", count))
}

// GET STATE
#[tauri::command]
pub async fn get_state(state: State<'_, AppState>) -> Result<StateResponse, String> {
    let manager = state.lock().await;
    let device_state = manager.get_state().await;
    
    Ok(StateResponse {
        connection_state: match device_state.connection {
            ConnectionState::Disconnected => "DISCONNECTED",
            ConnectionState::Connecting => "CONNECTING",
            ConnectionState::Connected => "CONNECTED",
            ConnectionState::Reconnecting => "RECONNECTING",
        }.to_string(),
        
        broadcast_state: match device_state.broadcast {
            BroadcastState::Idle => "IDLE",
            BroadcastState::Broadcasting => "BROADCASTING",
        }.to_string(),
        
        watchdog_state: match device_state.watchdog {
            WatchdogState::Ok => "OK",
            WatchdogState::Warning => "WARNING",
            WatchdogState::Triggered => "TRIGGERED",
        }.to_string(),
        
        channels: device_state.channels.iter().map(|c| ChannelResponse {
            id: c.id,
            enabled: c.enabled,
            frequency: c.frequency,
            amplitude: c.amplitude,
        }).collect(),
        
        source: match device_state.source {
            SourceMode::Bram => "BRAM",
            SourceMode::Adc => "ADC",
        }.to_string(),
        
        fpga_temperature: device_state.fpga_temperature,
        error_count: device_state.error_count,
    })
}

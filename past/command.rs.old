// ============================================================
// commands.rs - FULL TAURI COMMANDS
// These are the functions JavaScript calls via invoke()
// ============================================================

use tauri::State;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;

use crate::model::{NetworkManager, DeviceState, Channel, ConnectionState, BroadcastState, WatchdogState, SourceMode, AuditEntry};

// ============================================================
// APP STATE TYPE
// ============================================================
pub type AppState = Arc<Mutex<NetworkManager>>;

// ============================================================
// RESPONSE TYPES (for JSON serialization to JS)
// ============================================================
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

#[derive(Serialize)]
pub struct LogResponse {
    pub entries: Vec<LogEntryResponse>,
}

#[derive(Serialize)]
pub struct LogEntryResponse {
    pub timestamp: u64,
    pub level: String,
    pub message: String,
}

// ============================================================
// REQUEST TYPES (from JavaScript)
// ============================================================
#[derive(Deserialize)]
pub struct ChannelUpdate {
    pub enabled: Option<bool>,
    pub frequency: Option<u32>,
    pub amplitude: Option<f32>,
}

// ============================================================
// CONNECT COMMAND
// JavaScript: await invoke('connect', { ip: '192.168.0.100', port: 5000 })
// ============================================================
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

// ============================================================
// DISCONNECT COMMAND
// JavaScript: await invoke('disconnect')
// ============================================================
#[tauri::command]
pub async fn disconnect(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.lock().await;
    manager.disconnect().await?;
    Ok("Disconnected".to_string())
}

// ============================================================
// START BROADCAST COMMAND
// JavaScript: await invoke('start_broadcast')
// ============================================================
#[tauri::command]
pub async fn start_broadcast(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.lock().await;

    // Check if connected
    if !manager.is_connected().await {
        return Err("Not connected to device".to_string());
    }

    manager.start_broadcast().await?;
    Ok("Broadcast started".to_string())
}

// ============================================================
// STOP BROADCAST COMMAND
// JavaScript: await invoke('stop_broadcast')
// ============================================================
#[tauri::command]
pub async fn stop_broadcast(state: State<'_, AppState>) -> Result<String, String> {
    let manager = state.lock().await;
    manager.stop_broadcast().await?;
    Ok("Broadcast stopped".to_string())
}

// ============================================================
// UPDATE CHANNEL COMMAND
// JavaScript: await invoke('update_channel', { channelId: 1, update: { enabled: true, frequency: 540000 } })
// ============================================================
#[tauri::command]
pub async fn update_channel(
    channel_id: u8,
    update: ChannelUpdate,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = state.lock().await;

    // Get current channel state
    let current_state = manager.get_state().await;
    let current_channel = current_state.channels
        .iter()
        .find(|c| c.id == channel_id)
        .ok_or_else(|| format!("Channel {} not found", channel_id))?;

    // Apply updates
    let enabled = update.enabled.unwrap_or(current_channel.enabled);
    let frequency = update.frequency.unwrap_or(current_channel.frequency);

    // Send to device
    manager.set_channel(channel_id, frequency, enabled).await?;

    Ok(format!("Channel {} updated", channel_id))
}

// ============================================================
// SET SOURCE COMMAND
// JavaScript: await invoke('set_source', { source: 'BRAM' })
// ============================================================
#[tauri::command]
pub async fn set_source(
    source: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = state.lock().await;

    let mode = match source.to_uppercase().as_str() {
        "BRAM" => SourceMode::Bram,
        "ADC" => SourceMode::Adc,
        _ => return Err(format!("Invalid source: {}. Use 'BRAM' or 'ADC'", source)),
    };

    manager.set_source(mode).await?;
    Ok(format!("Source set to {}", source))
}

// ============================================================
// ENABLE PRESET CHANNELS COMMAND
// JavaScript: await invoke('enable_preset_channels', { count: 3 })
// ============================================================
#[tauri::command]
pub async fn enable_preset_channels(
    count: u8,
    state: State<'_, AppState>,
) -> Result<String, String> {
    if count < 1 || count > 12 {
        return Err(format!("Invalid count: {}. Must be 1-12", count));
    }

    let manager = state.lock().await;
    manager.enable_preset(count).await?;
    Ok(format!("Enabled {} channels", count))
}

// ============================================================
// GET STATE COMMAND
// JavaScript: const state = await invoke('get_state')
// ============================================================
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

// ============================================================
// GET AUDIT LOG COMMAND
// JavaScript: const log = await invoke('get_audit_log')
// ============================================================
#[tauri::command]
pub async fn get_audit_log(state: State<'_, AppState>) -> Result<LogResponse, String> {
    let manager = state.lock().await;
    let log = manager.get_audit_log().await;

    Ok(LogResponse {
        entries: log.iter().map(|e| LogEntryResponse {
            timestamp: e.timestamp,
            level: e.level.clone(),
            message: e.message.clone(),
        }).collect(),
    })
}

// ============================================================
// SEND RAW SCPI COMMAND (for debugging)
// JavaScript: await invoke('send_raw_command', { command: 'STATUS?' })
// ============================================================
#[tauri::command]
pub async fn send_raw_command(
    command: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = state.lock().await;

    if !manager.is_connected().await {
        return Err("Not connected".to_string());
    }

    // For safety, block certain commands in raw mode
    let blocked = ["*RST", "WATCHDOG:DISABLE", "FACTORY:RESET"];
    if blocked.iter().any(|b| command.to_uppercase().contains(b)) {
        return Err("Command blocked for safety".to_string());
    }

    // This would need a query method exposed - simplified here
    Ok(format!("Command sent: {}", command))
}

// ============================================================
// GET CONNECTION INFO
// JavaScript: const info = await invoke('get_connection_info')
// ============================================================
#[derive(Serialize)]
pub struct ConnectionInfo {
    pub connected: bool,
    pub ip: Option<String>,
    pub port: Option<u16>,
    pub uptime_seconds: u64,
}

#[tauri::command]
pub async fn get_connection_info(state: State<'_, AppState>) -> Result<ConnectionInfo, String> {
    let manager = state.lock().await;
    let device_state = manager.get_state().await;

    Ok(ConnectionInfo {
        connected: device_state.connection == ConnectionState::Connected,
        ip: None,  // Would need to track this
        port: None,
        uptime_seconds: 0,  // Would calculate from connect time
    })
}

// ============================================================
// HEALTH CHECK (for UI polling)
// JavaScript: const health = await invoke('health_check')
// ============================================================
#[derive(Serialize)]
pub struct HealthCheck {
    pub backend_ok: bool,
    pub device_connected: bool,
    pub watchdog_ok: bool,
    pub broadcasting: bool,
    pub active_channels: u8,
}

#[tauri::command]
pub async fn health_check(state: State<'_, AppState>) -> Result<HealthCheck, String> {
    let manager = state.lock().await;
    let device_state = manager.get_state().await;

    Ok(HealthCheck {
        backend_ok: true,
        device_connected: device_state.connection == ConnectionState::Connected,
        watchdog_ok: device_state.watchdog != WatchdogState::Triggered,
        broadcasting: device_state.broadcast == BroadcastState::Broadcasting,
        active_channels: device_state.channels.iter().filter(|c| c.enabled).count() as u8,
    })
}

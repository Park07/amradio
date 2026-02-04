// ============================================================
// commands.rs - TAURI COMMANDS
// These are the functions JavaScript calls via invoke()
// ============================================================

use tauri::State;
use crate::model::{NetworkManager, DeviceState};
use std::sync::Arc;
use tokio::sync::Mutex;

// The model is stored in Tauri's state management
type AppState = Arc<Mutex<NetworkManager>>;

// ============================================================
// CONNECT COMMAND
// JavaScript: await invoke('connect', { ip, port })
// ============================================================
#[tauri::command]
pub async fn connect(
    ip: String,
    port: u16,
    state: State<'_, AppState>
) -> Result<String, String> {
    let mut manager = state.lock().await;
    manager.connect(&ip, port).await?;
    Ok("Connected".to_string())
}

// ============================================================
// DISCONNECT COMMAND
// JavaScript: await invoke('disconnect')
// ============================================================
#[tauri::command]
pub async fn disconnect(state: State<'_, AppState>) -> Result<String, String> {
    let mut manager = state.lock().await;
    manager.disconnect().await?;
    Ok("Disconnected".to_string())
}

// ============================================================
// START BROADCAST COMMAND
// JavaScript: await invoke('start_broadcast')
// Rust sends: "OUTPUT:STATE ON" to FPGA
// ============================================================
#[tauri::command]
pub async fn start_broadcast(state: State<'_, AppState>) -> Result<String, String> {
    let mut manager = state.lock().await;
    manager.start_broadcast().await?;
    Ok("Broadcast started".to_string())
}

// ============================================================
// STOP BROADCAST COMMAND
// JavaScript: await invoke('stop_broadcast')
// Rust sends: "OUTPUT:STATE OFF" to FPGA
// ============================================================
#[tauri::command]
pub async fn stop_broadcast(state: State<'_, AppState>) -> Result<String, String> {
    let mut manager = state.lock().await;
    manager.stop_broadcast().await?;
    Ok("Broadcast stopped".to_string())
}

// ============================================================
// UPDATE CHANNEL COMMAND
// JavaScript: await invoke('update_channel', { channelId, update })
// Rust sends: "FREQ:CH1 540000" and "OUTPUT:CH1 ON" to FPGA
// ============================================================
#[derive(serde::Deserialize)]
pub struct ChannelUpdate {
    pub enabled: bool,
    pub frequency: Option<u32>,
}

#[tauri::command]
pub async fn update_channel(
    channel_id: u8,
    update: ChannelUpdate,
    state: State<'_, AppState>
) -> Result<String, String> {
    let mut manager = state.lock().await;
    let freq = update.frequency.unwrap_or(540000);
    manager.set_channel(channel_id, freq, update.enabled).await?;
    Ok(format!("Channel {} updated", channel_id))
}

// ============================================================
// SET SOURCE COMMAND
// JavaScript: await invoke('set_source', { source: 'BRAM' })
// Rust sends: "SOURCE:MODE BRAM" to FPGA
// ============================================================
#[tauri::command]
pub async fn set_source(
    source: String,
    state: State<'_, AppState>
) -> Result<String, String> {
    let mut manager = state.lock().await;
    manager.set_source(&source).await?;
    Ok(format!("Source set to {}", source))
}

// ============================================================
// GET STATE COMMAND
// JavaScript: const state = await invoke('get_state')
// Returns current device state to UI for display
// ============================================================
#[derive(serde::Serialize)]
pub struct StateResponse {
    pub connection_state: String,
    pub broadcast_state: String,
    pub watchdog_state: String,
    pub channels: Vec<ChannelInfo>,
    pub source: String,
}

#[derive(serde::Serialize)]
pub struct ChannelInfo {
    pub id: u8,
    pub enabled: bool,
    pub frequency: u32,
}

#[tauri::command]
pub async fn get_state(state: State<'_, AppState>) -> Result<StateResponse, String> {
    let manager = state.lock().await;
    let device_state = manager.get_state().await;

    Ok(StateResponse {
        connection_state: format!("{:?}", device_state.connection),
        broadcast_state: format!("{:?}", device_state.broadcast),
        watchdog_state: format!("{:?}", device_state.watchdog),
        channels: device_state.channels.iter().map(|c| ChannelInfo {
            id: c.id,
            enabled: c.enabled,
            frequency: c.frequency,
        }).collect(),
        source: device_state.source.clone(),
    })
}

// ============================================================
// ENABLE PRESET CHANNELS COMMAND
// JavaScript: await invoke('enable_preset_channels', { count: 3 })
// Enables N channels with distributed frequencies
// ============================================================
#[tauri::command]
pub async fn enable_preset_channels(
    count: u8,
    state: State<'_, AppState>
) -> Result<String, String> {
    let mut manager = state.lock().await;

    // Frequency presets (100kHz spacing)
    let freqs = [540000, 640000, 740000, 840000, 940000, 1040000,
                 1140000, 1240000, 1340000, 1440000, 1540000, 1640000];

    // Distribution patterns (same as Python)
    let channels: Vec<u8> = match count {
        1 => vec![1],
        2 => vec![1, 7],
        3 => vec![12, 4, 8],
        4 => vec![12, 3, 6, 9],
        6 => vec![12, 2, 4, 6, 8, 10],
        8 => vec![12, 1, 3, 4, 6, 7, 9, 10],
        12 => (1..=12).collect(),
        _ => vec![1],
    };

    // Disable all channels first
    for ch in 1..=12 {
        manager.set_channel(ch, 540000, false).await?;
    }

    // Enable selected channels with frequencies
    for &ch in &channels {
        let freq = freqs[(ch - 1) as usize];
        manager.set_channel(ch, freq, true).await?;
    }

    Ok(format!("Enabled {} channels", count))
}

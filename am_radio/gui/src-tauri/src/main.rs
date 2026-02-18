// main.rs
// Entry point for Tauri application
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
#![allow(dead_code, unused_imports)]

mod commands;
mod config;
mod event_bus;
mod model;
mod state_machine;
mod retry;

use std::sync::Arc;
use tokio::sync::RwLock;
use tauri::Manager;

use commands::AppState;
use tokio::sync::broadcast;
use model::NetworkManager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Create shared event bus
            let (event_tx, _) = broadcast::channel(100);
            // Create network manager
            let manager = NetworkManager::new(event_tx);


            let app_state: AppState = Arc::new(RwLock::new(manager));

            // Store in Tauri state
            app.manage(app_state);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Connection
            commands::connect,
            commands::disconnect,

            // Broadcast state machine
            commands::arm,
            commands::start_broadcast,
            commands::stop_broadcast,
            commands::start_emergency,
            commands::stop_emergency,

            // Channel control
            commands::update_channel,
            commands::enable_preset_channels,

            // Source control
            commands::set_source,

            // State query
            commands::get_state,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

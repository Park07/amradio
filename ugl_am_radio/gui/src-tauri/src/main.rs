#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod config;
mod event_bus;
mod model;
mod commands;

use std::sync::Arc;
use tokio::sync::Mutex;

use event_bus::EventBus;
use model::NetworkManager;
use commands::AppState;

fn main() {
    let event_bus = EventBus::new();
    let event_tx = event_bus.get_sender();
    let network_manager = NetworkManager::new(event_tx);
    let app_state: AppState = Arc::new(Mutex::new(network_manager));
    
    tauri::Builder::default()
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            commands::connect,
            commands::disconnect,
            commands::start_broadcast,
            commands::stop_broadcast,
            commands::update_channel,
            commands::enable_preset_channels,
            commands::set_source,
            commands::get_state,
        ])
        .setup(|_app| {
            println!("UGL AM Radio Control - Rust Backend Ready");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Error running tauri application");
}

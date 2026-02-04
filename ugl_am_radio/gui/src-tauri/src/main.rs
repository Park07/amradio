//! UGL AM Radio Control - Pure Rust
//!
//! Single binary desktop application
//! Author: William Park

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod config;
mod event_bus;
mod model;
mod commands;

use commands::*;
use tracing_subscriber;

fn main() {
    // Initialize logging
    tracing_subscriber::fmt::init();
    
    // Initialize tokio runtime for async operations
    let runtime = tokio::runtime::Runtime::new().expect("Failed to create Tokio runtime");
    
    // Enter the runtime context so model can spawn tasks
    let _guard = runtime.enter();
    
    // Initialize the model (this starts the event listener)
    let _ = model::model();
    
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_state,
            connect,
            disconnect,
            start_broadcast,
            stop_broadcast,
            update_channel,
            enable_preset_channels,
            set_source,
            set_message,
            reset_watchdog,
            get_log,
            get_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

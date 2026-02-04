#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{Manager, State};

// Store the Python process handle
struct PythonProcess(Mutex<Option<Child>>);

fn start_python_backend() -> Option<Child> {
    // Try different Python commands
    let python_commands = ["python", "python3", "python.exe"];
    
    for python_cmd in python_commands {
        // Get the directory where the app is running
        let result = Command::new(python_cmd)
            .args(["-m", "uvicorn", "api:app", "--port", "8000", "--host", "127.0.0.1"])
            .current_dir(get_backend_dir())
            .spawn();
        
        if let Ok(child) = result {
            println!("[Tauri] Started Python backend with: {}", python_cmd);
            return Some(child);
        }
    }
    
    eprintln!("[Tauri] Failed to start Python backend - is Python installed?");
    None
}

fn get_backend_dir() -> std::path::PathBuf {
    // In development, use the project root
    // In production, use the app's resource directory
    if cfg!(debug_assertions) {
        std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."))
    } else {
        // For production builds, the backend files should be next to the executable
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.to_path_buf()))
            .unwrap_or_else(|| std::path::PathBuf::from("."))
    }
}

#[tauri::command]
fn check_backend_ready() -> bool {
    // Simple health check - try to connect to the backend
    match std::net::TcpStream::connect("127.0.0.1:8000") {
        Ok(_) => true,
        Err(_) => false,
    }
}

fn main() {
    tauri::Builder::default()
        .manage(PythonProcess(Mutex::new(None)))
        .setup(|app| {
            // Start Python backend when app starts
            let python_process = start_python_backend();
            
            let state: State<PythonProcess> = app.state();
            *state.0.lock().unwrap() = python_process;
            
            // Give Python a moment to start
            std::thread::sleep(std::time::Duration::from_millis(1500));
            
            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::Destroyed = event.event() {
                // Kill Python when window closes
                let app = event.window().app_handle();
                let state: State<PythonProcess> = app.state();
                
                if let Some(mut child) = state.0.lock().unwrap().take() {
                    println!("[Tauri] Shutting down Python backend...");
                    let _ = child.kill();
                    let _ = child.wait();
                    println!("[Tauri] Python backend stopped");
                }
            }
        })
        .invoke_handler(tauri::generate_handler![check_backend_ready])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

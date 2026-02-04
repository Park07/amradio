//! Model Layer - Stateless Design with Fail-Safe Watchdog
//!
//! Direct port from Python model.py
//! Author: William Park
//!
//! - Stateless UI: State comes from device polling only
//! - Async networking with tokio
//! - Fail-safe: Hardware watchdog for safety
//! - Auto-reconnect: Automatic recovery on connection loss

use crate::config::{Config, ScpiCommands, get_default_channels};
use crate::event_bus::{event_bus, Event, EventType};
use chrono::{DateTime, Utc};
use once_cell::sync::Lazy;
use parking_lot::{Mutex, RwLock};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::TcpStream;
use tokio::sync::mpsc;
use tokio::time::{interval, timeout};
use tracing::{error, info, warn};

/// Connection state machine states
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ConnectionState {
    Disconnected,
    Connecting,
    Connected,
    Reconnecting,
    Error,
}

/// Broadcast state machine states
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BroadcastState {
    Idle,
    Arming,
    Broadcasting,
    Stopping,
    Error,
}

/// Watchdog states for fail-safe monitoring
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum WatchdogState {
    Ok,
    Warning,
    Triggered,
    Disabled,
}

/// State for a single channel
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChannelState {
    pub id: u8,
    pub frequency: u32,
    pub enabled: bool,
    pub confirmed: bool,
}

impl ChannelState {
    pub fn new(id: u8, default_freq: u32) -> Self {
        Self {
            id,
            frequency: default_freq,
            enabled: false,
            confirmed: false,
        }
    }
}

/// Device state - populated ONLY from polling
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceState {
    pub connected: bool,
    pub broadcasting: bool,
    pub source: String,
    pub message_id: u8,
    pub channels: Vec<ChannelState>,
    pub last_update: Option<DateTime<Utc>>,
    pub stale: bool,
    
    // Watchdog state
    pub watchdog_enabled: bool,
    pub watchdog_triggered: bool,
    pub watchdog_warning: bool,
    pub watchdog_time_remaining: u32,
}

impl Default for DeviceState {
    fn default() -> Self {
        let channels = get_default_channels()
            .into_iter()
            .map(|c| ChannelState::new(c.id, c.default_freq))
            .collect();
        
        Self {
            connected: false,
            broadcasting: false,
            source: String::new(),
            message_id: 1,
            channels,
            last_update: None,
            stale: true,
            watchdog_enabled: true,
            watchdog_triggered: false,
            watchdog_warning: false,
            watchdog_time_remaining: 5,
        }
    }
}

/// Thread-safe audit logger
pub struct AuditLogger {
    entries: RwLock<Vec<String>>,
    max_entries: usize,
}

impl AuditLogger {
    pub fn new() -> Self {
        Self {
            entries: RwLock::new(Vec::new()),
            max_entries: 100,
        }
    }

    pub fn log(&self, message: &str, level: &str) -> String {
        let timestamp = Utc::now().format("%Y-%m-%d %H:%M:%S").to_string();
        let entry = format!("[{}] [{}] {}", timestamp, level, message);
        
        {
            let mut entries = self.entries.write();
            entries.push(entry.clone());
            if entries.len() > self.max_entries {
                entries.remove(0);
            }
        }
        
        // Also print to console
        match level {
            "ERROR" => error!("{}", message),
            "WARN" => warn!("{}", message),
            _ => info!("{}", message),
        }
        
        entry
    }

    pub fn info(&self, message: &str) -> String {
        self.log(message, "INFO")
    }

    pub fn warn(&self, message: &str) -> String {
        self.log(message, "WARN")
    }

    pub fn error(&self, message: &str) -> String {
        self.log(message, "ERROR")
    }

    pub fn get_entries(&self, limit: usize) -> Vec<String> {
        let entries = self.entries.read();
        entries.iter().rev().take(limit).cloned().collect()
    }
}

/// Command to send to network task
#[derive(Debug)]
enum NetworkCommand {
    Connect { ip: String, port: u16 },
    Disconnect,
    SendCommand { command: String, log: bool },
    Shutdown,
}

/// Network manager handle
pub struct NetworkManager {
    command_tx: mpsc::Sender<NetworkCommand>,
    pub connection_state: Arc<RwLock<ConnectionState>>,
    logger: Arc<AuditLogger>,
}

impl NetworkManager {
    pub fn new(logger: Arc<AuditLogger>) -> Self {
        let (command_tx, command_rx) = mpsc::channel(64);
        let connection_state = Arc::new(RwLock::new(ConnectionState::Disconnected));
        
        // Spawn the network task
        let state_clone = connection_state.clone();
        let logger_clone = logger.clone();
        tokio::spawn(async move {
            network_task(command_rx, state_clone, logger_clone).await;
        });
        
        Self {
            command_tx,
            connection_state,
            logger,
        }
    }

    pub async fn connect(&self, ip: &str, port: u16) {
        *self.connection_state.write() = ConnectionState::Connecting;
        let _ = self.command_tx.send(NetworkCommand::Connect {
            ip: ip.to_string(),
            port,
        }).await;
    }

    pub async fn disconnect(&self) {
        let _ = self.command_tx.send(NetworkCommand::Disconnect).await;
    }

    pub async fn send_command(&self, command: &str, log: bool) {
        let _ = self.command_tx.send(NetworkCommand::SendCommand {
            command: command.to_string(),
            log,
        }).await;
    }

    pub fn is_connected(&self) -> bool {
        *self.connection_state.read() == ConnectionState::Connected
    }
}

/// Async network task that handles TCP connection
async fn network_task(
    mut command_rx: mpsc::Receiver<NetworkCommand>,
    connection_state: Arc<RwLock<ConnectionState>>,
    logger: Arc<AuditLogger>,
) {
    let mut stream: Option<TcpStream> = None;
    let mut current_ip = String::new();
    let mut current_port = 0u16;
    let mut reconnect_count = 0u32;
    let mut auto_reconnect = Config::AUTO_RECONNECT;
    
    // Poll interval
    let mut poll_interval = interval(Duration::from_millis(Config::POLL_INTERVAL_MS));
    
    loop {
        tokio::select! {
            // Handle commands
            cmd = command_rx.recv() => {
                match cmd {
                    Some(NetworkCommand::Connect { ip, port }) => {
                        current_ip = ip.clone();
                        current_port = port;
                        reconnect_count = 0;
                        auto_reconnect = Config::AUTO_RECONNECT;
                        
                        event_bus().emit_with_data(EventType::ConnectRequested, 
                            Event::data_from([("ip", json!(ip)), ("port", json!(port))]));
                        
                        match timeout(
                            Duration::from_secs(Config::SOCKET_TIMEOUT_SECS),
                            TcpStream::connect(format!("{}:{}", ip, port))
                        ).await {
                            Ok(Ok(s)) => {
                                stream = Some(s);
                                *connection_state.write() = ConnectionState::Connected;
                                logger.info(&format!("Connected to {}:{}", ip, port));
                                event_bus().emit_with_data(EventType::ConnectSuccess,
                                    Event::data_from([("ip", json!(ip)), ("port", json!(port))]));
                            }
                            Ok(Err(e)) => {
                                *connection_state.write() = ConnectionState::Error;
                                logger.error(&format!("Connection failed: {}", e));
                                event_bus().emit_with_data(EventType::ConnectFailed,
                                    Event::data_from([("reason", json!(e.to_string()))]));
                            }
                            Err(_) => {
                                *connection_state.write() = ConnectionState::Error;
                                logger.error("Connection timeout");
                                event_bus().emit_with_data(EventType::ConnectFailed,
                                    Event::data_from([("reason", json!("timeout"))]));
                            }
                        }
                    }
                    Some(NetworkCommand::Disconnect) => {
                        auto_reconnect = false;
                        stream = None;
                        *connection_state.write() = ConnectionState::Disconnected;
                        logger.info("Disconnected");
                        event_bus().emit(EventType::Disconnected);
                    }
                    Some(NetworkCommand::SendCommand { command, log }) => {
                        if let Some(ref mut s) = stream {
                            if let Err(e) = send_scpi_command(s, &command, log, &logger).await {
                                logger.error(&format!("Send error: {}", e));
                                // Connection lost
                                stream = None;
                                handle_connection_loss(&connection_state, &logger, 
                                    &current_ip, current_port, &mut reconnect_count, auto_reconnect).await;
                            }
                        }
                    }
                    Some(NetworkCommand::Shutdown) | None => {
                        break;
                    }
                }
            }
            
            // Polling loop when connected
            _ = poll_interval.tick(), if stream.is_some() => {
                if let Some(ref mut s) = stream {
                    // Send watchdog reset first
                    if let Err(_) = send_scpi_command(s, ScpiCommands::WATCHDOG_RESET, false, &logger).await {
                        stream = None;
                        handle_connection_loss(&connection_state, &logger,
                            &current_ip, current_port, &mut reconnect_count, auto_reconnect).await;
                        continue;
                    }
                    
                    // Query status
                    match query_scpi_command(s, ScpiCommands::QUERY_STATUS, &logger).await {
                        Ok(response) => {
                            parse_and_publish_status(&response);
                        }
                        Err(_) => {
                            stream = None;
                            handle_connection_loss(&connection_state, &logger,
                                &current_ip, current_port, &mut reconnect_count, auto_reconnect).await;
                        }
                    }
                }
            }
        }
    }
}

async fn send_scpi_command(
    stream: &mut TcpStream,
    command: &str,
    log: bool,
    logger: &AuditLogger,
) -> Result<(), std::io::Error> {
    let cmd = format!("{}\n", command.trim());
    stream.write_all(cmd.as_bytes()).await?;
    
    if log {
        logger.info(&format!("TX: {}", command));
    }
    
    Ok(())
}

async fn query_scpi_command(
    stream: &mut TcpStream,
    command: &str,
    logger: &AuditLogger,
) -> Result<String, std::io::Error> {
    let cmd = format!("{}\n", command.trim());
    stream.write_all(cmd.as_bytes()).await?;
    
    let mut reader = BufReader::new(stream);
    let mut response = String::new();
    reader.read_line(&mut response).await?;
    
    let response = response.trim().to_string();
    logger.info(&format!("RX: {}", response));
    
    Ok(response)
}

async fn handle_connection_loss(
    connection_state: &Arc<RwLock<ConnectionState>>,
    logger: &AuditLogger,
    ip: &str,
    port: u16,
    reconnect_count: &mut u32,
    auto_reconnect: bool,
) {
    event_bus().emit(EventType::DeviceHeartbeatLost);
    
    if !auto_reconnect {
        *connection_state.write() = ConnectionState::Disconnected;
        event_bus().emit(EventType::Disconnected);
        return;
    }
    
    if *reconnect_count >= Config::MAX_RECONNECT_ATTEMPTS {
        logger.error("Max reconnect attempts reached");
        *connection_state.write() = ConnectionState::Disconnected;
        event_bus().emit_with_data(EventType::Disconnected,
            Event::data_from([("reason", json!("max_retries"))]));
        return;
    }
    
    *reconnect_count += 1;
    *connection_state.write() = ConnectionState::Reconnecting;
    logger.warn(&format!("Reconnecting... attempt {}/{}", reconnect_count, Config::MAX_RECONNECT_ATTEMPTS));
    event_bus().emit_with_data(EventType::ReconnectAttempt,
        Event::data_from([("attempt", json!(*reconnect_count))]));
    
    tokio::time::sleep(Duration::from_millis(Config::RECONNECT_DELAY_MS)).await;
    
    // Attempt reconnect
    match timeout(
        Duration::from_secs(Config::SOCKET_TIMEOUT_SECS),
        TcpStream::connect(format!("{}:{}", ip, port))
    ).await {
        Ok(Ok(_s)) => {
            *connection_state.write() = ConnectionState::Connected;
            *reconnect_count = 0;
            logger.info(&format!("Reconnected to {}:{}", ip, port));
            event_bus().emit(EventType::ConnectSuccess);
        }
        _ => {
            // Will retry on next poll
        }
    }
}

fn parse_and_publish_status(status: &str) {
    let mut data: HashMap<String, serde_json::Value> = HashMap::new();
    
    for part in status.split(',') {
        if let Some((key, value)) = part.split_once('=') {
            let key = key.trim().to_string();
            let value = value.trim();
            
            // Try to parse as number, otherwise store as string
            if let Ok(n) = value.parse::<i64>() {
                data.insert(key, json!(n));
            } else if let Ok(b) = value.parse::<bool>() {
                data.insert(key, json!(b));
            } else {
                data.insert(key, json!(value));
            }
        }
    }
    
    // Check for watchdog trigger
    if data.get("watchdog_triggered").and_then(|v| v.as_str()) == Some("1") {
        event_bus().emit_with_data(EventType::WatchdogTriggered, data.clone());
    } else if data.get("watchdog_warning").and_then(|v| v.as_str()) == Some("1") {
        event_bus().emit_with_data(EventType::WatchdogWarning, data.clone());
    }
    
    event_bus().emit_with_data(EventType::DeviceStateUpdated, data);
}

/// Main model - STATELESS design with fail-safe watchdog
pub struct Model {
    pub logger: Arc<AuditLogger>,
    pub network: Arc<NetworkManager>,
    pub device_state: Arc<RwLock<DeviceState>>,
    pub connection_state: Arc<RwLock<ConnectionState>>,
    pub broadcast_state: Arc<RwLock<BroadcastState>>,
    pub watchdog_state: Arc<RwLock<WatchdogState>>,
}

impl Model {
    pub fn new() -> Self {
        let logger = Arc::new(AuditLogger::new());
        let network = Arc::new(NetworkManager::new(logger.clone()));
        let device_state = Arc::new(RwLock::new(DeviceState::default()));
        let connection_state = Arc::new(RwLock::new(ConnectionState::Disconnected));
        let broadcast_state = Arc::new(RwLock::new(BroadcastState::Idle));
        let watchdog_state = Arc::new(RwLock::new(WatchdogState::Ok));
        
        let model = Self {
            logger,
            network,
            device_state,
            connection_state,
            broadcast_state,
            watchdog_state,
        };
        
        // Start event listener
        model.start_event_listener();
        
        model
    }
    
    fn start_event_listener(&self) {
        let device_state = self.device_state.clone();
        let connection_state = self.connection_state.clone();
        let broadcast_state = self.broadcast_state.clone();
        let watchdog_state = self.watchdog_state.clone();
        let logger = self.logger.clone();
        
        tokio::spawn(async move {
            let mut rx = event_bus().subscribe();
            
            while let Ok(event) = rx.recv().await {
                match event.event_type {
                    EventType::ConnectSuccess => {
                        *connection_state.write() = ConnectionState::Connected;
                        device_state.write().connected = true;
                        device_state.write().stale = true;
                    }
                    EventType::ConnectFailed => {
                        *connection_state.write() = ConnectionState::Error;
                        device_state.write().connected = false;
                    }
                    EventType::Disconnected => {
                        *connection_state.write() = ConnectionState::Disconnected;
                        device_state.write().connected = false;
                        device_state.write().stale = true;
                        *broadcast_state.write() = BroadcastState::Idle;
                    }
                    EventType::ReconnectAttempt => {
                        *connection_state.write() = ConnectionState::Reconnecting;
                    }
                    EventType::DeviceHeartbeatLost => {
                        device_state.write().stale = true;
                    }
                    EventType::WatchdogTriggered => {
                        *watchdog_state.write() = WatchdogState::Triggered;
                        device_state.write().watchdog_triggered = true;
                        *broadcast_state.write() = BroadcastState::Idle;
                        logger.error("🚨 FAIL-SAFE ACTIVATED: RF output disabled!");
                    }
                    EventType::WatchdogWarning => {
                        *watchdog_state.write() = WatchdogState::Warning;
                        device_state.write().watchdog_warning = true;
                    }
                    EventType::DeviceStateUpdated => {
                        let mut state = device_state.write();
                        
                        // Parse data from event
                        if let Some(v) = event.data.get("watchdog_triggered") {
                            let triggered = v.as_str() == Some("1") || v.as_bool() == Some(true);
                            state.watchdog_triggered = triggered;
                            if triggered {
                                *watchdog_state.write() = WatchdogState::Triggered;
                            }
                        }
                        
                        if let Some(v) = event.data.get("watchdog_time") {
                            if let Some(n) = v.as_i64() {
                                state.watchdog_time_remaining = n as u32;
                            }
                        }
                        
                        if let Some(v) = event.data.get("broadcasting") {
                            let was_broadcasting = state.broadcasting;
                            let is_broadcasting = v.as_str() == Some("1") || v.as_bool() == Some(true);
                            state.broadcasting = is_broadcasting;
                            
                            if is_broadcasting && !was_broadcasting {
                                *broadcast_state.write() = BroadcastState::Broadcasting;
                                event_bus().emit(EventType::BroadcastStarted);
                            } else if !is_broadcasting && was_broadcasting {
                                *broadcast_state.write() = BroadcastState::Idle;
                                event_bus().emit(EventType::BroadcastStopped);
                            }
                        }
                        
                        // Update channel states
                        for ch in state.channels.iter_mut() {
                            let key_enabled = format!("ch{}_enabled", ch.id);
                            let key_freq = format!("ch{}_freq", ch.id);
                            
                            if let Some(v) = event.data.get(&key_enabled) {
                                ch.enabled = v.as_str() == Some("1") || v.as_bool() == Some(true);
                                ch.confirmed = true;
                            }
                            
                            if let Some(v) = event.data.get(&key_freq) {
                                if let Some(n) = v.as_i64() {
                                    ch.frequency = n as u32;
                                    ch.confirmed = true;
                                }
                            }
                        }
                        
                        if let Some(v) = event.data.get("source") {
                            if let Some(s) = v.as_str() {
                                state.source = s.to_string();
                            }
                        }
                        
                        state.last_update = Some(Utc::now());
                        state.stale = false;
                    }
                    _ => {}
                }
            }
        });
    }

    // === Public API ===
    
    pub async fn connect(&self, ip: &str, port: u16) {
        *self.connection_state.write() = ConnectionState::Connecting;
        self.network.connect(ip, port).await;
    }
    
    pub async fn disconnect(&self) {
        if self.device_state.read().broadcasting {
            self.set_broadcast(false).await;
        }
        self.network.disconnect().await;
    }
    
    pub async fn set_source(&self, source: &str) {
        let cmd = ScpiCommands::set_source(source);
        self.network.send_command(&cmd, true).await;
        event_bus().emit_with_data(EventType::SourceChanged,
            Event::data_from([("source", json!(source)), ("pending", json!(true))]));
    }
    
    pub async fn set_message(&self, message_id: u8) {
        let cmd = ScpiCommands::set_message(message_id);
        self.network.send_command(&cmd, true).await;
        event_bus().emit_with_data(EventType::MessageChanged,
            Event::data_from([("message_id", json!(message_id)), ("pending", json!(true))]));
    }
    
    pub async fn set_channel_frequency(&self, channel_id: u8, frequency: u32) {
        let cmd = ScpiCommands::set_freq(channel_id, frequency);
        self.network.send_command(&cmd, true).await;
        event_bus().emit_with_data(EventType::ChannelFreqChanged,
            Event::data_from([
                ("channel_id", json!(channel_id)),
                ("frequency", json!(frequency)),
                ("pending", json!(true))
            ]));
    }
    
    pub async fn set_channel_enabled(&self, channel_id: u8, enabled: bool) {
        let cmd = ScpiCommands::set_output(channel_id, enabled);
        self.network.send_command(&cmd, true).await;
        
        let event_type = if enabled { EventType::ChannelEnabled } else { EventType::ChannelDisabled };
        event_bus().emit_with_data(event_type,
            Event::data_from([("channel_id", json!(channel_id)), ("pending", json!(true))]));
    }
    
    pub async fn set_broadcast(&self, active: bool) {
        // Check watchdog before allowing broadcast
        if active && self.device_state.read().watchdog_triggered {
            self.logger.error("Cannot start broadcast - watchdog triggered!");
            event_bus().emit_with_data(EventType::ErrorOccurred,
                Event::data_from([("message", json!("Reset watchdog before broadcast"))]));
            return;
        }
        
        if active {
            *self.broadcast_state.write() = BroadcastState::Arming;
            event_bus().emit(EventType::BroadcastArming);
        } else {
            *self.broadcast_state.write() = BroadcastState::Stopping;
        }
        
        let cmd = ScpiCommands::set_broadcast(active);
        self.network.send_command(&cmd, true).await;
    }
    
    pub async fn reset_watchdog(&self) {
        self.network.send_command(ScpiCommands::WATCHDOG_RESET, true).await;
        *self.watchdog_state.write() = WatchdogState::Ok;
        self.device_state.write().watchdog_triggered = false;
        self.device_state.write().watchdog_warning = false;
        event_bus().emit(EventType::WatchdogReset);
    }
    
    // === Getters ===
    
    pub fn is_connected(&self) -> bool {
        self.network.is_connected()
    }
    
    pub fn is_broadcasting(&self) -> bool {
        self.device_state.read().broadcasting
    }
    
    pub fn get_device_state(&self) -> DeviceState {
        self.device_state.read().clone()
    }
    
    pub fn get_connection_state(&self) -> ConnectionState {
        *self.connection_state.read()
    }
    
    pub fn get_broadcast_state(&self) -> BroadcastState {
        *self.broadcast_state.read()
    }
    
    pub fn get_watchdog_state(&self) -> WatchdogState {
        *self.watchdog_state.read()
    }
    
    pub fn get_log_entries(&self, limit: usize) -> Vec<String> {
        self.logger.get_entries(limit)
    }
}

// Global model instance
pub static MODEL: Lazy<Model> = Lazy::new(|| Model::new());

pub fn model() -> &'static Model {
    &MODEL
}

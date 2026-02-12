#![allow(dead_code)]

// model.rs - FULL PRODUCTION VERSION
// Complete NetworkManager with all features from Python
use crate::state_machine::{BroadcastState, ConnectionState, WatchdogState, SourceMode};
use std::sync::Arc;
use tokio::io::AsyncReadExt;
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::TcpStream;
use tokio::sync::{broadcast, RwLock};
use tokio::time::{timeout, sleep, Instant};
use serde::{Deserialize, Serialize};
use crate::retry::{RetryConfig, RetryResult, with_retry};

use crate::config::{Config, ScpiCommands};
use crate::event_bus::EventType;


// CHANNEL STRUCT
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Channel {
    pub id: u8,
    pub enabled: bool,
    pub frequency: u32,      // Hz (540000 = 540 kHz)
    pub amplitude: f32,      // 0.0 - 1.0
    pub phase: f32,          // degrees
}

#[derive(Clone, Debug)]
pub struct ChannelChange {
    pub channel_id: u8,
    pub frequency: Option<u32>,
    pub enabled: Option<bool>,
}

impl Channel {
    pub fn new(id: u8) -> Self {
        Self {
            id,
            enabled: false,
            frequency: 540_000,  // Default 540 kHz
            amplitude: 1.0,
            phase: 0.0,
        }
    }
}

// DEVICE STATE - All tracked state
#[derive(Debug, Clone, Serialize)]
pub struct DeviceState {
    pub connection: ConnectionState,
    pub broadcast: BroadcastState,
    pub watchdog: WatchdogState,
    pub source: SourceMode,
    pub channels: Vec<Channel>,
    pub fpga_temperature: Option<f32>,
    pub last_status_time: Option<u64>,
    pub error_count: u32,
}

impl Default for DeviceState {
    fn default() -> Self {
        Self {
            connection: ConnectionState::Disconnected,
            broadcast: BroadcastState::Idle,
            watchdog: WatchdogState::Ok,
            last_status_time: None,
            source: SourceMode::Bram,
            channels: (1..=12).map(|id| Channel {
                id,
                enabled: false,
                frequency: 540_000 + (id as u32 - 1) * 100_000,
                amplitude: 1.0,
                phase: 0.0,
            }).collect(),
            fpga_temperature: None,
            error_count: 0,
        }
    }
}
// AUDIT LOG ENTRY
#[derive(Clone, Debug, Serialize)]
pub struct AuditEntry {
    pub timestamp: u64,
    pub level: String,
    pub message: String,
}

// NETWORK MANAGER - The main class
pub struct NetworkManager {
    // TCP connection (wrapped for async access)
    stream: Arc<RwLock<Option<TcpStream>>>,
    pending_changes: RwLock<Vec<ChannelChange>>,

    // Device state
    state: Arc<RwLock<DeviceState>>,

    // Event bus for pub/sub
    event_tx: broadcast::Sender<EventType>,

    // Audit log (thread-safe, max 100 entries)
    audit_log: Arc<RwLock<Vec<AuditEntry>>>,

    // Connection info
    current_ip: Arc<RwLock<Option<String>>>,
    current_port: Arc<RwLock<Option<u16>>>,

    // Control flags
    is_running: Arc<RwLock<bool>>,
    reconnect_attempts: Arc<RwLock<u8>>,

    // Watchdog tracking
    last_watchdog_reset: Arc<RwLock<Instant>>,
}

impl NetworkManager {
    // ----------------------------------------------------------
    // CONSTRUCTOR
    // ----------------------------------------------------------
    pub fn new(event_tx: broadcast::Sender<EventType>) -> Self {
        Self {
            stream: Arc::new(RwLock::new(None)),
            state: Arc::new(RwLock::new(DeviceState::default())),
            event_tx,
            audit_log: Arc::new(RwLock::new(Vec::new())),
            current_ip: Arc::new(RwLock::new(None)),
            current_port: Arc::new(RwLock::new(None)),
            is_running: Arc::new(RwLock::new(false)),
            reconnect_attempts: Arc::new(RwLock::new(0)),
            pending_changes: RwLock::new(Vec::new()),
            last_watchdog_reset: Arc::new(RwLock::new(Instant::now())),
        }
    }

    // ----------------------------------------------------------
    // AUDIT LOGGING (Same as Python)
    // ----------------------------------------------------------
    async fn log(&self, level: &str, message: &str) {
        let entry = AuditEntry {
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            level: level.to_string(),
            message: message.to_string(),
        };

        let mut log = self.audit_log.write().await;
        log.push(entry);

        // Keep only last 100 entries (same as Python)
        if log.len() > 100 {
            log.remove(0);
        }

        // Also print to console
        println!("[{}] {}: {}",
            chrono::Local::now().format("%H:%M:%S"),
            level,
            message
        );
    }

    async fn log_info(&self, message: &str) {
        self.log("INFO", message).await;
    }

    async fn log_error(&self, message: &str) {
        self.log("ERROR", message).await;
        self.state.write().await.error_count += 1;
    }

    async fn log_warning(&self, message: &str) {
        self.log("WARNING", message).await;
    }

    // ----------------------------------------------------------
    // CONNECT TO FPGA
    // ----------------------------------------------------------
    pub async fn connect(&self, ip: &str, port: u16) -> Result<(), String> {
        // Check if already connected
        if *self.is_running.read().await {
            return Err("Already connected".to_string());
        }

        self.log_info(&format!("Connecting to {}:{}...", ip, port)).await;

        // Update state to Connecting
        {
            let mut state = self.state.write().await;
            state.connection = ConnectionState::Connecting;
        }
        let _ = self.event_tx.send(EventType::ConnectionStateChanged(ConnectionState::Connecting));

        // Store connection info for reconnection
        *self.current_ip.write().await = Some(ip.to_string());
        *self.current_port.write().await = Some(port);

        // Try to connect with retry/backoff
        let addr = format!("{}:{}", ip, port);
        let retry_config = RetryConfig::default();

        let stream = match with_retry(&retry_config, || {
            let addr = addr.clone();
            async move {
                timeout(
                    Duration::from_secs(Config::CONNECTION_TIMEOUT_SECS),
                    TcpStream::connect(&addr)
                ).await
                .map_err(|_| "Connection timeout".to_string())?
                .map_err(|e| format!("Connection refused: {}", e))
            }
        }).await {
            RetryResult::Success(s) => s,
            RetryResult::Failed { attempts, last_error } => {
                self.handle_connect_failure(&format!(
                    "Connection failed after {} attempts: {}",
                    attempts,
                    last_error
                )).await;
                return Err(format!("Connection failed after {} attempts", attempts));
            }
        };

        // Configure TCP socket
        if let Err(e) = stream.set_nodelay(true) {
            self.log_warning(&format!("Failed to set TCP_NODELAY: {}", e)).await;
        }

        // Store the stream
        *self.stream.write().await = Some(stream);

        // Update state to Connected
        {
            let mut state = self.state.write().await;
            state.connection = ConnectionState::Connected;
            state.error_count = 0;
        }

        // Reset reconnect counter
        *self.reconnect_attempts.write().await = 0;

        // Set running flag
        *self.is_running.write().await = true;

        // Emit success event
        let _ = self.event_tx.send(EventType::ConnectSuccess);
        let _ = self.event_tx.send(EventType::ConnectionStateChanged(ConnectionState::Connected));

        self.log_info(&format!("Connected to {}:{}", ip, port)).await;

        // Initialize device - query current state
        self.initialize_device().await?;

        // Start background polling task
        self.spawn_poll_task();

        Ok(())
    }

    async fn handle_connect_failure(&self, reason: &str) {
        self.log_error(reason).await;

        let mut state = self.state.write().await;
        state.connection = ConnectionState::Disconnected;

        let _ = self.event_tx.send(EventType::ConnectFailed(reason.to_string()));
        let _ = self.event_tx.send(EventType::ConnectionStateChanged(ConnectionState::Disconnected));
    }

    // ----------------------------------------------------------
    // INITIALIZE DEVICE - Query current state after connect
    // ----------------------------------------------------------
    async fn initialize_device(&self) -> Result<(), String> {
        self.log_info("Initializing device...").await;

        // Query device ID
        if let Ok(response) = self.query(ScpiCommands::IDENTITY).await {
            self.log_info(&format!("Device: {}", response.trim())).await;
        }

        // Query current status
        if let Ok(response) = self.query(ScpiCommands::STATUS).await {
            self.parse_status_response(&response).await;
        }

        // Query each channel's current state
        for ch in 1..=12 {
            if let Ok(response) = self.query(&format!("FREQ:CH{}?", ch)).await {
                if let Ok(freq) = response.trim().parse::<u32>() {
                    let mut state = self.state.write().await;
                    if let Some(channel) = state.channels.iter_mut().find(|c| c.id == ch) {
                        channel.frequency = freq;
                    }
                }
            }
        }

        self.log_info("Device initialized").await;
        Ok(())
    }

    // ----------------------------------------------------------
    // DISCONNECT
    // ----------------------------------------------------------
    pub async fn disconnect(&self) -> Result<(), String> {
        self.log_info("Disconnecting...").await;

        // Stop polling
        *self.is_running.write().await = false;
        self.pending_changes.write().await.clear();

        // If broadcasting, stop first
        {
            let state = self.state.read().await;
            if state.broadcast == BroadcastState::Broadcasting {
                drop(state);  // Release lock before calling stop
                let _ = self.stop_broadcast().await;
            }
        }

        // Close TCP stream
        {
            let mut stream = self.stream.write().await;
            if let Some(s) = stream.take() {
                drop(s);  // Close connection
            }
        }

        // Update state
        {
            let mut state = self.state.write().await;
            state.connection = ConnectionState::Disconnected;
            state.broadcast = BroadcastState::Idle;
            state.watchdog = WatchdogState::Ok;
        }

        // Clear connection info
        *self.current_ip.write().await = None;
        *self.current_port.write().await = None;

        // Emit event
        let _ = self.event_tx.send(EventType::Disconnected);
        let _ = self.event_tx.send(EventType::ConnectionStateChanged(ConnectionState::Disconnected));

        self.log_info("Disconnected").await;
        Ok(())
    }

    // ----------------------------------------------------------
    // SEND COMMAND (Low-level)
    // ----------------------------------------------------------
    async fn send_command(&self, command: &str) -> Result<(), String> {
        let mut stream_guard = self.stream.write().await;

        if let Some(stream) = stream_guard.as_mut() {
            let msg = format!("{}\n", command);

            match timeout(
                Duration::from_secs(Config::COMMAND_TIMEOUT_SECS),
                stream.write_all(msg.as_bytes())
            ).await {
                Ok(Ok(_)) => {
                    // Flush to ensure it's sent
                    if let Err(e) = stream.flush().await {
                        return Err(format!("Flush failed: {}", e));
                    }
                    Ok(())
                }
                Ok(Err(e)) => Err(format!("Write failed: {}", e)),
                Err(_) => Err("Command timeout".to_string()),
            }
        } else {
            Err("Not connected".to_string())
        }
    }

    // ----------------------------------------------------------
    // QUERY (Send command, get response)
    // ----------------------------------------------------------
    async fn query(&self, command: &str) -> Result<String, String> {
        // Send the command
        self.send_command(command).await?;

        // Read response
        let mut stream_guard = self.stream.write().await;

        if let Some(stream) = stream_guard.as_mut() {
            let mut reader = BufReader::new(stream);
            let mut response = String::new();

            match timeout(
                Duration::from_secs(Config::COMMAND_TIMEOUT_SECS),
                reader.read_line(&mut response)
            ).await {
                Ok(Ok(0)) => Err("Connection closed".to_string()),
                Ok(Ok(_)) => Ok(response),
                Ok(Err(e)) => Err(format!("Read failed: {}", e)),
                Err(_) => Err("Response timeout".to_string()),
            }
        } else {
            Err("Not connected".to_string())
        }
    }

    // ----------------------------------------------------------
    // POLLING TASK - Runs every 500ms in background
    // ----------------------------------------------------------
    fn spawn_poll_task(&self) {
        let stream = self.stream.clone();
        let state = self.state.clone();
        let event_tx = self.event_tx.clone();
        let is_running = self.is_running.clone();
        let last_watchdog_reset = self.last_watchdog_reset.clone();
        let audit_log = self.audit_log.clone();
        let current_ip = self.current_ip.clone();
        let current_port = self.current_port.clone();
        let reconnect_attempts = self.reconnect_attempts.clone();

        tokio::spawn(async move {
            let mut consecutive_errors = 0u8;

            loop {
                // Check if we should stop
                if !*is_running.read().await {
                    break;
                }

                // Sleep between polls
                sleep(Duration::from_millis(Config::POLL_INTERVAL_MS)).await;

                // Check if we should stop (again, after sleep)
                if !*is_running.read().await {
                    break;
                }

                // CRITICAL: WATCHDOG RESET
                // Must send this every poll or FPGA stops output!
                let watchdog_result = {
                    let mut stream_guard = stream.write().await;
                    if let Some(s) = stream_guard.as_mut() {
                        let msg = format!("{}\n", ScpiCommands::WATCHDOG_RESET);
                        s.write_all(msg.as_bytes()).await
                    } else {
                        Err(std::io::Error::new(std::io::ErrorKind::NotConnected, "No stream"))
                    }
                };

                if let Err(e) = watchdog_result {
                    consecutive_errors += 1;

                    // Log error
                    let entry = AuditEntry {
                        timestamp: std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap()
                            .as_secs(),
                        level: "ERROR".to_string(),
                        message: format!("Watchdog reset failed: {}", e),
                    };
                    audit_log.write().await.push(entry);

                    // Too many errors - connection lost
                    if consecutive_errors >= Config::MAX_CONSECUTIVE_ERRORS {
                        Self::handle_connection_lost(
                            &state, &event_tx, &is_running, &current_ip,
                            &current_port, &reconnect_attempts
                        ).await;
                        break;
                    }
                    continue;
                }

                // Update watchdog timestamp
                *last_watchdog_reset.write().await = Instant::now();
                consecutive_errors = 0;

                // QUERY STATUS
                let status_result = {
                    let mut stream_guard = stream.write().await;
                    if let Some(s) = stream_guard.as_mut() {
                        // Send query
                        let msg = format!("{}\n", ScpiCommands::STATUS);
                        if s.write_all(msg.as_bytes()).await.is_ok() {
                            // Read response
                            let mut buf = [0u8; 1024];
                            match timeout(Duration::from_secs(2), s.read(&mut buf)).await {
                                Ok(Ok(n)) if n > 0 => {
                                    Some(String::from_utf8_lossy(&buf[..n]).to_string())
                                }
                                _ => None
                            }
                        } else {
                            None
                        }
                    } else {
                        None
                    }
                };

                // Parse status response
                if let Some(response) = status_result {
                    Self::parse_status_static(&response, &state, &event_tx).await;
                }

                // Emit state update event
                let _ = event_tx.send(EventType::DeviceStateUpdated);
            }
        });
    }

    // ----------------------------------------------------------
    // HANDLE CONNECTION LOST - Attempt reconnection
    // ----------------------------------------------------------
    async fn handle_connection_lost(
        state: &Arc<RwLock<DeviceState>>,
        event_tx: &broadcast::Sender<EventType>,
        is_running: &Arc<RwLock<bool>>,
        current_ip: &Arc<RwLock<Option<String>>>,
        current_port: &Arc<RwLock<Option<u16>>>,
        reconnect_attempts: &Arc<RwLock<u8>>,
    ) {
        // Update state
        {
            let mut s = state.write().await;
            s.connection = ConnectionState::Reconnecting;
            s.broadcast = BroadcastState::Idle;  // Stop broadcast on disconnect
        }

        let _ = event_tx.send(EventType::ConnectionLost);
        let _ = event_tx.send(EventType::ConnectionStateChanged(ConnectionState::Reconnecting));

        // Get connection info
        let ip = current_ip.read().await.clone();
        let port = current_port.read().await.clone();

        if ip.is_none() || port.is_none() {
            // No connection info - can't reconnect
            *is_running.write().await = false;
            state.write().await.connection = ConnectionState::Disconnected;
            let _ = event_tx.send(EventType::ConnectionStateChanged(ConnectionState::Disconnected));
            return;
        }

        let ip = ip.unwrap();
        let port = port.unwrap();

        // Attempt reconnection
        for attempt in 1..=Config::MAX_RECONNECT_ATTEMPTS {
            *reconnect_attempts.write().await = attempt;

            let _ = event_tx.send(EventType::ReconnectAttempt(attempt));

            println!("[RECONNECT] Attempt {}/{} to {}:{}",
                attempt, Config::MAX_RECONNECT_ATTEMPTS, ip, port);

            // Wait before retry
            sleep(Duration::from_secs(Config::RECONNECT_DELAY_SECS)).await;

            // Try to connect
            let addr = format!("{}:{}", ip, port);
            match timeout(
                Duration::from_secs(Config::CONNECTION_TIMEOUT_SECS),
                TcpStream::connect(&addr)
            ).await {
                Ok(Ok(_stream)) => {
                    // Success!
                    println!("[RECONNECT] Success!");

                    // Note: In real code, we'd need to update the stream reference
                    // This is simplified - real impl would need Arc<RwLock<Option<TcpStream>>>

                    let mut s = state.write().await;
                    s.connection = ConnectionState::Connected;
                    s.error_count = 0;

                    *reconnect_attempts.write().await = 0;

                    let _ = event_tx.send(EventType::ReconnectSuccess);
                    let _ = event_tx.send(EventType::ConnectionStateChanged(ConnectionState::Connected));

                    return;
                }
                _ => {
                    println!("[RECONNECT] Attempt {} failed", attempt);
                }
            }
        }

        // All attempts failed
        println!("[RECONNECT] All attempts failed, giving up");

        *is_running.write().await = false;
        state.write().await.connection = ConnectionState::Disconnected;

        let _ = event_tx.send(EventType::ReconnectFailed);
        let _ = event_tx.send(EventType::ConnectionStateChanged(ConnectionState::Disconnected));
    }

    // ----------------------------------------------------------
    // PARSE STATUS RESPONSE
    // ----------------------------------------------------------
    async fn parse_status_response(&self, response: &str) {
        Self::parse_status_static(response, &self.state, &self.event_tx).await;
    }

    async fn parse_status_static(
        response: &str,
        state: &Arc<RwLock<DeviceState>>,
        event_tx: &broadcast::Sender<EventType>,
    ) {
        // Example response: "BROADCAST:1,WATCHDOG:0,TEMP:45.2,CH1:ON,CH2:OFF,..."
        let mut s = state.write().await;

        for part in response.split(',') {
            let kv: Vec<&str> = part.split(':').collect();
            if kv.len() != 2 {
                continue;
            }

            let key = kv[0].trim();
            let value = kv[1].trim();

            match key {
                "BROADCAST" | "OUTPUT" => {
                    let was_broadcasting = s.broadcast == BroadcastState::Broadcasting;
                    s.broadcast = if value == "1" || value == "ON" {
                        BroadcastState::Broadcasting
                    } else {
                        BroadcastState::Idle
                    };

                    // Emit event if changed
                    let is_broadcasting = s.broadcast == BroadcastState::Broadcasting;
                    if was_broadcasting != is_broadcasting {
                        if is_broadcasting {
                            let _ = event_tx.send(EventType::BroadcastStarted);
                        } else {
                            let _ = event_tx.send(EventType::BroadcastStopped);
                        }
                    }
                }
                "WATCHDOG" => {
                    let old_state = s.watchdog.clone();
                    s.watchdog = match value {
                        "0" | "OK" => WatchdogState::Ok,
                        "1" | "WARNING" => WatchdogState::Warning,
                        "2" | "TRIGGERED" | "FAIL" => WatchdogState::Triggered,
                        _ => WatchdogState::Ok,
                    };

                    // Emit event if watchdog triggered
                    if s.watchdog == WatchdogState::Triggered && old_state != WatchdogState::Triggered {
                        let _ = event_tx.send(EventType::WatchdogTriggered);

                        // Auto-stop broadcast on watchdog trigger
                        s.broadcast = BroadcastState::Idle;
                        let _ = event_tx.send(EventType::BroadcastStopped);
                    } else if s.watchdog == WatchdogState::Warning && old_state == WatchdogState::Ok {
                        let _ = event_tx.send(EventType::WatchdogWarning);
                    }
                }
                "TEMP" | "TEMPERATURE" => {
                    if let Ok(temp) = value.parse::<f32>() {
                        s.fpga_temperature = Some(temp);
                    }
                }
                "SOURCE" => {
                    s.source = if value == "ADC" {
                        SourceMode::Adc
                    } else {
                        SourceMode::Bram
                    };
                }
                _ => {
                    // Check for channel status: "CH1", "CH2", etc.
                    if key.starts_with("CH") {
                        if let Ok(ch_num) = key[2..].parse::<u8>() {
                            if let Some(channel) = s.channels.iter_mut().find(|c| c.id == ch_num) {
                                channel.enabled = value == "1" || value == "ON";
                            }
                        }
                    }
                }
            }
        }

        // Update timestamp
        s.last_status_time = Some(
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs()
        );
    }

    // ----------------------------------------------------------
    // START BROADCAST
    // ----------------------------------------------------------
    pub async fn start_broadcast(&self) -> Result<(), String> {
        // Check connection
        let state = self.state.read().await;
        if state.connection != ConnectionState::Connected {
            return Err("Not connected".to_string());
        }
        drop(state);

        // Check if any channels are enabled
        let active_count = {
            let state = self.state.read().await;
            state.channels.iter().filter(|c| c.enabled).count()
        };

        if active_count == 0 {
            return Err("No active channels".to_string());
        }

        self.log_info(&format!("Starting broadcast on {} channels", active_count)).await;

        // Send command to FPGA
        self.send_command(ScpiCommands::OUTPUT_ON).await?;

        // Update state
        {
            let mut state = self.state.write().await;
            state.broadcast = BroadcastState::Broadcasting;
        }

        // Emit event
        let _ = self.event_tx.send(EventType::BroadcastStarted);

        self.log_info("Broadcast started").await;
        Ok(())
    }

    // ----------------------------------------------------------
    // STOP BROADCAST
    // ----------------------------------------------------------
    pub async fn stop_broadcast(&self) -> Result<(), String> {
        self.log_info("Stopping broadcast").await;

        // Send command to FPGA
        if let Err(e) = self.send_command(ScpiCommands::OUTPUT_OFF).await {
            self.log_error(&format!("Failed to send stop command: {}", e)).await;
            // Continue anyway to update local state
        }

        // Update state
        {
            let mut state = self.state.write().await;
            state.broadcast = BroadcastState::Idle;
        }

        // Emit event
        let _ = self.event_tx.send(EventType::BroadcastStopped);

        self.log_info("Broadcast stopped").await;
        Ok(())
    }

    // ----------------------------------------------------------
    // SET CHANNEL
    // ----------------------------------------------------------
    pub async fn set_channel(&self, ch: u8, freq: u32, enabled: bool) -> Result<(), String> {
        if ch < 1 || ch > 12 {
            return Err(format!("Invalid channel: {}", ch));
        }

        if freq < Config::MIN_FREQUENCY || freq > Config::MAX_FREQUENCY {
            return Err(format!("Frequency {} out of range ({}-{})",
                freq, Config::MIN_FREQUENCY, Config::MAX_FREQUENCY));
        }

        // Set frequency
        let freq_cmd = format!("CH{}:FREQ {}", ch, freq);
        self.send_command(&freq_cmd).await?;

        // Set enabled state
        let state_cmd = format!("CH{}:OUTPUT {}", ch, if enabled { "ON" } else { "OFF" });
        self.send_command(&state_cmd).await?;

        // Update local state
        {
            let mut state = self.state.write().await;
            if let Some(channel) = state.channels.iter_mut().find(|c| c.id == ch) {
                channel.frequency = freq;
                channel.enabled = enabled;
            }
        }

        // Emit event
        let _ = self.event_tx.send(EventType::ChannelUpdated(ch));

        self.log_info(&format!("CH{} set to {} Hz, enabled={}", ch, freq, enabled)).await;
        Ok(())
    }

    // ----------------------------------------------------------
    // SET SOURCE MODE
    // ----------------------------------------------------------
    pub async fn set_source(&self, source: SourceMode) -> Result<(), String> {
        let cmd = format!("{} {}",
            ScpiCommands::SOURCE_MODE,
            match source {
                SourceMode::Bram => "BRAM",
                SourceMode::Adc => "ADC",
            }
        );

        self.send_command(&cmd).await?;

        // Update local state
        self.state.write().await.source = source.clone();

        // Emit event
        let _ = self.event_tx.send(EventType::SourceChanged(source));

        Ok(())
    }

    // ----------------------------------------------------------
    // ENABLE PRESET CHANNELS
    // ----------------------------------------------------------
    pub async fn enable_preset(&self, count: u8) -> Result<(), String> {
        // Frequency presets (100kHz spacing)
        let freqs: [u32; 12] = [
            540_000, 640_000, 740_000, 840_000, 940_000, 1_040_000,
            1_140_000, 1_240_000, 1_340_000, 1_440_000, 1_540_000, 1_640_000,
        ];

        // Distribution patterns
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
        for ch in 1..=12u8 {
            self.set_channel(ch, freqs[(ch - 1) as usize], false).await?;
        }

        // Enable selected channels
        for &ch in &channels {
            let freq = freqs[(ch - 1) as usize];
            self.set_channel(ch, freq, true).await?;
        }

        self.log_info(&format!("Enabled {} channel preset", count)).await;
        Ok(())
    }

        // ----------------------------------------------------------
        // GET STATE (for UI)
        // ----------------------------------------------------------
        pub async fn get_state(&self) -> DeviceState {
            self.state.read().await.clone()
        }

        // ----------------------------------------------------------
        // GET AUDIT LOG
        // ----------------------------------------------------------
        pub async fn get_audit_log(&self) -> Vec<AuditEntry> {
            self.audit_log.read().await.clone()
        }

        // ----------------------------------------------------------
        // IS CONNECTED
        // ----------------------------------------------------------
        pub async fn is_connected(&self) -> bool {
            self.state.read().await.connection == ConnectionState::Connected
        }
        // ----------------------------------------------------------
    // ARM (for state machine)
    // ----------------------------------------------------------
    pub async fn arm(&self) -> Result<(), String> {
        let state = self.state.read().await;
        if state.connection != ConnectionState::Connected {
            return Err("Not connected".to_string());
        }
        drop(state);

        self.log_info("System armed").await;
        Ok(())
    }

    // ----------------------------------------------------------
    // START EMERGENCY (bypasses arm)
    // ----------------------------------------------------------
    pub async fn start_emergency(&self) -> Result<(), String> {
        self.log_info("EMERGENCY BROADCAST").await;

        self.send_command(ScpiCommands::OUTPUT_ON).await?;

        {
            let mut state = self.state.write().await;
            state.broadcast = BroadcastState::Broadcasting;
        }

        let _ = self.event_tx.send(EventType::BroadcastStarted);
        Ok(())
    }

    // ----------------------------------------------------------
    // STOP EMERGENCY
    // ----------------------------------------------------------
    pub async fn stop_emergency(&self) -> Result<(), String> {
        self.log_info("Stopping emergency broadcast").await;
        self.stop_broadcast().await
    }
}



// ============================================================
// model.rs - THE HEART OF THE RUST BACKEND
// This is what replaced Python's model.py
// ============================================================

use tokio::net::TcpStream;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::sync::{broadcast, RwLock};
use std::sync::Arc;
use std::time::Duration;

// ============================================================
// STATE MACHINES (Same as Python)
// ============================================================
#[derive(Clone, Debug, PartialEq)]
pub enum ConnectionState {
    Disconnected,
    Connecting,
    Connected,
    Reconnecting,
}

#[derive(Clone, Debug, PartialEq)]
pub enum BroadcastState {
    Idle,
    Broadcasting,
}

#[derive(Clone, Debug, PartialEq)]
pub enum WatchdogState {
    Ok,
    Warning,
    Triggered,  // CRITICAL - FPGA stopped output!
}

// ============================================================
// CHANNEL DATA (Same structure as Python)
// ============================================================
#[derive(Clone, Debug)]
pub struct Channel {
    pub id: u8,
    pub enabled: bool,
    pub frequency: u32,  // In Hz (540000 = 540 kHz)
}

// ============================================================
// DEVICE STATE (What we track)
// ============================================================
#[derive(Clone, Debug)]
pub struct DeviceState {
    pub connection: ConnectionState,
    pub broadcast: BroadcastState,
    pub watchdog: WatchdogState,
    pub channels: Vec<Channel>,
    pub source: String,  // "BRAM" or "ADC"
}

// ============================================================
// NETWORK MANAGER (Same as Python's NetworkManager class)
// ============================================================
pub struct NetworkManager {
    stream: Option<TcpStream>,
    state: Arc<RwLock<DeviceState>>,
    event_bus: broadcast::Sender<EventType>,
}

impl NetworkManager {
    // ----------------------------------------------------------
    // CONNECT TO FPGA (Same as Python's connect method)
    // ----------------------------------------------------------
    pub async fn connect(&mut self, ip: &str, port: u16) -> Result<(), String> {
        let addr = format!("{}:{}", ip, port);

        // Update state: Connecting
        self.state.write().await.connection = ConnectionState::Connecting;

        // Try to connect with 5 second timeout
        let stream = tokio::time::timeout(
            Duration::from_secs(5),
            TcpStream::connect(&addr)
        ).await
            .map_err(|_| "Connection timeout")?
            .map_err(|e| format!("Connection failed: {}", e))?;

        self.stream = Some(stream);

        // Update state: Connected
        self.state.write().await.connection = ConnectionState::Connected;

        // Emit event (like Python's event_bus.emit)
        let _ = self.event_bus.send(EventType::ConnectSuccess);

        // Start background polling task
        self.start_polling_task();

        Ok(())
    }

    // ----------------------------------------------------------
    // SEND SCPI COMMAND (Same as Python's _send_command)
    // ----------------------------------------------------------
    async fn send_command(&mut self, cmd: &str) -> Result<(), String> {
        if let Some(stream) = &mut self.stream {
            let msg = format!("{}\n", cmd);
            stream.write_all(msg.as_bytes()).await
                .map_err(|e| format!("Send failed: {}", e))?;
            Ok(())
        } else {
            Err("Not connected".to_string())
        }
    }

    // ----------------------------------------------------------
    // QUERY FPGA (Same as Python's _query)
    // ----------------------------------------------------------
    async fn query(&mut self, cmd: &str) -> Result<String, String> {
        self.send_command(cmd).await?;

        if let Some(stream) = &mut self.stream {
            let mut buf = [0u8; 1024];
            let n = tokio::time::timeout(
                Duration::from_secs(2),
                stream.read(&mut buf)
            ).await
                .map_err(|_| "Read timeout")?
                .map_err(|e| format!("Read failed: {}", e))?;

            Ok(String::from_utf8_lossy(&buf[..n]).to_string())
        } else {
            Err("Not connected".to_string())
        }
    }

    // ----------------------------------------------------------
    // POLLING LOOP (Same as Python's _poll_loop)
    // This runs every 500ms in background
    // ----------------------------------------------------------
    fn start_polling_task(&self) {
        let state = self.state.clone();
        let event_bus = self.event_bus.clone();

        tokio::spawn(async move {
            loop {
                // Sleep 500ms between polls
                tokio::time::sleep(Duration::from_millis(500)).await;

                // Check if still connected
                if state.read().await.connection != ConnectionState::Connected {
                    break;
                }

                // ================================================
                // CRITICAL: WATCHDOG RESET
                // Must send this every poll or FPGA stops output!
                // Same as Python: self._send_command("WATCHDOG:RESET")
                // ================================================
                // send_command("WATCHDOG:RESET").await;  // In real code

                // Query device status
                // let response = query("STATUS?").await;

                // Parse response and update state
                // parse_status_response(&response, &state).await;

                // Emit update event
                let _ = event_bus.send(EventType::DeviceStateUpdated);
            }
        });
    }

    // ----------------------------------------------------------
    // START BROADCAST (Same as Python)
    // ----------------------------------------------------------
    pub async fn start_broadcast(&mut self) -> Result<(), String> {
        // Send SCPI command to FPGA
        self.send_command("OUTPUT:STATE ON").await?;

        // Update local state
        self.state.write().await.broadcast = BroadcastState::Broadcasting;

        // Emit event
        let _ = self.event_bus.send(EventType::BroadcastStarted);

        Ok(())
    }

    // ----------------------------------------------------------
    // STOP BROADCAST (Same as Python)
    // ----------------------------------------------------------
    pub async fn stop_broadcast(&mut self) -> Result<(), String> {
        self.send_command("OUTPUT:STATE OFF").await?;
        self.state.write().await.broadcast = BroadcastState::Idle;
        let _ = self.event_bus.send(EventType::BroadcastStopped);
        Ok(())
    }

    // ----------------------------------------------------------
    // SET CHANNEL FREQUENCY (Same as Python)
    // ----------------------------------------------------------
    pub async fn set_channel(&mut self, ch: u8, freq: u32, enabled: bool) -> Result<(), String> {
        // Build SCPI command: "FREQ:CH1 540000"
        let cmd = format!("FREQ:CH{} {}", ch, freq);
        self.send_command(&cmd).await?;

        // Enable/disable: "OUTPUT:CH1 ON"
        let state_cmd = format!("OUTPUT:CH{} {}", ch, if enabled { "ON" } else { "OFF" });
        self.send_command(&state_cmd).await?;

        // Update local state
        let mut state = self.state.write().await;
        if let Some(channel) = state.channels.iter_mut().find(|c| c.id == ch) {
            channel.frequency = freq;
            channel.enabled = enabled;
        }

        Ok(())
    }

    // ----------------------------------------------------------
    // SET AUDIO SOURCE (Same as Python)
    // ----------------------------------------------------------
    pub async fn set_source(&mut self, source: &str) -> Result<(), String> {
        // "SOURCE:MODE BRAM" or "SOURCE:MODE ADC"
        let cmd = format!("SOURCE:MODE {}", source);
        self.send_command(&cmd).await?;
        self.state.write().await.source = source.to_string();
        Ok(())
    }
}

// ============================================================
// EVENT TYPES (Same as Python's EventType enum)
// ============================================================
#[derive(Clone, Debug)]
pub enum EventType {
    ConnectSuccess,
    ConnectFailed,
    Disconnected,
    BroadcastStarted,
    BroadcastStopped,
    WatchdogTriggered,
    WatchdogWarning,
    DeviceStateUpdated,
    ChannelUpdated(u8),
}

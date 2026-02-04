//! Mock SCPI Server for Testing
//!
//! Run with: cargo run --bin mock-server
//! Then connect GUI to: 127.0.0.1:5000

use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};

fn handle_client(mut stream: TcpStream) {
    let addr = stream.peer_addr().unwrap();
    println!("[CONNECTED] {}", addr);
    println!("{}", "-".repeat(50));

    let reader = BufReader::new(stream.try_clone().unwrap());

    // Simulated state
    let mut broadcasting = false;
    let mut source = "ADC".to_string();
    let mut channels_enabled = [false; 12];
    let mut channels_freq = [540_000u32; 12];

    for line in reader.lines() {
        match line {
            Ok(data) => {
                let data = data.trim();
                if data.is_empty() {
                    continue;
                }

                println!("[RX] {}", data);

                // Handle queries
                if data == "*IDN?" {
                    let response = "RedPitaya,STEMlab125-10,MOCK,v1.0\n";
                    stream.write_all(response.as_bytes()).unwrap();
                    println!("[TX] {}", response.trim());
                } else if data == "STATUS?" {
                    // Build status response
                    let mut parts = vec![
                        format!("broadcasting={}", if broadcasting { "1" } else { "0" }),
                        format!("source={}", source),
                        "watchdog_triggered=0".to_string(),
                        "watchdog_warning=0".to_string(),
                        "watchdog_time=5".to_string(),
                    ];
                    
                    for (i, (enabled, freq)) in channels_enabled.iter().zip(channels_freq.iter()).enumerate() {
                        parts.push(format!("ch{}_enabled={}", i + 1, if *enabled { "1" } else { "0" }));
                        parts.push(format!("ch{}_freq={}", i + 1, freq));
                    }
                    
                    let response = format!("{}\n", parts.join(","));
                    stream.write_all(response.as_bytes()).unwrap();
                    println!("[TX] STATUS (truncated)");
                } else if data == "WATCHDOG:RESET" {
                    println!("     -> Watchdog reset");
                } else if data.starts_with("SOURCE:INPUT ") {
                    source = data.replace("SOURCE:INPUT ", "");
                    println!("     -> Audio source set to: {}", source);
                } else if data.starts_with("SOURCE:MSG ") {
                    let msg = data.replace("SOURCE:MSG ", "");
                    println!("     -> Message selected: #{}", msg);
                } else if data.starts_with("FREQ:CH") {
                    // Parse FREQ:CH1 540000
                    let parts: Vec<&str> = data.split_whitespace().collect();
                    if parts.len() >= 2 {
                        let ch_str = parts[0].replace("FREQ:CH", "");
                        if let (Ok(ch), Ok(freq)) = (ch_str.parse::<usize>(), parts[1].parse::<u32>()) {
                            if ch >= 1 && ch <= 12 {
                                channels_freq[ch - 1] = freq;
                                println!("     -> CH{} frequency: {} Hz ({:.0} kHz)", ch, freq, freq as f64 / 1000.0);
                            }
                        }
                    }
                } else if data.starts_with("CH") && data.contains(":OUTPUT ") {
                    // Parse CH1:OUTPUT ON
                    let data = data.replace(":", " ");
                    let parts: Vec<&str> = data.split_whitespace().collect();
                    if parts.len() >= 3 {
                        let ch_str = parts[0].replace("CH", "");
                        if let Ok(ch) = ch_str.parse::<usize>() {
                            if ch >= 1 && ch <= 12 {
                                let enabled = parts[2] == "ON";
                                channels_enabled[ch - 1] = enabled;
                                println!("     -> CH{} output: {}", ch, if enabled { "ON" } else { "OFF" });
                            }
                        }
                    }
                } else if data.starts_with("OUTPUT:STATE ") {
                    let state = data.replace("OUTPUT:STATE ", "");
                    broadcasting = state == "ON";
                    if broadcasting {
                        println!("     -> *** BROADCAST STARTED ***");
                    } else {
                        println!("     -> *** BROADCAST STOPPED ***");
                    }
                }

                println!();
            }
            Err(_) => break,
        }
    }

    println!("{}", "-".repeat(50));
    println!("[DISCONNECTED]");
    println!();
}

fn main() {
    let listener = TcpListener::bind("0.0.0.0:5000").expect("Failed to bind to port 5000");

    println!("{}", "=".repeat(50));
    println!("MOCK SCPI SERVER (Rust)");
    println!("{}", "=".repeat(50));
    println!("Listening on port 5000...");
    println!("Connect GUI to: 127.0.0.1:5000");
    println!("{}", "=".repeat(50));
    println!();

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                std::thread::spawn(|| handle_client(stream));
            }
            Err(e) => {
                eprintln!("Error accepting connection: {}", e);
            }
        }
    }
}

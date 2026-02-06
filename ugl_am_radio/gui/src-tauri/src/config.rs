// ============================================================
// config.rs - ALL CONFIGURATION CONSTANTS
// Same as Python's config.py
// ============================================================

/// Application configuration constants
pub struct Config;

impl Config {
    // ----------------------------------------------------------
    // NETWORK
    // ----------------------------------------------------------
    pub const DEFAULT_IP: &'static str = "192.168.0.100";
    pub const DEFAULT_PORT: u16 = 5000;
    pub const CONNECTION_TIMEOUT_SECS: u64 = 5;
    pub const COMMAND_TIMEOUT_SECS: u64 = 2;

    // ----------------------------------------------------------
    // POLLING
    // ----------------------------------------------------------
    pub const POLL_INTERVAL_MS: u64 = 500;  // 500ms = 2Hz polling
    pub const WATCHDOG_TIMEOUT_SECS: u64 = 5;

    // ----------------------------------------------------------
    // RECONNECTION
    // ----------------------------------------------------------
    pub const MAX_RECONNECT_ATTEMPTS: u8 = 5;
    pub const RECONNECT_DELAY_SECS: u64 = 2;
    pub const MAX_CONSECUTIVE_ERRORS: u8 = 3;

    // ----------------------------------------------------------
    // FREQUENCY LIMITS (Hz)
    // ----------------------------------------------------------
    pub const MIN_FREQUENCY: u32 = 500_000;    // 500 kHz
    pub const MAX_FREQUENCY: u32 = 1_700_000;  // 1700 kHz
    pub const DEFAULT_FREQUENCY: u32 = 540_000; // 540 kHz

    // ----------------------------------------------------------
    // CHANNELS
    // ----------------------------------------------------------
    pub const NUM_CHANNELS: u8 = 12;

    // ----------------------------------------------------------
    // AUDIT LOG
    // ----------------------------------------------------------
    pub const MAX_LOG_ENTRIES: usize = 100;
}

/// SCPI Commands - matches FPGA firmware protocol
pub struct ScpiCommands;

impl ScpiCommands {
    // ----------------------------------------------------------
    // SYSTEM COMMANDS
    // ----------------------------------------------------------
    pub const IDENTITY: &'static str = "*IDN?";
    pub const RESET: &'static str = "*RST";
    pub const STATUS: &'static str = "STATUS?";

    // ----------------------------------------------------------
    // WATCHDOG (CRITICAL FOR SAFETY)
    // ----------------------------------------------------------
    pub const WATCHDOG_RESET: &'static str = "WATCHDOG:RESET";
    pub const WATCHDOG_STATUS: &'static str = "WATCHDOG:STATUS?";
    pub const WATCHDOG_TIMEOUT: &'static str = "WATCHDOG:TIMEOUT";  // Set timeout

    // ----------------------------------------------------------
    // OUTPUT CONTROL
    // ----------------------------------------------------------
    pub const OUTPUT_ON: &'static str = "OUTPUT:STATE ON";
    pub const OUTPUT_OFF: &'static str = "OUTPUT:STATE OFF";
    pub const OUTPUT_STATUS: &'static str = "OUTPUT:STATE?";
    pub const OUTPUT_CH_PREFIX: &'static str = "CH";  // OUTPUT:CH1 ON

    // ----------------------------------------------------------
    // FREQUENCY CONTROL
    // ----------------------------------------------------------
    pub const FREQ_PREFIX: &'static str = "CH";  // FREQ:CH1 540000
    pub const FREQ_QUERY_PREFIX: &'static str = "FREQ:CH";  // FREQ:CH1?

    // ----------------------------------------------------------
    // AMPLITUDE CONTROL
    // ----------------------------------------------------------
    pub const AMP_PREFIX: &'static str = "AMP:CH";  // AMP:CH1 0.5

    // ----------------------------------------------------------
    // PHASE CONTROL
    // ----------------------------------------------------------
    pub const PHASE_PREFIX: &'static str = "PHASE:CH";  // PHASE:CH1 90

    // ----------------------------------------------------------
    // SOURCE CONTROL
    // ----------------------------------------------------------
    pub const SOURCE_MODE: &'static str = "SOURCE:MODE";  // SOURCE:MODE BRAM
    pub const SOURCE_BRAM: &'static str = "SOURCE:MODE BRAM";
    pub const SOURCE_ADC: &'static str = "SOURCE:MODE ADC";
    pub const SOURCE_STATUS: &'static str = "SOURCE:MODE?";

    // ----------------------------------------------------------
    // BRAM (Pre-recorded audio) CONTROL
    // ----------------------------------------------------------
    pub const BRAM_SELECT: &'static str = "BRAM:SELECT";  // BRAM:SELECT 0 (message index)
    pub const BRAM_LIST: &'static str = "BRAM:LIST?";

    // ----------------------------------------------------------
    // DIAGNOSTIC COMMANDS
    // ----------------------------------------------------------
    pub const TEMP_QUERY: &'static str = "SYSTEM:TEMP?";
    pub const UPTIME_QUERY: &'static str = "SYSTEM:UPTIME?";
    pub const ERROR_QUERY: &'static str = "SYSTEM:ERROR?";
}

/// Frequency presets for quick channel setup
pub struct FrequencyPresets;

impl FrequencyPresets {
    /// Get frequency for channel (100kHz spacing starting at 540kHz)
    pub fn for_channel(ch: u8) -> u32 {
        let base = 540_000u32;
        let spacing = 100_000u32;
        base + (ch.saturating_sub(1) as u32) * spacing
    }

    /// Get all 12 preset frequencies
    pub fn all() -> [u32; 12] {
        [
            540_000,   // CH1
            640_000,   // CH2
            740_000,   // CH3
            840_000,   // CH4
            940_000,   // CH5
            1_040_000, // CH6
            1_140_000, // CH7
            1_240_000, // CH8
            1_340_000, // CH9
            1_440_000, // CH10
            1_540_000, // CH11
            1_640_000, // CH12
        ]
    }
}

/// Channel distribution presets
pub struct ChannelPresets;

impl ChannelPresets {
    /// Get channel IDs for a given preset count
    pub fn for_count(count: u8) -> Vec<u8> {
        match count {
            1 => vec![1],
            2 => vec![1, 7],
            3 => vec![12, 4, 8],
            4 => vec![12, 3, 6, 9],
            6 => vec![12, 2, 4, 6, 8, 10],
            8 => vec![12, 1, 3, 4, 6, 7, 9, 10],
            12 => (1..=12).collect(),
            _ => vec![1],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_frequency_presets() {
        assert_eq!(FrequencyPresets::for_channel(1), 540_000);
        assert_eq!(FrequencyPresets::for_channel(12), 1_640_000);
    }

    #[test]
    fn test_channel_presets() {
        assert_eq!(ChannelPresets::for_count(3), vec![12, 4, 8]);
        assert_eq!(ChannelPresets::for_count(12).len(), 12);
    }
}

#[cfg(test)]
mod additional_tests {
    use super::*;

    #[test]
    fn test_frequency_presets_spacing() {
        for ch in 1..12u8 {
            let diff = FrequencyPresets::for_channel(ch + 1) - FrequencyPresets::for_channel(ch);
            assert_eq!(diff, 100_000, "Channel {} to {} spacing wrong", ch, ch + 1);
        }
    }

    #[test]
    fn test_frequency_within_am_band() {
        for ch in 1..=12u8 {
            let freq = FrequencyPresets::for_channel(ch);
            assert!(freq >= Config::MIN_FREQUENCY,
                "CH{} freq {} below min", ch, freq);
            assert!(freq <= Config::MAX_FREQUENCY,
                "CH{} freq {} above max", ch, freq);
        }
    }

    #[test]
    fn test_all_presets_match_for_channel() {
        let all = FrequencyPresets::all();
        for (i, &freq) in all.iter().enumerate() {
            assert_eq!(freq, FrequencyPresets::for_channel((i + 1) as u8));
        }
    }

    #[test]
    fn test_channel_presets_no_duplicates() {
        for count in [1, 2, 3, 4, 6, 8, 12] {
            let channels = ChannelPresets::for_count(count);
            let mut sorted = channels.clone();
            sorted.sort();
            sorted.dedup();
            assert_eq!(channels.len(), sorted.len(),
                "Duplicate channels in preset {}", count);
        }
    }

    #[test]
    fn test_channel_presets_valid_range() {
        for count in [1, 2, 3, 4, 6, 8, 12] {
            for &ch in &ChannelPresets::for_count(count) {
                assert!(ch >= 1 && ch <= 12,
                    "Channel {} out of range in preset {}", ch, count);
            }
        }
    }

    #[test]
    fn test_channel_preset_counts() {
        assert_eq!(ChannelPresets::for_count(1).len(), 1);
        assert_eq!(ChannelPresets::for_count(2).len(), 2);
        assert_eq!(ChannelPresets::for_count(3).len(), 3);
        assert_eq!(ChannelPresets::for_count(4).len(), 4);
        assert_eq!(ChannelPresets::for_count(6).len(), 6);
        assert_eq!(ChannelPresets::for_count(8).len(), 8);
        assert_eq!(ChannelPresets::for_count(12).len(), 12);
    }

    #[test]
    fn test_invalid_preset_defaults_to_one() {
        assert_eq!(ChannelPresets::for_count(5).len(), 1);
        assert_eq!(ChannelPresets::for_count(0).len(), 1);
        assert_eq!(ChannelPresets::for_count(99).len(), 1);
    }

    #[test]
    fn test_polling_faster_than_watchdog() {
        assert!(Config::POLL_INTERVAL_MS < Config::WATCHDOG_TIMEOUT_SECS * 1000,
            "Polling slower than watchdog timeout!");
    }

    #[test]
    fn test_reconnect_config_sane() {
        assert!(Config::MAX_RECONNECT_ATTEMPTS > 0);
        assert!(Config::MAX_CONSECUTIVE_ERRORS > 0);
        assert!(Config::CONNECTION_TIMEOUT_SECS > 0);
    }
}

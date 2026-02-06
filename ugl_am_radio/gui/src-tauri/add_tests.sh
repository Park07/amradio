#!/bin/bash
# Run from: ~/amradio/ugl_am_radio/gui/src-tauri
# Usage: bash add_tests.sh

rm -f src/additional_tests.rs

echo "Adding tests to state_machine.rs..."
cat >> src/state_machine.rs << 'EOF'

#[cfg(test)]
mod additional_tests {
    use super::*;

    #[test]
    fn test_cannot_double_arm() {
        assert!(BroadcastState::Arming.request_arm().is_err());
        assert!(BroadcastState::Armed.request_arm().is_err());
    }

    #[test]
    fn test_cannot_start_while_stopping() {
        assert!(BroadcastState::Stopping.request_start().is_err());
    }

    #[test]
    fn test_stop_cancels_arming() {
        assert_eq!(BroadcastState::Arming.request_stop().unwrap(), BroadcastState::Idle);
    }

    #[test]
    fn test_stop_disarms() {
        assert_eq!(BroadcastState::Armed.request_stop().unwrap(), BroadcastState::Idle);
    }

    #[test]
    fn test_emergency_stops_correctly() {
        assert_eq!(BroadcastState::Emergency.request_stop_emergency().unwrap(), BroadcastState::Idle);
    }

    #[test]
    fn test_cannot_stop_emergency_from_normal() {
        assert!(BroadcastState::Idle.request_stop_emergency().is_err());
        assert!(BroadcastState::Broadcasting.request_stop_emergency().is_err());
    }

    #[test]
    fn test_is_broadcasting() {
        assert!(!BroadcastState::Idle.is_broadcasting());
        assert!(!BroadcastState::Armed.is_broadcasting());
        assert!(BroadcastState::Broadcasting.is_broadcasting());
        assert!(BroadcastState::Emergency.is_broadcasting());
    }

    #[test]
    fn test_is_transitioning() {
        assert!(BroadcastState::Arming.is_transitioning());
        assert!(BroadcastState::Starting.is_transitioning());
        assert!(BroadcastState::Stopping.is_transitioning());
        assert!(!BroadcastState::Idle.is_transitioning());
        assert!(!BroadcastState::Broadcasting.is_transitioning());
    }

    #[test]
    fn test_display_strings() {
        assert_eq!(BroadcastState::Idle.display(), "IDLE");
        assert_eq!(BroadcastState::Broadcasting.display(), "BROADCASTING");
        assert_eq!(BroadcastState::Emergency.display(), "EMERGENCY");
        assert_eq!(ConnectionState::Disconnected.display(), "DISCONNECTED");
        assert_eq!(ConnectionState::Connected.display(), "CONNECTED");
    }

    #[test]
    fn test_watchdog_from_status() {
        assert_eq!(WatchdogState::from_status("OK"), WatchdogState::Ok);
        assert_eq!(WatchdogState::from_status("0"), WatchdogState::Ok);
        assert_eq!(WatchdogState::from_status("WARNING"), WatchdogState::Warning);
        assert_eq!(WatchdogState::from_status("1"), WatchdogState::Warning);
        assert_eq!(WatchdogState::from_status("TRIGGERED"), WatchdogState::Triggered);
        assert_eq!(WatchdogState::from_status("FAIL"), WatchdogState::Triggered);
        assert_eq!(WatchdogState::from_status("garbage"), WatchdogState::Ok);
    }

    #[test]
    fn test_source_mode_roundtrip() {
        assert_eq!(SourceMode::from_str("BRAM"), SourceMode::Bram);
        assert_eq!(SourceMode::from_str("ADC"), SourceMode::Adc);
        assert_eq!(SourceMode::from_str("bram"), SourceMode::Bram);
        assert_eq!(SourceMode::from_str("garbage"), SourceMode::Bram);
        assert_eq!(SourceMode::from_str(SourceMode::Bram.as_str()), SourceMode::Bram);
        assert_eq!(SourceMode::from_str(SourceMode::Adc.as_str()), SourceMode::Adc);
    }

    #[test]
    fn test_default_states() {
        assert_eq!(BroadcastState::default(), BroadcastState::Idle);
        assert_eq!(ConnectionState::default(), ConnectionState::Disconnected);
        assert_eq!(WatchdogState::default(), WatchdogState::Ok);
        assert_eq!(SourceMode::default(), SourceMode::Bram);
    }

    #[test]
    fn test_confirm_noop_wrong_state() {
        assert_eq!(BroadcastState::Idle.confirm_armed(), BroadcastState::Idle);
        assert_eq!(BroadcastState::Idle.confirm_broadcasting(), BroadcastState::Idle);
        assert_eq!(BroadcastState::Idle.confirm_stopped(), BroadcastState::Idle);
        assert_eq!(BroadcastState::Broadcasting.confirm_armed(), BroadcastState::Broadcasting);
    }
}
EOF

echo "Adding tests to config.rs..."
cat >> src/config.rs << 'EOF'

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
EOF

echo "Adding tests to retry.rs..."
cat >> src/retry.rs << 'EOF'

#[cfg(test)]
mod additional_tests {
    use super::*;

    #[test]
    fn test_delay_never_exceeds_max() {
        let config = RetryConfig::default();
        for attempt in 0..100 {
            assert!(config.delay_for_attempt(attempt) <= Duration::from_millis(config.max_delay_ms));
        }
    }

    #[test]
    fn test_delay_is_exponential() {
        let config = RetryConfig::default();
        let d1 = config.delay_for_attempt(1);
        let d2 = config.delay_for_attempt(2);
        let d3 = config.delay_for_attempt(3);
        assert_eq!(d2.as_millis(), d1.as_millis() * 2);
        assert_eq!(d3.as_millis(), d2.as_millis() * 2);
    }

    #[test]
    fn test_custom_retry_config() {
        let config = RetryConfig {
            max_attempts: 10,
            initial_delay_ms: 500,
            max_delay_ms: 5000,
            multiplier: 3.0,
        };
        assert_eq!(config.delay_for_attempt(0), Duration::ZERO);
        assert_eq!(config.delay_for_attempt(1), Duration::from_millis(500));
        assert_eq!(config.delay_for_attempt(2), Duration::from_millis(1500));
        assert_eq!(config.delay_for_attempt(3), Duration::from_millis(4500));
        assert_eq!(config.delay_for_attempt(4), Duration::from_millis(5000));
    }
}
EOF

echo "Adding tests to event_bus.rs..."
cat >> src/event_bus.rs << 'EOF'

#[cfg(test)]
mod additional_tests {
    use super::*;

    #[tokio::test]
    async fn test_watchdog_event_types() {
        let bus = EventBus::new();
        let mut rx = bus.subscribe();

        bus.emit(EventType::WatchdogTriggered);
        assert!(matches!(rx.recv().await.unwrap(), EventType::WatchdogTriggered));

        bus.emit(EventType::WatchdogWarning);
        assert!(matches!(rx.recv().await.unwrap(), EventType::WatchdogWarning));
    }

    #[tokio::test]
    async fn test_event_ordering() {
        let bus = EventBus::new();
        let mut rx = bus.subscribe();

        bus.emit(EventType::ConnectSuccess);
        bus.emit(EventType::BroadcastStarted);
        bus.emit(EventType::WatchdogTriggered);

        assert!(matches!(rx.recv().await.unwrap(), EventType::ConnectSuccess));
        assert!(matches!(rx.recv().await.unwrap(), EventType::BroadcastStarted));
        assert!(matches!(rx.recv().await.unwrap(), EventType::WatchdogTriggered));
    }

    #[test]
    fn test_no_subscribers_doesnt_panic() {
        let bus = EventBus::new();
        bus.emit(EventType::ConnectSuccess);
        bus.emit(EventType::WatchdogTriggered);
    }
}
EOF

echo ""
echo "All tests added. Running cargo test..."
echo ""
cargo test 2>&1 | grep -E "^(running|test |test result)"
// event_bus.js
// Pub/Sub system + Tauri backend event listener

const EventBus = {
  subscribers: {},

  // Subscribe to an event
  subscribe(event, callback) {
    if (!this.subscribers[event]) {
      this.subscribers[event] = [];
    }
    this.subscribers[event].push(callback);

    // Return unsubscribe function
    return () => {
      this.subscribers[event] = this.subscribers[event].filter(cb => cb !== callback);
    };
  },

  // Publish an event
  publish(event, data) {
    if (this.subscribers[event]) {
      this.subscribers[event].forEach(callback => {
        try {
          callback(data);
        } catch (err) {
          console.error(`EventBus error in ${event}:`, err);
        }
      });
    }
  },

  // Initialize Tauri backend listener
  async initTauriBridge() {
    if (window.__TAURI__ && window.__TAURI__.event) {
      const { listen } = window.__TAURI__.event;

      // Listen for backend events
      await listen('backend_event', (event) => {
        const { type, payload } = event.payload;
        console.log('Backend event:', type, payload);

        // Republish to local subscribers
        this.publish(type, payload);

        // Also publish generic state_changed for View to re-render
        if (type === 'StateChanged') {
          this.publish('state_changed', payload);
        }
      });

      console.log('Tauri event bridge initialized');
    } else {
      console.warn('Tauri events not available - running in browser mode');
    }
  }
};

// Event types (mirrors Rust event_bus.rs)
const Events = {
  // Connection
  CONNECTED: 'Connected',
  DISCONNECTED: 'Disconnected',
  CONNECTION_FAILED: 'ConnectionFailed',
  RECONNECTING: 'Reconnecting',

  // Broadcast
  ARMED: 'Armed',
  BROADCAST_STARTED: 'BroadcastStarted',
  BROADCAST_STOPPED: 'BroadcastStopped',
  EMERGENCY_STARTED: 'EmergencyStarted',
  EMERGENCY_STOPPED: 'EmergencyStopped',

  // Watchdog
  WATCHDOG_OK: 'WatchdogOk',
  WATCHDOG_WARNING: 'WatchdogWarning',
  WATCHDOG_TRIGGERED: 'WatchdogTriggered',

  // Channel
  CHANNEL_ENABLED: 'ChannelEnabled',
  CHANNEL_DISABLED: 'ChannelDisabled',
  FREQUENCY_CHANGED: 'FrequencyChanged',

  // State
  STATE_CHANGED: 'state_changed',

  // UI events (local only)
  UI_CHANNEL_SELECTED: 'ui_channel_selected',
  UI_DIAL_ROTATED: 'ui_dial_rotated',
  UI_LOG: 'ui_log',
};

// Export for use in other modules
window.EventBus = EventBus;
window.Events = Events;

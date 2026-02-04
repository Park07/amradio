// model.js
// Stateless API calls to Rust backend
// NO LOCAL STATE - Rust is source of truth

const Model = {
  // Tauri invoke wrapper
  async invoke(cmd, args = {}) {
    if (window.__TAURI__ && window.__TAURI__.invoke) {
      return await window.__TAURI__.invoke(cmd, args);
    } else {
      console.log('Mock invoke:', cmd, args);
      return null;
    }
  },

  // ==================== CONNECTION ====================

  async connect(ip, port) {
    try {
      const result = await this.invoke('connect', { ip, port: parseInt(port) });
      EventBus.publish(Events.UI_LOG, { message: `Connected to ${ip}:${port}`, type: 'success' });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Connection failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  async disconnect() {
    try {
      const result = await this.invoke('disconnect');
      EventBus.publish(Events.UI_LOG, { message: 'Disconnected', type: 'warning' });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Disconnect failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  // ==================== BROADCAST STATE MACHINE ====================

  async arm() {
    try {
      const result = await this.invoke('arm');
      EventBus.publish(Events.UI_LOG, { message: 'System armed', type: 'success' });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Arm failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  async startBroadcast() {
    try {
      const result = await this.invoke('start_broadcast');
      EventBus.publish(Events.UI_LOG, { message: 'Broadcast started', type: 'success' });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Start failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  async stopBroadcast() {
    try {
      const result = await this.invoke('stop_broadcast');
      EventBus.publish(Events.UI_LOG, { message: 'Broadcast stopped', type: 'warning' });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Stop failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  async startEmergency() {
    try {
      const result = await this.invoke('start_emergency');
      EventBus.publish(Events.UI_LOG, { message: 'EMERGENCY BROADCAST STARTED', type: 'error' });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Emergency failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  async stopEmergency() {
    try {
      const result = await this.invoke('stop_emergency');
      EventBus.publish(Events.UI_LOG, { message: 'Emergency broadcast stopped', type: 'warning' });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Stop emergency failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  // ==================== CHANNEL CONTROL ====================

  async updateChannel(channelId, update) {
    try {
      const result = await this.invoke('update_channel', {
        channelId: parseInt(channelId),
        update
      });
      const status = update.enabled ? 'enabled' : 'disabled';
      EventBus.publish(Events.UI_LOG, { 
        message: `CH${channelId} ${status}${update.frequency ? ` @ ${update.frequency/1000}kHz` : ''}`, 
        type: update.enabled ? 'success' : 'warning' 
      });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Channel update failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  async enablePresetChannels(count) {
    try {
      const result = await this.invoke('enable_preset_channels', { count: parseInt(count) });
      EventBus.publish(Events.UI_LOG, { message: `Enabled ${count} channel(s)`, type: 'success' });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Preset failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  // ==================== SOURCE CONTROL ====================

  async setSource(source) {
    try {
      const result = await this.invoke('set_source', { source });
      EventBus.publish(Events.UI_LOG, { message: `Source set to ${source}`, type: 'success' });
      return result;
    } catch (err) {
      EventBus.publish(Events.UI_LOG, { message: `Source change failed: ${err}`, type: 'error' });
      throw err;
    }
  },

  // ==================== STATE POLLING ====================

  async getState() {
    try {
      return await this.invoke('get_state');
    } catch (err) {
      console.error('Failed to get state:', err);
      return null;
    }
  },

  // Start polling loop (500ms)
  startPolling(interval = 500) {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
    }

    this.pollTimer = setInterval(async () => {
      const state = await this.getState();
      if (state) {
        EventBus.publish(Events.STATE_CHANGED, state);
      }
    }, interval);

    console.log(`Polling started (${interval}ms)`);
  },

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
      console.log('Polling stopped');
    }
  }
};

// Export
window.Model = Model;

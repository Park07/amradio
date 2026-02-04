// controller.js
// Event handlers and user interaction logic
// Coordinates between View and Model

const Controller = {
  // Local UI state (only for things Rust doesn't track)
  isEditingFreq: false,
  selectedChannel: 12,
  currentFreq: 540,
  broadcastSeconds: 0,
  broadcastTimer: null,
  dialRotation: 0,
  isDragging: false,

  // Constants
  MIN_FREQ: 500,
  MAX_FREQ: 1700,

  // ==================== INITIALIZATION ====================

  async init() {
    // Initialize EventBus bridge
    await EventBus.initTauriBridge();

    // Initialize View
    View.init();

    // Bind event handlers
    this.bindConnectionEvents();
    this.bindBroadcastEvents();
    this.bindChannelEvents();
    this.bindDialEvents();
    this.bindFrequencyEvents();
    this.bindSourceEvents();
    this.bindKeyboardEvents();
    this.bindModalEvents();

    // Start polling
    Model.startPolling(500);

    // Subscribe to state changes for timer logic
    EventBus.subscribe(Events.STATE_CHANGED, (state) => this.onStateChanged(state));

    // Initial render
    this.selectChannel(12);
    View.addLog('System ready', 'success');

    console.log('Controller initialized');
  },

  // ==================== STATE CHANGE HANDLER ====================

  onStateChanged(state) {
    if (!state) return;

    // Handle broadcast timer
    const isBroadcasting = state.broadcast === 'BROADCASTING' || state.broadcast === 'EMERGENCY';

    if (isBroadcasting && !this.broadcastTimer) {
      // Start timer
      this.broadcastSeconds = 0;
      this.broadcastTimer = setInterval(() => {
        this.broadcastSeconds++;
        View.updateBroadcastTimer(this.broadcastSeconds);
      }, 1000);
    } else if (!isBroadcasting && this.broadcastTimer) {
      // Stop timer
      clearInterval(this.broadcastTimer);
      this.broadcastTimer = null;
      View.resetBroadcastTimer();
    }

    // Update channel config panel
  },

  // ==================== CONNECTION EVENTS ====================

  bindConnectionEvents() {
    const connectBtn = document.getElementById('connectBtn');

    connectBtn.addEventListener('click', async () => {
      const state = await Model.getState();

      if (state?.connection === 'CONNECTED') {
        await Model.disconnect();
      } else {
        const ip = document.getElementById('ipInput').value || '192.168.0.100';
        const port = document.getElementById('portInput').value || '5000';
        await Model.connect(ip, port);
      }
    });
  },

  // ==================== BROADCAST EVENTS ====================

  bindBroadcastEvents() {
    const broadcastBtn = document.getElementById('broadcastBtn');
    const armBtn = document.getElementById('armBtn');
    const emergencyBtn = document.getElementById('emergencyBtn');

    // Main broadcast button
    broadcastBtn.addEventListener('click', async () => {
      const state = await Model.getState();

      if (state.can_stop) {
        // Stop broadcast
        if (state.is_emergency) {
          await Model.stopEmergency();
        } else {
          await Model.stopBroadcast();
        }
      } else {
        // Show confirmation modal
        const activeCount = state.channels.filter(c => c.enabled).length;
        if (activeCount === 0) {
          View.addLog('No active channels to broadcast', 'error');
          return;
        }
        View.showModal(activeCount);
      }
    });

    // Arm button (if exists)
    if (armBtn) {
      armBtn.addEventListener('click', async () => {
        await Model.arm();
      });
    }

    // Emergency button (if exists)
    if (emergencyBtn) {
      emergencyBtn.addEventListener('click', async () => {
        const state = await Model.getState();
        if (state.is_emergency) {
          await Model.stopEmergency();
        } else {
          await Model.startEmergency();
        }
      });
    }
  },

  // ==================== CHANNEL EVENTS ====================

  bindChannelEvents() {
    const channelToggle = document.getElementById('channelToggle');

    // Channel toggle
    channelToggle.addEventListener('click', () => this.toggleSelectedChannel());

    // Channel markers (dial labels)
    document.querySelectorAll('.channel-marker').forEach(marker => {
      marker.addEventListener('click', () => {
        this.selectChannel(parseInt(marker.dataset.channel));
      });
    });

    // Summary grid items
    document.querySelectorAll('.summary-item').forEach(item => {
      item.addEventListener('click', () => {
        this.selectChannel(parseInt(item.dataset.channel));
      });

      item.addEventListener('dblclick', () => {
        this.selectChannel(parseInt(item.dataset.channel));
        this.toggleSelectedChannel();
      });
    });

    // Quick channel presets
    document.querySelectorAll('.quick-ch-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const count = parseInt(btn.dataset.count);
        await Model.enablePresetChannels(count);
      });
    });
  },

  selectChannel(channel) {
    this.selectedChannel = channel;

    // Update dial rotation
    const angle = ((channel % 12) * 30);
    this.dialRotation = angle;
    View.renderDialRotation(angle);

    // Publish for View to update
    EventBus.publish(Events.UI_CHANNEL_SELECTED, channel);

    // Get current state for this channel
    Model.getState().then(state => {
      const ch = state?.channels?.find(c => c.id === channel);
      View.renderChannelConfig(ch, this.currentFreq);
      if (ch?.enabled && ch?.frequency) {
        this.currentFreq = Math.round(ch.frequency / 1000);
      }
    });
  },

  async toggleSelectedChannel() {
    const state = await Model.getState();
    const channel = state?.channels?.find(c => c.id === this.selectedChannel);
    const newEnabled = !channel?.enabled;

    console.log("Sending freq:", this.currentFreq * 1000); await Model.updateChannel(this.selectedChannel, {
      enabled: newEnabled,
      frequency: this.currentFreq * 1000
    });

    if (newEnabled) {
      View.pulseDialEnabled();
    }
  },

  // ==================== DIAL EVENTS ====================

  bindDialEvents() {
    const dialKnob = document.getElementById('dialKnob');

    dialKnob.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      View.setDialDragging(true);
      e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
      if (!this.isDragging) return;

      const angle = this.getAngleFromCenter(e, dialKnob.parentElement);
      View.renderDialRotation(angle);
      this.dialRotation = angle;
    });

    document.addEventListener('mouseup', () => {
      if (this.isDragging) {
        this.isDragging = false;
        View.setDialDragging(false);

        // Snap to channel
        const channel = this.angleToChannel(this.dialRotation);
        this.selectChannel(channel);
      }
    });

    // Double-click to toggle
    dialKnob.addEventListener('dblclick', () => this.toggleSelectedChannel());
  },

  getAngleFromCenter(e, element) {
    const rect = element.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const x = e.clientX - centerX;
    const y = e.clientY - centerY;
    let angle = Math.atan2(y, x) * (180 / Math.PI) + 90;
    if (angle < 0) angle += 360;
    return angle;
  },

  angleToChannel(angle) {
    const normalized = (angle + 15) % 360;
    const channel = Math.floor(normalized / 30);
    return channel === 0 ? 12 : channel;
  },

  // ==================== FREQUENCY EVENTS ====================

  bindFrequencyEvents() {
    const freqSlider = document.getElementById('freqSlider');
    const freqInput = document.getElementById('freqInput');
    let isSliding = false; this.isEditingFreq = false;
    let rafId = null;

    // Slider drag
    freqSlider.addEventListener('mousedown', (e) => {
      isSliding = true; this.isEditingFreq = true;
      this.updateFreqFromSlider(e);
    });

    document.addEventListener('mousemove', (e) => {
      if (!isSliding) return;

      if (rafId) cancelAnimationFrame(rafId);

      rafId = requestAnimationFrame(() => {
        const rect = freqSlider.getBoundingClientRect();
        const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        this.currentFreq = Math.round((percent * (this.MAX_FREQ - this.MIN_FREQ) + this.MIN_FREQ) / 10) * 10;
        View.renderFrequency(this.currentFreq);
      });
    });

    document.addEventListener('mouseup', async () => {
      if (isSliding) {
        isSliding = false; this.isEditingFreq = false;
        if (rafId) cancelAnimationFrame(rafId);

        // Update channel if active
        const state = await Model.getState();
        const channel = state?.channels?.find(c => c.id === this.selectedChannel);
        if (channel?.enabled) {
          console.log("Sending freq:", this.currentFreq * 1000); await Model.updateChannel(this.selectedChannel, {
            enabled: true,
            frequency: this.currentFreq * 1000
          });
        }
      }
    });

    // Tick marks
    document.querySelectorAll('.freq-tick').forEach(tick => {
      tick.addEventListener('click', async () => {
        this.currentFreq = parseInt(tick.dataset.freq);
        View.renderFrequency(this.currentFreq);

        // Update channel if active
        const state = await Model.getState();
        const channel = state?.channels?.find(c => c.id === this.selectedChannel);
        if (channel?.enabled) {
          console.log("Sending freq:", this.currentFreq * 1000); await Model.updateChannel(this.selectedChannel, {
            enabled: true,
            frequency: this.currentFreq * 1000
          });
        }
      });
    });

    // Input field
    freqInput.addEventListener('change', async () => {
      const freq = parseInt(freqInput.value);
      if (!isNaN(freq) && freq >= this.MIN_FREQ && freq <= this.MAX_FREQ) {
        this.currentFreq = freq;
        View.renderFrequency(this.currentFreq);

        const state = await Model.getState();
        const channel = state?.channels?.find(c => c.id === this.selectedChannel);
        if (channel?.enabled) {
          console.log("Sending freq:", this.currentFreq * 1000); await Model.updateChannel(this.selectedChannel, {
            enabled: true,
            frequency: this.currentFreq * 1000
          });
        }
      }
    });

    freqInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        freqInput.blur();
      }
    });
  },

  updateFreqFromSlider(e) {
    const freqSlider = document.getElementById('freqSlider');
    const rect = freqSlider.getBoundingClientRect();
    const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    this.currentFreq = Math.round((percent * (this.MAX_FREQ - this.MIN_FREQ) + this.MIN_FREQ) / 10) * 10;
    View.renderFrequency(this.currentFreq);
  },

  // ==================== SOURCE EVENTS ====================

  bindSourceEvents() {
    const sourceToggle = document.getElementById('sourceToggle');

    sourceToggle.addEventListener('click', async () => {
      const state = await Model.getState();
      const newSource = state?.source === 'BRAM' ? 'ADC' : 'BRAM';
      await Model.setSource(newSource);
    });
  },

  // ==================== KEYBOARD EVENTS ====================

  bindKeyboardEvents() {
    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT') return;

      switch(e.key) {
        case 'ArrowRight':
        case 'ArrowDown':
          e.preventDefault();
          this.selectChannel(this.selectedChannel === 12 ? 1 : this.selectedChannel + 1);
          break;

        case 'ArrowLeft':
        case 'ArrowUp':
          e.preventDefault();
          this.selectChannel(this.selectedChannel === 1 ? 12 : this.selectedChannel - 1);
          break;

        case 'Enter':
        case ' ':
          e.preventDefault();
          this.toggleSelectedChannel();
          break;

        case 'a':
        case 'A':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            Model.arm();
          }
          break;

        case 'b':
        case 'B':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            this.handleBroadcastShortcut();
          }
          break;

        case 'e':
        case 'E':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            this.handleEmergencyShortcut();
          }
          break;

        case 'Escape':
          View.hideModal();
          break;
      }
    });
  },

  async handleBroadcastShortcut() {
    const state = await Model.getState();
    if (state.can_stop) {
      await Model.stopBroadcast();
    } else {
      await Model.startBroadcast();
    }
  },

  async handleEmergencyShortcut() {
    const state = await Model.getState();
    if (state.is_emergency) {
      await Model.stopEmergency();
    } else {
      await Model.startEmergency();
    }
  },

  // ==================== MODAL EVENTS ====================

  bindModalEvents() {
    const confirmModal = document.getElementById('confirmModal');
    const modalCancel = document.getElementById('modalCancel');
    const modalConfirm = document.getElementById('modalConfirm');

    modalCancel.addEventListener('click', () => View.hideModal());

    modalConfirm.addEventListener('click', async () => {
      View.hideModal();
      await Model.startBroadcast();
    });

    confirmModal.addEventListener('click', (e) => {
      if (e.target === confirmModal) View.hideModal();
    });
  }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  Controller.init();
});

// Export
window.Controller = Controller;

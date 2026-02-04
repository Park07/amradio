// view.js
// Pure DOM rendering - renders state from Rust backend
// NO BUSINESS LOGIC - just display

const View = {
  // Cache DOM elements
  elements: {},

  init() {
    // Cache all DOM elements
    this.elements = {
      // Connection
      app: document.getElementById('app'),
      ipInput: document.getElementById('ipInput'),
      portInput: document.getElementById('portInput'),
      connectBtn: document.getElementById('connectBtn'),
      statusBadge: document.getElementById('statusBadge'),
      statusText: document.getElementById('statusText'),
      watchdogStatus: document.getElementById('watchdogStatus'),
      watchdogText: document.getElementById('watchdogText'),

      // Dial
      dialKnob: document.getElementById('dialKnob'),
      channelDisplay: document.getElementById('channelDisplay'),
      freqMiniDisplay: document.getElementById('freqMiniDisplay'),

      // Broadcast
      broadcastCard: document.getElementById('broadcastCard'),
      broadcastBtn: document.getElementById('broadcastBtn'),
      armBtn: document.getElementById('armBtn'),
      emergencyBtn: document.getElementById('emergencyBtn'),
      durationDisplay: document.getElementById('durationDisplay'),
      infoChannelCount: document.getElementById('infoChannelCount'),
      broadcastStateDisplay: document.getElementById('broadcastStateDisplay'),

      // Channel config
      configChannelTitle: document.getElementById('configChannelTitle'),
      channelToggle: document.getElementById('channelToggle'),
      enableBadge: document.getElementById('enableBadge'),
      freqDisplay: document.getElementById('freqDisplay'),
      freqSlider: document.getElementById('freqSlider'),
      freqFill: document.getElementById('freqFill'),
      freqHandle: document.getElementById('freqHandle'),
      freqInput: document.getElementById('freqInput'),

      // Source
      sourceToggle: document.getElementById('sourceToggle'),
      sourceLabel: document.getElementById('sourceLabel'),

      // Counts
      activeCount: document.getElementById('activeCount'),
      summaryGrid: document.getElementById('summaryGrid'),

      // Log
      logContainer: document.getElementById('logContainer'),

      // Modal
      confirmModal: document.getElementById('confirmModal'),
      confirmChannelCount: document.getElementById('confirmChannelCount'),
    };

    // Subscribe to state changes
    EventBus.subscribe(Events.STATE_CHANGED, (state) => this.renderState(state));
    EventBus.subscribe(Events.UI_LOG, (data) => this.addLog(data.message, data.type));
    EventBus.subscribe(Events.UI_CHANNEL_SELECTED, (ch) => this.renderSelectedChannel(ch));

    console.log('View initialized');
  },

  // ==================== MAIN RENDER ====================

  renderState(state) {
    if (!state) return;

    this.renderConnection(state);
    this.renderBroadcast(state);
    this.renderWatchdog(state);
    this.renderChannels(state);
    this.renderSource(state);
  },

  // ==================== CONNECTION ====================

  renderConnection(state) {
    const { connection } = state;
    const isConnected = connection === 'CONNECTED';
    const isConnecting = connection === 'CONNECTING' || connection === 'RECONNECTING';

    // Status badge
    this.elements.statusBadge.className = `status-badge ${isConnected ? 'connected' : 'disconnected'}`;
    this.elements.statusText.textContent = connection;

    // Connect button
    if (isConnecting) {
      this.elements.connectBtn.textContent = 'CONNECTING...';
      this.elements.connectBtn.disabled = true;
    } else if (isConnected) {
      this.elements.connectBtn.textContent = 'DISCONNECT';
      this.elements.connectBtn.disabled = false;
    } else {
      this.elements.connectBtn.textContent = 'CONNECT';
      this.elements.connectBtn.disabled = false;
    }

    // App class
    this.elements.app.classList.toggle('disconnected', !isConnected);
  },

  // ==================== BROADCAST ====================

  renderBroadcast(state) {
    const { broadcast, can_arm, can_broadcast, can_stop, is_emergency } = state;

    // Update state display
    if (this.elements.broadcastStateDisplay) {
      this.elements.broadcastStateDisplay.textContent = broadcast;
    }

    // Broadcast card styling
    const isBroadcasting = broadcast === 'BROADCASTING' || broadcast === 'EMERGENCY';
    this.elements.broadcastCard.classList.toggle('broadcasting', isBroadcasting);
    this.elements.app.classList.toggle('broadcasting', isBroadcasting);

    // Arm button
    if (this.elements.armBtn) {
      this.elements.armBtn.disabled = !can_arm;
      this.elements.armBtn.textContent = broadcast === 'ARMING...' ? 'ARMING...' : 'ARM';
    }

    // Broadcast button
    if (can_stop) {
      this.elements.broadcastBtn.textContent = is_emergency ? 'STOP EMERGENCY' : 'STOP BROADCAST';
      this.elements.broadcastBtn.className = 'broadcast-btn stop';
    } else if (state.connection === "CONNECTED") {
      this.elements.broadcastBtn.textContent = 'START BROADCAST';
      this.elements.broadcastBtn.className = 'broadcast-btn start';
    } else {
      this.elements.broadcastBtn.textContent = broadcast === 'STARTING...' ? 'STARTING...' : 'START BROADCAST';
      this.elements.broadcastBtn.className = 'broadcast-btn start';
      this.elements.broadcastBtn.disabled = !can_broadcast;
    }

    // Active channel count
    const activeCount = state.channels ? state.channels.filter(c => c.enabled).length : 0;
    this.elements.infoChannelCount.textContent = activeCount;
  },

  // ==================== WATCHDOG ====================

  renderWatchdog(state) {
    const { watchdog } = state;

    this.elements.watchdogStatus.className = 'watchdog';
    if (watchdog === 'TRIGGERED') {
      this.elements.watchdogStatus.classList.add('triggered');
      this.elements.watchdogText.textContent = 'WATCHDOG TRIGGERED!';
    } else if (watchdog === 'WARNING') {
      this.elements.watchdogStatus.classList.add('warning');
      this.elements.watchdogText.textContent = 'WATCHDOG WARNING';
    } else {
      this.elements.watchdogText.textContent = 'WATCHDOG OK';
    }
  },

  // ==================== CHANNELS ====================

  renderChannels(state) {
    if (!state.channels) return;

    const activeCount = state.channels.filter(c => c.enabled).length;
    this.elements.activeCount.textContent = activeCount;

    // Update channel markers
    document.querySelectorAll('.channel-marker').forEach(marker => {
      const ch = parseInt(marker.dataset.channel);
      const channel = state.channels.find(c => c.id === ch);
      marker.classList.toggle('active', channel?.enabled || false);
    });

    // Update summary grid
    document.querySelectorAll('.summary-item').forEach(item => {
      const ch = parseInt(item.dataset.channel);
      const channel = state.channels.find(c => c.id === ch);
      const freqSpan = item.querySelector('.freq');

      if (channel?.enabled) {
        item.classList.add('active');
        freqSpan.textContent = Math.round(channel.frequency / 1000);
      } else {
        item.classList.remove('active');
        freqSpan.textContent = '--';
      }
    });
  },

  renderSelectedChannel(channelId) {
    // Highlight selected in markers
    document.querySelectorAll('.channel-marker').forEach(m => {
      m.classList.toggle('selected', parseInt(m.dataset.channel) === channelId);
    });

    // Highlight selected in grid
    document.querySelectorAll('.summary-item').forEach(item => {
      item.classList.toggle('selected', parseInt(item.dataset.channel) === channelId);
    });

    // Update config panel title
    this.elements.configChannelTitle.textContent = `Channel ${channelId}`;
    this.elements.channelDisplay.textContent = channelId;
  },

  renderChannelConfig(channel, currentFreq, skipFreq = false) {
    // Toggle state
    const isEnabled = channel?.enabled || false;
    this.elements.channelToggle.classList.toggle('active', isEnabled);
    this.elements.enableBadge.textContent = isEnabled ? 'Enabled' : 'Disabled';
    this.elements.enableBadge.className = `enable-badge ${isEnabled ? 'on' : 'off'}`;

    // Frequency
    const freq = channel?.frequency ? Math.round(channel.frequency / 1000) : currentFreq;
    // this.renderFrequency(freq); // disabled - slider controls freq

    // Mini display
    this.elements.freqMiniDisplay.textContent = isEnabled ? `${freq} kHz` : '-- kHz';
  },

  renderFrequency(freqKHz) {
    const minFreq = 500;
    const maxFreq = 1700;
    const percent = ((freqKHz - minFreq) / (maxFreq - minFreq)) * 100;

    this.elements.freqDisplay.textContent = freqKHz;
    this.elements.freqFill.style.width = `${percent}%`;
    this.elements.freqHandle.style.left = `${percent}%`;
    this.elements.freqInput.value = freqKHz;

    // Update tick marks
    document.querySelectorAll('.freq-tick').forEach(tick => {
      tick.classList.toggle('active', parseInt(tick.dataset.freq) === freqKHz);
    });
  },

  // ==================== SOURCE ====================

  renderSource(state) {
    const isBram = state.source === 'BRAM';
    this.elements.sourceToggle.classList.toggle('active', isBram);
    this.elements.sourceLabel.textContent = isBram ? 'BRAM' : 'ADC';
    this.elements.sourceLabel.style.color = isBram ? 'var(--accent-green)' : 'var(--accent-amber)';
  },

  // ==================== DIAL ====================

  renderDialRotation(angle) {
    this.elements.dialKnob.style.transform = `rotate(${angle}deg)`;
  },

  setDialDragging(isDragging) {
    this.elements.dialKnob.classList.toggle('dragging', isDragging);
  },

  pulseDialEnabled() {
    this.elements.dialKnob.classList.add('enabled-pulse');
    setTimeout(() => this.elements.dialKnob.classList.remove('enabled-pulse'), 400);
  },

  // ==================== MODAL ====================

  showModal(activeCount) {
    this.elements.confirmChannelCount.textContent = activeCount;
    this.elements.confirmModal.classList.add('show');
  },

  hideModal() {
    this.elements.confirmModal.classList.remove('show');
  },

  // ==================== LOG ====================

  addLog(message, type = '') {
    const time = new Date().toLocaleTimeString('en-US', {
      hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
    });

    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
      <span class="log-time">${time}</span>
      <span class="log-msg ${type}">${message}</span>
    `;

    this.elements.logContainer.insertBefore(entry, this.elements.logContainer.firstChild);

    // Keep max 100 entries
    while (this.elements.logContainer.children.length > 100) {
      this.elements.logContainer.removeChild(this.elements.logContainer.lastChild);
    }
  },

  // ==================== BROADCAST TIMER ====================

  updateBroadcastTimer(seconds) {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
    const secs = (seconds % 60).toString().padStart(2, '0');
    this.elements.durationDisplay.textContent = `${mins}:${secs}`;
  },

  resetBroadcastTimer() {
    this.elements.durationDisplay.textContent = '00:00';
  }
};

// Export
window.View = View;

# UGL AM Radio Control - Desktop GUI

Native desktop application for AM radio broadcast control. 

**Single click to launch** - Tauri auto-starts Python backend.

## Architecture

```
┌────────────────────────────────────────┐
│     Tauri App (what you see)           │
│  ┌──────────────────────────────────┐  │
│  │   Your HTML/CSS/JS UI            │  │
│  │   (dial, buttons, animations)    │  │
│  └──────────────┬───────────────────┘  │
│                 │ HTTP localhost:8000   │
│  ┌──────────────▼───────────────────┐  │
│  │   Python Backend (auto-started)  │  │
│  │   model.py → FPGA                │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

## Prerequisites

### 1. Install Rust
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### 2. Install Node.js
Download from https://nodejs.org/ (LTS version)

### 3. Install Python dependencies
```bash
pip install fastapi uvicorn
```

## Setup

### 1. Unzip and enter directory
```bash
unzip ugl-radio-gui.zip
cd ugl-radio-gui
```

### 2. Copy your Python files here
```bash
# From your existing project
cp ~/amradio/ugl_am_radio/model.py .
cp ~/amradio/ugl_am_radio/config.py .
cp ~/amradio/ugl_am_radio/event_bus.py .
```

### 3. Install Tauri CLI
```bash
npm install
```

### 4. Verify structure
```
ugl-radio-gui/
├── src/
│   └── index.html      # UI (don't touch)
├── src-tauri/
│   ├── src/main.rs     # Tauri app (auto-starts Python)
│   ├── Cargo.toml
│   └── tauri.conf.json
├── api.py              # FastAPI wrapper
├── model.py            # YOUR FILE (copy here)
├── config.py           # YOUR FILE (copy here)
├── event_bus.py        # YOUR FILE (copy here)
└── package.json
```

## Running

### Development Mode
```bash
npm run dev
```

This will:
1. Compile Rust (first time takes ~2 min)
2. Start Python backend automatically
3. Open the native window

### Production Build
```bash
npm run build
```

Creates installer in `src-tauri/target/release/bundle/`:
- macOS: `.dmg` file
- Windows: `.msi` file
- Linux: `.AppImage` file

## Usage

1. **Launch app** - Python starts automatically
2. **Enter IP/Port** - Your FPGA address
3. **Click Connect** - Establishes connection
4. **Enable channels** - Use dial or quick buttons
5. **Start Broadcast** - Confirm and go live

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `←` `→` | Rotate dial |
| `↑` `↓` | Rotate dial |
| `Space` / `Enter` | Toggle channel |
| `B` | Toggle broadcast |
| `Escape` | Close modal |

## Troubleshooting

### "Backend not responding"
- Check Python is installed: `python --version`
- Check uvicorn is installed: `pip install uvicorn`
- Check port 8000 is free: `lsof -i :8000`

### Rust compilation errors
```bash
rustup update
```

### Window doesn't open
Check the terminal for errors. Common issues:
- Missing Python files (model.py, config.py, event_bus.py)
- Port 8000 already in use

### Manual backend start (debugging)
```bash
# Terminal 1
uvicorn api:app --port 8000 --reload

# Terminal 2
npm run dev
```

## File Descriptions

| File | Purpose |
|------|---------|
| `src/index.html` | Complete UI - dial, buttons, animations |
| `src-tauri/src/main.rs` | Tauri app - spawns Python, manages window |
| `api.py` | REST API - wraps your model.py |
| `model.py` | Your existing FPGA communication |
| `config.py` | Your existing configuration |
| `event_bus.py` | Your existing event system |

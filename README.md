# Unitree Go2 for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/diRk262/ha-unitree-go2)](https://github.com/diRk262/ha-unitree-go2/releases)

Home Assistant integration for the **Unitree Go2** robot dog. Connects via WebRTC (local network) and exposes sensors, controls and camera as native HA entities.

## Features

- **Automatic setup** — Log in with your Unitree account, select your robot, done
- **Auto-discovery** — Finds your Go2 on the local network via multicast
- **18 sensors** — Battery, temperature, position, speed, IMU, LiDAR status, LED color
- **1 binary sensor** — Online status
- **2 switches** — Obstacle avoidance, LiDAR on/off
- **2 sliders** — Volume (0–10), head light brightness (0–10)
- **Camera** — Live stream from the Go2's front camera
- **LiDAR Map** — Real-time 2D top-down point cloud visualization
- **Auto-reconnect** — Automatically reconnects when the robot restarts
- **Localized** — English and German translations

## Supported Models

| Model | Status |
| --- | --- |
| Go2 Pro | Tested |
| Go2 EDU | Should work (untested) |
| Go2 Air | Limited (no LiDAR sensors) |

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right → **Custom repositories**
3. Add `https://github.com/diRk262/ha-unitree-go2` as **Integration**
4. Search for "Unitree Go2" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/unitree_go2` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Unitree Go2**
3. Enter your Unitree account email and password
4. Select your robot from the list
5. The integration will try to find your robot automatically — if not found, enter the IP manually

Your credentials are only used once during setup to fetch the device encryption key. They are **not stored** and **not transmitted** anywhere except to the official Unitree cloud API.

## Entities

### Sensors

| Sensor | Unit | Description |
| --- | --- | --- |
| Battery | % | Battery state of charge |
| Current | A | Battery current |
| Charge Cycles | | Battery charge cycles |
| Battery Temp 1/2 | °C | Battery cell temperatures |
| Body Temp | °C | Body temperature |
| Motor Temp Max | °C | Hottest motor temperature |
| Bus Voltage | V | Main bus voltage |
| Position X/Y/Z | m | Odometry position |
| Body Height | m | Current body height |
| Velocity | m/s | Forward velocity |
| Mode | | Current operating mode (21 mapped modes) |
| LiDAR Dirt Level | % | LiDAR lens dirt level |
| LiDAR Error | | LiDAR error state |
| IMU Roll/Pitch | ° | Body orientation |
| LED Color | | Current LED color |

### Switches

| Switch | Description |
| --- | --- |
| Obstacle Avoidance | Toggle obstacle avoidance on/off |
| LiDAR | Toggle LiDAR on/off |

### Sliders (Number)

| Slider | Range | Description |
| --- | --- | --- |
| Volume | 0–10 | Speaker volume |
| Head Light | 0–10 | Head lamp brightness |

### Other

| Entity | Type | Description |
| --- | --- | --- |
| Online | Binary Sensor | Connection status |
| Camera | Camera | Live front camera stream |
| LiDAR Map | Camera | Real-time 2D top-down point cloud |

## Requirements

- Unitree Go2 (Pro/EDU/Air) on the same local network as Home Assistant
- Unitree account (used for initial key retrieval only)
- Home Assistant 2024.1.0 or newer

## Troubleshooting

**Robot not found during setup**
- Make sure the Go2 is powered on and connected to your WiFi (not in AP mode)
- Close the Unitree app — only one WebRTC client can connect at a time
- Enter the IP manually if auto-discovery fails

**Connection drops**
- The Go2 only supports one WebRTC connection at a time
- Close the Unitree mobile app before using this integration
- The integration will automatically reconnect when the connection is restored

**Camera not showing**
- The camera requires the `av` (PyAV) Python package
- Some HA installations may not have it pre-installed

## Privacy & Security

- Credentials are used **once** during setup, then discarded
- All communication happens **locally** via WebRTC — no cloud relay
- No telemetry, no tracking, no external calls after setup

## Credits

This integration bundles [unitree_webrtc_connect](https://github.com/tfoldi/unitree_webrtc_connect) by Konstantin Severov (MIT License).

## License

MIT — see [LICENSE](LICENSE)

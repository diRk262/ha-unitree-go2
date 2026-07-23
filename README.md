# Unitree Go2 for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/diRk262/ha-unitree-go2)](https://github.com/diRk262/ha-unitree-go2/releases)

Home Assistant integration for the **Unitree Go2** robot dog. Connects via WebRTC (local network) and exposes sensors, controls, camera and full movement control as native HA entities.

Tested on **Go2 Pro with firmware 1.1.15**.

## Features

- **Automatic setup** — Log in with your Unitree account, select your robot, done
- **Auto-discovery** — Finds your Go2 on the local network via multicast
- **Full remote control** — All physical remote controller commands available 1:1
- **Two-tier safety system** — Commands switch (stationary) + Movement switch (spatial), both default OFF
- **Emergency Stop** — Immediately stops all animations and movement
- **Directional movement** — 6 direction buttons with configurable speed and duration
- **Command dropdown** — Select and execute commands, organized like the physical remote
- **Move service** — Obstacle avoidance movement with x/y/yaw speed control
- **Voice control** — Custom sentences for HA Assist (DE/EN): tricks, directions, start/stop, enable/disable
- **SLAM Mapping** — Start/stop mapping, live map visualization in the LiDAR camera entity
- **SLAM Navigation** — Start/stop navigation to saved map positions
- **Smart command chaining** — Auto stand-up after tricks, auto normal-mode after stand lock
- **17+ sensors** — Battery, temperature, position, speed, IMU, LiDAR status, SLAM position
- **Camera** — Live stream from the Go2's front camera
- **LiDAR Map** — Real-time 2D top-down point cloud / SLAM map visualization
- **Auto-reconnect** — Automatically reconnects when the robot restarts
- **Localized** — English and German translations

## Supported Models

| Model | Status |
| --- | --- |
| Go2 Pro | Tested (firmware 1.1.15) |
| Go2 EDU | Should work (untested) |
| Go2 Air | Should work (untested) |

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
6. Choose a **robot name** for voice control (e.g. "Robo", "Rex", "Buddy") — default is "Go2"

Your credentials are only used once during setup to fetch the device encryption key. They are **not stored** and **not transmitted** anywhere except to the official Unitree cloud API.

The robot name can be changed later in **Settings → Devices & Services → Unitree Go2 → Configure**.

## Entities

### Controls (main area)

| Entity | Type | Description |
| --- | --- | --- |
| Commands | Switch | Enable stationary commands (stand, sit, dance, etc.) |
| Movement | Switch | Enable spatial movement commands (auto-enables Commands) |
| Emergency Stop | Button | Immediately stop all movement and animations |
| Command | Select | Dropdown with all commands, organized by remote controller sections |
| Execute Command | Button | Execute the selected command |
| Move Forward | Button | Move forward (speed/duration from sliders) |
| Move Backward | Button | Move backward |
| Move Left | Button | Strafe left |
| Move Right | Button | Strafe right |
| Turn Left | Button | Rotate left |
| Turn Right | Button | Rotate right |

### Configuration

| Entity | Type | Range | Description |
| --- | --- | --- | --- |
| Volume | Slider | 0–10 | Speaker volume |
| Head Light | Slider | 0–10 | Head lamp brightness |
| Move Speed | Slider | 0.1–1.0 | Speed for direction buttons |
| Move Duration | Slider | 0.1–3.0s | Duration for direction button impulse |
| Obstacle Avoidance | Switch | | Toggle obstacle avoidance |
| LiDAR | Switch | | Toggle LiDAR on/off |

### Diagnostics

| Entity | Type | Description |
| --- | --- | --- |
| Battery | Sensor | Battery state of charge (%) |
| Current | Sensor | Battery current (A) |
| Charge Cycles | Sensor | Battery charge cycles |
| Battery Temp 1/2 | Sensor | Battery cell temperatures (°C) |
| Body Temp | Sensor | Body temperature (°C) |
| Motor Temp Max | Sensor | Hottest motor temperature (°C) |
| Bus Voltage | Sensor | Main bus voltage (V) |
| Position X/Y/Z | Sensor | Odometry position (m) |
| Body Height | Sensor | Current body height (m) |
| Velocity | Sensor | Forward velocity (m/s) |
| Mode | Sensor | Current operating mode (21 mapped modes) |
| LiDAR Dirt Level | Sensor | LiDAR lens dirt level (%) |
| LiDAR Error | Sensor | LiDAR error state |
| IMU Roll/Pitch | Sensor | Body orientation (°) |
| Online | Binary Sensor | Connection status |

### Camera

| Entity | Description |
| --- | --- |
| Camera | Live front camera stream |
| LiDAR Map | Real-time 2D top-down point cloud / SLAM map |

### SLAM Sensors

| Entity | Type | Description |
| --- | --- | --- |
| SLAM Status | Sensor | Current SLAM state (idle/mapping/localization) |
| SLAM Position X/Y | Sensor | Robot position from SLAM odometry (m) |
| SLAM Yaw | Sensor | Robot heading from SLAM odometry (°) |

## Available Commands

All commands from the physical remote controller are supported. Commands are executed via wireless controller simulation over the WebRTC data channel.

### Mode Switch

| Command | Remote Button | Safety |
| --- | --- | --- |
| Damping Mode (Emergency!) | L2+B | Movement |
| Stand Lock / Low Down | L2+A | Commands |
| Unlock / Default Gait | START | Movement |
| Running Mode | L2+START | Movement |
| Pose | SELECT | Commands |
| Normal Mode | L1+START | Movement |
| Classic | D-Pad+START | Movement |
| Free Walk | D-Pad+START | Movement |
| Free Avoid | Double Click A | Movement |
| Cross Step | Double Click B | Movement |
| Bound Gait | Double Click X | Movement |
| Jump Gait | Double Click Y | Movement |
| Hand Stand | Double Click R1 | Movement |
| Erect | Double Click R2 | Movement |
| Endurance | L1+SELECT | Commands |

### Customised Movements

| Command | Remote Button | Safety |
| --- | --- | --- |
| Stand Up From Fall | L2+X | Movement |
| Stretch | R2+A | Commands |
| Shake Hands | R2+B | Commands |
| Love | R2+Y | Commands |
| Greet | L1+A | Commands |
| Jump Forward | R1+A | Movement |
| Sit Down | R1+B | Commands |
| Pounce | R1+X | Movement |
| Dance 1 | L1+B | Movement |
| Dance 2 | L1+X | Movement |

### Extra (not on remote)

| Command | Method | Safety |
| --- | --- | --- |
| Balance Stand | Sport API | Commands |
| Stop Move | Sport API | Commands |
| Content | Sport API | Commands |

## Services

All commands are also available as HA services for use in automations:

- `unitree_go2.stand_lock`, `unitree_go2.sit`, `unitree_go2.greet`, etc.
- `unitree_go2.move` — Move with obstacle avoidance (x/y/yaw: -1.0 to 1.0)
- `unitree_go2.move_forward`, `move_backward`, `move_left`, `move_right`, `turn_left`, `turn_right` — Directional impulse movement
- `unitree_go2.mapping_start`, `mapping_stop` — Start/stop SLAM mapping
- `unitree_go2.navigation_start`, `navigation_stop` — Start/stop SLAM navigation

## Voice Control

Voice commands work with [HA Assist](https://www.home-assistant.io/voice_control/) in German and English. The integration automatically installs custom sentences when loaded.

### How it works

Commands use the **robot name** you chose during setup. If you named your robot "Rex", you say "Rex sitz". The name is optional in brackets — you can also just say "Roboter sitz" or "Hund sitz" as fallback.

| Trigger | Example (name = "Rex") |
| --- | --- |
| `{name} {command}` | "Rex sitz", "Rex tanz", "Rex steh auf" |
| `{name} mach {command}` | "Rex mach Platz", "Rex mach Handstand" |
| Fallback: `Roboter {command}` | "Roboter sitz" (always works, no name needed) |
| Fallback: `Hund {command}` | "Hund sitz" (always works, no name needed) |

### Available voice commands

| Category | German | English |
| --- | --- | --- |
| **Tricks** | sitz, steh auf, hallo, gib Pfote, strecken, herz, tanz, spring | sit, stand up, hello, shake hands, stretch, heart, dance, jump |
| **Directions** | vorwärts, rückwärts, links, rechts, dreh links, dreh rechts | forward, backward, left, right, turn left, turn right |
| **Stop** | Stop, Stopp, Halt, Notaus | stop, halt, emergency stop |
| **Safety** | Befehle an/aus, Bewegung an/aus | commands on/off, movement on/off |

### Smart command chaining

The integration automatically handles mode transitions between commands:

1. **After a trick** (sit, dance, handstand, etc.) — the robot needs to stand up first before executing the next command. The integration sends `stand_lock` (L2+A) automatically and waits 2 seconds.
2. **After standing up** (stand_lock) — the robot is in locked stand mode and can't move. The integration sends `normal mode` (L1+Start) automatically before the next movement or trick.

This means you can say "Rex sitz" → wait → "Rex vorwärts" and the robot will automatically: stand up → switch to normal mode → walk forward. No manual mode switching needed.

### Changing the robot name

Go to **Settings → Devices & Services → Unitree Go2 → Configure** to change the name. The voice sentences are regenerated automatically. Default name is "Go2".

## SLAM Mapping & Navigation

The Go2 Pro/EDU has a built-in SLAM system (Simultaneous Localization and Mapping) that can create floor plans of your home and navigate autonomously.

### Mapping

1. Call the service `unitree_go2.mapping_start` (or use an automation/button)
2. Walk the robot through the area you want to map — use the direction buttons, voice commands, or the Unitree app
3. Watch the map build up in real-time in the **LiDAR Map** camera entity
4. Call `unitree_go2.mapping_stop` when done — the map is saved on the robot

The LiDAR Map entity shows a 2D top-down view during mapping:
- **Gray dots** — walls and obstacles detected by the LiDAR
- **Green circle** — current robot position
- **Green line** — robot heading direction

The map accumulates over time as the robot moves. Performance is optimized with automatic downsampling (max 50,000 points).

### Navigation

After mapping, the robot can navigate autonomously:

1. Call `unitree_go2.navigation_start` to start autonomous navigation
2. Call `unitree_go2.navigation_stop` to stop

### SLAM Sensors

During mapping or navigation, additional sensors are available:

| Sensor | Description |
| --- | --- |
| SLAM Status | Current state: `idle`, `mapping`, or `localization` |
| SLAM X / SLAM Y | Robot position in the SLAM coordinate frame (meters) |
| SLAM Yaw | Robot heading angle (radians) |

## Safety System

The integration uses a two-tier safety system:

1. **Commands Switch (OFF by default)** — Must be enabled to execute stationary commands (stand, sit, dance poses, etc.)
2. **Movement Switch (OFF by default)** — Must be enabled for spatial movement commands. Automatically enables the Commands switch.
3. **Emergency Stop** — Sends a START button press to immediately stop all animations, cancels active move API commands, and turns off both switches.
4. **Auto-off** — Both switches automatically turn off after 5 minutes of inactivity.

Without any switch enabled, only read-only sensors, LED brightness, volume, and camera work.

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

**Commands not working**
- Make sure the Commands or Movement switch is enabled
- Check the HA logs for error messages
- Some commands require the robot to be standing first

**Camera not showing**
- The camera requires the `av` (PyAV) Python package
- Some HA installations may not have it pre-installed

**Voice commands not recognized**
- Make sure HA Assist is set up with a speech-to-text engine
- Check that the robot name matches what you're saying (Settings → Devices & Services → Configure)
- Try the fallback phrases: "Roboter sitz" or "Hund sitz" instead of using the custom name
- Voice commands require the Commands or Movement switch to be enabled (say "{name} Befehle an" first)

**SLAM map not showing**
- SLAM mapping requires a Go2 with LiDAR (all models have LiDAR, but only tested on Pro)
- Make sure mapping is started via `unitree_go2.mapping_start`
- The map appears in the **LiDAR Map** camera entity, not the regular camera
- Move the robot slowly for best mapping results

## Privacy & Security

- Credentials are used **once** during setup, then discarded
- All communication happens **locally** via WebRTC — no cloud relay
- No telemetry, no tracking, no external calls after setup

## Credits

This integration bundles [unitree_webrtc_connect](https://github.com/tfoldi/unitree_webrtc_connect) by Konstantin Severov (MIT License).

## License

MIT — see [LICENSE](LICENSE)

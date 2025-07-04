# ADB Helper

A powerful cross-platform ADB (Android Debug Bridge) helper tool that simplifies Android device management with an intuitive command-line interface.

## Features

### 📱 Device Management
- **Multi-device support** - Work with multiple devices simultaneously
- **Wireless ADB** - Connect devices over WiFi with pairing support
- **Device discovery** - Automatic mDNS/Bonjour device discovery
- **Connection history** - Remember and quickly reconnect to devices
- **Detailed device info** - View comprehensive device information

### 📦 App Management
- **List apps** - View installed applications with filtering
- **Launch apps** - Start applications directly or interactively
- **Clear app data** - Clear cache and data with confirmation prompts
- **Force stop** - Terminate running applications
- **App info** - Display detailed application information
- **APK backup** - Extract APK files from devices
- **Activity tracking** - Monitor current foreground app in real-time

### 📸 Screen Capture
- **Screenshots** - Capture device screen with automatic file naming
- **Screen recording** - Record device screen with customizable settings
- **Auto-open** - Automatically open captures after saving

### 📋 Log Management
- **Live logcat** - View real-time device logs with color coding
- **Multi-device logs** - View logs from multiple devices in one window
- **Filter support** - Filter logs by content or application
- **Save logs** - Export logs to files for analysis
- **Clear logs** - Wipe device log buffers

### 🛠️ Developer Tools
- **Shell access** - Run shell commands on single or multiple devices
- **Interactive mode** - Smart device selection when multiple devices connected
- **Batch operations** - Execute commands across all connected devices
- **Rich CLI** - Beautiful terminal output with colors and formatting

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/adbhelper.git
cd adbhelper

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Mac/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Quick Start

```bash
# Check system dependencies
adbh check

# List connected devices
adbh devices

# Enable ADB on a new device (interactive guide)
adbh enable-adb

# Connect a device wirelessly
adbh add-device pair         # First time pairing
adbh add-device wireless     # Connect to paired device

# Take a screenshot
adbh capture screenshot

# View device logs (with multi-device support)
adbh log view               # Select devices interactively
adbh log view -f MyApp      # Filter by app name

# Manage apps
adbh app list               # List all apps
adbh app launch com.example # Launch specific app
adbh app current -w         # Watch current app

# Run shell commands
adbh shell ls /sdcard       # Single device
adbh shell -a whoami        # All devices
```

## Advanced Usage

### Multi-Device Log Viewing

View logs from multiple devices simultaneously with color-coded output:

```bash
# Interactive device selection
adbh log view

# When multiple devices are selected, logs are color-coded
# Each device gets a unique color and prefix like:
# [Pixel_6] Log message here...
# [Galaxy_S21] Another log message...

# Save combined logs
adbh log view -s

# Filter across all devices
adbh log view -f "com.myapp"
```

### Wireless ADB Connection

```bash
# First time setup - pair with device
adbh add-device pair
# or with automatic discovery
adbh add-device pair --discover

# Connect to already paired device
adbh add-device wireless 192.168.1.100:5555

# Disconnect wireless device
adbh disconnect -d 192.168.1.100:5555
```

### App Management

```bash
# List all apps (including system apps)
adbh app list -s

# Filter apps by name
adbh app list -f chrome

# Get detailed app info
adbh app info com.android.chrome

# Clear app data (with confirmation)
adbh app clear com.example.app
adbh app clear -c com.example.app  # Cache only
adbh app clear -y com.example.app  # Skip confirmation

# Backup APKs
adbh app backup com.example.app
adbh app backup -a              # All apps
adbh app backup -o ~/Desktop    # Custom output directory
```

## Command Reference

Run `adbh helpv` for a complete command tree with examples.

### Main Commands
- `check` - Verify system dependencies
- `devices` - List connected devices
- `info` - Show device information
- `shell` - Execute shell commands
- `enable-adb` - Guide to enable ADB debugging
- `disconnect` - Disconnect wireless devices

### Command Groups
- `add-device` - Device connection commands (usb, wireless, pair, qrcode)
- `app` - Application management (list, launch, clear, stop, info, backup, current)
- `capture` - Screen capture (screenshot, screenrecord)
- `log` - Log management (view, dump, clear)

## Requirements

- Python 3.8+
- ADB (Android Debug Bridge) - installed automatically via Android SDK Platform Tools
- Operating System: macOS, Linux, Windows, or WSL

## Platform Support

| Feature | macOS | Linux | Windows | WSL |
|---------|-------|-------|---------|-----|
| Multi-device support | ✅ | ✅ | ✅ | ✅ |
| Screenshot/Recording | ✅ | ✅ | ✅ | ✅ |
| Wireless ADB | ✅ | ✅ | ✅ | ✅ |
| Multi-device logs | ✅ | ✅ | ✅ | ✅ |
| mDNS Discovery | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| App Management | ✅ | ✅ | ✅ | ✅ |

⚠️ mDNS discovery is sporadic and needs to be fixed

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI functionality
- Terminal formatting powered by [Rich](https://github.com/Textualize/rich)
- Inspired by the need for a more user-friendly ADB experience
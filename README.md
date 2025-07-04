# ADB Helper

A cross-platform ADB helper tool that simplifies Android device management.

## Features

- 📸 Easy screenshot capture
- 🎥 Screen recording
- 📋 Logcat management (view, save, clear)
- 🖥️ Scrcpy integration
- 🔧 Multi-device support
- 🔍 Automatic dependency checking

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
# Check dependencies
adbh check

# List connected devices
adbh devices

# Take a screenshot
adbh screenshot

# Start recording
adbh record start

# View logcat
adbh logcat

# Launch scrcpy
adbh scrcpy
```

## Requirements

- Python 3.8+
- ADB (Android Debug Bridge)
- scrcpy (optional, for screen mirroring)

## Platform Support

| Feature | Mac/Linux/WSL | Windows |
|---------|---------------|---------|
| Multi-device | ✅ | ✅ |
| Screenshot | ✅ | ✅ |
| Recording | ✅ | ✅ |
| Logcat | ✅ | ✅ |
| Scrcpy | ✅ | ✅ |

## License

MIT
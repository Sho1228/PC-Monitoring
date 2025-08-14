# PC Monitor with Discord Bot

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) <br>
Please note that this is for educational purposes for those who are studying about how different Python packages and discord bots work.

## Installation

1. Install Python 3.1 or higher
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a Discord bot:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the "Bot" section and create a bot
   - Copy the bot token
   - Go to the "OAuth2" section"
   - Select the needed permission and copy the URL shown
   -Copy and paste the URL on the server that you want to install the bot to
   - Click the link and authenticate the bot
4. Create a `.env` file in the project directory and add your bot token:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```
5. Invite the bot to your server with the following permissions:
   - Send Messages
   - Attach Files
   - Read Message History

## Usage

To run the bot, use:
```bash
python3 bot.py
```

Available commands (all use Discord slash commands):
- `/ss` - Takes a screenshot of the current screen
- `/mic` - Records 10 seconds of audio from the microphone
- `/media <play/next/prev>` - Controls media playback using system media keys
- `/volume <0-100>` - Sets system volume (0-100%)
- `/power <sleep/restart/shutdown>` - Controls system power state
- `/keylogger <start/stop>` - Starts or stops keylogging
- `/sysinfo` - Shows comprehensive system information (CPU, RAM, battery, location, etc.)
- `/ip` - Shows the system's IP address
- `/locate` - Gets precise location with GPS coordinates and timestamp
- `/uptime` - Shows system uptime
- `/processes <cpu/ram>` - Shows top 15 processes by CPU or RAM usage
- `/camera` - Takes a photo using the webcam
- `/all` - Runs all monitoring commands
- `/debug` - Tests all system functions
- `/help` - Shows a list of available commands and their descriptions

## Features

- **Screenshot capture** - High-quality screen captures
- **Audio recording** - 10-second microphone recordings
- **Media control** - System-wide media key simulation using Quartz framework
- **Volume control** - Precise system volume adjustment
- **Power control** - System shutdown, restart, and sleep with safety warnings
- **System monitoring** - Comprehensive system information (CPU, RAM, battery, display)
- **Location services** - Precise GPS location with coordinates and addresses
- **Process monitoring** - Top 15 processes by CPU or RAM usage with process grouping
- **Camera capture** - Webcam photos with automatic warmup
- **Network information** - IP addresses and geographic location
- **Keylogging** - Real-time keystroke monitoring (for educational purposes)
- **System uptime** - Detailed uptime information
- **Discord slash commands** - Modern command interface with auto-completion
- **Automatic file cleanup** - Temporary files cleaned after transmission
- **Comprehensive error handling** - Graceful failure handling with detailed messages
- **Permission management** - Automatic permission checks for camera/microphone/location
- **Multi-format support** - Screenshots, audio, photos, and text responses

## Permissions (IMPORTANT)

- The bot requires camera and microphone permissions to function fully.
- The first time you run the bot, macOS will prompt you to grant these permissions.
- If you deny access, you must manually enable them in **System Preferences > Security & Privacy > Privacy > Camera/Microphone**.
- The bot will notify you via Discord if permissions are missing.

### Location Services Setup (for `/locate` command)
- **GPS-based location** requires setting up a macOS Shortcut:
  1. Open **Shortcuts** app on macOS
  2. Create a new shortcut named **"Get Location Data"**
  3. Add **"Get Current Location"** action
  4. Grant location permissions when prompted
  5. Test the shortcut manually before using the bot command
- **Permissions**: Requires Location Services enabled for Shortcuts app
- **Privacy**: All location data is processed locally and transmitted only to Discord
- **Accuracy**: Uses precise GPS coordinates, not IP-based approximation

### Power Control Setup (for `/power` command)
- **⚠️ WARNING**: Shutdown and restart commands are **immediate** and **irreversible**
- **Administrative access**: May require password for shutdown/restart operations
- **Sleep command**: Generally works without additional permissions
- **Safety features**: Warning messages and confirmations for destructive actions
- **Remote access**: Be cautious - these actions will terminate the connection

## FYI

This bot is designed exclusively for macOS systems and is currently in an experimental phase. Please note the following important points:

- This is a development project and should be used responsibly
- The bot requires appropriate permissions to function properly
- Some features may not work as expected due to the experimental nature
- Use this tool only for legitimate purposes and with proper authorization
- The developer, I am not responsible for any misuse of this software
- Might change licence from GPL to MIT

### Warning: Unauthorized use of this bot, especially for malicious purposes, may violate laws and ToS.

### Please use this tool responsibly and ethically.

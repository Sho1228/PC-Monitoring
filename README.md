# PC Monitor Discord Bot

A comprehensive Discord bot for remotely monitoring and controlling a macOS computer through Discord slash commands.

## Features

### 📊 System Monitoring
- **`/sysinfo`**: Get comprehensive system details (CPU, RAM, battery, network, location, etc.)
- **`/ip`**: Display local and public IP addresses
- **`/uptime`**: Show how long the system has been running
- **`/processes`**: List top 15 processes by CPU or RAM usage
- **`/locate`**: Get precise GPS location using macOS Location Services

### 📸 Surveillance & Media Capture
- **`/ss`**: Take a screenshot of the entire screen
- **`/camera`**: Capture a photo from the webcam
- **`/mic`**: Record 10 seconds of audio from the microphone
- **`/keylogger`**: Start or stop a keylogger that sends keystrokes to Discord in real-time

### 🎛️ System Control
- **`/power`**: Shut down, restart, or sleep the computer
- **`/volume`**: Set the system volume (0-100%)
- **`/media`**: Control media playback (play/pause, next, previous) for apps like Spotify, Apple Music, and YouTube

### 🔍 File & Process Management
- **`/find`**: Search files by name with partial matching (includes hidden files)
- **`/find-process`**: Search processes by name or PID
- **`/kill`**: Terminate processes by PID or name with safety checks

### 🌐 Browser Monitoring
- **`/active-tabs`**: Show currently open browser tabs across all browsers
- **`/browser-history`**: Show recent browser history from databases (requires Full Disk Access)
- **`/website-monitor`**: Monitor active website changes in real-time

### 🚀 Remote Control & Automation
- **`/open`**: Open applications, websites, files, or system utilities with quick choices
- **`/open-custom`**: Open anything by typing freely (apps, URLs, files, search queries)
- **`/cmd`**: Execute shell commands silently in background (no visible terminal)
- **`/cmd-history`**: Show recent command execution history
- **`/cmd-help`**: Show help and examples for safe command usage

### 🖱️ GUI Automation
- **`/click`**: Click at screen coordinates with mouse buttons (supports long clicks)
  - Normal clicks: `/click 500 300`
  - Long clicks: `/click 500 300 left 1 2.5` (hold for 2.5 seconds)
  - Button types: left, right, middle
- **`/type`**: Type text with special key support
  - Basic typing: `/type Hello World!`
  - Special keys: `/type Username\nPassword\n` (uses Enter keys)
- **`/scroll`**: Scroll mouse wheel at coordinates or current position
  - Current position: `/scroll 5 up`
  - Specific coordinates: `/scroll 500 300 10 down`
- **`/shortcut`**: Execute keyboard shortcuts and hotkeys
  - Copy/Paste: `/shortcut command+c`, `/shortcut command+v`
  - System shortcuts: `/shortcut fn+f3` (Mission Control)
  - Complex combinations: `/shortcut ctrl+shift+esc`

### 🚫 Website Blocking & Filtering
- **`/block`**: Unified website blocking and filtering management
  - **Block**: `/block action:🚫 Block Website domain:facebook.com`
  - **Unblock**: `/block action:✅ Unblock Website domain:facebook.com`
  - **List**: `/block action:📋 List Blocked` - Show all blocked websites
  - **Clear**: `/block action:🗑️ Clear All confirm:yes` - Remove all blocks
  - **Features**: Domain format support (`facebook.com`, `www.facebook.com`, `https://facebook.com`), automatic protocol/path stripping, DNS resolution verification, critical domain protection, hosts file modification, automatic DNS cache flushing, backup system

### 🛠️ Utilities
- **`/all`**: Run all major monitoring commands at once
- **`/debug`**: Test core functionalities and check for permission issues
- **`/help`**: Display comprehensive help with examples and usage instructions

## Prerequisites

- **macOS 12 (Monterey) or newer** (required for Shortcuts app integration)
- **Python 3.8 or newer**
- **Discord account** with server permissions to add bots

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Sho1228/PC-Monitoring.git
cd PC-Monitoring
```

### 2. Install Dependencies

It's highly recommended to use a Python virtual environment.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application", give it a name (e.g., "PC Monitor Bot"), and click "Create"
3. Go to the "Bot" tab and click "Add Bot"
4. Under the bot's username, click "Reset Token" to view and copy your bot's token. **Treat this token like a password!**
5. Enable the **Message Content Intent** and **Server Members Intent** under "Privileged Gateway Intents"

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
echo "DISCORD_TOKEN=your_discord_bot_token_here" > .env
```

Replace `your_discord_bot_token_here` with your actual Discord bot token.

**Optional Environment Variables:**
```bash
# For process termination authorization (/kill command)
ALLOWED_USER_IDS=123456789,987654321

# For website blocking authorization (/block commands)  
BLOCK_AUTHORIZED_USERS=123456789,987654321

# For custom search path (/find command)
FIND_DEFAULT_PATH=/Users/yourusername
```

- `ALLOWED_USER_IDS`: Comma-separated Discord user IDs authorized to use the `/kill` command
- `BLOCK_AUTHORIZED_USERS`: Comma-separated Discord user IDs authorized to use website blocking commands (if empty, all users can use blocking)
- `FIND_DEFAULT_PATH`: Default path for file searches (defaults to home directory)

### 5. Set Up Location Shortcut (For `/locate` command)

The `/locate` command relies on a macOS Shortcut to access precise GPS data.

1. Open the **Shortcuts** app on your Mac
2. Click the **`+`** button to create a new shortcut
3. Search for **"Get Current Location"** action and drag it into the main window
4. Rename the shortcut to **exactly** `Get Location Data`
5. **Important**: Run the shortcut once manually to trigger Location Services permission prompt and allow it

### 6. Grant System Permissions

The bot requires several macOS permissions. Go to **System Settings > Privacy & Security** and ensure your terminal application has these permissions:

- **Screen Recording**: For `/ss` (screenshot functionality)
- **Camera**: For `/camera` (webcam photo capture)
- **Microphone**: For `/mic` (audio recording)
- **Accessibility**: For `/keylogger`, media controls, browser automation, and GUI automation (`/click`, `/type`, `/scroll`, `/shortcut`)
- **Full Disk Access**: For browser history database access (`/browser-history`)
- **Location Services**: Ensure the **Shortcuts** app is enabled for `/locate`
- **Admin/Sudo Privileges**: For website blocking commands (`/block`, `/unblock`, `/block-list`, `/block-clear`) to modify `/etc/hosts` file

**Important for Website Blocking**: The terminal or Python application needs admin privileges to modify the system hosts file. You may need to run the bot with `sudo python3 bot.py` or grant admin access to your terminal application.

### 7. Invite Bot to Your Server

1. In the Discord Developer Portal, go to your application
2. Select "OAuth2" tab, then "URL Generator"
3. Select `bot` and `applications.commands` scopes
4. Under "Bot Permissions", select:
   - `Send Messages`
   - `Attach Files`
   - `Read Message History`
   - `Use Slash Commands`
5. Copy the generated URL, paste it into your browser, and invite the bot to your server

### 8. Create Required Discord Channel

Create a text channel named **`pc-monitor`** in your Discord server. All bot commands are restricted to this channel for security.

## Running the Bot

1. Make sure you have a `#pc-monitor` channel in your Discord server
2. Run the bot:

```bash
python3 bot.py
```

The bot will announce startup in the `#pc-monitor` channel and be ready for slash commands.

## Security Considerations

⚠️ **Important Security Notes:**

- This bot provides **full remote access** to your computer
- All commands are **restricted to the `#pc-monitor` channel only**
- The bot captures screenshots, audio, keystrokes, and camera images
- Browser history and active tabs can be monitored
- Commands can execute with full system privileges
- **Website blocking modifies system hosts file** and affects all applications
- DNS cache flushing requires admin privileges and affects system networking
- **Never share your Discord bot token**
- Only use this bot on servers you trust completely
- Consider the implications of keylogger, surveillance, and network control features
- Website blocks persist until explicitly removed and affect all users on the system

## Troubleshooting

### Permission Issues
- Run `/debug` to check all system permissions and functionality
- If permissions are denied, manually grant them in System Settings
- Restart the bot after granting new permissions

### Command Failures
- Check `/debug` output for specific error messages
- Ensure the `#pc-monitor` channel exists and bot has access
- Verify all dependencies are installed: `pip install -r requirements.txt`

### Location Services
- Ensure the "Get Location Data" shortcut exists and has been run manually once
- Check that Shortcuts app has Location Services permission
- Location may not work in virtual environments or certain network configurations

## Command Examples

```
# System Monitoring
/sysinfo
/processes cpu
/ip

# GUI Automation  
/click 500 300
/click 100 200 right 2
/click 300 400 left 1 3.0
/type Hello World!
/type Username\nPassword\n
/scroll 10 up
/scroll 500 300 5 down
/shortcut command+c
/shortcut fn+f3
/shortcut ctrl+shift+esc

# File Operations
/find config
/open calculator
/cmd ls -la

# Browser Monitoring
/active-tabs
/website-monitor start

# Website Blocking
/block action:🚫 Block Website domain:facebook.com
/block action:🚫 Block Website domain:youtube.com
/block action:✅ Unblock Website domain:facebook.com
/block action:📋 List Blocked
/block action:🗑️ Clear All confirm:yes

# System Control
/volume 50
/power sleep
```

## License

This project is for personal use and educational purposes. Use responsibly and in compliance with local laws and regulations.
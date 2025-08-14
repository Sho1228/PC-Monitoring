# PC Monitor Discord Bot

A powerful Discord bot for remotely monitoring and controlling a macOS computer.

## Features

- **System Monitoring**:
    - `/sysinfo`: Get comprehensive system details (CPU, RAM, battery, network, location, etc.).
    - `/ip`: Display local and public IP addresses.
    - `/uptime`: Show how long the system has been running.
    - `/processes`: List top processes by CPU or RAM usage.
    - `/locate`: Get precise GPS location using macOS Location Services.
- **Surveillance**:
    - `/ss`: Take a screenshot of the entire screen.
    - `/camera`: Capture a photo from the webcam.
    - `/mic`: Record 10 seconds of audio from the microphone.
    - `/keylogger`: Start or stop a keylogger that sends keystrokes to Discord.
- **System Control**:
    - `/power`: Shut down, restart, or sleep the computer.
    - `/volume`: Set the system volume.
    - `/media`: Control media playback (play/pause, next, previous) for apps like Spotify, Apple Music, and YouTube.
- **Utilities**:
    - `/all`: Run all major monitoring commands at once.
    - `/debug`: Test core functionalities and check for permission issues.
    - `/help`: Display a list of all available commands.

## Prerequisites

- macOS 12 (Monterey) or newer (required for the Shortcuts app integration).
- Python 3.8 or newer.
- A Discord account and a server where you have permissions to add bots.

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

1.  Go to the Discord Developer Portal.
2.  Click "New Application". Give it a name (e.g., "My PC Monitor") and click "Create".
3.  Go to the "Bot" tab and click "Add Bot".
4.  Under the bot's username, click "Reset Token" to view and copy your bot's token. **Treat this token like a password!**
5.  Enable the **Message Content Intent** and **Server Members Intent** under "Privileged Gateway Intents".

### 4. Configure Environment Variables

Create a `.env` file in the project root by copying the template:

```bash
cp .env.template .env
```

Open the `.env` file with a text editor and paste your Discord bot token:

```
DISCORD_TOKEN=your_token_here
```

### 5. Set Up the Location Shortcut (Crucial for `/locate`)

The `/locate` command relies on a macOS Shortcut to access precise GPS data.

1.  Open the **Shortcuts** app on your Mac.
2.  Click the **`+`** button to create a new shortcut.
3.  In the search bar on the right, find the **"Get Current Location"** action and drag it into the main window.
4.  Click on the shortcut's title at the top and rename it to **exactly** `Get Location Data`.
5.  The shortcut saves automatically.
6.  **Important**: Run the shortcut once manually from within the Shortcuts app. This will trigger the system permission prompt for Location Services. **You must allow it.**

### 6. Grant System Permissions

The bot requires several permissions to function correctly. The first time you run a command that needs a new permission, macOS will prompt you.

Go to **System Settings > Privacy & Security** and ensure your terminal application (e.g., `Terminal`, `iTerm2`, or your code editor's integrated terminal) has the following permissions:

-   **Screen Recording**: For `/ss`.
-   **Camera**: For `/camera`.
-   **Microphone**: For `/mic`.
-   **Accessibility**: For the `/keylogger` and media controls.
-   **Location Services**: Make sure the **Shortcuts** app is enabled here.

### 7. Invite the Bot to Your Server

1.  In the Discord Developer Portal, go to your application.
2.  Select the "OAuth2" tab, then "URL Generator".
3.  Select the `bot` and `applications.commands` scopes.
4.  Under "Bot Permissions", select `Send Messages`, `Attach Files`, and `Read Message History`.
5.  Copy the generated URL, paste it into your browser, and invite the bot to your server.

## Running the Bot

1.  Make sure you have a text channel named `pc-monitor` in your Discord server. The bot will send startup and warning messages there.
2.  Run the Python script:

```bash
python bot.py
```

The bot should now be online in your Discord server. You can start using slash commands (e.g., `/sysinfo`).
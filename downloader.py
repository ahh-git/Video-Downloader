import yt_dlp
import os
import time

DOWNLOAD_FOLDER = "downloads"
COOKIE_FILE = "cookies.txt"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def get_video_info(url):
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'noplaylist': True,
        'extract_flat': 'in_playlist',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    if os.path.exists(COOKIE_FILE): ydl_opts['cookiefile'] = COOKIE_FILE
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: return ydl.extract_info(url, download=False)
    except: return None

def download_video(url, format_id):
    timestamp = int(time.time())
    ydl_opts = {
        'format': f"{format_id}+bestaudio/best" if 'audio' not in format_id else format_id,
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'merge_output_format': 'mp4',
        'quiet': True, 'noplaylist': True,
        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base = os.path.splitext(filename)[0]
            # If merged to mp4, return that
            if os.path.exists(base + ".mp4"): return base + ".mp4", info.get('title'), None
            return filename, info.get('title'), None
    except Exception as e: return None, None, str(e)

#!/usr/bin/env python3
"""
Radio client — plays tracks from local Flask server.

Fetches track list and audio files from Flask server, caches locally, and plays.

Setup:
1. Install dependencies:
   pip install requests pygame

2. On Raspberry Pi, also install mpg123 as fallback:
   sudo apt-get install mpg123

3. Start the Flask server first:
   python server.py

4. Run this client:
   python pi_radio_client_simple.py

The client will:
- Fetch track list from http://localhost:5000/api/tracks
- Download MP3s to ~/.radio_cache/
- Play tracks using pygame or mpg123
- Auto-advance when a track finishes
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path
import random
import json

# --- Config ---
SERVER_URL = os.getenv('RADIO_SERVER_URL', 'http://localhost:5000')
CACHE_DIR = Path.home() / '.radio_cache'
CACHE_DIR.mkdir(exist_ok=True)
NOW_PLAYING = CACHE_DIR / 'now_playing.json'

print(f'[Config] Server: {SERVER_URL}')
print(f'[Config] Cache: {CACHE_DIR}')

# State
playlist = []
# order is a shuffled list of track indices
order = []
current_pos = 0
is_playing = False
player_process = None


def fetch_tracks() -> list:
    """Fetch track list from Flask server."""
    try:
        res = requests.get(f'{SERVER_URL}/api/tracks', timeout=5)
        res.raise_for_status()
        tracks = res.json()
        print(f'[Tracks] Loaded {len(tracks)} from server')
        return tracks
    except Exception as e:
        print(f'[Error] Failed to fetch tracks: {e}')
        return []


def download_audio(track_id: int, filename: str) -> Path:
    """Download MP3 from server and cache locally."""
    filepath = CACHE_DIR / filename
    
    # Return if already cached
    if filepath.exists():
        return filepath
    
    print(f'[Download] {filename}...')
    try:
        audio_url = f'{SERVER_URL}/api/audio/{track_id}'
        
        # Follow redirects (in case Flask redirects to remote URL)
        res = requests.get(audio_url, timeout=30, allow_redirects=True)
        res.raise_for_status()
        
        filepath.write_bytes(res.content)
        print(f'[Cached] {filename}')
        return filepath
    except Exception as e:
        print(f'[Error] Download failed: {e}')
        return None


def play_audio_file(filepath: Path, title: str):
    """Play cached MP3 file using pygame or mpg123."""
    global player_process, is_playing
    
    # Stop current playback
    if player_process:
        try:
            player_process.terminate()
            player_process.wait(timeout=2)
        except Exception:
            try:
                player_process.kill()
            except Exception:
                pass
        player_process = None
    
    is_playing = True
    print(f'[Playing] {title}')
    
    # Try pygame first (if available)
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(str(filepath))
        pygame.mixer.music.play()
        
        # Wait for playback
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        is_playing = False
        print(f'[Finished] {title}')
        return True
    except ImportError:
        pass  # Fall through to mpg123
    except Exception as e:
        print(f'[pygame error] {e}')
    
    # Fallback to mpg123 CLI
    try:
        player_process = subprocess.Popen(
            ['mpg123', str(filepath)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        player_process.wait()
        is_playing = False
        print(f'[Finished] {title}')
        return True
    except FileNotFoundError:
        print('[Error] Neither pygame nor mpg123 available.')
        print('  Windows: pip install pygame')
        print('  Pi: sudo apt-get install mpg123')
        is_playing = False
        return False


def main():
    """Main loop: load tracks and play sequentially."""
    global playlist, current_index, is_playing
    
    print('[Radio] Client started')
    print('[Radio] Press Ctrl+C to stop\n')
    
    # Load tracks once at startup
    playlist = fetch_tracks()
    if not playlist:
        print('[Error] No tracks loaded. Is Flask server running?')
        print(f'[Info] Check: {SERVER_URL}/health')
        return

    # Create shuffled play order
    order = list(range(len(playlist)))
    random.shuffle(order)
    current_pos = 0
    
    try:
        while True:
            if is_playing:
                # Wait for current playback to finish
                time.sleep(0.5)
                continue
            
            if current_pos < len(order):
                # Determine next track index from shuffled order
                track_index = order[current_pos]
                track = playlist[track_index]
                title = track.get('title', 'Unknown')
                file_url = track.get('file', '')

                # Extract filename from URL
                filename = file_url.split('/')[-1] if '/' in file_url else file_url

                print(f'[Track {current_pos + 1}/{len(playlist)}] #{track_index + 1} {title}')

                # Download to cache (use original track index for server API)
                filepath = download_audio(track_index, filename)
                # Write now playing state to disk so display can pick it up
                try:
                    now_state = {
                        'track_index': track_index,
                        'title': title,
                        'file': file_url,
                        'cover': track.get('cover', ''),
                        'selectedBy': track.get('selectedBy', ''),
                        'start_time': int(time.time())
                    }
                    NOW_PLAYING.write_text(json.dumps(now_state))
                except Exception as e:
                    print(f'[Warning] Failed to write now playing state: {e}')
                if filepath:
                    # Play cached file
                    success = play_audio_file(filepath, title)
                    if success:
                        # Update start_time after successful play (best-effort)
                        try:
                            now_state['start_time'] = int(time.time())
                            NOW_PLAYING.write_text(json.dumps(now_state))
                        except Exception:
                            pass
                        current_pos += 1
                    else:
                        # Playback failed; wait and retry
                        time.sleep(2)
                else:
                    # Download failed; skip and move to next
                    print(f'[Skip] {title}')
                    current_pos += 1
                    time.sleep(1)
            else:
                # Reached end of shuffled order: reshuffle and continue
                print('[Shuffle] Playlist finished; reshuffling...')
                order = list(range(len(playlist)))
                random.shuffle(order)
                current_pos = 0
                time.sleep(1)
    
    except KeyboardInterrupt:
        print('\n[Radio] Shutting down...')
        if player_process:
            try:
                player_process.terminate()
            except Exception:
                pass


if __name__ == '__main__':
    main()

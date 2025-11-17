#!/usr/bin/env python3
"""
Raspberry Pi Radio Client
Syncs playback with Firebase Realtime Database and plays audio locally.

Usage:
    python3 pi_radio_client.py --config firebase-config.json --music-dir ./music

Requirements:
    pip install firebase-admin pygame
    (or for audio: mpg123, pygame, or vlc)
"""

import json
import os
import sys
import time
import threading
import argparse
import urllib.request
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, db

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

# Global playback state
current_track = None
current_index = 0
is_playing = False
playback_thread = None
stop_playback = threading.Event()
last_sync_time = 0
music_cache = {}  # Downloaded tracks cache


def load_config(config_path):
    """Load Firebase config from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def init_firebase(config):
    """Initialize Firebase Admin SDK."""
    try:
        # Use the config to initialize (no service account needed for test mode)
        options = {
            'databaseURL': config['databaseURL']
        }
        firebase_admin.initialize_app(options=options)
        print("[Firebase] Initialized")
        return True
    except Exception as e:
        print(f"[Firebase] Error: {e}")
        return False


def init_audio():
    """Initialize audio playback (pygame or fallback)."""
    if HAS_PYGAME:
        try:
            pygame.mixer.init()
            print("[Audio] Initialized pygame mixer")
            return 'pygame'
        except Exception as e:
            print(f"[Audio] pygame init failed: {e}")
    
    # Fallback: check for mpg123
    try:
        os.system("which mpg123 > /dev/null 2>&1")
        print("[Audio] Using mpg123")
        return 'mpg123'
    except:
        pass
    
    print("[Audio] No audio backend available (pygame or mpg123)")
    return None


def download_track(url, cache_dir):
    """Download a track if not already cached."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Use URL hash as cache key
    cache_file = cache_dir / f"{hash(url) % 10**8}.mp3"
    
    if cache_file.exists():
        print(f"[Cache] Using cached: {cache_file}")
        return str(cache_file)
    
    try:
        print(f"[Download] Fetching: {url}")
        urllib.request.urlretrieve(url, cache_file)
        print(f"[Download] Saved to: {cache_file}")
        return str(cache_file)
    except Exception as e:
        print(f"[Download] Error: {e}")
        return None


def play_audio_pygame(file_path, start_pos=0):
    """Play audio using pygame."""
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        
        # Seek to start position if possible
        if start_pos > 0:
            # pygame doesn't have reliable seek; approximate by waiting
            time.sleep(min(start_pos, 0.5))
        
        print(f"[Playback] Playing (pygame): {file_path}")
        
        # Block until music ends or stop event is set
        while pygame.mixer.music.get_busy() and not stop_playback.is_set():
            time.sleep(0.1)
        
        print("[Playback] Track ended")
    except Exception as e:
        print(f"[Playback] Error: {e}")


def play_audio_mpg123(file_path, start_pos=0):
    """Play audio using mpg123."""
    try:
        cmd = f"mpg123 '{file_path}'"
        print(f"[Playback] Playing (mpg123): {file_path}")
        os.system(cmd)
        print("[Playback] Track ended")
    except Exception as e:
        print(f"[Playback] Error: {e}")


def play_track(track, audio_backend, music_cache_dir, elapsed_seconds):
    """Download and play a track, seeking to elapsed position."""
    global is_playing, playback_thread, stop_playback
    
    if not track:
        print("[Playback] No track to play")
        return
    
    # Determine track URL
    track_url = track.get('file')
    if not track_url:
        print("[Playback] Track has no file URL")
        return
    
    # If it's a relative path, skip (not hosted remotely)
    if not track_url.startswith('http'):
        print(f"[Playback] Skipping local path (not remote): {track_url}")
        return
    
    # Download if needed
    file_path = download_track(track_url, music_cache_dir)
    if not file_path:
        print("[Playback] Download failed")
        return
    
    # Stop any existing playback
    stop_playback.set()
    if playback_thread and playback_thread.is_alive():
        playback_thread.join(timeout=2)
    
    # Start new playback in a thread
    stop_playback.clear()
    is_playing = True
    
    if audio_backend == 'pygame':
        playback_thread = threading.Thread(
            target=play_audio_pygame,
            args=(file_path, elapsed_seconds),
            daemon=True
        )
    elif audio_backend == 'mpg123':
        playback_thread = threading.Thread(
            target=play_audio_mpg123,
            args=(file_path, elapsed_seconds),
            daemon=True
        )
    else:
        print("[Playback] No audio backend")
        is_playing = False
        return
    
    playback_thread.start()


def sync_from_firebase(audio_backend, music_cache_dir):
    """Fetch current state from Firebase and sync playback."""
    global current_track, current_index, last_sync_time
    
    try:
        ref = db.reference('radio/state')
        state = ref.get()
        
        if not state:
            print("[Sync] No radio/state in Firebase")
            return
        
        current_index = state.get('currentTrackIndex', 0)
        tracks = state.get('tracks', [])
        start_time = state.get('startTime', 0)
        
        if not tracks or current_index >= len(tracks):
            print("[Sync] Invalid track index or no tracks")
            return
        
        current_track = tracks[current_index]
        elapsed_seconds = (time.time() * 1000 - start_time) / 1000.0
        
        print(f"[Sync] Track {current_index}: {current_track.get('title', 'Unknown')}")
        print(f"[Sync] Elapsed: {elapsed_seconds:.1f}s")
        
        play_track(current_track, audio_backend, music_cache_dir, elapsed_seconds)
        last_sync_time = time.time()
    
    except Exception as e:
        print(f"[Sync] Error: {e}")


def listen_firebase(audio_backend, music_cache_dir):
    """Listen to Firebase state changes."""
    try:
        ref = db.reference('radio/state')
        
        def on_change(message):
            print("[Firebase] State changed")
            sync_from_firebase(audio_backend, music_cache_dir)
        
        ref.listen(on_change)
    except Exception as e:
        print(f"[Firebase] Listen error: {e}")


def main():
    parser = argparse.ArgumentParser(description='Raspberry Pi Radio Client')
    parser.add_argument('--config', default='firebase-config.json',
                        help='Path to Firebase config JSON')
    parser.add_argument('--music-dir', default='./music_cache',
                        help='Directory to cache downloaded music')
    
    args = parser.parse_args()
    
    # Load config
    if not os.path.exists(args.config):
        print(f"Error: {args.config} not found")
        sys.exit(1)
    
    config = load_config(args.config)
    
    # Initialize Firebase
    if not init_firebase(config):
        print("Error: Firebase initialization failed")
        sys.exit(1)
    
    # Initialize audio
    audio_backend = init_audio()
    if not audio_backend:
        print("Warning: No audio backend available")
    
    print("[Pi Radio] Starting sync listener...")
    print(f"[Pi Radio] Music cache: {args.music_dir}")
    
    # Initial sync
    sync_from_firebase(audio_backend, args.music_dir)
    
    # Start listening for state changes
    listen_firebase(audio_backend, args.music_dir)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Pi Radio] Shutting down...")
        stop_playback.set()
        if playback_thread:
            playback_thread.join(timeout=2)
        sys.exit(0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""

- Scans 'music/' for .mp3 files
- Extracts embedded album art (APIC ID3) into 'album-art/' (if present)
- Builds a tracks JSON in memory, serves /api/tracks
- Serves static files, album-art, and music files
- Serves the HTML dashboard at /
"""

import os
import time
import json
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, render_template
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, error as ID3Error
from mutagen.mp3 import MP3

BASE_DIR = Path(__file__).parent.resolve()
MUSIC_DIR = BASE_DIR / "music"
ART_DIR = BASE_DIR / "album-art"

app = Flask(__name__, template_folder="templates", static_folder="static")

# Ensure directories exist
MUSIC_DIR.mkdir(exist_ok=True)
ART_DIR.mkdir(exist_ok=True)

def sanitize_filename(name: str) -> str:
    # remove path components and keep safe chars
    return os.path.basename(name)

def extract_art(mp3_path: Path, dest_path: Path) -> bool:
    """
    Extract APIC frame (album art) if present and write to dest_path.
    Returns True if art was written.
    """
    try:
        tags = ID3(mp3_path)
    except ID3Error:
        return False

    for frame in tags.getall("APIC"):
        # APIC frame found
        try:
            with open(dest_path, "wb") as f:
                f.write(frame.data)
            return True
        except Exception:
            return False
    return False

def read_track_info(mp3_path: Path):
    """
    Returns a dict with metadata for this mp3:
      {
        "file": "<filename.mp3>",
        "title": "Song Title",
        "artist": "Artist",
        "album": "Album",
        "duration": seconds (int),
        "art": "album-art/filename.jpg" or null
      }
    """
    fname = sanitize_filename(mp3_path.name)
    info = {
        "file": fname,
        "title": None,
        "artist": None,
        "album": None,
        "duration": None,
        "art": None,
    }

    # duration (in seconds)
    try:
        mp = MP3(mp3_path)
        info["duration"] = int(mp.info.length)
    except Exception:
        info["duration"] = 0

    try:
        tags = ID3(mp3_path)
        if TIT2 := tags.get("TIT2"):
            info["title"] = str(TIT2.text[0])
        if TPE1 := tags.get("TPE1"):
            info["artist"] = str(TPE1.text[0])
        if TALB := tags.get("TALB"):
            info["album"] = str(TALB.text[0])
    except Exception:
        # no id3v2 tags or parse error
        pass

    # fallback title is filename without extension
    if not info["title"]:
        info["title"] = mp3_path.stem

    # extract album art if not already extracted
    art_filename = mp3_path.with_suffix(".jpg").name
    art_path = ART_DIR / art_filename
    if art_path.exists():
        info["art"] = f"/album-art/{art_filename}"
    else:
        ok = extract_art(mp3_path, art_path)
        if ok:
            info["art"] = f"/album-art/{art_filename}"
        else:
            info["art"] = None

    return info

def build_playlist():
    """
    Scan the music directory and return a list of track dicts.
    """
    tracks = []
    for f in sorted(MUSIC_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() == ".mp3":
            tracks.append(read_track_info(f))
    return tracks

# Cache playlist in memory and update periodically
_playlist_cache = {"tracks": [], "updated": 0}
CACHE_TTL = 3  # seconds

def get_playlist():
    now = time.time()
    if now - _playlist_cache["updated"] > CACHE_TTL:
        _playlist_cache["tracks"] = build_playlist()
        _playlist_cache["updated"] = now
    return _playlist_cache["tracks"]

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/tracks")
def api_tracks():
    tracks = get_playlist()
    return jsonify(tracks)

@app.route("/music/<path:filename>")
def serve_music(filename):
    # Serve mp3 files
    filename = sanitize_filename(filename)
    return send_from_directory(str(MUSIC_DIR), filename, conditional=True)

@app.route("/album-art/<path:filename>")
def serve_art(filename):
    filename = sanitize_filename(filename)
    return send_from_directory(str(ART_DIR), filename, conditional=True)

# Let Flask serve static files from /static (CSS/JS)
# Run
if __name__ == "__main__":
    # Optionally pre-build playlist to extract art on startup
    print("Scanning music folder and extracting album art...")
    _ = get_playlist()
    print(f"Found {_playlist_cache['tracks'].__len__()} tracks")
    # Use host=0.0.0.0 if you want to access from other devices on the network
    app.run(host="0.0.0.0", port=8000, debug=False)

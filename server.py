#!/usr/bin/env python3
"""
Local Flask server for Raspberry Pi radio player.

Serves:
- /api/tracks          → JSON list of tracks with metadata
- /api/audio/<id>      → MP3 file stream (by 0-based index in tracks.json)
- /health              → Health check
- /                     → Static HTML dashboard (optional)

Runs on http://localhost:5000 (or 0.0.0.0:5000 if FLASK_ENV=production).
Raspberry Pi client fetches from here; Neocities can optionally use this
if Pi is exposed on the LAN.
"""
import os
import json
from pathlib import Path
from flask import Flask, jsonify, send_file, request, render_template_string
from flask_cors import CORS
import logging

# Setup
ROOT = Path(__file__).resolve().parent
MUSIC_DIR = ROOT / 'music'
TRACKS_FILE = ROOT / 'tracks.json'

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests (e.g., from Neocities)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate directories
if not MUSIC_DIR.exists():
    logger.warning(f'Music directory not found: {MUSIC_DIR}')
if not TRACKS_FILE.exists():
    logger.warning(f'Tracks file not found: {TRACKS_FILE}')


def load_tracks():
    """Load and parse tracks.json."""
    try:
        with open(TRACKS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f'Failed to load tracks.json: {e}')
        return []


# Cache tracks in memory (reload periodically or on demand)
_tracks_cache = None
_tracks_mtime = None

def get_tracks_cached():
    """Load tracks with simple file mtime caching."""
    global _tracks_cache, _tracks_mtime
    if TRACKS_FILE.exists():
        mtime = TRACKS_FILE.stat().st_mtime
        if _tracks_cache is None or _tracks_mtime != mtime:
            _tracks_cache = load_tracks()
            _tracks_mtime = mtime
            logger.info(f'Loaded {len(_tracks_cache)} tracks')
    return _tracks_cache or []


@app.route('/api/tracks', methods=['GET'])
def api_tracks():
    """Return track list as JSON."""
    tracks = get_tracks_cached()
    return jsonify(tracks)


@app.route('/api/audio/<int:track_id>', methods=['GET'])
def api_audio(track_id):
    """
    Serve audio for a track.
    
    Strategy:
    1. If the track's 'file' is a local path (music/...), serve from disk
    2. If it's a remote URL (http://...), proxy/redirect to it
    
    Args:
        track_id: 0-based index into tracks array
    
    Returns:
        MP3 file stream or redirect
    """
    tracks = get_tracks_cached()
    if not (0 <= track_id < len(tracks)):
        return jsonify({'error': 'Track not found'}), 404
    
    track = tracks[track_id]
    file_path = track.get('file', '')
    
    # Check if it's a remote URL
    if file_path.startswith('http://') or file_path.startswith('https://'):
        # Redirect to the remote URL (client will fetch directly)
        # Or proxy it (slower but works with CORS)
        # For now, redirect:
        return {'redirect': file_path}, 302, {'Location': file_path}
    
    # Otherwise treat as local file path
    # Extract filename from local path (handle "music/..." or just "filename")
    if '/' in file_path:
        filename = file_path.split('/')[-1]
    else:
        filename = file_path
    
    # Build safe path (prevent directory traversal)
    audio_file = MUSIC_DIR / filename
    
    if not audio_file.exists():
        logger.warning(f'Audio file not found: {audio_file}')
        return jsonify({'error': 'Audio file not found'}), 404
    
    try:
        # Flask's send_file with range request support
        return send_file(
            str(audio_file),
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=filename
        )
    except Exception as e:
        logger.error(f'Error serving audio {filename}: {e}')
        return jsonify({'error': 'Failed to serve audio'}), 500


@app.route('/api/state', methods=['GET', 'POST'])
def api_state():
    """
    Stub for playback state sync (Firebase can handle this; Pi client
    can also POST state updates here for logging).
    """
    if request.method == 'POST':
        state = request.get_json()
        logger.info(f'State update: {state}')
        return jsonify({'ok': True})
    
    return jsonify({
        'currentTrackIndex': 0,
        'startTime': 0,
        'lastUpdated': None
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'tracks': len(get_tracks_cached()),
        'music_dir_exists': MUSIC_DIR.exists(),
        'tracks_file_exists': TRACKS_FILE.exists()
    })


@app.route('/', methods=['GET'])
def dashboard():
    """Simple HTML dashboard showing server status and available tracks."""
    tracks = get_tracks_cached()
    tracks_html = ''.join(
        f'<li>{t.get("title", "Unknown")} ({t.get("selectedBy", "?")})</li>'
        for t in tracks[:10]
    )
    more = f'<p>... and {len(tracks) - 10} more</p>' if len(tracks) > 10 else ''
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Radio Server</title>
        <style>
            body {{ font-family: sans-serif; margin: 20px; }}
            .status {{ background: #e8f5e9; padding: 10px; border-radius: 5px; }}
            .error {{ background: #ffebee; color: #c62828; }}
            ul {{ max-height: 300px; overflow-y: auto; }}
        </style>
    </head>
    <body>
        <h1>Radio Server</h1>
        <div class="status">
            <p><strong>Status:</strong> Running ✓</p>
            <p><strong>Tracks loaded:</strong> {len(tracks)}</p>
            <p><strong>Music directory:</strong> {MUSIC_DIR}</p>
        </div>
        <h2>API Endpoints</h2>
        <ul>
            <li><code>GET /api/tracks</code> — List all tracks</li>
            <li><code>GET /api/audio/&lt;id&gt;</code> — Stream MP3 by index</li>
            <li><code>GET /health</code> — Health check</li>
            <li><code>GET /api/state</code> — Get playback state</li>
        </ul>
        <h2>Sample Tracks (first 10)</h2>
        <ul>
            {tracks_html}
        </ul>
        {more}
    </body>
    </html>
    """
    return render_template_string(html)


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500


if __name__ == '__main__':
    # Local development: bind to 127.0.0.1:5000
    # For LAN access from other machines, set host='0.0.0.0'
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    logger.info(f'Starting server on {host}:{port} (debug={debug})')
    app.run(host=host, port=port, debug=debug, threaded=True)

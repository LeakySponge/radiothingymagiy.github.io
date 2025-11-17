#!/usr/bin/env python3
"""
Stylish TUI display for Raspberry Pi radio.

This script reads the current playing track state from
`~/.radio_cache/now_playing.json` (written by `pi_radio_client_simple.py`) and
displays a beautiful terminal UI with:
- Now-playing track info (title, artist, selector)
- Animated waveform bars reacting to audio RMS levels
- Progress display with elapsed time
- Server status

If `pydub` or `numpy` are not available, uses animated pulse bars instead.

Requirements:
  pip install rich pydub numpy requests
  sudo apt-get install ffmpeg   # for pydub to read MP3s (optional)

Run:
  python radio_display.py

Press Ctrl+C to exit.
"""

import time
import json
import os
import math
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.columns import Columns

# Optional imports for audio analysis
HAS_PYDUB = False
HAS_NUMPY = False
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except Exception:
    HAS_PYDUB = False

try:
    import numpy as np
    HAS_NUMPY = True
except Exception:
    HAS_NUMPY = False

# Config
CACHE_DIR = Path.home() / '.radio_cache'
NOW_PLAYING_FILE = CACHE_DIR / 'now_playing.json'

console = Console()


def load_segment_for_file(filepath: Path):
    """Load full audio file via pydub if available."""
    if not HAS_PYDUB:
        return None
    try:
        return AudioSegment.from_file(str(filepath))
    except Exception as e:
        console.log(f'[yellow]pydub failed to load {filepath}: {e}[/yellow]')
        return None


def rms_from_segment(seg, start_ms: int, window_ms: int = 100):
    """Return RMS value (0-1) for a short window starting at start_ms."""
    if not HAS_PYDUB or not HAS_NUMPY or seg is None:
        return 0.0
    if start_ms < 0:
        start_ms = 0
    end_ms = min(len(seg), start_ms + window_ms)
    window = seg[start_ms:end_ms]
    samples = np.array(window.get_array_of_samples())
    if window.channels > 1:
        samples = samples.reshape((-1, window.channels))
        samples = samples.mean(axis=1)
    if samples.size == 0:
        return 0.0
    rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
    max_val = float(2 ** (8 * window.sample_width - 1) - 1)
    return float(rms / max_val)


def build_waveform_bars(amplitudes, bar_count=32):
    """Convert amplitudes to a string of bar characters."""
    bars = '▁▂▃▄▅▆▇█'
    if not amplitudes:
        return ''
    # Downsample to bar_count
    step = max(1, len(amplitudes) // bar_count)
    sampled = amplitudes[::step][:bar_count]
    result = ''
    for a in sampled:
        idx = int(a * (len(bars) - 1))
        result += bars[idx]
    return result


def build_visual_waveform(amplitudes, width=50):
    """Build a vertical waveform visualization with height variation."""
    bars = '▁▂▃▄▅▆▇█'
    if not amplitudes:
        return ''
    
    step = max(1, len(amplitudes) // width)
    sampled = amplitudes[::step][:width]
    
    # Create multiple rows for visual depth
    lines = []
    for row in range(8, 0, -1):
        line = ''
        for a in sampled:
            height = int(a * 8)
            if height >= row:
                line += '█'
            else:
                line += ' '
        lines.append(line)
    return '\n'.join(lines)


def main():
    loaded_seg = None
    current_file = None
    amplitudes = [0.0] * 200
    last_state_mtime = 0
    
    console.print('[bold cyan]🎵 Radio TUI Display[/bold cyan]\n', justify='center')

    try:
        with Live(refresh_per_second=10) as live:
            while True:
                elapsed = None
                state = None
                
                # Read now_playing file if present
                if NOW_PLAYING_FILE.exists():
                    try:
                        mtime = NOW_PLAYING_FILE.stat().st_mtime
                        if mtime != last_state_mtime:
                            last_state_mtime = mtime
                            raw = NOW_PLAYING_FILE.read_text()
                            state = json.loads(raw)
                            # Map to cached file path
                            file_url = state.get('file', '')
                            filename = file_url.split('/')[-1] if '/' in file_url else file_url
                            cached = CACHE_DIR / filename
                            if cached.exists():
                                if current_file != str(cached):
                                    current_file = str(cached)
                                    loaded_seg = None
                                    if HAS_PYDUB:
                                        loaded_seg = load_segment_for_file(cached)
                        else:
                            # Still read current state even if file unchanged
                            raw = NOW_PLAYING_FILE.read_text()
                            state = json.loads(raw)
                        
                        if state:
                            start_time = state.get('start_time', int(time.time()))
                            elapsed = int(time.time()) - int(start_time)
                    except Exception as e:
                        pass  # Silent fail, display "waiting" message
                
                # Build display content
                if state:
                    title = state.get('title', 'Unknown')
                    selected_by = state.get('selectedBy', 'Unknown')
                    
                    # Compute amplitudes from audio if available
                    if HAS_PYDUB and HAS_NUMPY and loaded_seg is not None and elapsed is not None:
                        pos_ms = int(elapsed * 1000)
                        new_amps = []
                        windows = 200
                        total_span_ms = 2000
                        step = max(1, total_span_ms // windows)
                        for i in range(windows):
                            ms = pos_ms + i * step
                            a = rms_from_segment(loaded_seg, ms, window_ms=step)
                            new_amps.append(min(max(a, 0.0), 1.0))
                        amplitudes = new_amps
                    else:
                        # Fallback: animate bars based on time
                        t = time.time()
                        amplitudes = [
                            0.5 + 0.4 * math.sin(t * 2 + i * 0.1)
                            for i in range(32)
                        ]
                    
                    # Build visual waveform (vertical bars)
                    waveform_visual = build_visual_waveform(amplitudes, width=60)
                    
                    # Build horizontal bars
                    waveform_bars = build_waveform_bars(amplitudes, bar_count=60)
                    
                    # Create layout
                    layout = Layout()
                    layout.split_column(
                        Layout(name='title', size=5),
                        Layout(name='viz1', size=10),
                        Layout(name='bars', size=3),
                        Layout(name='info', size=4)
                    )
                    
                    # Title panel
                    title_text = Text(title, style='bold bright_cyan', justify='center')
                    layout['title'].update(Panel(
                        title_text,
                        box=ROUNDED,
                        border_style='bright_cyan',
                        padding=(1, 2)
                    ))
                    
                    # Waveform visualization with vertical bars
                    waveform_text = Text(waveform_visual, style='bold bright_green')
                    layout['viz1'].update(Panel(
                        waveform_text,
                        box=ROUNDED,
                        border_style='bright_green',
                        padding=(0, 1)
                    ))
                    
                    # Horizontal bar visualization
                    bars_text = Text(waveform_bars, style='bold green')
                    layout['bars'].update(Panel(
                        bars_text,
                        box=ROUNDED,
                        border_style='green'
                    ))
                    
                    # Info section
                    elapsed_str = f'{int(elapsed // 60):02d}:{int(elapsed % 60):02d}'
                    frames = ['▮ ', '▯ ', '▮ ']
                    frame = frames[int(time.time() * 2) % len(frames)]
                    
                    info_text = f'⏱ {elapsed_str}\n🎧 {selected_by}\n{frame}Playing'
                    info_display = Text(info_text, style='bold bright_yellow', justify='center')
                    layout['info'].update(Panel(
                        info_display,
                        box=ROUNDED,
                        border_style='bright_yellow'
                    ))
                    
                    live.update(layout)
                else:
                    # Waiting for tracks - animated
                    frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                    frame = frames[int(time.time() * 5) % len(frames)]
                    waiting_text = Text(f'{frame} Waiting for now_playing.json...', style='bold bright_yellow', justify='center')
                    waiting_panel = Panel(waiting_text, box=ROUNDED, border_style='bright_yellow', padding=(1, 2))
                    live.update(waiting_panel)
                
                time.sleep(0.05)  # ~20 FPS, let Live handle refresh rate

    except KeyboardInterrupt:
        console.print('\n[bright_yellow]👋 Exiting...[/bright_yellow]', justify='center')


if __name__ == '__main__':
    main()

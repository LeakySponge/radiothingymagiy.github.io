#!/usr/bin/env python3
"""
Radio player for Raspberry Pi — runs both client (audio) and display together.

This script starts:
1. pi_radio_client_simple.py (audio playback)
2. radio_display.py (screen display)

Usage:
    python radio_player.py

Kill with Ctrl+C to stop both.
"""

import subprocess
import sys
import signal
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    print('[Radio] Starting Raspberry Pi radio player...')
    print('[Radio] Press Ctrl+C to stop\n')
    
    # Start both processes
    client_proc = None
    display_proc = None
    
    try:
        # Start audio client
        print('[Client] Starting audio playback...')
        client_proc = subprocess.Popen(
            [sys.executable, str(ROOT / 'pi_radio_client_simple.py')],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        # Give client a moment to start
        time.sleep(1)
        
        # Start display
        print('[Display] Starting screen display...')
        display_proc = subprocess.Popen(
            [sys.executable, str(ROOT / 'radio_display.py')],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        # Wait for both to finish (or be interrupted)
        while True:
            time.sleep(1)
            
            # Check if either process died
            if client_proc and client_proc.poll() is not None:
                print('[Client] Process exited')
                break
            if display_proc and display_proc.poll() is not None:
                print('[Display] Process exited')
                break
    
    except KeyboardInterrupt:
        print('\n[Radio] Shutting down...')
    
    finally:
        # Kill both processes
        if client_proc:
            try:
                client_proc.terminate()
                client_proc.wait(timeout=2)
            except Exception:
                client_proc.kill()
        
        if display_proc:
            try:
                display_proc.terminate()
                display_proc.wait(timeout=2)
            except Exception:
                display_proc.kill()
        
        print('[Radio] Done')


if __name__ == '__main__':
    main()

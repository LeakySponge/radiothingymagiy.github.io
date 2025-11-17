# Raspberry Pi Radio Client Setup

This guide helps you run the synced radio player on a Raspberry Pi Zero 2W (or any Raspberry Pi).

## What It Does

- Connects to Firebase Realtime Database (same as web clients)
- Listens for track changes and playback state
- Downloads and plays MP3 files in sync with web clients
- Uses the Pi's audio jack or HDMI to play sound

## Prerequisites

1. **Raspberry Pi Zero 2W** (or any Pi with network + audio output)
2. **Raspberry Pi OS Lite** or **Full** (Debian-based)
3. **Internet connection** (ethernet or WiFi)
4. **Audio output** (3.5mm jack, HDMI, or USB speaker)

## Installation

### 1. SSH into your Raspberry Pi

```bash
ssh pi@<your-pi-hostname>.local
# or: ssh pi@<your-pi-ip>
# default password: raspberry
```

### 2. Clone or copy the repo to your Pi

Option A: Clone from GitHub
```bash
cd ~
git clone https://github.com/LeakySponge/radiothingymagiy.git
cd radiothingymagiy
```

Option B: Copy files manually
- Copy `pi_radio_client.py`, `firebase-config.json`, and `requirements.txt` to the Pi via SCP or USB

### 3. Install dependencies

```bash
# Update package manager
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and pip
sudo apt-get install -y python3 python3-pip

# Install audio library (pygame needs this)
sudo apt-get install -y libsdl2-mixer-2.0

# Optional: install mpg123 (lightweight MP3 player, good fallback)
sudo apt-get install -y mpg123

# Install Python packages
pip3 install -r requirements.txt
```

### 4. Prepare Firebase config

Ensure `firebase-config.json` is in the same directory as `pi_radio_client.py`:

```bash
ls firebase-config.json
# Should output: firebase-config.json
```

### 5. Test audio playback

Before running the client, test that audio works:

```bash
# Test pygame mixer (if installed)
python3 -c "import pygame; pygame.mixer.init(); print('pygame OK')"

# Or test mpg123
which mpg123
```

## Running the Client

### Basic Usage

```bash
python3 pi_radio_client.py --config firebase-config.json --music-dir ./music_cache
```

The client will:
1. Connect to Firebase
2. Fetch the current track and position
3. Download the MP3 to `./music_cache/` (default)
4. Play it in sync with other clients
5. Listen for state changes and resync when needed

### Command-line Options

```bash
python3 pi_radio_client.py \
  --config firebase-config.json \      # Path to Firebase config
  --music-dir ./radio_music            # Directory to cache downloads
```

### Run as a systemd Service (Recommended)

To auto-start on boot and manage logs:

1. Create a systemd service file:
```bash
sudo nano /etc/systemd/system/pi-radio.service
```

2. Paste this config (adjust paths if needed):
```ini
[Unit]
Description=Raspberry Pi Radio Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/radiothingymagiy
ExecStart=/usr/bin/python3 /home/pi/radiothingymagiy/pi_radio_client.py \
  --config firebase-config.json \
  --music-dir /home/pi/radiothingymagiy/music_cache
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start:
```bash
sudo systemctl enable pi-radio.service
sudo systemctl start pi-radio.service
```

4. Check status:
```bash
sudo systemctl status pi-radio.service

# View logs
sudo journalctl -u pi-radio.service -f
```

## Troubleshooting

### Audio not playing

- Check if audio is muted: `amixer set PCM 100%`
- Test with `mpg123 /path/to/song.mp3`
- Ensure speakers/headphones are plugged in
- Check device: `sudo alsamixer` (arrow keys to adjust volume)

### Firebase connection issues

- Confirm `firebase-config.json` is valid JSON: `python3 -c "import json; json.load(open('firebase-config.json'))"`
- Check network: `ping google.com`
- Verify Firebase Realtime Database allows read/write (test mode or proper rules)

### Slow downloads

- Music files are cached in `./music_cache/` — check disk space: `df -h`
- First run will be slow while downloading; subsequent runs use cache

### Memory/CPU issues on Pi Zero

- Pi Zero 2W has limited resources; if playback stutters:
  - Use `mpg123` instead of pygame (lighter weight)
  - Close other programs
  - Consider a Pi 3 or 4 if possible

## Notes

- **Web clients and Pi sync together**: When a web user advances to the next track, the Pi automatically syncs.
- **No internet = no sync**: The Pi must be online to connect to Firebase.
- **Music cache**: Downloaded files are cached locally on the Pi to avoid re-downloading. Delete `./music_cache/` to clear.
- **Credentials**: `firebase-config.json` is safe to store on the Pi (it contains public web credentials, not private keys).

## Next Steps

1. Test the client locally in a terminal (see "Running the Client" above).
2. Once verified, set up as a systemd service to auto-start on boot.
3. Open a web browser to your Neocities/GitHub Pages radio and the Pi should sync!

Need help? Check the console output or systemd logs for error messages.

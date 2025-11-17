#!/usr/bin/env python3
"""
Convert tracks.json file paths to GitHub Release URLs.

Usage:
    python3 convert_to_github_urls.py \
      --github-repo LeakySponge/radiothingymagiy \
      --release-tag v1 \
      --input tracks.json \
      --output tracks.json
"""

import json
import argparse
from pathlib import Path


def convert_tracks_to_urls(tracks, github_repo, release_tag):
    """
    Convert relative file paths to GitHub Release download URLs.
    
    Example:
      "file": "music/Song Name.mp3"
      becomes:
      "file": "https://github.com/LeakySponge/radiothingymagiy/releases/download/v1/Song%20Name.mp3"
    """
    for track in tracks:
        if 'file' in track and track['file'].startswith('music/'):
            filename = track['file'].replace('music/', '')
            # URL-encode the filename (spaces → %20, etc.)
            filename_encoded = filename.replace(' ', '%20')
            track['file'] = f"https://github.com/{github_repo}/releases/download/{release_tag}/{filename_encoded}"
    
    return tracks


def main():
    parser = argparse.ArgumentParser(description='Convert tracks.json to GitHub Release URLs')
    parser.add_argument('--github-repo', default='LeakySponge/radiothingymagiy',
                        help='GitHub repo (owner/repo)')
    parser.add_argument('--release-tag', default='v1',
                        help='GitHub release tag (e.g., v1)')
    parser.add_argument('--input', default='tracks.json',
                        help='Input tracks.json file')
    parser.add_argument('--output', default='tracks.json',
                        help='Output tracks.json file (will overwrite if same as input)')
    
    args = parser.parse_args()
    
    # Load tracks.json
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {args.input} not found")
        return
    
    with open(input_path, 'r') as f:
        tracks = json.load(f)
    
    print(f"Loaded {len(tracks)} tracks from {args.input}")
    
    # Convert file paths to GitHub URLs
    tracks = convert_tracks_to_urls(tracks, args.github_repo, args.release_tag)
    
    # Save converted tracks
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(tracks, f, indent=4)
    
    print(f"Saved {len(tracks)} tracks to {args.output}")
    print(f"\nExample converted URL:")
    if tracks and 'file' in tracks[0]:
        print(f"  {tracks[0]['file']}")


if __name__ == '__main__':
    main()

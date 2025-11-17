#!/usr/bin/env python3
import json
from pathlib import Path

WORKDIR = Path(__file__).resolve().parent
TRACKS = WORKDIR / 'tracks.json'

RELEASE_PREFIX = 'https://github.com/LeakySponge/radiothingymagiy/releases/download/'
RAW_PREFIX = 'https://raw.githubusercontent.com/LeakySponge/radiothingymagiy.github.io/main/music/'


def convert_url(url: str) -> str:
    if not isinstance(url, str):
        return url
    if url.startswith(RAW_PREFIX):
        return url
    # If it's a releases download URL, replace prefix and keep filename
    if RELEASE_PREFIX in url:
        filename = url.split('/')[-1]
        return RAW_PREFIX + filename
    # If it's a blob URL like /blob/main/, convert to raw.githubusercontent.com form
    if '/blob/' in url and 'github.com' in url:
        # example: https://github.com/OWNER/REPO/blob/main/path/file.mp3
        parts = url.split('/')
        try:
            owner = parts[3]
            repo = parts[4]
            # find index of 'blob'
            blob_idx = parts.index('blob')
            branch = parts[blob_idx + 1]
            path = '/'.join(parts[blob_idx + 2:])
            return f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}'
        except Exception:
            return url
    # If it's the /raw/refs/heads/ style, convert to raw.githubusercontent
    if '/raw/refs/heads/' in url and 'github.com' in url:
        # example: https://github.com/OWNER/REPO/raw/refs/heads/BRANCH/path/to/file
        parts = url.split('/')
        try:
            owner = parts[3]
            repo = parts[4]
            raw_idx = parts.index('raw')
            # next should be 'refs', 'heads', branch
            branch = parts[raw_idx + 3]
            path = '/'.join(parts[raw_idx + 4:])
            return f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}'
        except Exception:
            return url
    return url


def main():
    if not TRACKS.exists():
        print('tracks.json not found at', TRACKS)
        return
    data = json.loads(TRACKS.read_text(encoding='utf-8'))
    changed = 0
    for item in data:
        old = item.get('file')
        new = convert_url(old)
        if new != old:
            item['file'] = new
            changed += 1
    if changed:
        TRACKS.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding='utf-8')
        print(f'Updated {changed} URLs in {TRACKS}')
    else:
        print('No URLs needed updating')

if __name__ == '__main__':
    main()

# Deploy Audio to GitHub Releases + Neocities

This guide walks you through uploading your MP3 files to GitHub Releases and updating your Neocities radio player.

## Step 1: Create a GitHub Release

1. Go to your repository: https://github.com/LeakySponge/radiothingymagiy
2. Click **Releases** (on the right sidebar)
3. Click **Draft a new release**
4. Fill in:
   - **Tag version**: `v1` (or any version you like)
   - **Release title**: `Audio Files` (or anything)
   - **Description**: `Audio files for the radio player` (optional)
5. Click **Attach binaries by dropping them here or selecting them** (or the upload button)
6. Upload all your MP3 files from your `music/` folder

   > **Tip**: If you have many files, you can drag-drop a folder, or use GitHub CLI:
   > ```bash
   > gh release create v1 music/*.mp3 --title "Audio Files"
   > ```

7. Click **Publish release**

## Step 2: Convert `tracks.json` to Use GitHub URLs

I've created a script to convert your file paths automatically.

### Option A: Use the Python script

```bash
python3 convert_to_github_urls.py \
  --github-repo LeakySponge/radiothingymagiy \
  --release-tag v1 \
  --input tracks.json \
  --output tracks.json
```

This will rewrite:
```json
"file": "music/Song Name.mp3"
```

to:
```json
"file": "https://github.com/LeakySponge/radiothingymagiy/releases/download/v1/Song%20Name.mp3"
```

### Option B: Manual (if only a few tracks)

Edit `tracks.json` directly and replace each `music/` path with:
```
https://github.com/LeakySponge/radiothingymagiy/releases/download/v1/<FILENAME>.mp3
```

## Step 3: Verify the URLs Work

After conversion, test one URL in a browser:
```
https://github.com/LeakySponge/radiothingymagiy/releases/download/v1/After%20The%20Burial%20-%20Neo%20Seoul.mp3
```

It should download the MP3 (or play in a player). If you get a 404, check:
- The filename exactly matches what's in the release
- You replaced spaces with `%20`
- The release tag is correct (`v1`)

## Step 4: Update Neocities

1. Download or copy your updated `tracks.json` (from Step 2)
2. Upload it to Neocities (replace the old one)
3. Open your Neocities radio site in a browser
4. Check DevTools Console:
   - Should show `[Firebase] Tracks updated: X tracks`
   - Status badge should show `Synced — Live`
   - Audio should play

## Step 5: Verify the Pi Client Works (Optional)

Once Firebase has the track URLs, run the Pi client on your Raspberry Pi:

```bash
python3 pi_radio_client.py --config firebase-config.json --music-dir ./music_cache
```

It will:
1. Read `radio/tracks` from Firebase (with GitHub Release URLs)
2. Download the MP3s to `./music_cache/`
3. Play in sync with the web client

## Troubleshooting

**"404 Not Found" when clicking a track link**
- Check the GitHub release page: are the MP3s there?
- Verify the filename in `tracks.json` matches exactly (including spaces, capitalization, hyphens)
- Test the URL directly in a browser

**Neocities shows "Synced — Live" but no audio plays**
- Open DevTools → Network tab
- Look for the MP3 download request (should be a `https://github.com/...` URL)
- If it's a 404, the filename doesn't match the release
- If it's 200 but no audio, check your browser's autoplay settings

**"Too many files" or "Release size limit"**
- GitHub releases have no hard limit, but uploading 100+ files at once can be slow
- Use the GitHub CLI for faster bulk uploads:
  ```bash
  gh release create v1 music/*.mp3
  ```

## Next Steps

Once everything works on Neocities:
- Deploy the Pi client to your Raspberry Pi
- Both web and Pi clients will play the same audio in sync via Firebase
- Update `radio/state` in Firebase to advance tracks — all clients sync automatically

That's it! Your radio is now fully distributed:
- **Code** on Neocities (or GitHub Pages)
- **Audio** on GitHub Releases (or any public host)
- **State** in Firebase (synced across all clients)
- **Playback** on web + Raspberry Pi

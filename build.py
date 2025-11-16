import os
import json
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

MUSIC_DIR = "music"
ART_DIR = "album-art"
OUTPUT_JSON = "tracks.json"

os.makedirs(ART_DIR, exist_ok=True)

tracks = []

for filename in os.listdir(MUSIC_DIR):
    if not filename.lower().endswith(".mp3"):
        continue

    mp3_path = os.path.join(MUSIC_DIR, filename)
    art_path = os.path.join(ART_DIR, filename.replace(".mp3", ".jpg"))

    title = filename.rsplit(".", 1)[0]
    selected_by = "Unknown"  # You can edit this if needed

    # extract album art
    try:
        tags = ID3(mp3_path)
        for tag in tags.values():
            if tag.FrameID == "APIC":
                with open(art_path, "wb") as img:
                    img.write(tag.data)
                break
    except Exception as e:
        print("No album art found for", filename)

    tracks.append({
        "file": f"music/{filename}",
        "title": title,
        "cover": f"album-art/{filename.replace('.mp3', '.jpg')}",
        "selectedBy": selected_by
    })

with open(OUTPUT_JSON, "w") as f:
    json.dump(tracks, f, indent=4)

print("build complete! tracks.json generated.")

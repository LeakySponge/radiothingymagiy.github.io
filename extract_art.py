import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

music_folder = "music"
art_folder = "album-art"

os.makedirs(art_folder, exist_ok=True)

for file in os.listdir(music_folder):
    if file.endswith(".mp3"):
        mp3_path = os.path.join(music_folder, file)
        art_path = os.path.join(art_folder, file.replace(".mp3", ".jpg"))

        try:
            tags = ID3(mp3_path)

            for tag in tags.values():
                if tag.FrameID == "APIC":  # Album art frame
                    with open(art_path, "wb") as img:
                        img.write(tag.data)
                    print(f"Extracted art for {file}")
                    break
            else:
                print(f"No album art found in {file}")

        except Exception as e:
            print(f"Error processing {file}: {e}")

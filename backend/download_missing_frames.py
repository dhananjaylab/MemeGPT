import os
import requests
import json
from pathlib import Path

# Paths
BACKEND_ROOT = Path(__file__).resolve().parent
FRAMES_DIR = BACKEND_ROOT / "public" / "frames"
MEME_DATA_PATH = BACKEND_ROOT / "public" / "meme_data.json"

# Hardcoded fallback mappings for known memes in case of mismatch or missing from top 100
FALLBACK_MAPPINGS = {
    "Woman-Yelling-At-Cat.jpg": "https://i.imgflip.com/345v9t.jpg",
    "This-Is-Fine.jpg": "https://i.imgflip.com/39t1o3.jpg",
    "Surprised-Pikachu.jpg": "https://i.imgflip.com/2k351h.jpg",
    "Two-Buttons.jpg": "https://i.imgflip.com/1g8my4.jpg",
    "Always-Has-Been.jpg": "https://i.imgflip.com/43a45p.jpg",
    "Grus-Plan.jpg": "https://i.imgflip.com/261o3j.jpg",
    "Me-Explaining-To-Mom.jpg": "https://i.imgflip.com/2zb350.jpg",
    "Mocking-SpongeBob.jpg": "https://i.imgflip.com/1otk96.jpg",
    "Bike-Fall.jpg": "https://i.imgflip.com/109fpl.jpg",
    "Change-My-Mind.jpg": "https://i.imgflip.com/24y43o.jpg",
    "Ancient-Aliens.jpg": "https://i.imgflip.com/26am.jpg"
}

def clean_name(name):
    return "".join(c for c in name.lower() if c.isalnum())

def main():
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    
    if not MEME_DATA_PATH.exists():
        print(f"Error: meme_data.json not found at {MEME_DATA_PATH}")
        return
        
    with open(MEME_DATA_PATH, "r", encoding="utf-8") as f:
        templates = json.load(f)
        
    print(f"Fetching template catalog from Imgflip API...")
    try:
        resp = requests.get("https://api.imgflip.com/get_memes").json()
        imgflip_memes = resp.get("data", {}).get("memes", [])
    except Exception as e:
        print(f"Failed to fetch Imgflip API: {e}. Using hardcoded fallbacks only.")
        imgflip_memes = []
        
    # Map cleaned name to URL
    imgflip_map = {}
    for m in imgflip_memes:
        cleaned = clean_name(m["name"])
        imgflip_map[cleaned] = m["url"]
        
    downloaded = 0
    skipped = 0
    
    for t in templates:
        file_name = t.get("file_path")
        if not file_name:
            continue
            
        target_path = FRAMES_DIR / file_name
        if target_path.exists() and target_path.stat().st_size > 0:
            skipped += 1
            continue
            
        print(f"Missing template frame: {file_name}")
        url = None
        
        # Try hardcoded fallback first (most specific to our filenames)
        if file_name in FALLBACK_MAPPINGS:
            url = FALLBACK_MAPPINGS[file_name]
            
        # Try matching by name
        if not url:
            cleaned_name = clean_name(t["name"])
            url = imgflip_map.get(cleaned_name)
            
        # Try matching by alternative names
        if not url:
            for alt in t.get("alternative_names", []):
                cleaned_alt = clean_name(alt)
                if cleaned_alt in imgflip_map:
                    url = imgflip_map[cleaned_alt]
                    break
                    
        if url:
            print(f"  Downloading from {url}...")
            try:
                img_data = requests.get(url, timeout=10).content
                with open(target_path, "wb") as img_file:
                    img_file.write(img_data)
                downloaded += 1
                print(f"  Saved to {target_path}")
            except Exception as e:
                print(f"  Failed to download {url}: {e}")
        else:
            print(f"  Could not find download URL for {t['name']}")
            
    print(f"\nCompleted! Downloaded {downloaded} missing frames. Skipped {skipped} existing frames.")

if __name__ == "__main__":
    main()

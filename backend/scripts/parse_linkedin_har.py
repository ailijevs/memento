#!/usr/bin/env python3
"""
Parse LinkedIn HAR file(s) to extract and download profile pictures.

Usage:
    # Single HAR file:
    python parse_linkedin_har.py path/to/file.har
    
    # Directory of HAR files:
    python parse_linkedin_har.py path/to/har_directory/
    
    # Default (processes backend/data/har_files/):
    python parse_linkedin_har.py

Steps to create HAR files:
    1. Open Chrome DevTools -> Network tab -> check "Preserve log"
    2. Log into LinkedIn and browse through each profile you want
    3. Right-click in Network tab -> "Save all as HAR with content"
    4. Save to backend/data/har_files/ (or any location)

The script will:
    - Extract profile picture URLs from the HAR(s)
    - Download each image
    - Save to backend/data/profile_images/
    - Output a mapping of URLs to local files
"""

import json
import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

# Directories
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
OUTPUT_DIR = DATA_DIR / "profile_images"
DEFAULT_HAR_DIR = DATA_DIR / "har_files"


def extract_profile_pics_from_har(har_path: str) -> list[dict]:
    """
    Extract LinkedIn profile picture URLs from a HAR file.
    
    Returns list of dicts with 'url' and optional 'profile_hint' keys.
    """
    with open(har_path, "r", encoding="utf-8") as f:
        har_data = json.load(f)
    
    entries = har_data.get("log", {}).get("entries", [])
    profile_pics = []
    seen_urls = set()
    
    for entry in entries:
        request = entry.get("request", {})
        url = request.get("url", "")
        
        # LinkedIn profile pictures are served from media.licdn.com
        if "media.licdn.com" in url or "media-exp1.licdn.com" in url:
            # Skip company logos and background images
            if "company-logo" in url:
                continue
            if "background" in url:
                continue
            
            # Only keep actual profile photos
            if any(pattern in url for pattern in [
                "profile-displayphoto",
                "profile-framedphoto",
            ]):
                # Skip duplicates and tiny thumbnails
                if url in seen_urls:
                    continue
                    
                # Skip very small images (usually thumbnails)
                if "shrink_100_100" in url or "shrink_50_50" in url:
                    continue
                
                seen_urls.add(url)
                
                # Try to extract profile info from referer
                referer = ""
                for header in request.get("headers", []):
                    if header.get("name", "").lower() == "referer":
                        referer = header.get("value", "")
                        break
                
                profile_hint = None
                if "/in/" in referer:
                    # Extract LinkedIn username from referer
                    match = re.search(r"/in/([^/?]+)", referer)
                    if match:
                        profile_hint = match.group(1)
                
                profile_pics.append({
                    "url": url,
                    "profile_hint": profile_hint,
                    "referer": referer
                })
    
    return profile_pics


def download_image(url: str, output_path: Path, referer: str = None) -> bool:
    """Download an image from URL to output_path."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        output_path.write_bytes(response.content)
        return True
    except Exception as e:
        print(f"  Error downloading: {e}")
        return False


def get_har_files(path: Path) -> list[Path]:
    """Get list of HAR files from a path (file or directory)."""
    if path.is_file() and path.suffix.lower() == ".har":
        return [path]
    elif path.is_dir():
        return list(path.glob("*.har"))
    return []


def get_best_profile_pic(pics: list[dict]) -> dict | None:
    """
    From a list of profile pics, return the best one (largest/highest quality).
    Prefers 400x400 over 100x100 thumbnails.
    """
    if not pics:
        return None
    
    # Score by size preference (larger = better)
    def score(pic):
        url = pic["url"]
        if "400_400" in url or "800_800" in url:
            return 3
        elif "200_200" in url:
            return 2
        elif "100_100" in url:
            return 1
        return 2  # Default for unknown sizes
    
    return max(pics, key=score)


def load_classlist() -> list[dict]:
    """Load the classlist.json file."""
    classlist_path = DATA_DIR / "classlist.json"
    if classlist_path.exists():
        with open(classlist_path) as f:
            return json.load(f)
    return []


def save_classlist(classlist: list[dict]):
    """Save the classlist.json file."""
    classlist_path = DATA_DIR / "classlist.json"
    with open(classlist_path, "w") as f:
        json.dump(classlist, f, indent=2)


def find_person_in_classlist(classlist: list[dict], name_hint: str) -> dict | None:
    """Try to find a person in the classlist by name."""
    name_hint_lower = name_hint.lower().replace("-", " ").replace("_", " ")
    
    for person in classlist:
        full_name_lower = person.get("full_name", "").lower()
        # Check if the hint matches the full name
        if name_hint_lower in full_name_lower or full_name_lower in name_hint_lower:
            return person
        # Check individual name parts
        name_parts = full_name_lower.split()
        hint_parts = name_hint_lower.split()
        if any(part in name_parts for part in hint_parts):
            return person
    return None


def main():
    # Determine input path
    if len(sys.argv) >= 2:
        input_path = Path(sys.argv[1])
    else:
        input_path = DEFAULT_HAR_DIR
    
    # Check if path exists
    if not input_path.exists():
        if input_path == DEFAULT_HAR_DIR:
            print(f"Default HAR directory not found. Creating: {DEFAULT_HAR_DIR}")
            DEFAULT_HAR_DIR.mkdir(parents=True, exist_ok=True)
            print("\nHow to use:")
            print("  1. Open Chrome DevTools (F12)")
            print("  2. Go to Network tab, check 'Preserve log'")
            print("  3. Log into LinkedIn")
            print("  4. Visit a profile you want to capture")
            print("  5. Right-click in Network tab -> 'Save all as HAR with content'")
            print(f"  6. Save as the person's name: firstname-lastname.har")
            print(f"  7. Save to: {DEFAULT_HAR_DIR}")
            print("  8. Run this script again: python parse_linkedin_har.py")
            sys.exit(0)
        else:
            print(f"Error: Path not found: {input_path}")
            sys.exit(1)
    
    # Get HAR files
    har_files = get_har_files(input_path)
    
    if not har_files:
        print(f"No .har files found in: {input_path}")
        print("\nSave your HAR file(s) there and run again.")
        sys.exit(1)
    
    print(f"Found {len(har_files)} HAR file(s) to process")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load classlist for auto-matching
    classlist = load_classlist()
    classlist_updated = False
    
    results = []
    
    # Process each HAR file individually
    for har_file in har_files:
        har_name = har_file.stem  # filename without extension
        print(f"\n{'='*50}")
        print(f"Processing: {har_file.name}")
        
        pics = extract_profile_pics_from_har(str(har_file))
        print(f"  Found {len(pics)} profile picture(s)")
        
        if not pics:
            print(f"  No profile pictures found in {har_file.name}")
            continue
        
        # Get the best quality image
        best_pic = get_best_profile_pic(pics)
        if not best_pic:
            continue
        
        url = best_pic["url"]
        referer = best_pic.get("referer", "")
        
        # Use HAR filename as the image name
        filename = f"{har_name}.jpg"
        output_path = OUTPUT_DIR / filename
        
        # Skip if already exists
        if output_path.exists():
            print(f"  Skipping (already exists): {filename}")
            results.append({
                "name": har_name,
                "local_path": f"data/profile_images/{filename}",
                "original_url": url
            })
        else:
            print(f"  Downloading best quality image...")
            if download_image(url, output_path, referer):
                print(f"  Saved: {filename}")
                results.append({
                    "name": har_name,
                    "local_path": f"data/profile_images/{filename}",
                    "original_url": url
                })
            else:
                print(f"  Failed to download")
                continue
        
        # Try to auto-update classlist
        if classlist:
            person = find_person_in_classlist(classlist, har_name)
            if person:
                if not person.get("photo_path"):
                    person["photo_path"] = f"profile_images/{filename}"
                    classlist_updated = True
                    print(f"  Auto-matched to: {person.get('full_name')}")
                else:
                    print(f"  Already has photo: {person.get('full_name')}")
            else:
                print(f"  Could not auto-match '{har_name}' to classlist")
    
    # Save updated classlist
    if classlist_updated:
        save_classlist(classlist)
        print(f"\nUpdated classlist.json with new photo paths")
    
    # Save mapping file
    mapping_path = OUTPUT_DIR / "_image_mapping.json"
    with open(mapping_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"Processed {len(results)} profile(s)")
    print(f"Images saved to: {OUTPUT_DIR}")
    
    if classlist:
        # Show progress
        with_photos = sum(1 for p in classlist if p.get("photo_path"))
        print(f"Classlist progress: {with_photos}/{len(classlist)} have photos")


if __name__ == "__main__":
    main()

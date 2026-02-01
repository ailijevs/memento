#!/usr/bin/env python3
"""
Scrape LinkedIn profiles using Exa.ai API.

Exa.ai can retrieve web page contents including LinkedIn profiles.

Usage:
    # Set your API key
    export EXA_API_KEY=your_key_here
    
    # Run the scraper
    python scrape_linkedin_exa.py
    
    # Or scrape specific URLs
    python scrape_linkedin_exa.py --urls https://linkedin.com/in/person1

Requirements:
    pip install exa_py
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

try:
    from exa_py import Exa
except ImportError:
    print("Exa SDK not installed. Run:")
    print("  pip install exa_py")
    sys.exit(1)

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CLASSLIST_PATH = DATA_DIR / "classlist.json"
OUTPUT_PATH = DATA_DIR / "scraped_profiles_exa.json"


def get_exa_client() -> Exa:
    """Get Exa client with API key."""
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        print("EXA_API_KEY environment variable not set.")
        print("Get your API key from https://exa.ai and run:")
        print("  export EXA_API_KEY=your_key_here")
        sys.exit(1)
    return Exa(api_key)


def clean_text(text: str) -> str:
    """Remove markdown artifacts from text."""
    import re
    if not text:
        return text
    # Remove markdown headers
    text = re.sub(r'^#+\s*', '', text)
    # Remove markdown links [text]<web_link> or [text](url)
    text = re.sub(r'\[([^\]]+)\]<[^>]*>', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    # Remove other markdown
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # italic
    # Clean up extra whitespace
    text = ' '.join(text.split())
    return text.strip()


def parse_linkedin_content(content: str, url: str) -> dict:
    """Parse LinkedIn profile content into structured data."""
    import re
    
    profile = {
        "full_name": None,
        "headline": None,
        "location": None,
        "about": None,
        "experience": [],
        "education": [],
        "skills": [],
        "linkedin_url": url,
        "scraped_at": datetime.now().isoformat(),
        "raw_content": content[:3000] if content else None,  # Keep raw for debugging
    }
    
    lines = content.split('\n')
    
    # Usually the first non-empty line is the name
    for line in lines[:10]:
        line = clean_text(line.strip())
        if line and len(line) > 2 and len(line) < 100:
            if not profile["full_name"]:
                profile["full_name"] = line
            elif not profile["headline"] and len(line) > 10:
                profile["headline"] = line
                break
    
    # Track seen entries to avoid duplicates
    seen_experience = set()
    seen_education = set()
    
    # Look for common patterns
    for i, line in enumerate(lines):
        line_clean = clean_text(line.strip())
        
        # Experience patterns
        if any(word in line.lower() for word in ['experience', 'work history']):
            for j in range(i+1, min(i+30, len(lines))):
                exp_line = clean_text(lines[j].strip())
                if exp_line and ' at ' in exp_line.lower():
                    # Split on " at " case-insensitive
                    parts = re.split(r'\s+at\s+', exp_line, maxsplit=1, flags=re.IGNORECASE)
                    if len(parts) == 2:
                        title = parts[0].strip()
                        company = parts[1].strip()
                        # Skip noise entries
                        if len(title) > 3 and len(company) > 2 and not title.startswith("I'm") and not title.startswith("Self-"):
                            key = (title.lower(), company.lower())
                            if key not in seen_experience:
                                seen_experience.add(key)
                                profile["experience"].append({
                                    "title": title,
                                    "company": company,
                                })
        
        # Education patterns - look for degree info
        if 'degree' in line_clean.lower() or ("at" in line_clean.lower() and any(x in line_clean for x in ["University", "College", "Institute"])):
            # Extract school name
            match = re.search(r'at\s+\[?([^\]<]+?)(?:\]|<|\(|$)', line_clean, re.IGNORECASE)
            if match:
                school = clean_text(match.group(1))
                if school and school.lower() not in seen_education:
                    seen_education.add(school.lower())
                    # Try to extract degree
                    degree_match = re.search(r"(Bachelor'?s?|Master'?s?|PhD|BS|MS|BA|MA)[^,]*", line_clean, re.IGNORECASE)
                    degree = degree_match.group(0) if degree_match else None
                    profile["education"].append({
                        "school": school,
                        "degree": degree,
                    })
        
        # About/Summary - look for longer text blocks
        if 'about' in line.lower() and i + 1 < len(lines):
            about_text = clean_text(lines[i+1].strip())
            if len(about_text) > 50 and not about_text.startswith("###"):
                profile["about"] = about_text
    
    return profile


def scrape_profile_with_exa(exa: Exa, url: str) -> dict | None:
    """Scrape a LinkedIn profile using Exa API."""
    print(f"\nScraping: {url}")
    
    try:
        # Use Exa's get_contents to retrieve the page
        result = exa.get_contents(
            urls=[url],
            text=True,  # Get text content
        )
        
        if result.results and len(result.results) > 0:
            content = result.results[0].text
            
            if content:
                profile = parse_linkedin_content(content, url)
                
                if profile["full_name"]:
                    print(f"  Found: {profile['full_name']}")
                    if profile["headline"]:
                        print(f"  Headline: {profile['headline'][:50]}...")
                    return profile
                else:
                    print("  Could not parse profile data")
                    # Still return raw content for debugging
                    return {
                        "linkedin_url": url,
                        "raw_content": content[:2000],
                        "scraped_at": datetime.now().isoformat(),
                    }
            else:
                print("  No content returned")
                return None
        else:
            print("  No results from Exa")
            return None
            
    except Exception as e:
        print(f"  Error: {e}")
        return None


def search_linkedin_profiles(exa: Exa, names: list[str]) -> list[str]:
    """Search for LinkedIn profile URLs by name."""
    urls = []
    
    for name in names:
        print(f"Searching for: {name}")
        try:
            result = exa.search(
                f"{name} site:linkedin.com/in",
                num_results=1,
                use_autoprompt=False,
            )
            
            if result.results:
                url = result.results[0].url
                if "linkedin.com/in/" in url:
                    print(f"  Found: {url}")
                    urls.append(url)
                else:
                    print(f"  No LinkedIn profile found")
            else:
                print(f"  No results")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    return urls


def update_classlist(profiles: list[dict]) -> int:
    """Update classlist.json with scraped profile data."""
    if not CLASSLIST_PATH.exists():
        print("Classlist not found")
        return 0
    
    with open(CLASSLIST_PATH) as f:
        classlist = json.load(f)
    
    # Create lookup by LinkedIn URL
    scraped_by_url = {p["linkedin_url"]: p for p in profiles if p.get("linkedin_url")}
    
    updated = 0
    for person in classlist:
        url = person.get("linkedin_url")
        if url and url in scraped_by_url:
            scraped = scraped_by_url[url]
            
            # Update fields (don't overwrite existing non-null values unless scraped is better)
            if scraped.get("headline"):
                person["headline"] = scraped["headline"]
            
            # Clean and update experience
            if scraped.get("experience"):
                clean_exp = []
                for exp in scraped["experience"]:
                    # Filter out noise entries
                    title = exp.get("title", "")
                    if title and not title.startswith("I'm") and not title.startswith("Self-") and len(title) > 3:
                        clean_exp.append({
                            "title": exp.get("title"),
                            "company": exp.get("company", "").replace(" (Current)", ""),
                        })
                if clean_exp:
                    person["experience"] = clean_exp[:5]  # Keep top 5
            
            # Clean and update education
            if scraped.get("education"):
                clean_edu = []
                seen = set()
                for edu in scraped["education"]:
                    school = edu.get("school", "")
                    # Filter out noise
                    if school and len(school) < 100 and school.lower() not in seen:
                        if "University" in school or "College" in school or "Institute" in school:
                            seen.add(school.lower())
                            clean_edu.append({
                                "school": school,
                                "degree": edu.get("degree"),
                            })
                if clean_edu:
                    person["education"] = clean_edu[:3]  # Keep top 3
            
            if scraped.get("about"):
                person["about"] = scraped["about"]
            
            updated += 1
    
    # Save updated classlist
    with open(CLASSLIST_PATH, "w") as f:
        json.dump(classlist, f, indent=2)
    
    return updated


def main():
    parser = argparse.ArgumentParser(description="Scrape LinkedIn profiles using Exa.ai")
    parser.add_argument("--urls", nargs="*", help="Specific LinkedIn URLs to scrape")
    parser.add_argument("--search", nargs="*", help="Search for profiles by name")
    parser.add_argument("--update-classlist", action="store_true", help="Update classlist.json with scraped data")
    args = parser.parse_args()
    
    exa = get_exa_client()
    print("Exa client initialized")
    
    urls = []
    
    # Search mode
    if args.search:
        urls = search_linkedin_profiles(exa, args.search)
    # Specific URLs mode
    elif args.urls:
        urls = args.urls
    # Default: use classlist
    else:
        if CLASSLIST_PATH.exists():
            with open(CLASSLIST_PATH) as f:
                classlist = json.load(f)
            urls = [p.get("linkedin_url") for p in classlist if p.get("linkedin_url")]
            print(f"Found {len(urls)} LinkedIn URLs in classlist")
        
        if not urls:
            # Try to search by name
            print("No URLs found, searching by name...")
            names = [p.get("full_name") for p in classlist if p.get("full_name")][:5]
            urls = search_linkedin_profiles(exa, names)
    
    if not urls:
        print("No URLs to scrape.")
        return
    
    # Scrape profiles
    profiles = []
    for url in urls:
        profile = scrape_profile_with_exa(exa, url)
        if profile:
            profiles.append(profile)
    
    # Save results
    with open(OUTPUT_PATH, "w") as f:
        json.dump(profiles, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"Scraped {len(profiles)} profiles")
    print(f"Saved to: {OUTPUT_PATH}")
    
    # Show summary
    for p in profiles:
        if p.get("full_name"):
            print(f"  - {p['full_name']}: {p.get('headline', 'No headline')[:40]}...")
    
    # Update classlist if requested
    if args.update_classlist:
        updated = update_classlist(profiles)
        print(f"\nUpdated {updated} profiles in classlist.json")


if __name__ == "__main__":
    main()

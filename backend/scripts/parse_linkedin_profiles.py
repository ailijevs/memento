#!/usr/bin/env python3
"""
Parse LinkedIn HAR files to extract full profile data.

This extracts structured profile information from LinkedIn API responses
captured in HAR files, including:
- Name, headline, location
- Current company and position
- Education (schools, degrees, years)
- Skills
- About/bio section

Usage:
    python parse_linkedin_profiles.py [path_to_har_or_directory]
    
    # Default: processes all HAR files in backend/data/har_files/
    python parse_linkedin_profiles.py
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_HAR_DIR = DATA_DIR / "har_files"
CLASSLIST_PATH = DATA_DIR / "classlist.json"
OUTPUT_PATH = DATA_DIR / "parsed_profiles.json"


def extract_json_from_har_entry(entry: dict) -> dict | None:
    """Try to extract JSON response from a HAR entry."""
    try:
        response = entry.get("response", {})
        content = response.get("content", {})
        text = content.get("text", "")
        
        if not text:
            return None
        
        # Try to parse as JSON
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def extract_profile_from_voyager_api(data: dict) -> dict | None:
    """
    Extract profile data from LinkedIn Voyager API response.
    LinkedIn's internal API returns data in a specific format.
    """
    if not isinstance(data, dict):
        return None
    
    # Look for profile data in various LinkedIn API response formats
    included = data.get("included", [])
    
    profile_data = {
        "full_name": None,
        "headline": None,
        "location": None,
        "company": None,
        "position": None,
        "about": None,
        "education": [],
        "experience": [],
        "skills": [],
        "linkedin_username": None,
    }
    
    for item in included:
        if not isinstance(item, dict):
            continue
        
        item_type = item.get("$type", "")
        
        # Profile basic info
        if "Profile" in item_type or item.get("firstName"):
            if item.get("firstName") and item.get("lastName"):
                profile_data["full_name"] = f"{item['firstName']} {item['lastName']}"
            if item.get("headline"):
                profile_data["headline"] = item["headline"]
            if item.get("locationName"):
                profile_data["location"] = item["locationName"]
            if item.get("summary"):
                profile_data["about"] = item["summary"]
            if item.get("publicIdentifier"):
                profile_data["linkedin_username"] = item["publicIdentifier"]
        
        # Education
        if "Education" in item_type or (item.get("schoolName") and item.get("degreeName")):
            edu = {
                "school": item.get("schoolName"),
                "degree": item.get("degreeName"),
                "field": item.get("fieldOfStudy"),
                "start_year": None,
                "end_year": None,
            }
            
            # Extract years from timePeriod
            time_period = item.get("timePeriod", {})
            if time_period:
                start = time_period.get("startDate", {})
                end = time_period.get("endDate", {})
                edu["start_year"] = start.get("year")
                edu["end_year"] = end.get("year")
            
            if edu["school"]:
                profile_data["education"].append(edu)
        
        # Experience/Position
        if "Position" in item_type or (item.get("companyName") and item.get("title")):
            exp = {
                "company": item.get("companyName"),
                "title": item.get("title"),
                "start_year": None,
                "end_year": None,
                "current": False,
            }
            
            time_period = item.get("timePeriod", {})
            if time_period:
                start = time_period.get("startDate", {})
                end = time_period.get("endDate", {})
                exp["start_year"] = start.get("year")
                exp["end_year"] = end.get("year")
                exp["current"] = end.get("year") is None
            
            if exp["company"]:
                profile_data["experience"].append(exp)
        
        # Skills
        if "Skill" in item_type or item.get("name") and "skill" in str(item.get("$type", "")).lower():
            skill_name = item.get("name")
            if skill_name and skill_name not in profile_data["skills"]:
                profile_data["skills"].append(skill_name)
    
    # Determine current company/position from most recent experience
    if profile_data["experience"]:
        current_jobs = [e for e in profile_data["experience"] if e.get("current")]
        if current_jobs:
            profile_data["company"] = current_jobs[0]["company"]
            profile_data["position"] = current_jobs[0]["title"]
        else:
            # Use most recent
            profile_data["company"] = profile_data["experience"][0]["company"]
            profile_data["position"] = profile_data["experience"][0]["title"]
    
    # Check if we found meaningful data
    if profile_data["full_name"] or profile_data["headline"]:
        return profile_data
    
    return None


def extract_embedded_json_from_html(html: str) -> list[dict]:
    """Extract embedded JSON data from LinkedIn HTML page."""
    json_objects = []
    
    # LinkedIn embeds data in various script tags
    # Look for patterns like: {"included":[...]}
    
    # Pattern 1: Look for data in script tags with type="application/ld+json"
    ld_json_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    for match in re.finditer(ld_json_pattern, html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            json_objects.append(data)
        except json.JSONDecodeError:
            pass
    
    # Pattern 2: Look for embedded Voyager data (LinkedIn's format)
    # Usually in format: "included":[{...}]
    included_pattern = r'"included"\s*:\s*(\[\{.*?\}\])'
    
    # More robust: find large JSON objects that contain profile data
    # Look for the data island pattern
    data_pattern = r'<code[^>]*id="[^"]*"[^>]*><!--(.+?)--></code>'
    for match in re.finditer(data_pattern, html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and "included" in data:
                json_objects.append(data)
        except json.JSONDecodeError:
            pass
    
    # Pattern 3: Look for voyagerIdentityDashProfiles data
    # This is often in a script tag or embedded
    profile_patterns = [
        r'\*voyagerIdentityDashProfiles[^}]+\}',
        r'"firstName"\s*:\s*"([^"]+)".*?"lastName"\s*:\s*"([^"]+)"',
    ]
    
    # Try to find and parse the main data blob
    # LinkedIn often has: window.__li_init_data__ = {...}
    init_data_pattern = r'window\.__li_init_data__\s*=\s*(\{.+?\});?\s*</script>'
    for match in re.finditer(init_data_pattern, html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            json_objects.append(data)
        except json.JSONDecodeError:
            pass
    
    return json_objects


def extract_profile_from_html(html_content: str) -> dict | None:
    """Extract profile data directly from HTML using regex patterns."""
    import html
    
    # Decode HTML entities first
    html_text = html.unescape(html_content)
    
    profile_data = {
        "full_name": None,
        "headline": None,
        "location": None,
        "company": None,
        "position": None,
        "about": None,
        "education": [],
        "experience": [],
        "skills": [],
        "linkedin_username": None,
    }
    
    # Extract from JSON-LD (structured data for SEO)
    ld_json_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    for match in re.finditer(ld_json_pattern, html_text, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                if data.get("@type") == "Person":
                    profile_data["full_name"] = data.get("name")
                    if data.get("jobTitle"):
                        profile_data["headline"] = data.get("jobTitle")[0] if isinstance(data.get("jobTitle"), list) else data.get("jobTitle")
                    if data.get("worksFor"):
                        works_for = data.get("worksFor")
                        if isinstance(works_for, list) and works_for:
                            profile_data["company"] = works_for[0].get("name")
                        elif isinstance(works_for, dict):
                            profile_data["company"] = works_for.get("name")
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Extract firstName and lastName from embedded data
    first_name_match = re.search(r'"firstName"\s*:\s*"([^"]+)"', html_text)
    last_name_match = re.search(r'"lastName"\s*:\s*"([^"]+)"', html_text)
    if first_name_match and last_name_match:
        profile_data["full_name"] = f"{first_name_match.group(1)} {last_name_match.group(1)}"
    
    # Extract headline - look for the one associated with publicIdentifier
    # Pattern: near publicIdentifier we often find the real headline
    headline_pattern = r'Purdue[^"]*\|[^"]*|Student[^"]*at[^"]*|Software[^"]*Engineer[^"]*|[A-Z][a-z]+\s+at\s+[A-Z][^"]{5,80}'
    headline_context = re.search(r'"headline"\s*:\s*"([^"]{5,200})"', html_text)
    if headline_context:
        headline_text = headline_context.group(1)
        # Filter out internal LinkedIn types
        if not headline_text.startswith("com.linkedin"):
            profile_data["headline"] = headline_text
    
    # Try to get headline from publicIdentifier context
    pub_id_match = re.search(r'"publicIdentifier"\s*:\s*"([^"]+)"', html_text)
    if pub_id_match:
        profile_data["linkedin_username"] = pub_id_match.group(1)
        # Look for headline near publicIdentifier
        context_start = max(0, pub_id_match.start() - 500)
        context = html_text[context_start:pub_id_match.start()]
        nearby_headline = re.search(r'"headline"\s*:\s*"([^"]{5,200})"', context)
        if nearby_headline:
            hl = nearby_headline.group(1)
            if not hl.startswith("com.linkedin"):
                profile_data["headline"] = hl
    
    # Extract from title tag as fallback
    title_match = re.search(r'<title>([^<]+)</title>', html_text)
    if title_match and not profile_data["full_name"]:
        title = title_match.group(1)
        # LinkedIn titles are usually "Name - Title | LinkedIn"
        if " | LinkedIn" in title:
            name_part = title.split(" | LinkedIn")[0]
            if " - " in name_part:
                profile_data["full_name"] = name_part.split(" - ")[0].strip()
    
    # Extract LinkedIn username from URL in the data
    if not profile_data["linkedin_username"]:
        username_match = re.search(r'linkedin\.com/in/([a-zA-Z0-9_-]+)', html_text)
        if username_match:
            profile_data["linkedin_username"] = username_match.group(1)
    
    # Extract location
    location_match = re.search(r'"locationName"\s*:\s*"([^"]+)"', html_text)
    if location_match:
        profile_data["location"] = location_match.group(1)
    
    # Extract summary/about
    summary_match = re.search(r'"summary"\s*:\s*"([^"]{10,})"', html_text)
    if summary_match:
        try:
            profile_data["about"] = summary_match.group(1).encode().decode('unicode_escape')
        except:
            profile_data["about"] = summary_match.group(1)
    
    # Extract education entries
    edu_pattern = r'"schoolName"\s*:\s*"([^"]+)"'
    schools_found = set()
    for match in re.finditer(edu_pattern, html_text):
        school = match.group(1)
        if school not in schools_found and len(school) > 3:
            schools_found.add(school)
            edu = {"school": school, "degree": None}
            profile_data["education"].append(edu)
    
    # Extract experience/positions
    exp_pattern = r'"companyName"\s*:\s*"([^"]+)"'
    companies_found = set()
    for match in re.finditer(exp_pattern, html_text):
        company = match.group(1)
        if company not in companies_found and len(company) > 2:
            companies_found.add(company)
            exp = {"company": company, "title": None}
            profile_data["experience"].append(exp)
            # Set current company from first experience
            if not profile_data["company"]:
                profile_data["company"] = company
    
    # Check if we found meaningful data
    if profile_data["full_name"]:
        return profile_data
    
    return None


def extract_target_profile_from_html(html_content: str, target_username: str = None) -> dict | None:
    """
    Extract the VISITED profile data (not the logged-in user).
    
    Args:
        html_content: The HTML content from LinkedIn
        target_username: The LinkedIn username from the URL (e.g., "noddie-jm")
    """
    import html as html_module
    
    # Decode HTML entities
    html_text = html_module.unescape(html_content)
    
    profile_data = {
        "full_name": None,
        "headline": None,
        "location": None,
        "company": None,
        "position": None,
        "about": None,
        "education": [],
        "experience": [],
        "skills": [],
        "linkedin_username": target_username,
    }
    
    # Strategy: Find the profile block for the target username
    # LinkedIn data includes publicIdentifier which matches the URL username
    
    if target_username:
        # Find the context around the target username's publicIdentifier
        # Use a simpler pattern that's more forgiving
        escaped_username = re.escape(target_username)
        pattern = rf'publicIdentifier["\s:]+{escaped_username}'
        match = re.search(pattern, html_text, re.IGNORECASE)
        
        if match:
            # Get a window around this match to find related data
            start = max(0, match.start() - 2000)
            end = min(len(html_text), match.end() + 2000)
            context = html_text[start:end]
            
            # Extract firstName and lastName from this context
            fn_match = re.search(r'"firstName"\s*:\s*"([^"]+)"', context)
            ln_match = re.search(r'"lastName"\s*:\s*"([^"]+)"', context)
            
            if fn_match and ln_match:
                profile_data["full_name"] = f"{fn_match.group(1)} {ln_match.group(1)}"
            
            # Extract headline from context
            hl_match = re.search(r'"headline"\s*:\s*"([^"]{5,200})"', context)
            if hl_match:
                hl = hl_match.group(1)
                if not hl.startswith("com.linkedin"):
                    profile_data["headline"] = hl
            
            # Extract location
            loc_match = re.search(r'"locationName"\s*:\s*"([^"]+)"', context)
            if loc_match:
                profile_data["location"] = loc_match.group(1)
    
    # If we didn't find via username, try to extract from the full document
    # but look for the profile that's NOT the logged-in user
    if not profile_data["full_name"]:
        # Find all firstName/lastName pairs with their publicIdentifier
        profile_blocks = re.finditer(
            r'"firstName"\s*:\s*"([^"]+)"[^}]{0,200}"lastName"\s*:\s*"([^"]+)"[^}]{0,500}"publicIdentifier"\s*:\s*"([^"]+)"',
            html_text
        )
        
        for block in profile_blocks:
            first, last, username = block.groups()
            # Skip if this is likely the logged-in user (check if username matches target)
            if target_username and username == target_username:
                profile_data["full_name"] = f"{first} {last}"
                profile_data["linkedin_username"] = username
                break
            elif not target_username:
                # Take the first one that's not obviously a schema type
                if not first.startswith("com.linkedin"):
                    profile_data["full_name"] = f"{first} {last}"
                    profile_data["linkedin_username"] = username
                    break
    
    # Extract education (school names)
    schools = set()
    for match in re.finditer(r'"schoolName"\s*:\s*"([^"]+)"', html_text):
        school = match.group(1)
        if len(school) > 3 and not school.startswith("com.linkedin"):
            schools.add(school)
    profile_data["education"] = [{"school": s} for s in list(schools)[:5]]
    
    # Extract companies
    companies = set()
    for match in re.finditer(r'"companyName"\s*:\s*"([^"]+)"', html_text):
        company = match.group(1)
        if len(company) > 2 and not company.startswith("com.linkedin"):
            companies.add(company)
    
    if companies:
        profile_data["experience"] = [{"company": c} for c in list(companies)[:5]]
        profile_data["company"] = list(companies)[0]
    
    if profile_data["full_name"]:
        return profile_data
    
    return None


def extract_linkedin_url_from_har(har_path: Path) -> str | None:
    """Extract the LinkedIn profile URL from a HAR file."""
    with open(har_path, "r", encoding="utf-8") as f:
        har_data = json.load(f)
    
    entries = har_data.get("log", {}).get("entries", [])
    
    # Find the first linkedin.com/in/ URL
    for entry in entries:
        url = entry.get("request", {}).get("url", "")
        if "linkedin.com/in/" in url:
            # Extract clean URL
            match = re.search(r'(https?://[^/]*linkedin\.com/in/[a-zA-Z0-9_-]+)', url)
            if match:
                return match.group(1)
    return None


def parse_har_for_profiles(har_path: Path) -> list[dict]:
    """Parse a HAR file and extract the visited LinkedIn profile data."""
    with open(har_path, "r", encoding="utf-8") as f:
        har_data = json.load(f)
    
    entries = har_data.get("log", {}).get("entries", [])
    profiles = []
    seen_names = set()
    
    # Use filename as hint for target name
    filename_name = har_path.stem  # e.g., "Nathan Galinowski"
    
    # First, find the target profile URL to get the username
    target_username = None
    linkedin_url = None
    for entry in entries:
        url = entry.get("request", {}).get("url", "")
        if "linkedin.com/in/" in url:
            # Extract username from URL like linkedin.com/in/noddie-jm/
            match = re.search(r'linkedin\.com/in/([a-zA-Z0-9_-]+)', url)
            if match:
                target_username = match.group(1)
                linkedin_url = f"https://linkedin.com/in/{target_username}"
                break
    
    for entry in entries:
        request = entry.get("request", {})
        url = request.get("url", "")
        
        # Look for LinkedIn profile pages
        if "linkedin.com" not in url:
            continue
        
        # Get response content
        content = entry.get("response", {}).get("content", {}).get("text", "")
        if not content:
            continue
        
        # Profile page HTML with embedded data
        if "/in/" in url and len(content) > 10000:
            profile = extract_target_profile_from_html(content, target_username)
            if profile and profile.get("full_name"):
                name = profile["full_name"]
                # Skip if we got the logged-in user instead of the target
                if "ilijevski" in name.lower() or "aleksandar" in name.lower():
                    # Use filename as fallback for name, but keep URL
                    profile = {
                        "full_name": filename_name,
                        "linkedin_url": linkedin_url,
                        "linkedin_username": target_username,
                    }
                else:
                    profile["linkedin_url"] = linkedin_url
                    profile["linkedin_username"] = target_username
                
                if name not in seen_names:
                    seen_names.add(name)
                    profiles.append(profile)
                    break  # Found the main profile, stop
    
    # If no profile found but we have a URL, create minimal profile from filename
    if not profiles and linkedin_url:
        profiles.append({
            "full_name": filename_name,
            "linkedin_url": linkedin_url,
            "linkedin_username": target_username,
        })
    
    return profiles


def get_har_files(path: Path) -> list[Path]:
    """Get list of HAR files from a path (file or directory)."""
    if path.is_file() and path.suffix.lower() == ".har":
        return [path]
    elif path.is_dir():
        return list(path.glob("*.har"))
    return []


def merge_with_classlist(profiles: list[dict], classlist: list[dict]) -> list[dict]:
    """Merge parsed profile data with existing classlist."""
    # Create lookup by name (normalized)
    profile_lookup = {}
    for p in profiles:
        name = p.get("full_name", "").lower().strip()
        if name and "ilijevski" not in name and "aleksandar" not in name:  # Skip logged-in user
            profile_lookup[name] = p
            # Also add by first name + last name parts for fuzzy matching
            parts = name.split()
            if len(parts) >= 2:
                # Add by last name
                profile_lookup[parts[-1]] = p
    
    updated = 0
    for person in classlist:
        name = person.get("full_name", "").lower().strip()
        
        # Try exact match first
        parsed = profile_lookup.get(name)
        
        # Try fuzzy match by last name
        if not parsed:
            parts = name.split()
            if len(parts) >= 2:
                parsed = profile_lookup.get(parts[-1])
        
        if parsed:
            # Update fields if not already set
            if parsed.get("headline") and parsed["headline"] != "string":
                if not person.get("headline"):
                    person["headline"] = parsed["headline"]
                    updated += 1
            
            # Skip "string" values for company/school
            if parsed.get("company") and parsed["company"] != "string":
                if not person.get("company"):
                    person["company"] = parsed["company"]
            
            if parsed.get("about") and parsed["about"] != "string":
                if not person.get("bio"):
                    person["bio"] = parsed["about"]
            
            # Add LinkedIn URL
            if parsed.get("linkedin_username"):
                if not person.get("linkedin_url"):
                    person["linkedin_url"] = f"https://linkedin.com/in/{parsed['linkedin_username']}"
                    updated += 1
    
    print(f"Updated {updated} fields across profiles")
    return classlist


def main():
    # Determine input path
    if len(sys.argv) >= 2:
        input_path = Path(sys.argv[1])
    else:
        input_path = DEFAULT_HAR_DIR
    
    if not input_path.exists():
        print(f"Path not found: {input_path}")
        print(f"Place HAR files in {DEFAULT_HAR_DIR} and run again.")
        sys.exit(1)
    
    # Get HAR files
    har_files = get_har_files(input_path)
    
    if not har_files:
        print(f"No .har files found in: {input_path}")
        sys.exit(1)
    
    print(f"Found {len(har_files)} HAR file(s) to process")
    print("=" * 50)
    
    # Parse all HAR files
    all_profiles = []
    
    for har_file in har_files:
        print(f"\nParsing: {har_file.name}")
        profiles = parse_har_for_profiles(har_file)
        
        for p in profiles:
            print(f"  Found: {p.get('full_name', 'Unknown')}")
            if p.get("headline"):
                print(f"    Headline: {p['headline'][:50]}...")
            if p.get("company"):
                print(f"    Company: {p['company']}")
            if p.get("education"):
                print(f"    Education: {len(p['education'])} entries")
            if p.get("skills"):
                print(f"    Skills: {len(p['skills'])} skills")
        
        all_profiles.extend(profiles)
    
    # Deduplicate by name
    seen = set()
    unique_profiles = []
    for p in all_profiles:
        name = p.get("full_name", "").lower()
        if name and name not in seen:
            seen.add(name)
            unique_profiles.append(p)
    
    print(f"\n{'=' * 50}")
    print(f"Total unique profiles parsed: {len(unique_profiles)}")
    
    # Save parsed profiles
    with open(OUTPUT_PATH, "w") as f:
        json.dump(unique_profiles, f, indent=2)
    print(f"Saved to: {OUTPUT_PATH}")
    
    # Optionally merge with classlist
    if CLASSLIST_PATH.exists():
        print(f"\nMerging with classlist...")
        with open(CLASSLIST_PATH) as f:
            classlist = json.load(f)
        
        updated_classlist = merge_with_classlist(unique_profiles, classlist)
        
        with open(CLASSLIST_PATH, "w") as f:
            json.dump(updated_classlist, f, indent=2)
        print(f"Updated: {CLASSLIST_PATH}")


if __name__ == "__main__":
    main()

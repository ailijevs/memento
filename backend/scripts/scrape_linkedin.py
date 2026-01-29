#!/usr/bin/env python3
"""
Scrape LinkedIn profiles using Playwright.

This script uses your existing browser session to scrape LinkedIn profiles,
extracting full profile data including experience, education, and skills.

Usage:
    # First time: Run with --login to authenticate
    playwright install chromium
    python scrape_linkedin.py --login
    
    # After logging in, scrape profiles:
    python scrape_linkedin.py
    
    # Scrape specific profiles:
    python scrape_linkedin.py --urls https://linkedin.com/in/person1 https://linkedin.com/in/person2

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("Playwright not installed. Run:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CLASSLIST_PATH = DATA_DIR / "classlist.json"
OUTPUT_PATH = DATA_DIR / "scraped_profiles.json"
COOKIES_PATH = DATA_DIR / "linkedin_cookies.json"


async def save_cookies(page: Page):
    """Save browser cookies for future sessions."""
    cookies = await page.context.cookies()
    with open(COOKIES_PATH, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"Cookies saved to {COOKIES_PATH}")


async def load_cookies(context):
    """Load previously saved cookies."""
    if COOKIES_PATH.exists():
        with open(COOKIES_PATH) as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print("Loaded saved cookies")
        return True
    return False


async def login_to_linkedin(page: Page):
    """Interactive login to LinkedIn."""
    print("\n" + "="*50)
    print("LinkedIn Login")
    print("="*50)
    print("A browser window will open.")
    print("Please log in to LinkedIn manually.")
    print("After logging in, press Enter here to continue...")
    print("="*50 + "\n")
    
    await page.goto("https://www.linkedin.com/login")
    
    # Wait for user to log in
    input("Press Enter after you've logged in to LinkedIn...")
    
    # Verify login
    await page.goto("https://www.linkedin.com/feed/")
    await page.wait_for_timeout(2000)
    
    if "feed" in page.url:
        print("Login successful!")
        await save_cookies(page)
        return True
    else:
        print("Login may have failed. Please try again.")
        return False


async def scroll_and_expand(page: Page):
    """Scroll through the profile and expand all sections."""
    # Scroll down slowly to trigger lazy loading
    for _ in range(5):
        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(500)
    
    # Scroll back to top
    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(500)
    
    # Click "Show all" buttons for experience, education, etc.
    show_all_buttons = [
        'button:has-text("Show all experience")',
        'button:has-text("Show all education")',
        'button:has-text("Show all skills")',
        'button:has-text("see more")',
        '[aria-label*="expand"]',
    ]
    
    for selector in show_all_buttons:
        try:
            buttons = await page.query_selector_all(selector)
            for btn in buttons[:3]:  # Limit to avoid infinite loops
                await btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass


async def extract_profile_data(page: Page) -> dict:
    """Extract profile data from the current page."""
    profile = {
        "full_name": None,
        "headline": None,
        "location": None,
        "about": None,
        "experience": [],
        "education": [],
        "skills": [],
        "linkedin_url": page.url,
        "scraped_at": datetime.now().isoformat(),
    }
    
    try:
        # Name
        name_el = await page.query_selector('h1')
        if name_el:
            profile["full_name"] = await name_el.inner_text()
        
        # Headline
        headline_el = await page.query_selector('.text-body-medium.break-words')
        if headline_el:
            profile["headline"] = await headline_el.inner_text()
        
        # Location
        location_el = await page.query_selector('.text-body-small.inline.t-black--light.break-words')
        if location_el:
            profile["location"] = await location_el.inner_text()
        
        # About section
        about_el = await page.query_selector('#about ~ .display-flex .inline-show-more-text')
        if about_el:
            profile["about"] = await about_el.inner_text()
        
        # Experience
        exp_section = await page.query_selector('#experience')
        if exp_section:
            exp_items = await page.query_selector_all('#experience ~ .pvs-list__outer-container li.artdeco-list__item')
            for item in exp_items[:10]:
                try:
                    title_el = await item.query_selector('.t-bold span[aria-hidden="true"]')
                    company_el = await item.query_selector('.t-14.t-normal span[aria-hidden="true"]')
                    dates_el = await item.query_selector('.t-14.t-normal.t-black--light span[aria-hidden="true"]')
                    
                    exp = {
                        "title": await title_el.inner_text() if title_el else None,
                        "company": await company_el.inner_text() if company_el else None,
                        "dates": await dates_el.inner_text() if dates_el else None,
                    }
                    if exp["title"] or exp["company"]:
                        profile["experience"].append(exp)
                except:
                    pass
        
        # Education
        edu_section = await page.query_selector('#education')
        if edu_section:
            edu_items = await page.query_selector_all('#education ~ .pvs-list__outer-container li.artdeco-list__item')
            for item in edu_items[:5]:
                try:
                    school_el = await item.query_selector('.t-bold span[aria-hidden="true"]')
                    degree_el = await item.query_selector('.t-14.t-normal span[aria-hidden="true"]')
                    dates_el = await item.query_selector('.t-14.t-normal.t-black--light span[aria-hidden="true"]')
                    
                    edu = {
                        "school": await school_el.inner_text() if school_el else None,
                        "degree": await degree_el.inner_text() if degree_el else None,
                        "dates": await dates_el.inner_text() if dates_el else None,
                    }
                    if edu["school"]:
                        profile["education"].append(edu)
                except:
                    pass
        
        # Skills
        skills_section = await page.query_selector('#skills')
        if skills_section:
            skill_items = await page.query_selector_all('#skills ~ .pvs-list__outer-container li.artdeco-list__item .t-bold span[aria-hidden="true"]')
            for item in skill_items[:20]:
                try:
                    skill = await item.inner_text()
                    if skill and skill not in profile["skills"]:
                        profile["skills"].append(skill)
                except:
                    pass
        
    except Exception as e:
        print(f"  Error extracting data: {e}")
    
    return profile


async def scrape_profile(page: Page, url: str) -> dict | None:
    """Scrape a single LinkedIn profile."""
    print(f"\nScraping: {url}")
    
    try:
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Check if we're on a profile page
        if "/in/" not in page.url:
            print("  Not a profile page, skipping")
            return None
        
        # Scroll and expand sections
        await scroll_and_expand(page)
        
        # Extract data
        profile = await extract_profile_data(page)
        
        if profile["full_name"]:
            print(f"  Found: {profile['full_name']}")
            if profile["headline"]:
                print(f"  Headline: {profile['headline'][:50]}...")
            print(f"  Experience: {len(profile['experience'])} entries")
            print(f"  Education: {len(profile['education'])} entries")
            print(f"  Skills: {len(profile['skills'])} skills")
            return profile
        else:
            print("  Could not extract profile data")
            return None
            
    except Exception as e:
        print(f"  Error: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(description="Scrape LinkedIn profiles")
    parser.add_argument("--login", action="store_true", help="Log in to LinkedIn interactively")
    parser.add_argument("--urls", nargs="*", help="Specific LinkedIn URLs to scrape")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Login mode
        if args.login:
            await login_to_linkedin(page)
            await browser.close()
            return
        
        # Load cookies
        if not await load_cookies(context):
            print("No saved session found. Run with --login first:")
            print("  python scrape_linkedin.py --login")
            await browser.close()
            return
        
        # Verify session
        await page.goto("https://www.linkedin.com/feed/")
        await page.wait_for_timeout(2000)
        
        if "login" in page.url:
            print("Session expired. Please run with --login again.")
            await browser.close()
            return
        
        print("Session valid, starting scrape...")
        
        # Get URLs to scrape
        urls = []
        if args.urls:
            urls = args.urls
        else:
            # Get from classlist
            if CLASSLIST_PATH.exists():
                with open(CLASSLIST_PATH) as f:
                    classlist = json.load(f)
                urls = [p.get("linkedin_url") for p in classlist if p.get("linkedin_url")]
                print(f"Found {len(urls)} LinkedIn URLs in classlist")
        
        if not urls:
            print("No URLs to scrape. Provide URLs or ensure classlist.json has linkedin_url fields.")
            await browser.close()
            return
        
        # Scrape profiles
        profiles = []
        for url in urls:
            profile = await scrape_profile(page, url)
            if profile:
                profiles.append(profile)
            
            # Rate limiting - be nice to LinkedIn
            await page.wait_for_timeout(3000)
        
        # Save results
        with open(OUTPUT_PATH, "w") as f:
            json.dump(profiles, f, indent=2)
        print(f"\n{'='*50}")
        print(f"Scraped {len(profiles)} profiles")
        print(f"Saved to: {OUTPUT_PATH}")
        
        # Merge with classlist
        if CLASSLIST_PATH.exists() and profiles:
            print("\nMerging with classlist...")
            with open(CLASSLIST_PATH) as f:
                classlist = json.load(f)
            
            # Create lookup by linkedin_url
            profile_lookup = {p["linkedin_url"]: p for p in profiles}
            
            updated = 0
            for person in classlist:
                url = person.get("linkedin_url")
                if url and url in profile_lookup:
                    scraped = profile_lookup[url]
                    
                    if scraped.get("headline") and not person.get("headline"):
                        person["headline"] = scraped["headline"]
                        updated += 1
                    
                    if scraped.get("about") and not person.get("bio"):
                        person["bio"] = scraped["about"]
                    
                    if scraped.get("experience"):
                        person["experience"] = scraped["experience"]
                        if scraped["experience"]:
                            person["company"] = scraped["experience"][0].get("company")
                    
                    if scraped.get("education"):
                        person["education"] = scraped["education"]
                    
                    if scraped.get("skills"):
                        person["skills"] = scraped["skills"]
                    
                    if scraped.get("location") and not person.get("location"):
                        person["location"] = scraped["location"]
            
            with open(CLASSLIST_PATH, "w") as f:
                json.dump(classlist, f, indent=2)
            print(f"Updated {updated} profiles in classlist.json")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

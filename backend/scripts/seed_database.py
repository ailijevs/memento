#!/usr/bin/env python3
"""
Seed the Supabase database with test data from classlist.json.

This script:
1. Creates test users in Supabase Auth
2. Creates profiles for those users
3. Uploads profile photos to Supabase Storage
4. Creates a test event
5. Adds all users as event members with consent

Usage:
    cd backend
    python scripts/seed_database.py

Requirements:
    - .env file with Supabase credentials
    - classlist.json with user data
    - profile_images/ with photos
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client
from app.config import get_settings

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CLASSLIST_PATH = DATA_DIR / "classlist.json"
IMAGES_DIR = DATA_DIR / "profile_images"

# Storage bucket name
STORAGE_BUCKET = "profile-photos"


def get_admin_client() -> Client:
    """Get Supabase client with service role key (bypasses RLS)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def load_classlist() -> list[dict]:
    """Load the classlist.json file."""
    with open(CLASSLIST_PATH) as f:
        return json.load(f)


def ensure_storage_bucket(client: Client):
    """Create the storage bucket if it doesn't exist."""
    try:
        # Try to get bucket info
        client.storage.get_bucket(STORAGE_BUCKET)
        print(f"Storage bucket '{STORAGE_BUCKET}' exists")
    except Exception:
        # Create bucket
        try:
            client.storage.create_bucket(
                STORAGE_BUCKET,
                options={"public": True}  # Public so profile pics are accessible
            )
            print(f"Created storage bucket '{STORAGE_BUCKET}'")
        except Exception as e:
            print(f"Note: Could not create bucket (may already exist): {e}")


def create_test_user(client: Client, email: str, full_name: str) -> str | None:
    """
    Create a test user in Supabase Auth.
    Returns the user_id or None if failed.
    """
    try:
        # Generate a random password for test users
        password = f"TestPass123!{uuid.uuid4().hex[:8]}"
        
        response = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,  # Auto-confirm email for test users
            "user_metadata": {
                "full_name": full_name
            }
        })
        
        if response.user:
            return response.user.id
        return None
    except Exception as e:
        # User might already exist
        if "already been registered" in str(e).lower() or "already exists" in str(e).lower():
            # Try to get existing user
            try:
                users = client.auth.admin.list_users()
                for user in users:
                    if user.email == email:
                        return user.id
            except Exception:
                pass
        print(f"  Error creating user {email}: {e}")
        return None


def upload_photo(client: Client, local_path: Path, storage_path: str) -> str | None:
    """
    Upload a photo to Supabase Storage.
    Returns the public URL or None if failed.
    """
    try:
        with open(local_path, "rb") as f:
            file_data = f.read()
        
        # Upload to storage
        client.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            file_data,
            {"content-type": "image/jpeg", "upsert": "true"}
        )
        
        # Get public URL
        public_url = client.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        return public_url
    except Exception as e:
        print(f"  Error uploading {local_path}: {e}")
        return None


def create_profile(client: Client, user_id: str, person: dict, photo_url: str | None) -> bool:
    """Create a profile for a user."""
    try:
        profile_data = {
            "user_id": user_id,
            "full_name": person["full_name"],
            "headline": person.get("role", "Student"),
            "linkedin_url": person.get("linkedin_url"),
            "photo_path": photo_url,
            "major": "Electrical and Computer Engineering",  # Default for ECE class
        }
        
        client.table("profiles").upsert(profile_data).execute()
        return True
    except Exception as e:
        print(f"  Error creating profile for {person['full_name']}: {e}")
        return False


def create_event(client: Client, creator_id: str) -> str | None:
    """Create a test event. Returns event_id."""
    try:
        event_data = {
            "name": "ECE 495 Spring 2026 Demo",
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=7, hours=3)).isoformat(),
            "location": "WALC 1018",
            "is_active": True,
            "created_by": creator_id,
        }
        
        response = client.table("events").insert(event_data).execute()
        
        if response.data:
            return response.data[0]["event_id"]
        return None
    except Exception as e:
        print(f"Error creating event: {e}")
        return None


def add_membership_and_consent(
    client: Client, 
    event_id: str, 
    user_id: str, 
    role: str = "attendee"
) -> bool:
    """Add a user to an event with membership and consent."""
    try:
        # Add membership
        membership_data = {
            "event_id": event_id,
            "user_id": user_id,
            "role": role,
        }
        client.table("event_memberships").upsert(membership_data).execute()
        
        # Add consent (opt-in for demo)
        consent_data = {
            "event_id": event_id,
            "user_id": user_id,
            "allow_profile_display": True,
            "allow_recognition": True,
            "consented_at": datetime.now(timezone.utc).isoformat(),
        }
        client.table("event_consents").upsert(consent_data).execute()
        
        return True
    except Exception as e:
        print(f"  Error adding membership/consent: {e}")
        return False


def main():
    print("=" * 60)
    print("Memento Database Seeder")
    print("=" * 60)
    
    # Load classlist
    classlist = load_classlist()
    print(f"\nLoaded {len(classlist)} people from classlist.json")
    
    # Filter to only those with photos (for meaningful test data)
    with_photos = [p for p in classlist if p.get("photo_path")]
    print(f"  {len(with_photos)} have profile photos")
    
    # Get admin client
    print("\nConnecting to Supabase...")
    client = get_admin_client()
    
    # Ensure storage bucket exists
    ensure_storage_bucket(client)
    
    # Create users and profiles
    print("\n" + "-" * 40)
    print("Creating users and profiles...")
    print("-" * 40)
    
    created_users = []
    first_user_id = None
    
    for i, person in enumerate(with_photos, 1):
        email = person.get("email")
        if not email:
            print(f"[{i}/{len(with_photos)}] Skipping {person['full_name']} (no email)")
            continue
        
        print(f"[{i}/{len(with_photos)}] {person['full_name']}")
        
        # Create user in Auth
        user_id = create_test_user(client, email, person["full_name"])
        if not user_id:
            continue
        
        if not first_user_id:
            first_user_id = user_id
        
        print(f"  Created/found user: {user_id[:8]}...")
        
        # Upload photo
        photo_url = None
        photo_path = person.get("photo_path")
        if photo_path:
            local_photo = DATA_DIR / photo_path
            if local_photo.exists():
                storage_path = f"{user_id}.jpg"
                photo_url = upload_photo(client, local_photo, storage_path)
                if photo_url:
                    print(f"  Uploaded photo")
        
        # Create profile
        if create_profile(client, user_id, person, photo_url):
            print(f"  Created profile")
            created_users.append({
                "user_id": user_id,
                "person": person
            })
    
    print(f"\nCreated {len(created_users)} users with profiles")
    
    if not created_users:
        print("\nNo users created. Check your Supabase credentials and try again.")
        return
    
    # Create test event
    print("\n" + "-" * 40)
    print("Creating test event...")
    print("-" * 40)
    
    event_id = create_event(client, first_user_id)
    if not event_id:
        print("Failed to create event")
        return
    
    print(f"Created event: {event_id}")
    
    # Add memberships and consents
    print("\n" + "-" * 40)
    print("Adding memberships and consents...")
    print("-" * 40)
    
    for user_data in created_users:
        user_id = user_data["user_id"]
        person = user_data["person"]
        role = "organizer" if user_id == first_user_id else "attendee"
        
        # Check if they have a special role
        if person.get("role") == "Instructor":
            role = "admin"
        elif person.get("role") == "Teaching Assistant":
            role = "organizer"
        
        if add_membership_and_consent(client, event_id, user_id, role):
            print(f"  Added {person['full_name']} as {role}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print("=" * 60)
    print(f"Users created: {len(created_users)}")
    print(f"Event ID: {event_id}")
    print(f"\nYou can now test the API with this data!")


if __name__ == "__main__":
    main()

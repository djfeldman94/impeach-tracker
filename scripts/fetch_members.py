#!/usr/bin/env python3
"""
Fetch current members of Congress from @unitedstates/congress-legislators.

Outputs:
  - src/content/representatives/members.json  (House)
  - src/content/senators/senators.json        (Senate)
"""

import json
import sys
from pathlib import Path

import requests
import yaml
from slugify import slugify

# Add scripts dir to path for local imports
sys.path.insert(0, str(Path(__file__).parent))
from utils.fips import make_district_fips, make_state_fips

BASE_URL = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main"
LEGISLATORS_URL = f"{BASE_URL}/legislators-current.yaml"
SOCIAL_MEDIA_URL = f"{BASE_URL}/legislators-social-media.yaml"

PROJECT_ROOT = Path(__file__).parent.parent
HOUSE_OUTPUT = PROJECT_ROOT / "src" / "content" / "representatives" / "members.json"
SENATE_OUTPUT = PROJECT_ROOT / "src" / "content" / "senators" / "senators.json"


def fetch_yaml(url: str) -> list:
    print(f"  Fetching {url.split('/')[-1]}...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return yaml.safe_load(resp.text)


def build_social_lookup(social_data: list) -> dict:
    """Map bioguide ID -> social media info."""
    lookup = {}
    for entry in social_data:
        bioguide = entry.get("id", {}).get("bioguide", "")
        if bioguide and "social" in entry:
            lookup[bioguide] = entry["social"]
    return lookup


def get_current_term(terms: list) -> dict | None:
    """Get the most recent (current) term."""
    if not terms:
        return None
    return terms[-1]


def party_letter(party_name: str) -> str:
    mapping = {
        "Democrat": "D",
        "Republican": "R",
        "Independent": "I",
        "Libertarian": "I",
    }
    return mapping.get(party_name, "I")


def build_member(legislator: dict, social_lookup: dict) -> dict | None:
    """Convert a legislator entry to our member schema."""
    ids = legislator.get("id", {})
    name = legislator.get("name", {})
    bio = legislator.get("bio", {})
    terms = legislator.get("terms", [])

    bioguide = ids.get("bioguide", "")
    if not bioguide:
        return None

    term = get_current_term(terms)
    if not term:
        return None

    term_type = term.get("type", "")  # "rep" or "sen"
    state = term.get("state", "")
    party = party_letter(term.get("party", ""))

    first_name = name.get("first", "")
    last_name = name.get("last", "")
    official_full = name.get("official_full", f"{first_name} {last_name}")

    # Build slug
    slug = slugify(official_full)

    # District info (House only)
    district = term.get("district")

    # FIPS code
    if term_type == "rep":
        fips = make_district_fips(state, district)
    else:
        fips = make_state_fips(state)

    if not fips:
        print(f"  Warning: no FIPS for {official_full} ({state}, district={district})")
        return None

    # Contact info from term
    phone = term.get("phone", "")
    url = term.get("url", "")
    address = term.get("address", "")
    office = term.get("office", "")
    contact_form = term.get("contact_form", "")

    # Social media
    social = social_lookup.get(bioguide, {})
    twitter = social.get("twitter", "")
    facebook = social.get("facebook", "")

    # Photo URL — congress.gov hosts official photos by bioguide ID
    photo_url = f"https://bioguide.congress.gov/bioguide/photo/{bioguide[0]}/{bioguide}.jpg"

    member = {
        "id": bioguide,
        "slug": slug,
        "firstName": first_name,
        "lastName": last_name,
        "fullName": official_full,
        "party": party,
        "photoUrl": photo_url,
        "state": state,
        "fipsCode": fips,
        # Stance defaults to silent — updated by scrape_stances.py
        "stance": "silent",
        "stanceSummary": "No public position on impeachment recorded.",
        "stanceSources": [],
        "stanceUpdatedAt": "",
        # Contact
        "phone": phone or None,
        "email": contact_form or None,
        "website": url or None,
        "officeAddress": address or office or None,
        "districtOffices": [],
        # Social
        "twitter": twitter or None,
        "facebook": facebook or None,
        # Term
        "termStart": term.get("start", ""),
        "termEnd": term.get("end", ""),
    }

    # House-specific
    if term_type == "rep":
        member["district"] = district if district and district != 0 else 0

    return member, term_type


def main():
    print("Fetching congress-legislators data...")
    legislators = fetch_yaml(LEGISLATORS_URL)
    social_data = fetch_yaml(SOCIAL_MEDIA_URL)

    social_lookup = build_social_lookup(social_data)

    house_members = []
    senate_members = []
    skipped = 0

    for leg in legislators:
        result = build_member(leg, social_lookup)
        if result is None:
            skipped += 1
            continue

        member, term_type = result
        if term_type == "rep":
            house_members.append(member)
        elif term_type == "sen":
            senate_members.append(member)

    # Sort for stable output
    house_members.sort(key=lambda m: (m["state"], m.get("district", 0)))
    senate_members.sort(key=lambda m: (m["state"], m["lastName"]))

    # Write output
    HOUSE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SENATE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(HOUSE_OUTPUT, "w") as f:
        json.dump(house_members, f, indent=2)

    with open(SENATE_OUTPUT, "w") as f:
        json.dump(senate_members, f, indent=2)

    print(f"\nResults:")
    print(f"  House members: {len(house_members)} -> {HOUSE_OUTPUT}")
    print(f"  Senators:      {len(senate_members)} -> {SENATE_OUTPUT}")
    print(f"  Skipped:       {skipped}")


if __name__ == "__main__":
    main()

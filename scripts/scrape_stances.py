#!/usr/bin/env python3
"""
Scrape and classify impeachment stances for all members.

Data sources (in priority order):
  1. Manual overrides from data/stances.json (highest priority)
  2. Congress.gov API co-sponsorship data (if API key available)
  3. Keyword classification of scraped statements (future)

Outputs: Updates stance fields in members.json, senators.json, governors.json
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from utils.stance_classifier import classify_text

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
CONTENT_DIR = PROJECT_ROOT / "src" / "content"

HOUSE_FILE = CONTENT_DIR / "representatives" / "members.json"
SENATE_FILE = CONTENT_DIR / "senators" / "senators.json"
GOVERNOR_FILE = CONTENT_DIR / "governors" / "governors.json"
STANCES_FILE = DATA_DIR / "stances.json"

# Congress.gov API (optional — set CONGRESS_API_KEY env var)
CONGRESS_API_KEY = os.environ.get("CONGRESS_API_KEY", "")
CONGRESS_API_BASE = "https://api.congress.gov/v3"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_json(path: Path) -> list:
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data: list):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_manual_overrides() -> dict:
    """Load manual stance overrides keyed by member ID."""
    if not STANCES_FILE.exists():
        return {}
    overrides = load_json(STANCES_FILE)
    return {o["memberId"]: o for o in overrides if "memberId" in o}


def fetch_impeachment_cosponsors() -> set[str]:
    """
    Fetch bioguide IDs of co-sponsors of impeachment-related bills
    from the Congress.gov API.

    Returns a set of bioguide IDs.
    """
    if not CONGRESS_API_KEY:
        print("  No CONGRESS_API_KEY set — skipping co-sponsorship lookup")
        return set()

    cosponsors = set()
    # Search for impeachment bills in current congress (119th)
    search_url = f"{CONGRESS_API_BASE}/bill/119"
    params = {
        "api_key": CONGRESS_API_KEY,
        "limit": 250,
        "format": "json",
    }

    try:
        print("  Fetching bills from Congress.gov API...")
        resp = requests.get(search_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        bills = data.get("bills", [])
        impeachment_bills = [
            b for b in bills
            if "impeach" in b.get("title", "").lower()
        ]

        print(f"  Found {len(impeachment_bills)} impeachment-related bills")

        for bill in impeachment_bills:
            bill_url = bill.get("url", "")
            if not bill_url:
                continue

            # Fetch cosponsors for this bill
            cosponsor_url = f"{bill_url}/cosponsors"
            resp = requests.get(
                cosponsor_url,
                params={"api_key": CONGRESS_API_KEY, "format": "json", "limit": 250},
                timeout=30,
            )
            if resp.ok:
                cosponsor_data = resp.json()
                for cs in cosponsor_data.get("cosponsors", []):
                    bioguide = cs.get("bioguideId", "")
                    if bioguide:
                        cosponsors.add(bioguide)

            # Also get the sponsor
            detail_resp = requests.get(
                bill_url,
                params={"api_key": CONGRESS_API_KEY, "format": "json"},
                timeout=30,
            )
            if detail_resp.ok:
                bill_detail = detail_resp.json().get("bill", {})
                sponsors = bill_detail.get("sponsors", [])
                for sp in sponsors:
                    bioguide = sp.get("bioguideId", "")
                    if bioguide:
                        cosponsors.add(bioguide)

        print(f"  Found {len(cosponsors)} total co-sponsors/sponsors")

    except Exception as e:
        print(f"  Warning: Congress.gov API error: {e}")

    return cosponsors


def apply_stances(
    members: list,
    manual_overrides: dict,
    cosponsors: set[str],
) -> int:
    """Apply stance data to members. Returns count of members with non-silent stances."""
    updated = 0

    for member in members:
        member_id = member["id"]

        # Priority 1: Manual override
        if member_id in manual_overrides:
            override = manual_overrides[member_id]
            member["stance"] = override.get("stance", member["stance"])
            member["stanceSummary"] = override.get("summary", member["stanceSummary"])
            member["stanceSources"] = override.get("sources", member["stanceSources"])
            member["stanceUpdatedAt"] = override.get("updatedAt", TODAY)
            updated += 1
            continue

        # Priority 2: Congress.gov co-sponsorship
        if member_id in cosponsors:
            member["stance"] = "cosponsor"
            member["stanceSummary"] = "Co-sponsor of impeachment legislation per Congress.gov records."
            member["stanceSources"] = [{
                "title": "Congress.gov bill co-sponsorship record",
                "url": f"https://www.congress.gov/member/{member_id}",
                "date": TODAY,
            }]
            member["stanceUpdatedAt"] = TODAY
            updated += 1
            continue

        # Priority 3: No data — keep as silent
        if member["stance"] == "silent":
            member["stanceUpdatedAt"] = TODAY

    return updated


def main():
    print("Updating stance data...")

    # Load data
    house = load_json(HOUSE_FILE)
    senate = load_json(SENATE_FILE)
    governors = load_json(GOVERNOR_FILE)
    manual_overrides = load_manual_overrides()

    print(f"  Manual overrides loaded: {len(manual_overrides)}")

    # Fetch co-sponsors from Congress.gov
    cosponsors = fetch_impeachment_cosponsors()

    # Apply stances
    house_updated = apply_stances(house, manual_overrides, cosponsors)
    senate_updated = apply_stances(senate, manual_overrides, cosponsors)
    gov_updated = apply_stances(governors, manual_overrides, set())

    # Save
    save_json(HOUSE_FILE, house)
    save_json(SENATE_FILE, senate)
    save_json(GOVERNOR_FILE, governors)

    print(f"\nResults:")
    print(f"  House:     {house_updated} members with stance data (of {len(house)})")
    print(f"  Senate:    {senate_updated} senators with stance data (of {len(senate)})")
    print(f"  Governors: {gov_updated} governors with stance data (of {len(governors)})")

    # Summary
    all_members = house + senate + governors
    from collections import Counter
    stance_counts = Counter(m["stance"] for m in all_members)
    print(f"\nStance distribution:")
    for stance, count in sorted(stance_counts.items(), key=lambda x: -x[1]):
        print(f"  {stance}: {count}")


if __name__ == "__main__":
    main()

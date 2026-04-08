#!/usr/bin/env python3
"""
Fetch district office data from @unitedstates/congress-legislators
and merge into the existing member JSON files.
"""

import json
import sys
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main"
OFFICES_URL = f"{BASE_URL}/legislators-district-offices.yaml"

PROJECT_ROOT = Path(__file__).parent.parent
HOUSE_FILE = PROJECT_ROOT / "src" / "content" / "representatives" / "members.json"
SENATE_FILE = PROJECT_ROOT / "src" / "content" / "senators" / "senators.json"


def fetch_yaml(url: str) -> list:
    print(f"  Fetching {url.split('/')[-1]}...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return yaml.safe_load(resp.text)


def build_offices_lookup(offices_data: list) -> dict:
    """Map bioguide ID -> list of district offices."""
    lookup = {}
    for entry in offices_data:
        bioguide = entry.get("id", {}).get("bioguide", "")
        if not bioguide:
            continue
        offices = []
        for office in entry.get("offices", []):
            addr_parts = [
                str(office.get("address", "")),
                str(office.get("suite", "")),
                str(office.get("building", "")),
            ]
            addr = ", ".join(p for p in addr_parts if p)
            city = office.get("city", "")
            state = office.get("state", "")
            zipcode = office.get("zip", "")
            full_addr = f"{addr}, {city}, {state} {zipcode}".strip(", ")

            phone = office.get("phone", "")
            if not phone:
                continue

            offices.append({
                "city": city,
                "address": full_addr,
                "phone": phone,
            })
        if offices:
            lookup[bioguide] = offices
    return lookup


def merge_offices(members_file: Path, offices_lookup: dict) -> int:
    """Merge district offices into member JSON. Returns count of members updated."""
    with open(members_file) as f:
        members = json.load(f)

    updated = 0
    for member in members:
        bioguide = member["id"]
        offices = offices_lookup.get(bioguide, [])
        if offices:
            member["districtOffices"] = offices
            updated += 1

    with open(members_file, "w") as f:
        json.dump(members, f, indent=2)

    return updated


def main():
    print("Fetching district office data...")
    offices_data = fetch_yaml(OFFICES_URL)
    offices_lookup = build_offices_lookup(offices_data)
    print(f"  Found offices for {len(offices_lookup)} legislators")

    house_updated = merge_offices(HOUSE_FILE, offices_lookup)
    senate_updated = merge_offices(SENATE_FILE, offices_lookup)

    print(f"\nResults:")
    print(f"  House members with offices: {house_updated}")
    print(f"  Senators with offices:      {senate_updated}")


if __name__ == "__main__":
    main()

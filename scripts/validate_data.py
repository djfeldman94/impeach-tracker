#!/usr/bin/env python3
"""
Validate all member JSON data against expected schemas and cross-check
FIPS codes against the TopoJSON boundary files.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONTENT_DIR = PROJECT_ROOT / "src" / "content"
GEO_DIR = PROJECT_ROOT / "public" / "geo"

HOUSE_FILE = CONTENT_DIR / "representatives" / "members.json"
SENATE_FILE = CONTENT_DIR / "senators" / "senators.json"
GOVERNOR_FILE = CONTENT_DIR / "governors" / "governors.json"
DISTRICTS_TOPO = GEO_DIR / "us-congress-districts.topo.json"
STATES_TOPO = GEO_DIR / "us-states.topo.json"

VALID_STANCES = {
    "cosponsor", "publicly-supports", "leaning-support",
    "silent", "leaning-oppose", "publicly-opposes",
}
VALID_PARTIES = {"D", "R", "I"}

REQUIRED_FIELDS = ["id", "slug", "firstName", "lastName", "fullName", "party", "state", "fipsCode", "stance"]

errors = []
warnings = []


def error(msg: str):
    errors.append(msg)
    print(f"  ERROR: {msg}")


def warn(msg: str):
    warnings.append(msg)
    print(f"  WARN:  {msg}")


def load_geoids_from_topo(topo_path: Path) -> set[str]:
    """Extract all GEOIDs from a TopoJSON file."""
    if not topo_path.exists():
        warn(f"TopoJSON file not found: {topo_path}")
        return set()
    with open(topo_path) as f:
        topo = json.load(f)
    layer = list(topo["objects"].keys())[0]
    geoids = set()
    for geom in topo["objects"][layer]["geometries"]:
        geoid = geom.get("properties", {}).get("GEOID", "")
        if geoid:
            geoids.add(geoid)
    return geoids


def validate_member(member: dict, chamber: str, idx: int):
    prefix = f"{chamber}[{idx}] ({member.get('fullName', 'UNKNOWN')})"

    for field in REQUIRED_FIELDS:
        if field not in member or not member[field]:
            error(f"{prefix}: missing required field '{field}'")

    if member.get("party") not in VALID_PARTIES:
        error(f"{prefix}: invalid party '{member.get('party')}'")

    if member.get("stance") not in VALID_STANCES:
        error(f"{prefix}: invalid stance '{member.get('stance')}'")

    if not member.get("slug"):
        error(f"{prefix}: empty slug")

    if chamber == "house" and "district" not in member:
        warn(f"{prefix}: missing district field")


def validate_fips(members: list, geoids: set[str], chamber: str):
    member_fips = {m["fipsCode"] for m in members if m.get("fipsCode")}

    # Check members without matching geo features
    unmatched = member_fips - geoids
    if unmatched:
        # Filter out territories we may not display
        important_unmatched = {f for f in unmatched if not f.startswith(("60", "66", "69", "72", "78"))}
        if important_unmatched:
            for fips in sorted(important_unmatched):
                names = [m["fullName"] for m in members if m.get("fipsCode") == fips]
                warn(f"{chamber}: FIPS {fips} ({', '.join(names)}) not found in TopoJSON")


def validate_duplicates(members: list, chamber: str):
    seen_ids = {}
    seen_slugs = {}
    for m in members:
        mid = m.get("id", "")
        slug = m.get("slug", "")

        if mid in seen_ids:
            error(f"{chamber}: duplicate ID '{mid}' — {m['fullName']} vs {seen_ids[mid]}")
        seen_ids[mid] = m.get("fullName", "")

        if slug in seen_slugs:
            error(f"{chamber}: duplicate slug '{slug}' — {m['fullName']} vs {seen_slugs[slug]}")
        seen_slugs[slug] = m.get("fullName", "")


def main():
    print("Validating data files...\n")

    # Load geo data
    district_geoids = load_geoids_from_topo(DISTRICTS_TOPO)
    state_geoids = load_geoids_from_topo(STATES_TOPO)
    print(f"  District GEOIDs in TopoJSON: {len(district_geoids)}")
    print(f"  State GEOIDs in TopoJSON: {len(state_geoids)}")
    print()

    # Validate House
    print("--- House ---")
    house = json.loads(HOUSE_FILE.read_text())
    print(f"  Members: {len(house)}")
    for i, m in enumerate(house):
        validate_member(m, "house", i)
    validate_duplicates(house, "house")
    validate_fips(house, district_geoids, "house")
    print()

    # Validate Senate
    print("--- Senate ---")
    senate = json.loads(SENATE_FILE.read_text())
    print(f"  Senators: {len(senate)}")
    for i, m in enumerate(senate):
        validate_member(m, "senate", i)
    validate_duplicates(senate, "senate")
    validate_fips(senate, state_geoids, "senate")
    print()

    # Validate Governors
    print("--- Governors ---")
    governors = json.loads(GOVERNOR_FILE.read_text())
    print(f"  Governors: {len(governors)}")
    for i, m in enumerate(governors):
        validate_member(m, "governors", i)
    validate_duplicates(governors, "governors")
    validate_fips(governors, state_geoids, "governors")
    print()

    # Summary
    total = len(house) + len(senate) + len(governors)
    print("=" * 50)
    print(f"Total members: {total}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    if errors:
        print("\nValidation FAILED")
        sys.exit(1)
    else:
        print("\nValidation PASSED")


if __name__ == "__main__":
    main()

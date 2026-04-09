#!/usr/bin/env python3
"""
CLI tool for managing stance overrides.

Usage:
  # Search for a member and add/update their override
  python override_stance.py set "Josh Harder" publicly-supports

  # With a source URL and summary
  python override_stance.py set "Josh Harder" publicly-supports \
    --summary "Joined calls for removal per Fresno Bee report" \
    --source-url "https://fresnobee.com/article123" \
    --source-title "Harder joins calls for Trump removal"

  # List all current overrides
  python override_stance.py list

  # Remove an override (member reverts to LLM classification)
  python override_stance.py remove "Josh Harder"

  # Search for a member by name (shows current stance + override status)
  python override_stance.py search "Harder"
  python override_stance.py search --state CA
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONTENT_DIR = PROJECT_ROOT / "src" / "content"
STANCES_FILE = PROJECT_ROOT / "src" / "data" / "stances.json"

HOUSE_FILE = CONTENT_DIR / "representatives" / "members.json"
SENATE_FILE = CONTENT_DIR / "senators" / "senators.json"
GOVERNOR_FILE = CONTENT_DIR / "governors" / "governors.json"

VALID_STANCES = [
    "cosponsor", "publicly-supports", "leaning-support",
    "silent", "leaning-oppose", "publicly-opposes",
]

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_json(path: Path) -> list:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data: list):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved {path.name}")


def load_all_members() -> list[dict]:
    """Load all members from all chambers with a 'chamber' tag."""
    members = []
    for chamber, path in [("house", HOUSE_FILE), ("senate", SENATE_FILE), ("governors", GOVERNOR_FILE)]:
        for m in load_json(path):
            m["_chamber"] = chamber
            members.append(m)
    return members


def find_members(query: str, members: list[dict], state: str | None = None) -> list[dict]:
    """Fuzzy search members by name, optionally filtered by state."""
    query_lower = query.lower() if query else ""
    results = []
    for m in members:
        if state and m.get("state") != state.upper():
            continue
        if query_lower and query_lower not in m.get("fullName", "").lower():
            continue
        if not query_lower and not state:
            continue
        results.append(m)
    return results


def load_overrides() -> list[dict]:
    return load_json(STANCES_FILE)


def save_overrides(overrides: list[dict]):
    save_json(STANCES_FILE, overrides)


def format_member(m: dict, overrides_by_id: dict) -> str:
    """Format a member for display."""
    mid = m["id"]
    name = m["fullName"]
    party = m.get("party", "?")
    state = m.get("state", "?")
    district = m.get("district")
    chamber = m.get("_chamber", "?")
    stance = m.get("stance", "silent")

    loc = f"{state}-{district}" if district is not None else state
    override = overrides_by_id.get(mid)

    line = f"  {name:30s} ({party}) {loc:6s} [{chamber:9s}]  stance: {stance}"
    if override:
        line += "  [OVERRIDE]"
    line += f"\n  {'':30s} ID: {mid}"
    return line


def cmd_search(args):
    members = load_all_members()
    overrides = load_overrides()
    overrides_by_id = {o["memberId"]: o for o in overrides}

    results = find_members(args.query or "", members, state=args.state)

    if not results:
        print("No members found.")
        return

    print(f"Found {len(results)} member(s):\n")
    for m in sorted(results, key=lambda x: (x.get("state", ""), x.get("fullName", ""))):
        print(format_member(m, overrides_by_id))
        print()


def cmd_list(args):
    overrides = load_overrides()
    members = load_all_members()
    members_by_id = {m["id"]: m for m in members}

    if not overrides:
        print("No overrides configured.")
        return

    print(f"{len(overrides)} override(s):\n")
    for o in overrides:
        mid = o["memberId"]
        m = members_by_id.get(mid, {})
        name = m.get("fullName", mid)
        state = m.get("state", "?")
        party = m.get("party", "?")
        stance = o.get("stance", "?")
        summary = o.get("summary", "")[:60]
        print(f"  {name:30s} ({party}, {state})  -> {stance}")
        if summary:
            print(f"  {'':30s} {summary}...")
        print()


def cmd_set(args):
    members = load_all_members()
    results = find_members(args.name, members)

    if not results:
        print(f"No member found matching '{args.name}'")
        return

    if len(results) > 1:
        print(f"Multiple matches for '{args.name}' — be more specific:\n")
        for m in results:
            loc = f"{m['state']}-{m.get('district', '')}" if m.get("district") is not None else m["state"]
            print(f"  {m['fullName']:30s} ({m['party']}) {loc} [{m['_chamber']}]  ID: {m['id']}")
        return

    member = results[0]
    mid = member["id"]
    name = member["fullName"]

    if args.stance not in VALID_STANCES:
        print(f"Invalid stance '{args.stance}'. Must be one of: {', '.join(VALID_STANCES)}")
        return

    overrides = load_overrides()

    # Build source if provided
    sources = []
    if args.source_url:
        sources.append({
            "title": args.source_title or args.source_url,
            "url": args.source_url,
            "date": TODAY,
        })

    override = {
        "memberId": mid,
        "stance": args.stance,
        "summary": args.summary or "",
        "sources": sources,
        "updatedAt": TODAY,
    }

    # Update or insert
    existing_idx = next((i for i, o in enumerate(overrides) if o["memberId"] == mid), None)
    if existing_idx is not None:
        overrides[existing_idx] = override
        print(f"Updated override for {name} -> {args.stance}")
    else:
        overrides.append(override)
        print(f"Added override for {name} -> {args.stance}")

    save_overrides(overrides)

    # Also update the member JSON directly so the change is immediate
    chamber = member["_chamber"]
    chamber_file = {"house": HOUSE_FILE, "senate": SENATE_FILE, "governors": GOVERNOR_FILE}[chamber]
    chamber_members = load_json(chamber_file)
    for m in chamber_members:
        if m["id"] == mid:
            m["stance"] = args.stance
            m["stanceSummary"] = override["summary"]
            m["stanceSources"] = sources
            m["stanceUpdatedAt"] = TODAY
            break
    save_json(chamber_file, chamber_members)
    print(f"  Updated {chamber} data directly")


def cmd_remove(args):
    members = load_all_members()
    results = find_members(args.name, members)

    if not results:
        print(f"No member found matching '{args.name}'")
        return

    if len(results) > 1:
        print(f"Multiple matches — be more specific:")
        for m in results:
            print(f"  {m['fullName']} ({m['state']})")
        return

    member = results[0]
    mid = member["id"]
    name = member["fullName"]

    overrides = load_overrides()
    new_overrides = [o for o in overrides if o["memberId"] != mid]

    if len(new_overrides) == len(overrides):
        print(f"No override found for {name}")
        return

    save_overrides(new_overrides)
    print(f"Removed override for {name} (will revert to LLM classification on next run)")


def main():
    parser = argparse.ArgumentParser(description="Manage stance overrides")
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Search for members")
    p_search.add_argument("query", nargs="?", default="", help="Name to search for")
    p_search.add_argument("--state", help="Filter by state abbreviation")

    # list
    sub.add_parser("list", help="List all overrides")

    # set
    p_set = sub.add_parser("set", help="Add or update an override")
    p_set.add_argument("name", help="Member name (partial match)")
    p_set.add_argument("stance", choices=VALID_STANCES, help="Stance category")
    p_set.add_argument("--summary", help="1-2 sentence summary")
    p_set.add_argument("--source-url", help="Source article URL")
    p_set.add_argument("--source-title", help="Source article title")

    # remove
    p_remove = sub.add_parser("remove", help="Remove an override")
    p_remove.add_argument("name", help="Member name (partial match)")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "set":
        cmd_set(args)
    elif args.command == "remove":
        cmd_remove(args)


if __name__ == "__main__":
    main()

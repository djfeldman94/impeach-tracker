#!/usr/bin/env python3
"""
LLM-powered stance classification using web search + Claude Sonnet.

For each member, this script:
  1. Searches the web for their impeachment stance (via DuckDuckGo)
  2. Sends the search results to Claude Sonnet for structured classification
  3. Updates the member JSON with the classified stance

Usage:
  # Test with specific members
  python scrape_stances_llm.py --test "Eric Swalwell" "Nancy Pelosi"

  # Run for all members (with rate limiting)
  python scrape_stances_llm.py --all

  # Run for members currently marked 'silent'
  python scrape_stances_llm.py --silent-only

  # Run for a specific state
  python scrape_stances_llm.py --state CA

Requires: ANTHROPIC_API_KEY environment variable
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import anthropic
from ddgs import DDGS

sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).parent.parent

# Load .env file if present
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())
CONTENT_DIR = PROJECT_ROOT / "src" / "content"
DATA_DIR = PROJECT_ROOT / "src" / "data"

HOUSE_FILE = CONTENT_DIR / "representatives" / "members.json"
SENATE_FILE = CONTENT_DIR / "senators" / "senators.json"
GOVERNOR_FILE = CONTENT_DIR / "governors" / "governors.json"
STANCES_FILE = DATA_DIR / "stances.json"

CLASSIFICATION_PROMPT = """\
You are classifying a US politician's stance on impeaching Donald Trump based on web search results.
Today's date is {today}. There has been a MASSIVE shift in impeachment stances in the last 48 hours.

Analyze the following search results about **{name}** ({role}, {party}, {location}) and determine their current impeachment stance.

{recent_section}

{older_section}

## CRITICAL Classification Rules
- **Results from the last 2 days (April 7-8, 2026) OVERRIDE everything else.** Positions have shifted dramatically — many members who previously opposed or were silent have changed their stance.
- If a RECENT result (last 2 days) contradicts an OLDER result, the recent result wins. Always.
- If someone has co-sponsored articles, voted for impeachment, or called for removal/impeachment in the last 2 days, classify accordingly even if they held a different position before.
- "Calls for removal", "supports removal", "25th amendment" should all count as support for impeachment/removal.
- If there are ONLY older results and NO recent results, classify based on the older results but set confidence to "low".
- If there is genuinely no information about their stance, classify as "silent".
- Consider party affiliation as context but do NOT classify based on party alone.

## Stance Categories (choose exactly one)
- **cosponsor**: Has co-sponsored or introduced articles of impeachment
- **publicly-supports**: Has publicly stated support for impeachment or removal (speeches, votes, press releases, calls for removal)
- **leaning-support**: Has signaled openness to impeachment without fully committing (e.g., supports investigation, "open to it", "considering")
- **silent**: No public position found, or deliberately avoiding the topic
- **leaning-oppose**: Has expressed reservations or soft opposition without firmly opposing
- **publicly-opposes**: Has publicly stated opposition to impeachment

## Response Format
Respond with ONLY valid JSON, no markdown fences:
{{
  "stance": "<one of the 6 categories above>",
  "summary": "<1-2 sentence summary of their position with specific evidence from the MOST RECENT sources>",
  "confidence": "<high|medium|low>",
  "used_recent_sources": <true if classification was based on last-2-day results, false if only older results>,
  "sources": [
    {{
      "title": "<article title>",
      "url": "<article url>",
      "date": "<date if available, otherwise empty string>"
    }}
  ]
}}
"""


def search_member_stance(name: str, role: str, state: str) -> tuple[list[dict], list[dict]]:
    """Search DuckDuckGo for a member's impeachment stance.

    Returns (recent_results, older_results) where recent = last 2 days.
    """
    recent_results = []
    older_results = []

    with DDGS() as ddgs:
        # Phase 1: Recent results (last 2 days) — highest priority
        recent_queries = [
            f'"{name}" impeachment Trump removal 2026',
            f'"{name}" impeach remove Trump',
        ]
        for query in recent_queries:
            try:
                results = list(ddgs.text(query, max_results=5, timelimit="d"))
                recent_results.extend(results)
            except Exception as e:
                print(f"    Recent search error: {e}")
            time.sleep(0.5)

        # Phase 2: Older results as fallback context
        older_queries = [
            f'"{name}" impeachment Trump 2025 2026 stance',
        ]
        for query in older_queries:
            try:
                results = list(ddgs.text(query, max_results=5))
                older_results.extend(results)
            except Exception as e:
                print(f"    Older search error: {e}")
            time.sleep(0.5)

    # Deduplicate each list by URL
    def dedup(results: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique = []
        for r in results:
            url = r.get("href", r.get("link", ""))
            if url and url not in seen:
                seen.add(url)
                unique.append(r)
        return unique

    recent_results = dedup(recent_results)[:6]
    # Remove from older anything already in recent
    recent_urls = {r.get("href", r.get("link", "")) for r in recent_results}
    older_results = [r for r in dedup(older_results) if r.get("href", r.get("link", "")) not in recent_urls][:4]

    return recent_results, older_results


NEEDS_REVIEW_FILE = DATA_DIR / "needs_review.json"


def format_search_results(results: list[dict]) -> str:
    """Format search results for the LLM prompt."""
    if not results:
        return "No search results found."

    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("href", r.get("link", ""))
        body = r.get("body", r.get("snippet", ""))
        lines.append(f"{i}. **{title}**\n   URL: {url}\n   {body}")

    return "\n\n".join(lines)


def classify_with_llm(
    client: anthropic.Anthropic,
    name: str,
    role: str,
    party: str,
    location: str,
    recent_results: list[dict],
    older_results: list[dict],
) -> dict | None:
    """Send search results to Claude Sonnet for stance classification."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    recent_formatted = format_search_results(recent_results)
    older_formatted = format_search_results(older_results)

    if recent_results:
        recent_section = f"## RECENT Results (last 48 hours — THESE TAKE PRIORITY)\n{recent_formatted}"
    else:
        recent_section = "## RECENT Results (last 48 hours)\nNo recent results found. Use older results below, but set confidence to LOW."

    if older_results:
        older_section = f"## Older Results (background context — use ONLY if no recent results exist)\n{older_formatted}"
    else:
        older_section = "## Older Results\nNone found."

    prompt = CLASSIFICATION_PROMPT.format(
        name=name,
        role=role,
        party=party,
        location=location,
        today=today,
        recent_section=recent_section,
        older_section=older_section,
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        print(f"    Raw response: {text[:200]}")
        return None
    except Exception as e:
        print(f"    LLM error: {e}")
        return None


# Track members that need manual review (no recent sources)
_needs_review: list[dict] = []


def process_member(
    client: anthropic.Anthropic,
    member: dict,
    chamber: str,
) -> dict | None:
    """Process a single member: search + classify."""
    name = member["fullName"]
    party_map = {"D": "Democrat", "R": "Republican", "I": "Independent"}
    party = party_map.get(member["party"], member["party"]) or "Unknown"
    state = member["state"]
    district = member.get("district")

    if chamber == "house":
        role = "US Representative"
        location = f"{state}-{district}" if district else state
    elif chamber == "senate":
        role = "US Senator"
        location = state
    else:
        role = "Governor"
        location = state

    print(f"  [{chamber.upper()}] {name} ({party}, {location})")

    # Search — returns (recent, older)
    recent_results, older_results = search_member_stance(name, role, state)

    if not recent_results and not older_results:
        print(f"    No search results found — keeping as silent")
        return None

    has_recent = len(recent_results) > 0
    print(f"    Found {len(recent_results)} recent + {len(older_results)} older results")

    # Classify
    classification = classify_with_llm(
        client, name, role, party, location, recent_results, older_results
    )
    if not classification:
        print(f"    Classification failed — keeping current stance")
        return None

    stance = classification.get("stance", "silent")
    confidence = classification.get("confidence", "low")
    summary = classification.get("summary", "")
    used_recent = classification.get("used_recent_sources", has_recent)

    tag = "RECENT" if used_recent else "OLDER"
    print(f"    -> {stance} (confidence: {confidence}, source: {tag})")
    print(f"       {summary[:80]}...")

    # Flag for review if only older sources were used
    if not used_recent and stance != "silent":
        _needs_review.append({
            "id": member["id"],
            "name": name,
            "chamber": chamber,
            "state": state,
            "district": district,
            "classified_stance": stance,
            "confidence": confidence,
            "summary": summary,
            "reason": "No recent (last 48h) sources found — classified from older results only",
        })

    return classification


def save_needs_review():
    """Write the needs-review list to a JSON file for manual checking."""
    if not _needs_review:
        return

    # Merge with existing review items
    existing = []
    if NEEDS_REVIEW_FILE.exists():
        existing = load_json(NEEDS_REVIEW_FILE)

    existing_ids = {e["id"] for e in existing}
    for item in _needs_review:
        if item["id"] not in existing_ids:
            existing.append(item)
        else:
            # Update existing entry
            for i, e in enumerate(existing):
                if e["id"] == item["id"]:
                    existing[i] = item
                    break

    save_json(NEEDS_REVIEW_FILE, existing)
    print(f"\n  Needs-review list: {len(existing)} members -> {NEEDS_REVIEW_FILE}")


def update_member_stance(member: dict, classification: dict, today: str):
    """Apply an LLM classification to a member dict."""
    member["stance"] = classification["stance"]
    member["stanceSummary"] = classification.get("summary", member["stanceSummary"])
    member["stanceUpdatedAt"] = today

    # Add sources from classification
    sources = classification.get("sources", [])
    if sources:
        member["stanceSources"] = [
            {
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "date": s.get("date", ""),
            }
            for s in sources
            if s.get("url")
        ]


def load_json(path: Path) -> list:
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data: list):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="LLM-powered stance classification")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--test", nargs="+", help="Test with specific member names")
    group.add_argument("--all", action="store_true", help="Process all members")
    group.add_argument("--silent-only", action="store_true", help="Only process members with 'silent' stance")
    group.add_argument("--state", type=str, help="Process members from a specific state (e.g., CA)")
    parser.add_argument("--chamber", choices=["house", "senate", "governors", "all"], default="all",
                        help="Which chamber to process (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Search and classify but don't save")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between members (seconds)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load data
    chambers = {}
    if args.chamber in ("house", "all"):
        chambers["house"] = {"file": HOUSE_FILE, "data": load_json(HOUSE_FILE)}
    if args.chamber in ("senate", "all"):
        chambers["senate"] = {"file": SENATE_FILE, "data": load_json(SENATE_FILE)}
    if args.chamber in ("governors", "all"):
        chambers["governors"] = {"file": GOVERNOR_FILE, "data": load_json(GOVERNOR_FILE)}

    # Load manual overrides (these take priority, skip those members)
    manual_ids = set()
    if STANCES_FILE.exists():
        overrides = load_json(STANCES_FILE)
        manual_ids = {o["memberId"] for o in overrides if "memberId" in o}

    processed = 0
    updated = 0
    skipped = 0

    for chamber_name, chamber_info in chambers.items():
        members = chamber_info["data"]

        for member in members:
            # Skip members with manual overrides
            if member["id"] in manual_ids:
                continue

            # Filter logic
            if args.test:
                name_lower = member["fullName"].lower()
                if not any(t.lower() in name_lower for t in args.test):
                    continue
            elif args.silent_only:
                if member["stance"] != "silent":
                    continue
            elif args.state:
                if member["state"] != args.state.upper():
                    continue

            classification = process_member(client, member, chamber_name)
            processed += 1

            if classification:
                if not args.dry_run:
                    update_member_stance(member, classification, today)
                updated += 1
            else:
                skipped += 1

            if args.delay > 0:
                time.sleep(args.delay)

        # Save
        if not args.dry_run:
            save_json(chamber_info["file"], members)

    # Save the needs-review list
    if not args.dry_run:
        save_needs_review()

    print(f"\n{'=' * 50}")
    print(f"Processed: {processed}")
    print(f"Updated:   {updated}")
    print(f"Skipped:   {skipped}")
    if _needs_review:
        print(f"Needs review (older sources only): {len(_needs_review)}")
    if args.dry_run:
        print("(DRY RUN — no files modified)")


if __name__ == "__main__":
    main()

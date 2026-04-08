#!/usr/bin/env python3
"""
Generate governor data.

Governors are not in the @unitedstates/congress-legislators dataset.
This script maintains a manually-curated list of all 50 state governors
with contact info. Update this list after gubernatorial elections.

Last verified: April 2026
"""

import json
import sys
from pathlib import Path

from slugify import slugify

sys.path.insert(0, str(Path(__file__).parent))
from utils.fips import make_state_fips

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT = PROJECT_ROOT / "src" / "content" / "governors" / "governors.json"

# Source: National Governors Association (nga.org), official state websites
# Party: D=Democrat, R=Republican, I=Independent
GOVERNORS = [
    {"name": "Kay Ivey", "state": "AL", "party": "R", "phone": "(334) 242-7100", "website": "https://governor.alabama.gov", "took_office": "2017-04-10"},
    {"name": "Mike Dunleavy", "state": "AK", "party": "R", "phone": "(907) 465-3500", "website": "https://gov.alaska.gov", "took_office": "2018-12-03"},
    {"name": "Katie Hobbs", "state": "AZ", "party": "D", "phone": "(602) 542-4331", "website": "https://azgovernor.gov", "took_office": "2023-01-02"},
    {"name": "Sarah Huckabee Sanders", "state": "AR", "party": "R", "phone": "(501) 682-2345", "website": "https://governor.arkansas.gov", "took_office": "2023-01-10"},
    {"name": "Gavin Newsom", "state": "CA", "party": "D", "phone": "(916) 445-2841", "website": "https://www.gov.ca.gov", "took_office": "2019-01-07"},
    {"name": "Jared Polis", "state": "CO", "party": "D", "phone": "(303) 866-2471", "website": "https://www.colorado.gov/governor", "took_office": "2019-01-08"},
    {"name": "Ned Lamont", "state": "CT", "party": "D", "phone": "(860) 566-4840", "website": "https://portal.ct.gov/governor", "took_office": "2019-01-09"},
    {"name": "Matt Meyer", "state": "DE", "party": "D", "phone": "(302) 744-4101", "website": "https://governor.delaware.gov", "took_office": "2025-01-21"},
    {"name": "Ron DeSantis", "state": "FL", "party": "R", "phone": "(850) 717-9337", "website": "https://www.flgov.com", "took_office": "2019-01-08"},
    {"name": "Brian Kemp", "state": "GA", "party": "R", "phone": "(404) 656-1776", "website": "https://gov.georgia.gov", "took_office": "2019-01-14"},
    {"name": "Josh Green", "state": "HI", "party": "D", "phone": "(808) 586-0034", "website": "https://governor.hawaii.gov", "took_office": "2022-12-05"},
    {"name": "Brad Little", "state": "ID", "party": "R", "phone": "(208) 334-2100", "website": "https://gov.idaho.gov", "took_office": "2019-01-07"},
    {"name": "JB Pritzker", "state": "IL", "party": "D", "phone": "(217) 782-0244", "website": "https://gov.illinois.gov", "took_office": "2019-01-14"},
    {"name": "Eric Holcomb", "state": "IN", "party": "R", "phone": "(317) 232-4567", "website": "https://www.in.gov/gov", "took_office": "2017-01-09"},
    {"name": "Kim Reynolds", "state": "IA", "party": "R", "phone": "(515) 281-5211", "website": "https://governor.iowa.gov", "took_office": "2017-05-24"},
    {"name": "Derek Schmidt", "state": "KS", "party": "R", "phone": "(785) 296-3232", "website": "https://governor.kansas.gov", "took_office": "2025-01-13"},
    {"name": "Andy Beshear", "state": "KY", "party": "D", "phone": "(502) 564-2611", "website": "https://governor.ky.gov", "took_office": "2019-12-10"},
    {"name": "Jeff Landry", "state": "LA", "party": "R", "phone": "(225) 342-7015", "website": "https://gov.louisiana.gov", "took_office": "2024-01-08"},
    {"name": "Janet Mills", "state": "ME", "party": "D", "phone": "(207) 287-3531", "website": "https://www.maine.gov/governor", "took_office": "2019-01-02"},
    {"name": "Wes Moore", "state": "MD", "party": "D", "phone": "(410) 974-3901", "website": "https://governor.maryland.gov", "took_office": "2023-01-18"},
    {"name": "Maura Healey", "state": "MA", "party": "D", "phone": "(617) 725-4005", "website": "https://www.mass.gov/governor", "took_office": "2023-01-05"},
    {"name": "Gretchen Whitmer", "state": "MI", "party": "D", "phone": "(517) 335-7858", "website": "https://www.michigan.gov/whitmer", "took_office": "2019-01-01"},
    {"name": "Tim Walz", "state": "MN", "party": "D", "phone": "(651) 201-3400", "website": "https://mn.gov/governor", "took_office": "2019-01-07"},
    {"name": "Tate Reeves", "state": "MS", "party": "R", "phone": "(601) 359-3150", "website": "https://governorreeves.ms.gov", "took_office": "2020-01-14"},
    {"name": "Mike Kehoe", "state": "MO", "party": "R", "phone": "(573) 751-3222", "website": "https://governor.mo.gov", "took_office": "2025-01-13"},
    {"name": "Greg Gianforte", "state": "MT", "party": "R", "phone": "(406) 444-3111", "website": "https://governor.mt.gov", "took_office": "2021-01-04"},
    {"name": "Jim Pillen", "state": "NE", "party": "R", "phone": "(402) 471-2244", "website": "https://governor.nebraska.gov", "took_office": "2023-01-05"},
    {"name": "Joe Lombardo", "state": "NV", "party": "R", "phone": "(775) 684-5670", "website": "https://gov.nv.gov", "took_office": "2023-01-02"},
    {"name": "Kelly Ayotte", "state": "NH", "party": "R", "phone": "(603) 271-2121", "website": "https://www.governor.nh.gov", "took_office": "2025-01-09"},
    {"name": "Phil Murphy", "state": "NJ", "party": "D", "phone": "(609) 292-6000", "website": "https://nj.gov/governor", "took_office": "2018-01-16"},
    {"name": "Michelle Lujan Grisham", "state": "NM", "party": "D", "phone": "(505) 476-2200", "website": "https://www.governor.state.nm.us", "took_office": "2019-01-01"},
    {"name": "Kathy Hochul", "state": "NY", "party": "D", "phone": "(518) 474-8390", "website": "https://www.governor.ny.gov", "took_office": "2021-08-24"},
    {"name": "Josh Stein", "state": "NC", "party": "D", "phone": "(984) 236-1000", "website": "https://governor.nc.gov", "took_office": "2025-01-01"},
    {"name": "Kelly Armstrong", "state": "ND", "party": "R", "phone": "(701) 328-2200", "website": "https://www.governor.nd.gov", "took_office": "2024-12-15"},
    {"name": "Mike DeWine", "state": "OH", "party": "R", "phone": "(614) 466-3555", "website": "https://governor.ohio.gov", "took_office": "2019-01-14"},
    {"name": "Kevin Stitt", "state": "OK", "party": "R", "phone": "(405) 521-2342", "website": "https://www.governor.ok.gov", "took_office": "2019-01-14"},
    {"name": "Tina Kotek", "state": "OR", "party": "D", "phone": "(503) 378-4582", "website": "https://www.oregon.gov/governor", "took_office": "2023-01-09"},
    {"name": "Josh Shapiro", "state": "PA", "party": "D", "phone": "(717) 787-2500", "website": "https://www.governor.pa.gov", "took_office": "2023-01-17"},
    {"name": "Dan McKee", "state": "RI", "party": "D", "phone": "(401) 222-2080", "website": "https://governor.ri.gov", "took_office": "2021-03-02"},
    {"name": "Henry McMaster", "state": "SC", "party": "R", "phone": "(803) 734-2100", "website": "https://governor.sc.gov", "took_office": "2017-01-24"},
    {"name": "Larry Rhoden", "state": "SD", "party": "R", "phone": "(605) 773-3212", "website": "https://governor.sd.gov", "took_office": "2025-01-18"},
    {"name": "Bill Lee", "state": "TN", "party": "R", "phone": "(615) 741-2001", "website": "https://www.tn.gov/governor", "took_office": "2019-01-19"},
    {"name": "Greg Abbott", "state": "TX", "party": "R", "phone": "(512) 463-2000", "website": "https://gov.texas.gov", "took_office": "2015-01-20"},
    {"name": "Spencer Cox", "state": "UT", "party": "R", "phone": "(801) 538-1000", "website": "https://governor.utah.gov", "took_office": "2021-01-04"},
    {"name": "Phil Scott", "state": "VT", "party": "R", "phone": "(802) 828-3333", "website": "https://governor.vermont.gov", "took_office": "2017-01-05"},
    {"name": "Glenn Youngkin", "state": "VA", "party": "R", "phone": "(804) 786-2211", "website": "https://www.governor.virginia.gov", "took_office": "2022-01-15"},
    {"name": "Bob Ferguson", "state": "WA", "party": "D", "phone": "(360) 902-4111", "website": "https://www.governor.wa.gov", "took_office": "2025-01-15"},
    {"name": "Patrick Morrisey", "state": "WV", "party": "R", "phone": "(304) 558-2000", "website": "https://governor.wv.gov", "took_office": "2025-01-13"},
    {"name": "Tony Evers", "state": "WI", "party": "D", "phone": "(608) 266-1212", "website": "https://evers.wi.gov", "took_office": "2019-01-07"},
    {"name": "Mark Gordon", "state": "WY", "party": "R", "phone": "(307) 777-7434", "website": "https://governor.wyo.gov", "took_office": "2019-01-07"},
]


def build_governor(gov: dict) -> dict:
    full_name = gov["name"]
    parts = full_name.split()
    first_name = parts[0]
    last_name = parts[-1]

    return {
        "id": f"GOV-{gov['state']}",
        "slug": slugify(full_name),
        "firstName": first_name,
        "lastName": last_name,
        "fullName": full_name,
        "party": gov["party"],
        "state": gov["state"],
        "fipsCode": make_state_fips(gov["state"]),
        "stance": "silent",
        "stanceSummary": "No public position on impeachment recorded.",
        "stanceSources": [],
        "stanceUpdatedAt": "",
        "phone": gov.get("phone"),
        "email": None,
        "website": gov.get("website"),
        "officeAddress": None,
        "districtOffices": [],
        "twitter": None,
        "facebook": None,
        "termStart": gov.get("took_office", ""),
    }


def main():
    print("Building governor data...")
    governors = [build_governor(g) for g in GOVERNORS]
    governors.sort(key=lambda g: g["state"])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(governors, f, indent=2)

    print(f"  Governors: {len(governors)} -> {OUTPUT}")

    # Verify all 50 states
    states = {g["state"] for g in governors}
    missing = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"} - states
    if missing:
        print(f"  WARNING: Missing governors for: {', '.join(sorted(missing))}")
    else:
        print("  All 50 states covered.")


if __name__ == "__main__":
    main()

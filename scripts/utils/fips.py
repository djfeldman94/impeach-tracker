"""State abbreviation to FIPS code mapping."""

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "FL": "12", "GA": "13",
    "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
    "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
    "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29",
    "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
    "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45",
    "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50",
    "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
    # Territories
    "DC": "11", "AS": "60", "GU": "66", "MP": "69", "PR": "72", "VI": "78",
}

# At-large states (single congressional district) — use '00' in Census data
AT_LARGE_STATES = {"AK", "DE", "ND", "SD", "VT", "WY"}

# Territories/DC use '98' for non-voting delegate districts in Census data
DELEGATE_DISTRICT_STATES = {"DC", "AS", "GU", "MP", "PR", "VI"}


def make_district_fips(state_abbr: str, district: int | None) -> str:
    """Build a 4-char FIPS code matching Census GEOID format (SSDD).

    At-large states use '00'. Territories/DC use '98' (non-voting delegate).
    """
    state_fips = STATE_FIPS.get(state_abbr, "")
    if not state_fips:
        return ""
    if state_abbr in DELEGATE_DISTRICT_STATES:
        return f"{state_fips}98"
    if district is None or district == 0 or state_abbr in AT_LARGE_STATES:
        return f"{state_fips}00"
    return f"{state_fips}{district:02d}"


def make_state_fips(state_abbr: str) -> str:
    """Return the 2-char state FIPS code."""
    return STATE_FIPS.get(state_abbr, "")

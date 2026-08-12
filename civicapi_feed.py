"""
civicAPI live feed for the South Carolina Republican Senate Primary.

Endpoint:  https://civicapi.org/api/v2/race/{race_id}
Race:      TODO -- no race ID yet. RACE_ID below is a placeholder; fetch_race
           will raise clearly if called before this is set to a real ID.
Auth:      none. Attribution required for non-personal use, so credit
           civicapi.org anywhere this output is published.

Structurally identical to the MN Governor client (same schema pattern, same
UNVERIFIED-until-a-real-race-exists caveat -- get a sample payload early
once civicAPI opens this race).

SIX-WAY, MORE THAN ANY PRIOR CLIENT IN THIS FAMILY. GRAHAM_KEYS / NORMAN_KEYS
/ FRY_KEYS / SANFORD_KEYS / LYNCH_KEYS match by substring same as before;
everyone else in the field is summed into "other" and KEPT (matching the
baseline's real Other bucket), same pattern as the MN Governor client.
"""

import re
import time
import unicodedata

try:
    import requests
except ImportError:
    requests = None

API_BASE = "https://civicapi.org/api/v2"
SC_SENATE_GOP_PRIMARY = 86330  # 2026 South Carolina US Senate Special --
                                # civicapi.org/results/elections/86330. The
                                # results page is a client-rendered SPA
                                # (no JSON in the initial HTML), so this ID
                                # is confirmed to EXIST but NOT verified
                                # against the actual /api/v2/race/86330
                                # payload -- and its title says "Special",
                                # not "Primary". South Carolina special
                                # elections run their own primary phase, so
                                # this is very likely the right race, but
                                # confirm on first deploy that the payload's
                                # candidate list is the five-way GOP primary
                                # field (Graham/Norman/Fry/Sanford/Lynch) and
                                # not the special election overall or a
                                # different phase of it. Watch the first
                                # Render deploy's logs (DEPLOY.md Part 2.3).

# Substring match keys -- VERIFY against the actual payload once reachable.
GRAHAM_KEYS = ("graham",)
NORMAN_KEYS = ("norman",)
FRY_KEYS = ("fry",)
SANFORD_KEYS = ("sanford",)
LYNCH_KEYS = ("lynch",)

CANDIDATES = ("graham", "norman", "fry", "sanford", "lynch", "other")

REQUEST_TIMEOUT = 15
MAX_RETRIES = 4


def normalize_county(name: str) -> str:
    """Same normalization as every prior build: handles 'St. Louis'-style
    punctuation quirks (not that SC has one, but the feed's formatting
    habits are the same civicAPI-wide), a trailing 'County', and accents."""
    if name is None:
        return ""
    text = unicodedata.normalize("NFKD", str(name))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"\bcounty\b", " ", text)
    text = text.replace(".", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def build_county_lookup(county_names) -> dict:
    return {normalize_county(c): c for c in county_names}


def fetch_race(race_id=SC_SENATE_GOP_PRIMARY, timeout: int = REQUEST_TIMEOUT,
               max_retries: int = MAX_RETRIES, session=None) -> dict:
    """GET a race payload, retrying on transient failure with backoff.
    Raises immediately if race_id is still the None placeholder, rather
    than sending a request that can't possibly work."""
    if race_id is None:
        raise RuntimeError(
            "SC_SENATE_GOP_PRIMARY / RACE_ID is not set -- get the real "
            "civicAPI race ID for this primary and set it before deploying.")
    if requests is None:
        raise RuntimeError("requests is not installed: pip install requests")

    url = "{}/race/{}".format(API_BASE, race_id)
    getter = session.get if session is not None else requests.get
    last_error = None

    for attempt in range(max_retries):
        try:
            response = getter(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    raise RuntimeError("civicAPI fetch failed after {} attempts: {}".format(
        max_retries, last_error))


def _match_one(name: str, keys: tuple) -> bool:
    lowered = str(name).lower()
    return any(k in lowered for k in keys)


def extract_six_way(candidate_list: list) -> tuple:
    """Pull Graham/Norman/Fry/Sanford/Lynch votes out of a candidate array;
    everyone else is summed into 'other' and kept. Returns
    (votes_dict, matched_names)."""
    votes = {c: 0 for c in CANDIDATES}
    matched = {"graham": None, "norman": None, "fry": None,
               "sanford": None, "lynch": None}

    for entry in candidate_list or []:
        name = entry.get("name", "")
        n = int(entry.get("votes") or 0)
        if _match_one(name, GRAHAM_KEYS):
            votes["graham"] += n
            matched["graham"] = name
        elif _match_one(name, NORMAN_KEYS):
            votes["norman"] += n
            matched["norman"] = name
        elif _match_one(name, FRY_KEYS):
            votes["fry"] += n
            matched["fry"] = name
        elif _match_one(name, SANFORD_KEYS):
            votes["sanford"] += n
            matched["sanford"] = name
        elif _match_one(name, LYNCH_KEYS):
            votes["lynch"] += n
            matched["lynch"] = name
        else:
            votes["other"] += n

    return votes, matched


def normalize_pct_reporting(value):
    """civicAPI's percent_reporting field format was never confirmed
    against a real payload (see this module's docstring), and the live
    data strongly suggests it's on a 0-100 SCALE, not the 0-1 FRACTION
    every pct_reporting consumer in this codebase assumes -- observed
    symptom: projected turnout collapsing to almost exactly 0.4x baseline
    (the TURNOUT_CLAMP floor) almost immediately, which is exactly what
    happens when implied_turnout = counted_votes / pct_reporting divides
    by a number ~100x too large. Any value > 1 is treated as a percentage
    and divided by 100; values already <= 1 (a real fraction, or 0) pass
    through unchanged. Remove this the moment the real payload format is
    confirmed and this turns out to be unnecessary (or wrong)."""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value / 100.0 if value > 1.0 else value


def parse_payload(payload: dict, county_names) -> dict:
    """Turn a civicAPI race payload into county-level six-way vote counts."""
    lookup = build_county_lookup(county_names)

    state_votes, matched_names = extract_six_way(payload.get("candidates"))

    records = {}
    unmatched = []

    for _slug, region in (payload.get("region_results") or {}).items():
        if str(region.get("type", "")).lower() not in ("county", ""):
            continue
        raw_name = region.get("name", _slug)
        key = normalize_county(raw_name)
        county = lookup.get(key)
        if county is None:
            unmatched.append(raw_name)
            continue

        votes, _ = extract_six_way(region.get("candidates"))
        if sum(votes.values()) <= 0:
            continue

        records[county] = {
            "votes": votes,
            "percent_precincts": normalize_pct_reporting(region.get("percent_reporting")),
        }

    return {
        "election_name": payload.get("election_name"),
        "last_updated": payload.get("last_updated"),
        "percent_precincts_statewide": normalize_pct_reporting(payload.get("percent_reporting")),
        "state_votes": state_votes,
        "candidate_names": matched_names,
        "counties": records,
        "unmatched": unmatched,
    }

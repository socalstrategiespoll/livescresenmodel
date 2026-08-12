"""
Aiken County ONLY feed -- South Carolina's own SOS Election Night
Reporting site (enr-scvotes.org), used to work around a civicAPI glitch
specific to Aiken County. Every other county keeps coming from civicAPI
via civicapi_feed.py; this module touches Aiken and nothing else.

SOURCE URL (Wilson-supplied):
  https://www.enr-scvotes.org/SC/127017/web.345435/#/detail/26001
  -- election 127017, contest/detail id 26001 in the site's own scheme.

enr-scvotes.org disallows automated fetches via robots.txt, and its
results page is a client-rendered SPA, so THE ENDPOINTS BELOW ARE NOT
VERIFIED against a real payload -- unlike civicapi_feed.py (which at
least had a reachable results page to confirm a race ID against), nothing
here has been confirmed to work. This is built against the documented
Clarity/Scytl schema (the same election-reporting platform used at
results.enr.clarityelections.com elsewhere, which enr-scvotes.org is a
white-labeled instance of), matching the same pattern this family's own
clarity_feed.py (Michigan build) uses:
  1. GET {BASE}/current_ver.txt -> a version string
  2. GET {BASE}/{ver}/json/en/summary.json -> race list, no per-county detail
  3. GET {BASE}/{ver}/reports/detailxml.zip -> unzips to detail.xml, which
     has the real per-county breakdown: each candidate <Choice> contains
     one or more <VoteType> blocks (Election Day / Absentee / etc.), each
     of which contains a <County name="..." votes="..."/> row per county.
     Summing a candidate's County="Aiken" rows across all its VoteType
     blocks gives Aiken's count for that candidate.

BASE below is a guess at where those three endpoints sit relative to the
detail-page URL Wilson gave (stripping the #/detail/26001 SPA route,
which is client-side only and not itself a fetchable resource). CONFIRM
ALL OF THIS against a real response before trusting it live -- watch the
first Render deploy's logs (matching the family convention: "watch the
matched: line").

GATING: unlike the family's Detroit/Clarity sub-feeds (which require
agreement with civicAPI before applying, since disagreement there usually
means the two feeds describe different sets of ballots), THIS feed is
being used BECAUSE civicAPI is already known to be glitching for Aiken --
so it intentionally overrides civicAPI's Aiken numbers unconditionally
rather than requiring agreement. If SOS and civicAPI disagree on Aiken,
that disagreement is logged, not treated as a reason to fall back.
"""

import re
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
import io

try:
    import requests
except ImportError:
    requests = None

# Strip the SPA hash route -- everything after '#' is client-side only.
BASE = "https://www.enr-scvotes.org/SC/127017/web.345435"

TARGET_COUNTY = "Aiken"

# Same substring-match convention as civicapi_feed.py -- keep these two
# files' *_KEYS in sync if one gets corrected against a real payload.
GRAHAM_KEYS = ("graham",)
NORMAN_KEYS = ("norman",)
FRY_KEYS = ("fry",)
SANFORD_KEYS = ("sanford",)
LYNCH_KEYS = ("lynch",)
CANDIDATES = ("graham", "norman", "fry", "sanford", "lynch", "other")

# UNVERIFIED -- the actual contest text in this election's detail.xml may
# read differently (e.g. "U.S. Senate" vs "United States Senator"). Set
# from the first real fetch's contest list; matching is substring/lowercase.
CONTEST_TEXT_HINTS = ("senate", "senator")

REQUEST_TIMEOUT = 15
MAX_RETRIES = 3


def _get(session, url, timeout=REQUEST_TIMEOUT, max_retries=MAX_RETRIES):
    if requests is None:
        raise RuntimeError("requests is not installed: pip install requests")
    getter = session.get if session is not None else requests.get
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = getter(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"SOS feed fetch failed for {url} after {max_retries} attempts: {last_error}")


def fetch_current_version(session=None) -> str:
    resp = _get(session, f"{BASE}/current_ver.txt")
    return resp.text.strip()


def fetch_detail_xml(version: str, session=None) -> bytes:
    """Downloads and unzips reports/detailxml.zip, returns the raw detail.xml bytes."""
    resp = _get(session, f"{BASE}/{version}/reports/detailxml.zip")
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_names:
            raise RuntimeError("detailxml.zip contained no .xml file -- unexpected archive layout")
        return zf.read(xml_names[0])


def _match_one(name: str, keys: tuple) -> bool:
    return any(k in str(name).lower() for k in keys)


def _find_senate_contest(root: ET.Element) -> ET.Element:
    contests = root.findall(".//Contest")
    matches = [c for c in contests if any(h in str(c.get("text", "")).lower() for h in CONTEST_TEXT_HINTS)]
    if not matches:
        available = [c.get("text") for c in contests]
        raise RuntimeError(
            f"No contest matched CONTEST_TEXT_HINTS={CONTEST_TEXT_HINTS} -- "
            f"available contests in this detail.xml: {available}. "
            f"Update CONTEST_TEXT_HINTS in aiken_sos_feed.py."
        )
    if len(matches) > 1:
        raise RuntimeError(
            f"CONTEST_TEXT_HINTS matched {len(matches)} contests, expected exactly one: "
            f"{[c.get('text') for c in matches]}. Narrow CONTEST_TEXT_HINTS."
        )
    return matches[0]


def parse_aiken_votes(detail_xml_bytes: bytes) -> dict:
    """Returns {'votes': {candidate: int, ...}, 'matched_names': {...}} for
    Aiken County ONLY, summed across all VoteType blocks (Election Day,
    Absentee, etc.) for the matched Senate contest."""
    root = ET.fromstring(detail_xml_bytes)
    contest = _find_senate_contest(root)

    votes = {c: 0 for c in CANDIDATES}
    matched = {"graham": None, "norman": None, "fry": None, "sanford": None, "lynch": None}

    for choice in contest.findall("Choice"):
        name = choice.get("text", "")
        aiken_total = 0
        for vote_type in choice.findall("VoteType"):
            for county_el in vote_type.findall("County"):
                if county_el.get("name", "").strip().lower() == TARGET_COUNTY.lower():
                    aiken_total += int(county_el.get("votes") or 0)

        if _match_one(name, GRAHAM_KEYS):
            votes["graham"] += aiken_total
            matched["graham"] = name
        elif _match_one(name, NORMAN_KEYS):
            votes["norman"] += aiken_total
            matched["norman"] = name
        elif _match_one(name, FRY_KEYS):
            votes["fry"] += aiken_total
            matched["fry"] = name
        elif _match_one(name, SANFORD_KEYS):
            votes["sanford"] += aiken_total
            matched["sanford"] = name
        elif _match_one(name, LYNCH_KEYS):
            votes["lynch"] += aiken_total
            matched["lynch"] = name
        else:
            votes["other"] += aiken_total

    return {"votes": votes, "matched_names": matched}


def fetch_aiken(session=None) -> dict:
    """Full cycle: version -> detail.xml -> Aiken-only vote extraction.
    Returns None-safe dict; raises on any failure so the caller can log
    and fall back to whatever civicAPI last had for Aiken."""
    version = fetch_current_version(session)
    xml_bytes = fetch_detail_xml(version, session)
    result = parse_aiken_votes(xml_bytes)
    result["version"] = version
    return result

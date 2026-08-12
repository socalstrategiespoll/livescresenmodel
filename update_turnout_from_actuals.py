"""
Recalibrate sc_senate_gop_primary_baseline.csv's turnout column from
manually-supplied reporting-county totals -- NOT from civicAPI.

WHY THIS EXISTS. civicAPI's percent_reporting/vote totals for this race
were unreliable enough that Wilson supplied a hand-verified snapshot
instead (county, votes-so-far, percent-of-precincts-in) for the counties
already reporting. This script turns that snapshot into a corrected
turnout column for the ENTIRE baseline -- both the counties in the
snapshot and the ones not yet reporting -- and does NOT touch the
candidate share columns (graham/norman/fry/sanford/lynch/other) at all.

METHOD
1. For each county IN the snapshot: implied_turnout = votes / pct_in.
   This is the same math County.recalibrate_turnout() does live in
   south_carolina_senate_model.py, just applied here as a one-time batch
   correction to the baseline file instead of at runtime.
2. ratio = implied_turnout / that county's OLD baseline turnout, clamped to
   [0.5, 2.0] so one noisy small-sample county can't produce an absurd
   ratio.
3. A size-weighted (by old baseline turnout) MEDIAN of those ratios --
   not a mean, so a single outlier can't drag the correction around --
   is computed and applied to every county NOT in the snapshot, so the
   turnout correction observed in the ~80% of the state that's reporting
   propagates to the rest rather than leaving it on the old, likely-stale
   projection.
4. Candidate vote-count columns are recomputed under the new turnout at
   each county's existing (unchanged) percentage shares.

RUNNING THIS AGAIN LATER: paste a fresher snapshot into ACTUALS_RAW below
(same three-column format) and rerun. Every county not present in
ACTUALS_RAW is treated as "not yet reporting" and gets the propagated
ratio, so a snapshot doesn't need to cover all 46 counties every time.

RELATIONSHIP TO THE LIVE MODEL: south_carolina_senate_model.py's own
County.recalibrate_turnout() will still recompute a county's
effective_turnout from civicAPI's OWN percent_reporting the next time
civicAPI reports data for that county through update_county() -- this
script only corrects the static baseline file the model loads at startup.
If civicAPI's numbers are being distrusted broadly rather than just at
this moment, that live recalculation needs to be disabled or bypassed
separately (e.g. routing real updates through
SouthCarolinaSenateModel.update_turnout_estimate() instead of
update_county(), which recalibrates turnout only, without asserting a
per-candidate split) -- worth flagging back to Wilson rather than assuming.
"""

import pandas as pd

CANDIDATES = ["graham", "norman", "fry", "sanford", "lynch", "other"]
BASELINE_PATH = "sc_senate_gop_primary_baseline.csv"
RATIO_CLAMP = (0.5, 2.0)

# Wilson-supplied actual reporting-county totals.
# Format: county,votes_so_far,pct_in (fraction; ">95%"-style entries used
# their stated threshold, e.g. ">95%" -> 0.95, as a conservative floor)
ACTUALS_RAW = """Horry,17776,0.53
Spartanburg,12879,0.61
Anderson,10162,0.48
Greenville,6505,0.14
Lancaster,6474,0.86
Berkeley,5873,0.65
Oconee,5641,0.62
Pickens,5619,0.50
Lexington,4862,0.22
Dorchester,4662,0.57
Laurens,4379,0.85
Richland,4242,0.29
Georgetown,4039,0.66
Beaufort,3521,0.27
Kershaw,3478,0.90
Sumter,2677,0.72
Florence,2639,0.34
Darlington,2596,0.70
Charleston,2045,0.09
Greenwood,1900,0.38
York,1875,0.12
Chesterfield,1776,0.95
Cherokee,1739,0.39
Dillon,1236,0.89
McCormick,1212,0.95
Barnwell,912,0.95
Newberry,771,0.21
Marlboro,663,0.95
Williamsburg,638,0.74
Lee,634,0.82
Clarendon,615,0.26
Colleton,615,0.29
Marion,556,0.53
Union,501,0.24
Bamberg,373,0.95
Orangeburg,340,0.13
Hampton,201,0.65"""


def weighted_median(values, weights):
    order = values.argsort()
    v_sorted, w_sorted = values[order], weights[order]
    cum = w_sorted.cumsum()
    half = cum[-1] / 2
    return float(v_sorted[cum.searchsorted(half)])


def recalibrate(baseline_path=BASELINE_PATH, actuals_raw=ACTUALS_RAW) -> pd.DataFrame:
    actual = pd.DataFrame(
        [line.split(",") for line in actuals_raw.strip().splitlines()],
        columns=["county", "votes", "pct_in"],
    ).set_index("county")
    actual["votes"] = actual["votes"].astype(int)
    actual["pct_in"] = actual["pct_in"].astype(float)
    actual["implied_turnout"] = actual["votes"] / actual["pct_in"]

    baseline = pd.read_csv(baseline_path).set_index("county")
    old_turnout = baseline["turnout"].astype(float).copy()

    missing = [c for c in old_turnout.index if c not in actual.index]
    unknown = [c for c in actual.index if c not in old_turnout.index]
    if unknown:
        raise ValueError(f"ACTUALS_RAW has county names not in the baseline: {unknown}")

    ratio = (actual["implied_turnout"] / old_turnout.loc[actual.index]).clip(*RATIO_CLAMP)
    median_ratio = weighted_median(ratio.to_numpy(), old_turnout.loc[actual.index].to_numpy())

    new_turnout = old_turnout.copy()
    new_turnout.loc[actual.index] = actual["implied_turnout"].round()
    new_turnout.loc[missing] = (old_turnout.loc[missing] * median_ratio).round()

    out = baseline.copy()
    out["turnout"] = new_turnout.astype(int)
    for cand in CANDIDATES:
        out[f"{cand}_votes"] = (out["turnout"] * out[cand] / 100).round().astype(int)

    return out, median_ratio, missing


if __name__ == "__main__":
    out, median_ratio, missing = recalibrate()
    print(f"size-weighted median turnout ratio (reporting counties): {median_ratio:.4f}")
    print(f"propagated to {len(missing)} not-yet-reporting counties: {missing}")
    old_total = pd.read_csv(BASELINE_PATH)["turnout"].sum()
    print(f"\nStatewide turnout: {old_total:,} -> {out['turnout'].sum():,}")
    out.round(3).to_csv(BASELINE_PATH)
    print(f"\nWrote {BASELINE_PATH}")

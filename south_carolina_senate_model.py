"""
South Carolina Republican Senate Primary -- live county-level model.
Graham vs. Norman vs. Fry vs. Sanford vs. Lynch (+ Other), fed by civicAPI.

SIX-WAY, MORE CANDIDATES THAN ANY PRIOR BUILD IN THIS FAMILY. Every field
that used to be a two-candidate margin or a four-candidate share vector
(Michigan, Wisconsin, South Dakota, MN Senate, MN Governor) is now a
six-entry dict keyed by CANDIDATES everywhere. Nothing here assumes any
fixed number of candidates beyond that constant.

WHAT'S DIFFERENT FROM EVERY PRIOR MODEL IN THIS FAMILY: SC RUNS A RUNOFF.
No candidate needs to be projected as "the winner" on election night --
they need to clear 50% outright, or they don't, and the two highest
finishers meet again. So on top of the usual blended point-estimate
projection, every cycle also runs a Monte Carlo simulation whose real
purpose is answering two questions a plain point estimate can't:
  (1) P(runoff)   -- probability nobody clears 50% statewide
  (2) P(advance)  -- probability each candidate finishes top two
Both converge to 0/100 as reporting completes (see UNCERTAINTY SHRINKAGE
below), so they're genuinely live, not just a pre-election fixed number
that a results page ignores once votes start coming in.

ARCHITECTURE (same three pieces as every model in this family, but with
DEDUCTIVE remainder projection rather than a full-county blend -- see
below for why this build differs from the rest of the family here)
1. BASELINE -- sc_senate_gop_primary_baseline.csv from build_sc_senate_baseline.py,
   itself built from four different coalition-proxy source races (see that
   file's docstring). This is a rougher foundation than a real poll.
2. DEDUCTIVE COUNTY PROJECTION -- a county's counted votes are held FIXED,
   exactly as reported, for every candidate. Only the REMAINING uncounted
   portion of that county is projected, as a credibility-weighted blend of
   the county's own raw observed shares and a (shift-adjusted) baseline:
       remainder_shares = credibility * raw_shares + (1 - credibility) * shifted_baseline
   where credibility grows from 0 toward 1 as more of the county reports
   (pct_counted ** CREDIBILITY_EXPONENT) -- i.e. credibility is literally
   "how close the still-uncounted votes should be assumed to run to the
   votes already in." The county's final projected total is then
       final_votes[cand] = counted_votes[cand] + remaining_votes * remainder_shares[cand]
   At 0% reporting, credibility is 0 and the whole county (all of it
   "remaining") is projected at the shifted baseline. At 100% reporting,
   remaining is 0 and the county's projection is exactly its counted
   votes -- nothing else can move it. A single large county partially in
   is capped (MAX_SINGLE_COUNTY_SHARE) so it can't dominate the statewide
   SHIFT below on its own.
3. STATEWIDE SHIFT -- an evidence-weighted deviation (reporting counties'
   observed shares vs. their baseline shares) shrunk toward zero by
   GLOBAL_EVIDENCE_PRIOR, then applied to the REMAINDER expectation of
   every county (reporting or not) before blending. A genuine multi-county
   pattern moves the shift well before 100% is in; one outlier county
   mostly doesn't.
4. TURNOUT RECALIBRATION -- civicAPI's percent_reporting counts PRECINCTS,
   not votes, so counted_votes / pct_reporting gives a feed-implied total
   turnout for that county that can be compared against the baseline
   projection. This ONLY happens when pct_reporting is a real nonzero
   value (County.recalibrate_turnout, called from update_county) -- with
   no percent_reporting, effective_turnout is left exactly where it was;
   there's nothing to divide by and no signal to act on. When it IS
   nonzero, the implied turnout is clamped to TURNOUT_CLAMP (0.40x-2.50x
   the baseline) and ramped in by TURNOUT_FULL_TRUST_PCT so one precinct's
   worth of an early batch can't imply a wild county total. This feeds
   directly into the deductive remainder calculation above --
   remaining_votes = effective_turnout - counted_votes -- so a county
   whose real turnout is running above or below its baseline projection
   gets a correspondingly larger or smaller remainder to project, not just
   a corrected total.

UNCERTAINTY SHRINKAGE (new for this build). SIGMA_STATE and SIGMA_COUNTY
(the Monte Carlo shock SDs -- see simulate_sc_senate.py for the original
pre-election-only version this generalizes) are multiplied by
sqrt(1 - reported_fraction) each cycle, where reported_fraction is total
counted votes / total projected turnout. At 0% in, the sim runs at full
pre-election uncertainty. As the state fills in, the shock shrinks toward
zero and the sim collapses onto the point-estimate projection -- so
P(runoff) and P(advance) converge to a hard 0 or 100 exactly when the
state finishes counting, not before.

REGIONS (added for this build, no prior source data) -- four geographic
groupings (Upstate, Midlands, Pee Dee, Lowcountry) for the site's regional
swing panel, assigned by whole-county convention, not an official
Election Commission grouping. Purely a diagnostic display, doesn't feed
into the model math anywhere.
"""

import numpy as np
import pandas as pd

CANDIDATES = ["graham", "norman", "fry", "sanford", "lynch", "other"]
REFERENCE = "other"

REGIONS = {
    "Upstate": ["Greenville", "Spartanburg", "Anderson", "Pickens", "Oconee",
                "Cherokee", "Union", "Laurens", "Newberry", "Abbeville",
                "Greenwood", "McCormick", "Edgefield", "Saluda"],
    "Midlands": ["Richland", "Lexington", "Kershaw", "Fairfield", "Chester",
                 "Lancaster", "Sumter", "Calhoun", "Clarendon", "York"],
    "Pee Dee": ["Florence", "Darlington", "Marion", "Marlboro", "Dillon",
                "Chesterfield", "Horry", "Georgetown", "Williamsburg"],
    "Lowcountry": ["Charleston", "Berkeley", "Dorchester", "Beaufort",
                   "Colleton", "Jasper", "Hampton", "Allendale", "Bamberg",
                   "Barnwell", "Orangeburg"],
}
COUNTY_REGION = {c: r for r, cs in REGIONS.items() for c in cs}

GLOBAL_EVIDENCE_PRIOR = 55_000     # votes of evidence before the shift trusts
                                    # observed results over the baseline
REGIONAL_EVIDENCE_PRIOR = 9_000
MAX_SINGLE_COUNTY_SHARE = 0.20     # cap on one county's share of total evidence weight
CREDIBILITY_EXPONENT = 2.0

SIGMA_STATE_0 = 0.22               # pre-election statewide shock SD (logit scale)
SIGMA_COUNTY_0 = 0.35              # pre-election county idiosyncratic shock SD
RUNOFF_THRESHOLD = 50.0
N_SIMS = 20_000

TURNOUT_CLAMP = (0.40, 2.50)       # feed-implied turnout can't move a county's
                                    # effective turnout outside 0.40x-2.50x
                                    # its baseline projection, no matter what
                                    # the feed says -- guards against a
                                    # garbage/partial percent_reporting value
TURNOUT_FULL_TRUST_PCT = 0.25      # precincts-reporting fraction at which the
                                    # feed-implied turnout is fully trusted;
                                    # below that it's blended toward the
                                    # baseline turnout, since counted/pct_in
                                    # is noisy on a tiny initial batch


class County:
    def __init__(self, name, region, baseline_shares, turnout):
        self.name = name
        self.region = region
        self.baseline_shares = dict(baseline_shares)   # pct, sums to 100
        self.baseline_turnout = turnout                 # fixed, from the CSV -- never changes
        self.effective_turnout = turnout                # recalibrated live, see update_county
        self.votes = {c: 0 for c in CANDIDATES}
        self.counted_votes = 0
        self.pct_reporting = 0.0
        self.is_first_batch = False

    @property
    def pct_counted(self):
        if self.effective_turnout <= 0:
            return 0.0
        return min(1.0, self.counted_votes / self.effective_turnout)

    @property
    def raw_shares(self):
        if self.counted_votes <= 0:
            return None
        return {c: 100.0 * self.votes[c] / self.counted_votes for c in CANDIDATES}

    @property
    def credibility(self):
        return self.pct_counted ** CREDIBILITY_EXPONENT

    @property
    def evidence_weight(self):
        return self.counted_votes

    def recalibrate_turnout(self, total_votes=None, pct_reporting=None):
        """Feed-implied turnout = total_votes / pct_reporting, used ONLY
        when pct_reporting is a real nonzero value -- a live feed's
        percent_reporting counts precincts, not votes, so a tiny early
        batch (e.g. one precinct in) can imply a wild total; that's why
        this is clamped to TURNOUT_CLAMP and ramped in by
        TURNOUT_FULL_TRUST_PCT rather than trusted outright. If
        pct_reporting is 0/None, effective_turnout is left exactly as it
        was (the baseline, or whatever was last calibrated) -- there is
        nothing to divide by and no reason to move it.

        total_votes/pct_reporting default to this county's own
        counted_votes/pct_reporting (the normal live-feed path via
        update_county), but can be passed explicitly -- see
        SouthCarolinaSenateModel.update_turnout_estimate, which recalibrates
        turnout ONLY, from a manually-supplied total, without asserting
        anything about the per-candidate split of those votes."""
        total_votes = self.counted_votes if total_votes is None else total_votes
        pct_reporting = self.pct_reporting if pct_reporting is None else pct_reporting
        if not pct_reporting or pct_reporting <= 0:
            return
        implied = total_votes / pct_reporting
        lo, hi = TURNOUT_CLAMP[0] * self.baseline_turnout, TURNOUT_CLAMP[1] * self.baseline_turnout
        clamped = min(max(implied, lo), hi)
        trust = min(1.0, pct_reporting / TURNOUT_FULL_TRUST_PCT)
        self.effective_turnout = trust * clamped + (1 - trust) * self.baseline_turnout


class SouthCarolinaSenateModel:
    def __init__(self, baseline_path="sc_senate_gop_primary_baseline.csv"):
        df = pd.read_csv(baseline_path).set_index("county")
        self.counties = {}
        for name, row in df.iterrows():
            shares = {c: float(row[c]) for c in CANDIDATES}
            self.counties[name] = County(name, COUNTY_REGION.get(name, "Unknown"),
                                          shares, float(row["turnout"]))

    @property
    def total_turnout(self) -> float:
        """Live sum of every county's current effective_turnout -- recomputed
        each call rather than fixed at init, since recalibrate_turnout()
        can move individual counties' turnout as results come in."""
        return sum(c.effective_turnout for c in self.counties.values())

    def update_county(self, name, votes: dict, pct_reporting=None):
        if name not in self.counties:
            return
        c = self.counties[name]
        was_zero = c.counted_votes == 0
        c.votes = {cand: int(votes.get(cand, 0)) for cand in CANDIDATES}
        c.counted_votes = sum(c.votes.values())
        if pct_reporting is not None:
            c.pct_reporting = pct_reporting
        c.recalibrate_turnout()
        if was_zero and c.counted_votes > 0:
            c.is_first_batch = True
        elif c.counted_votes > 0:
            c.is_first_batch = False

    def update_turnout_estimate(self, name, total_votes, pct_reporting):
        """Recalibrate ONE county's effective_turnout from a manually
        supplied total-votes-so-far figure, WITHOUT touching that county's
        per-candidate votes/credibility at all. Use this when a total +
        percent-in is trusted (e.g. hand-verified county results) but a
        six-way candidate breakdown isn't available or isn't trusted --
        unlike update_county, this never marks the county as reporting for
        share-blending purposes; it only sharpens how much of that
        county's vote pool is left to project."""
        if name not in self.counties:
            return
        c = self.counties[name]
        c.pct_reporting = pct_reporting
        c.recalibrate_turnout(total_votes=total_votes, pct_reporting=pct_reporting)

    # ---- statewide shift -------------------------------------------------


    def statewide_shift(self) -> dict:
        """Evidence-weighted deviation of observed vs. baseline shares,
        shrunk toward zero by GLOBAL_EVIDENCE_PRIOR. Any single county's
        evidence weight is capped at MAX_SINGLE_COUNTY_SHARE of the total
        so one big county can't masquerade as a statewide pattern."""
        reporting = [c for c in self.counties.values() if c.counted_votes > 0]
        if not reporting:
            return {c: 0.0 for c in CANDIDATES}

        raw_weights = {c.name: c.evidence_weight for c in reporting}
        total_w = sum(raw_weights.values())
        cap = MAX_SINGLE_COUNTY_SHARE * total_w if total_w > 0 else 0
        capped = {n: min(w, cap) if cap > 0 else w for n, w in raw_weights.items()}
        capped_total = sum(capped.values())

        shift = {cand: 0.0 for cand in CANDIDATES}
        if capped_total <= 0:
            return shift
        for c in reporting:
            raw = c.raw_shares
            w = capped[c.name]
            for cand in CANDIDATES:
                shift[cand] += w * (raw[cand] - c.baseline_shares[cand])
        shrink = capped_total / (capped_total + GLOBAL_EVIDENCE_PRIOR)
        for cand in CANDIDATES:
            shift[cand] = shrink * (shift[cand] / capped_total)
        return shift

    def regional_shift(self) -> dict:
        out = {}
        for region, names in REGIONS.items():
            reporting = [self.counties[n] for n in names if self.counties[n].counted_votes > 0]
            shift = {cand: 0.0 for cand in CANDIDATES}
            total_w = sum(c.evidence_weight for c in reporting)
            if total_w > 0:
                for c in reporting:
                    raw = c.raw_shares
                    w = c.evidence_weight
                    for cand in CANDIDATES:
                        shift[cand] += w * (raw[cand] - c.baseline_shares[cand])
                shrink = total_w / (total_w + REGIONAL_EVIDENCE_PRIOR)
                for cand in CANDIDATES:
                    shift[cand] = shrink * (shift[cand] / total_w)
            out[region] = shift
        return out

    # ---- per-county deductive projection -----------------------------------

    def remainder_shares(self, county: "County") -> dict:
        """The projected split of that county's STILL-UNCOUNTED votes only
        -- not its final total. credibility=0 -> pure shifted baseline;
        credibility=1 -> exactly the county's own raw shares so far."""
        shift = self.statewide_shift()
        rshift = self.regional_shift().get(county.region, {cand: 0.0 for cand in CANDIDATES})
        shifted_baseline = {}
        for cand in CANDIDATES:
            shifted_baseline[cand] = county.baseline_shares[cand] + 0.5 * shift[cand] + 0.5 * rshift[cand]

        raw = county.raw_shares
        if raw is None:
            return shifted_baseline

        cred = county.credibility
        blended = {cand: cred * raw[cand] + (1 - cred) * shifted_baseline[cand]
                   for cand in CANDIDATES}
        total = sum(blended.values())
        return {cand: 100.0 * blended[cand] / total for cand in CANDIDATES}

    def project_shares(self, county: "County") -> dict:
        """Deductive final share for the county: counted votes held fixed
        exactly as reported, plus the projected remainder distributed
        according to remainder_shares(). At 100% reporting this returns
        precisely the raw counted shares -- nothing else can move it."""
        remaining = max(0.0, county.effective_turnout - county.counted_votes)
        if remaining <= 0 and county.counted_votes > 0:
            return county.raw_shares

        rem_shares = self.remainder_shares(county)
        final_votes = {
            cand: county.votes[cand] + remaining * rem_shares[cand] / 100.0
            for cand in CANDIDATES
        }
        total = sum(final_votes.values())
        if total <= 0:
            return rem_shares
        return {cand: 100.0 * final_votes[cand] / total for cand in CANDIDATES}

    def blended_baseline_frame(self) -> pd.DataFrame:
        """Every county's current deductive projection, as a DataFrame
        indexed by county -- this is what the Monte Carlo sim shocks
        around.""" 
        rows = []
        for name, c in self.counties.items():
            row = {"county": name, "turnout": c.effective_turnout}
            row.update(self.project_shares(c))
            rows.append(row)
        return pd.DataFrame(rows).set_index("county")

    # ---- point-estimate statewide projection -------------------------------

    def project(self) -> dict:
        frame = self.blended_baseline_frame()
        votes = {}
        for cand in CANDIDATES:
            votes[cand] = (frame[cand] / 100.0 * frame["turnout"]).sum()
        total_votes = sum(votes.values())
        pct = {cand: 100.0 * votes[cand] / total_votes for cand in CANDIDATES}

        pct = {c: float(v) for c, v in pct.items()}
        votes = {c: float(v) for c, v in votes.items()}
        ranked = sorted(CANDIDATES, key=lambda c: -pct[c])
        leader, runner_up = ranked[0], ranked[1]

        reported_votes = sum(c.counted_votes for c in self.counties.values())
        pct_counted_raw = reported_votes / self.total_turnout if self.total_turnout else 0.0
        pct_counted = min(1.0, pct_counted_raw)
        turnout_overshoot = pct_counted_raw > 1.02   # >102% of projected turnout already counted
        n_reported = sum(1 for c in self.counties.values() if c.counted_votes > 0)

        return {
            "pct": pct,
            "votes": votes,
            "leader": leader,
            "runner_up": runner_up,
            "lead_margin": pct[leader] - pct[runner_up],
            "runoff_needed_point_estimate": bool(pct[leader] < RUNOFF_THRESHOLD),
            "projected_turnout": float(total_votes),
            "reported_votes": int(reported_votes),
            "pct_counted_raw": pct_counted_raw,
            "turnout_overshoot": turnout_overshoot,
            "pct_counted": pct_counted,
            "n_reported": n_reported,
            "statewide_shift": {c: float(v) for c, v in self.statewide_shift().items()},
            "regional_shift": {r: {c: float(v) for c, v in shifts.items()}
                                for r, shifts in self.regional_shift().items()},
            "total_evidence_weight": float(sum(c.evidence_weight for c in self.counties.values())),
        }

    # ---- Monte Carlo: P(runoff) and P(advance) -----------------------------

    def run_simulation(self, n_sims=N_SIMS, seed=None) -> dict:
        """Shocks only the UNCOUNTED remainder of each county, then adds
        each county's fixed counted votes back in -- consistent with the
        deductive projection above. A fully-counted county contributes
        zero simulation variance (remaining=0), exactly as it should."""
        counties_list = list(self.counties.keys())
        n_county = len(counties_list)

        # IMPORTANT: for an "overshoot" county (counted votes already exceed
        # its effective_turnout -- remaining <= 0), project_shares() scales
        # that county's raw split DOWN proportionally to effective_turnout
        # rather than using its true, uncapped vote counts. counted_votes
        # here has to do the exact same thing, or this simulation's
        # zero-noise baseline stops matching project()'s point estimate --
        # which is exactly the bug that flipped Norman/Fry's ranking on
        # 2026-08-12: a corrupted, massively overshot county's TRUE vote
        # counts dominated this array while project() had already
        # discounted that same county's influence. Both now treat an
        # overshoot county identically: proportionally capped to
        # effective_turnout, matching County.raw_shares' percentages.
        capped_votes = []
        for name in counties_list:
            c = self.counties[name]
            remaining_c = max(0.0, c.effective_turnout - c.counted_votes)
            if remaining_c <= 0 and c.counted_votes > 0:
                raw = c.raw_shares
                capped_votes.append([raw[cand] / 100.0 * c.effective_turnout for cand in CANDIDATES])
            else:
                capped_votes.append([c.votes[cand] for cand in CANDIDATES])
        counted_votes = np.array(capped_votes, dtype=float)
        remaining = np.array([max(0.0, self.counties[n].effective_turnout -
                                   self.counties[n].counted_votes)
                               for n in counties_list], dtype=float)
        rem_share = np.array([[self.remainder_shares(self.counties[n])[c] / 100.0
                                for c in CANDIDATES] for n in counties_list], dtype=float)

        reported_votes = sum(c.counted_votes for c in self.counties.values())
        reported_fraction = min(1.0, reported_votes / self.total_turnout) if self.total_turnout else 0.0
        shrink = np.sqrt(max(0.0, 1.0 - reported_fraction))
        sigma_state = SIGMA_STATE_0 * shrink
        sigma_county = SIGMA_COUNTY_0 * shrink

        mean_remaining = remaining[remaining > 0].mean() if (remaining > 0).any() else 1.0
        county_scale = np.sqrt(mean_remaining / np.maximum(remaining, 1.0))

        others = [c for c in CANDIDATES if c != REFERENCE]
        ref_idx = CANDIDATES.index(REFERENCE)
        base_logit = np.log(np.clip(rem_share[:, [CANDIDATES.index(c) for c in others]], 1e-6, None) /
                             np.clip(rem_share[:, [ref_idx]], 1e-6, None))

        rng = np.random.default_rng(seed)
        n_cand = len(others)

        statewide_pct = {c: np.zeros(n_sims) for c in CANDIDATES}
        for s in range(n_sims):
            if sigma_state > 0:
                state_shock = rng.normal(0, sigma_state, size=n_cand)
                county_shock = rng.normal(0, sigma_county, size=(n_county, n_cand)) * county_scale[:, None]
                logit = base_logit + state_shock[None, :] + county_shock
            else:
                logit = base_logit
            exp_logit = np.exp(logit)
            denom = 1.0 + exp_logit.sum(axis=1)
            shocked_rem_share = np.zeros((n_county, len(CANDIDATES)))
            for j, cand in enumerate(others):
                shocked_rem_share[:, CANDIDATES.index(cand)] = exp_logit[:, j] / denom
            shocked_rem_share[:, ref_idx] = 1.0 / denom

            final_votes = counted_votes + remaining[:, None] * shocked_rem_share
            total_votes = final_votes.sum(axis=0)
            pct = 100.0 * total_votes / total_votes.sum()
            for j, cand in enumerate(CANDIDATES):
                statewide_pct[cand][s] = pct[j]

        mat = np.column_stack([statewide_pct[c] for c in CANDIDATES])
        max_pct = mat.max(axis=1)
        no_runoff = max_pct >= RUNOFF_THRESHOLD
        p_runoff = float(1.0 - no_runoff.mean())

        order = np.argsort(-mat, axis=1)
        top2 = order[:, :2]

        advance, win_outright, first_place = {}, {}, {}
        median_pct, p05, p25, p75, p95 = {}, {}, {}, {}, {}
        for i, cand in enumerate(CANDIDATES):
            advance[cand] = float(np.mean(np.any(top2 == i, axis=1)))
            win_outright[cand] = float(np.mean(no_runoff & (order[:, 0] == i)))
            first_place[cand] = float(np.mean(order[:, 0] == i))
            median_pct[cand] = float(np.percentile(statewide_pct[cand], 50))
            p05[cand] = float(np.percentile(statewide_pct[cand], 5))
            p25[cand] = float(np.percentile(statewide_pct[cand], 25))
            p75[cand] = float(np.percentile(statewide_pct[cand], 75))
            p95[cand] = float(np.percentile(statewide_pct[cand], 95))

        return {
            "p_runoff": p_runoff,
            "advance": advance,
            "win_outright": win_outright,
            "first_place": first_place,
            "median_pct": median_pct,
            "p05": p05,
            "p25": p25,
            "p75": p75,
            "p95": p95,
            "sigma_state_used": sigma_state,
            "reported_fraction": reported_fraction,
        }


if __name__ == "__main__":
    model = SouthCarolinaSenateModel()
    proj = model.project()
    sim = model.run_simulation(n_sims=5000)
    print("Pre-election point estimate:")
    for cand in CANDIDATES:
        print(f"  {cand:8s} {proj['pct'][cand]:5.2f}%")
    print(f"\nP(runoff): {sim['p_runoff']*100:.2f}%")
    print("\nAdvance-to-runoff probabilities:")
    for cand in CANDIDATES:
        print(f"  {cand:8s} advance {sim['advance'][cand]*100:5.1f}%  "
              f"1st {sim['first_place'][cand]*100:5.1f}%  "
              f"median {sim['median_pct'][cand]:5.1f}%  "
              f"mid50 [{sim['p25'][cand]:5.1f}, {sim['p75'][cand]:5.1f}]  "
              f"mid90 [{sim['p05'][cand]:5.1f}, {sim['p95'][cand]:5.1f}]")

# South Carolina Republican Senate Primary — Live Model

County-level Bayesian live election-night model for the South Carolina
Republican Senate primary (Graham vs. Norman vs. Fry vs. Sanford vs. Lynch,
plus Other), fed by civicAPI once a race ID exists for it.

Results from [civicAPI](https://civicapi.org).

## SIX-WAY, plus a runoff

Every prior model in this family (Michigan, Wisconsin, South Dakota, MN
Senate, MN Governor) tracked either a two-candidate margin or a
four-candidate share vector. `south_carolina_senate_model.py` tracks a
six-entry `{graham, norman, fry, sanford, lynch, other}` share vector
everywhere. On top of that, **South Carolina requires 50%+1 to win a
primary outright** — anything else sends the top two to a runoff. So this
build is the first in the family whose headline outputs aren't just a
projected winner: every cycle also reports **P(runoff)** and each
candidate's **probability of advancing to the runoff** (finishing top two),
both from a Monte Carlo simulation layered on top of the usual
credibility-weighted county blend. See `south_carolina_senate_model.py`'s
module docstring for the full mechanics.

## How it fits together

```
civicAPI  ──►  Render web service  ──►  Cloudflare Pages
 (poll)         (model + JSON API)        (the site)
```

One backend service. It polls civicAPI on a background thread, runs the
model and the runoff simulation, and serves the result over HTTP. The site
reads that URL directly.

**This is a web service, not a cron job.** A cron container is destroyed
after every run, which wipes the credibility/shift state the model
accumulates over the night, and it has no URL for a site to read. The web
service solves both by staying alive.

## This model IS deductive

Unlike every prior build in this family (Michigan, Wisconsin, South Dakota,
MN Senate, MN Governor -- all of which explicitly blend a county's full
projection, counted votes included), this one holds each county's counted
votes **fixed exactly as reported** and only projects the still-uncounted
remainder. That remainder is a credibility-weighted blend of the county's
own raw shares so far and a (shift-adjusted) baseline, where credibility
grows from 0 toward 1 as more of the county reports -- literally "how close
the still-uncounted votes should be assumed to run to the votes already
in." At 100% reporting a county's projection is its exact counted result;
nothing else can move it. A single large county partially reporting is
capped (`MAX_SINGLE_COUNTY_SHARE`) so it can't dominate the statewide shift
on its own; a genuine multi-county pattern converges the shift toward the
real swing well before 100% reporting. The Monte Carlo runoff/advance
simulation shocks only each county's uncounted remainder too, so a
fully-counted county contributes zero simulated variance. Full reasoning in
`south_carolina_senate_model.py`'s module docstring.

## Files

| File | Does |
|---|---|
| `server.py` | background poller + JSON API. The entrypoint |
| `civicapi_feed.py` | API client, payload parsing, county name matching (six-way) |
| `south_carolina_senate_model.py` | baseline loading, credibility blending, shift shrinkage, regional shift, Monte Carlo runoff/advance simulation |
| `build_sc_senate_baseline.py` | builds `sc_senate_gop_primary_baseline.csv` from four coalition-proxy source races |
| `sc_senate_gop_primary_baseline.csv` | the 46-county baseline the model loads at startup |
| `sc-counties.geojson` | county shapes for the map -- built from the npm us-atlas counties-10m TopoJSON filtered to FIPS 45 (South Carolina) |
| `index.html` / `app.js` / `style.css` | the static site |

## Endpoints

| Route | Returns |
|---|---|
| `/health` | uptime, cycle count, last error, whether `RACE_ID` is set |
| `/api/projection` | current projection, runoff/advance probabilities, county table, diagnostics |
| `/api/history` | one compact record per cycle since start |

CORS is open, so the site can be hosted anywhere.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `RACE_ID` | civicAPI race | **unset -- see Known limitations** |
| `N_SIMS` | Monte Carlo draws | `20000` |
| `POLL_INTERVAL` | seconds between cycles | `60` |
| `STATE_DIR` | optional disk path so credibility/shift state survives a restart | unset |

## Known limitations

- **civicAPI race ID is set (86330)** but **NOT verified against the raw
  API payload** -- confirmed only via the human-facing results page at
  `civicapi.org/results/elections/86330` ("2026 South Carolina US Senate
  Special"), which renders client-side and doesn't expose the JSON.
  `/api/v2/race/86330` itself hasn't been checked, and the title says
  "Special" rather than "Primary" -- South Carolina special elections run
  their own primary phase, so this is very likely the right race, but
  confirm the candidate list on first deploy before trusting it live (see
  DEPLOY.md Part 2.3/2.4). `GRAHAM_KEYS`/`NORMAN_KEYS`/`FRY_KEYS`/
  `SANFORD_KEYS`/`LYNCH_KEYS` in `civicapi_feed.py` are still guesses at
  substring matches.
- **`percent_reporting` counts precincts, not votes**, same caution as every
  prior build in this family.
- **The baseline is a coalition-proxy construction, not a direct poll of
  this primary.** It's built from four different source races (an actual
  Graham-vs-Lynch Senate primary, Norman's own gubernatorial primary
  performance, Haley's 2024 presidential primary as a Sanford proxy with a
  district-boost adjustment, and a flat baseline for Fry boosted only in his
  home SC-07 counties). See `build_sc_senate_baseline.py`'s module
  docstring for the full method and every placeholder magnitude flagged
  there for Wilson to revisit -- in particular:
    - The SC-01/Columbia adjustment for Sanford and the SC-07 boost for Fry
      are both judgment-call multipliers, not fitted numbers.
    - **Fry has no underlying proxy race at all** -- his entire county-level
      shape comes from a flat baseline boosted in his home district. This is
      the weakest link in the baseline; replace with an actual Fry proxy
      (his own past House primary/general results by county) if one becomes
      available.
- **Runoff/advance Monte Carlo uncertainty (`SIGMA_STATE_0`, `SIGMA_COUNTY_0`
  in `south_carolina_senate_model.py`) is a judgment call, not calibrated
  against real polling error**, since none of the four baseline source races
  is an actual poll of this primary. Pre-election, this currently produces
  roughly a +/-4-5 point 90% band on Graham's and Norman's statewide share.
  Retune before trusting the live P(runoff)/advance numbers on election
  night.
- **No turnout target was specified for this race.** `TARGET_TURNOUT` in
  `build_sc_senate_baseline.py` defaults to the (also Wilson-supplied)
  Wilson/Evette runoff turnout table's own total, used only for its
  relative county shape -- rescale if there's a different expectation for
  Senate primary turnout specifically.
- **State is in memory.** A restart costs the credibility/shift calibration
  until counties report again. Set `STATE_DIR` to a mounted disk to avoid
  that.

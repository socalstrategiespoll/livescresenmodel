# Deploy: step by step

Two things to stand up.

1. **Render** runs the model and serves it at a URL. About 15 minutes.
2. **Cloudflare Pages** serves the site, which reads that URL. About 5 minutes.

No local setup, no terminal, no API tokens, no object storage. Everything happens in
three browser tabs: GitHub, Render, Cloudflare.

Everything is flat. No folders anywhere, because GitHub's web uploader does not
preserve them.

**Before you start:** there is no civicAPI race ID for this primary yet --
see README.md "Known limitations". You can deploy everything below now; the
service will start and serve the pre-election baseline (P(runoff) and
advance probabilities included) at `/api/projection`, but every poll cycle
will log `!! RACE_ID is not set` until you fill one in.

---

## Part 1 — Create the repo

1. Create a new GitHub repo, e.g. `sc-senate-gop-primary`
2. Go to `github.com/<you>/sc-senate-gop-primary/upload/main`
3. Select and drag in all of these, flattened (no `web/` folder — the three site
   files go at the repo root alongside everything else):
   ```
   README.md
   DEPLOY.md
   server.py
   civicapi_feed.py
   south_carolina_senate_model.py
   build_sc_senate_baseline.py
   sc_senate_gop_primary_baseline.csv
   sc-counties.geojson
   index.html
   app.js
   style.css
   render.yaml
   requirements.txt
   ```
4. Commit message: `Initial model and site`
5. Click **Commit changes**

### Check

Your repo should contain exactly those 13 files at the root, no folders.

---

## Part 2 — Render

### 2.1 Create the service

1. Log in at **dashboard.render.com**
2. Click **New +** in the top right
3. Choose **Blueprint**
4. If Render hasn't seen your GitHub yet, connect it and grant access to
   `sc-senate-gop-primary`
5. Select the repo
6. Render reads `render.yaml` and shows **one** service:
   `sc-senate-gop-primary-model`
7. Blueprint name: anything
8. Click **Apply** (or **Create**)

**If Render can't find `render.yaml`**, it's not at the repo root — recheck Part 1.

### 2.2 Nothing to configure yet

No secrets needed. `RACE_ID` is intentionally blank in `render.yaml` — see
"Before you start" above. Fill it in under the service's **Environment**
tab the moment civicAPI opens this race (Render redeploys automatically).

### 2.3 Watch the first build

Open the service, then the **Logs** tab. First build takes 2-4 minutes. You'll see:

```
poller started: race None every 60s, 20000 sims
!! RACE_ID is not set -- every cycle will fail until it is. See civicapi_feed.py / render.yaml.
serving on :10000
[HH:MM:SS] cycle failed, serving last good projection: SC_SENATE_GOP_PRIMARY / RACE_ID is not set -- ...
```

That's expected until a race ID exists. `/api/projection` will still 503
until the first successful cycle — this is different from every prior
build in this family, which at least had a placeholder ID to start from.

**Once you set `RACE_ID`** (see 2.2), the next deploy should show:

```
   matched: <Graham's exact name> / <Norman's exact name> / <Fry's exact name> / <Sanford's exact name> / <Lynch's exact name>
[HH:MM:SS] 0.0% counted | 0 cty | G 31.0 N 24.0 F 19.0 S 14.0 L 8.0 O 4.0 | leader graham +7.0 | P(runoff) 100.0%
```

repeating once a minute. Before polls close, `0.0% counted | 0 cty` is
correct — that's the pre-election baseline.

### 2.4 Read the log carefully. This is your only pre-flight.

**`serving on :10000`** — the HTTP server is up.

**`matched: <name> / <name> / <name> / <name> / <name>`** — the model found
all five named candidates in the civicAPI payload.

If you instead see:
```
!! CANDIDATE MATCH FAILED for ['graham', 'sanford'] -- fix the matching KEYS in civicapi_feed.py
```
the feed spells one or more names differently than the matcher expects. Fix
it on GitHub:
1. Open `civicapi_feed.py`, click the pencil icon
2. Near the top find:
   ```python
   GRAHAM_KEYS = ("graham",)
   NORMAN_KEYS = ("norman",)
   FRY_KEYS = ("fry",)
   SANFORD_KEYS = ("sanford",)
   LYNCH_KEYS = ("lynch",)
   ```
3. Add the actual spelling from the error message, lowercase
4. **Commit changes** to `main` — Render redeploys automatically

**No `!! UNMATCHED COUNTIES:` line.** If it appears, a county name in the feed
didn't match the model's 46 and got silently dropped. Fix the same way, editing
`normalize_county()` in `civicapi_feed.py`.

### 2.5 Get your URL and test it

Render shows the URL at the top of the service page, e.g.
`https://sc-senate-gop-primary-model.onrender.com`. **Copy it.**

Open in your browser:

| URL | Should show |
|---|---|
| `<your-url>/health` | `{"ok": true, "cycles": N, "race_id_set": true/false, ...}` |
| `<your-url>/api/projection` | a large JSON blob with `projection`, `runoff`, `counties`, `diagnostics` (503 until the first successful cycle) |
| `<your-url>/api/history` | a list of past cycles |

### 2.6 Plan note

`render.yaml` specifies `starter`, not `free` — Render spins free services down
after a period without traffic, and a spun-down service stops polling. Change it
in the service's **Settings** if you want to reconsider.

---

## Part 3 — Cloudflare Pages

### 3.1 Point the site at Render

1. In GitHub, open `app.js`, click the pencil icon
2. Line 1 reads:
   ```js
   const API_BASE = "https://sc-senate-gop-primary-model.onrender.com";
   ```
3. Replace with your actual Render URL from 2.5. **No trailing slash.**
4. **Commit changes** to `main`

### 3.2 Create the Pages project

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** tab
2. **Connect to Git**, authorize GitHub if prompted, grant access to
   `sc-senate-gop-primary`
3. Select the repo, click **Begin setup**

### 3.3 Build settings

| Setting | Value |
|---|---|
| Production branch | `main` |
| Framework preset | **None** |
| Build command | **leave empty** |
| Build output directory | **`/`** |
| Root directory | `/` |

No build — the site is plain files, Cloudflare just copies them. The `.py`/`.csv`
files get copied alongside `index.html` too; they're never linked to and do no harm.

4. **Save and Deploy**

### 3.4 Open the site

Cloudflare gives you a URL like `https://sc-senate-gop-primary.pages.dev`.

**What you should see:** status pill top-right, headline shows Graham
leading (pre-election baseline), a runoff-probability stat near 100%,
advance-to-runoff bars for all six, county table says "No counties
reporting yet." If `RACE_ID` isn't set yet, the page will show a
reconnecting/error state instead — that's expected, see Part 2.

**If the pill says "reconnecting":** open the browser console (F12).
- **CORS error** → `API_BASE` in `app.js` is wrong. Recheck 3.1
- **404 / connection refused** → Render service is down, check its logs
- **503 "no projection yet"** → either `RACE_ID` isn't set, or the first
  poll cycle hasn't finished

### 3.5 Optional: custom domain

Pages project → **Custom domains** → **Set up a custom domain**.

---

## Part 4 — Before polls close

**Set `RACE_ID`.** This is the one step every other build in this family
didn't need to do fresh at this stage — do it as soon as civicAPI has the
race, then confirm the candidate-matching log line (2.3/2.4).

**Service still awake.** Open `<render-url>/health`, `cycles` should be roughly one
per minute since `RACE_ID` was set, and `race_id_set` should read `true`.

**Site updates on its own.** Leave it open a minute — timestamp should tick forward
without reloading.

**Revisit the placeholder magnitudes.** Fry's SC-07 boost, Sanford's
SC-01/Columbia adjustment, and the runoff simulation's `SIGMA_STATE_0` are
all judgment calls flagged in README.md "Known limitations" — reconsider
before trusting P(runoff)/advance numbers live.

---

## Part 5 — Election night

### What the page is telling you

**The runoff-probability stat and advance-to-runoff bars** are drawn from
the actual 20,000-simulation Monte Carlo, whose uncertainty shrinks as more
of the state reports (see `south_carolina_senate_model.py`). They converge
to a hard 0%/100% only once counting finishes — a candidate near the
runoff line will show real movement in these numbers well before that.

**The county table** shows each county's *raw* reported split against
baseline — unmodeled, exactly what's been counted — next to the model's
blended projection.

**The two maps** — colored by whichever candidate is *leading* in each
county. This model isn't deductive, so "Counted so far" and "Model
projection" aren't "actual" vs. "remainder" — the projection map shows the
full blended call for every county, present from the first cycle on.

**Model state** shows the statewide shift per candidate. A single large
county reporting won't move any candidate's shift much on its own by design
— watch for it to move once a real multi-county pattern shows up.

### What not to do

**Don't read the runoff/advance numbers as a call early.** At low reporting
the model is still mostly showing you the baseline plus its full
pre-election uncertainty band — and this baseline is a coalition-proxy
construction (see README "Known limitations"), not a direct poll of this
primary.

**Don't restart the Render service** unless you have to — state is in
memory, a restart costs the credibility/shift calibration until counties
report again.

### If something breaks

**Feed goes down.** Nothing to do — each cycle catches its own exceptions and
keeps serving the last good projection.

**Need to change a parameter.** Edit on GitHub, commit to `main`, Render
redeploys in a few minutes — you lose in-memory state, weigh that against
the fix.

| Constant | File | Controls |
|---|---|---|
| `GLOBAL_EVIDENCE_PRIOR` | `south_carolina_senate_model.py` | how much statewide evidence it takes before the shift trusts observed results over the baseline, per candidate |
| `MAX_SINGLE_COUNTY_SHARE` | `south_carolina_senate_model.py` | how much any one county (even Greenville or Richland) can move any candidate's shift alone |
| `MOMENTUM_MAX_DRIFT` | `south_carolina_senate_model.py` | how far a well-reported county's blended projection can stray from its own raw results, per candidate |
| `SIGMA_STATE_0` / `SIGMA_COUNTY_0` | `south_carolina_senate_model.py` | pre-election Monte Carlo uncertainty for P(runoff)/advance -- shrinks automatically as reporting progresses |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Render can't find `render.yaml` | not at repo root | redo Part 1 |
| No `serving on` line, service restarts | server didn't bind | check logs for a traceback above it |
| `!! RACE_ID is not set` repeating | no civicAPI race yet | expected until the race is scheduled -- set `RACE_ID` when it exists |
| `!! CANDIDATE MATCH FAILED` | feed spells names differently | edit the `*_KEYS` tuples on GitHub |
| `!! UNMATCHED COUNTIES` | county name variant | edit `normalize_county()` on GitHub |
| `/api/projection` says no projection yet (503) | `RACE_ID` unset, or first cycle not done | set `RACE_ID`, or wait 60 seconds |
| Site pill stuck on "reconnecting" | wrong `API_BASE`, or Render down | check browser console for CORS vs 404 |
| Site shows nothing but the header | Pages output directory wrong | should be `/`, not `web` |

---

## Timeline

| When | Do |
|---|---|
| Now | Parts 1-3 (race ID not yet available -- site will run on baseline only) |
| Once civicAPI opens the race | Set `RACE_ID` (Part 4), confirm candidate matching |
| Any time before polls open | Rest of Part 4 |
| Polls close | Results start |
| Through the night | Part 5 |

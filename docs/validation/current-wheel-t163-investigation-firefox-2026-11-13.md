# Current wheel and T163 investigation — Firefox verification

**Run:** 2026-11-13 09:13 UTC

**Source revision:** `4ebf939`

**Case:** Rio Grande do Sul T163 diagnostic investigation

**Browser:** Firefox 158.0.1, headless; geckodriver 0.37.1

## Build identity

The wheel was built offline from a temporary staging copy of the current
`pyproject.toml` and `echo/` package, leaving the worktree unchanged. Its SHA-256
is `084a7ce289b0faa79aa08aeaccfccb905ffe135cd7dc701a6fc619b6c052e955`
(418,434 bytes). The packaged `web.py`, CLI, HTML, JavaScript, and CSS match the
checkout byte-for-byte.

The wheel was installed into a target directory and imported from that
directory while the application process ran with `/tmp` as its working
directory. This confirms the test did not import the source checkout. Runtime
dependencies came from the previously prepared isolated evaluation virtual
environment; this run did not rebuild or reinstall dependency pins.

The separate T163 evidence bundle contained 65 files (5,312,290 bytes). A
deterministic SHA-256 over each relative path and file SHA-256 is
`7d4c49cd5a88f881789d185fe7967e0b253fb027c42b249caa2ad49233389f8c`.

## Runtime and browser behavior

The installed wheel served the bundle with `--read-only-demo`, `--data-root`,
and loopback binding, from an isolated temporary `HOME` without `.netrc`.
Firefox's external HTTP/HTTPS proxy pointed to unreachable loopback port 9;
loopback ECHO traffic remained available.

- `/api/cases`, `/api/case`, `/api/review`,
  `/api/cross-sensor-assessment`, the selected hypothesis challenge, and
  `/api/dswx-context` returned HTTP 200.
- The UI showed the curated read-only banner, rendered the geographic map,
  opened the assessment with all six hypotheses, and opened a source-linked
  adversarial challenge. The rendered assessment/challenge retained the
  diagnostic OPERA boundary and `NOT TESTABLE WITH RETAINED EVIDENCE` wording.
- Browser API traffic consisted of three local GETs for the assessment, SAR
  evidence, and challenge. No writes or provider requests occurred. No browser
  JavaScript errors were recorded.
- `GET /api/investigation-drafts` and `POST /api/catalog` returned HTTP 403.

This validates the packaged current interface and evidence links for the main
curated investigation workflow on this host. The SAR source remains a
Sentinel-1-derived OPERA diagnostic comparison with unresolved consolidated
provider QA; the UI does not assert a validated flood extent or physical cause.

## Water-hypothesis challenge interaction — 2026-11-13 09:18 UTC

A follow-up browser run selected the specific water-change hypothesis from the
six hypothesis controls, then expanded the challenge's progressive-disclosure
sections. The case assessment displayed the optical WTR count change `36 → 27`
and WTR-2 change `135 → 59`, plus the SAR common-clear support `1,199 / 1,199`
and rounded median `-1.66 dB`. The source-linked challenge separately displayed
the recomputed median `-1.657 dB`, `NOT TESTABLE WITH RETAINED EVIDENCE`, and
`PROVIDER QA UNRESOLVED`. Its alternatives, missing-evidence, and sensitivity
sections opened; the spatial sensitivity disclosure rendered 1,254 cell
polygons. These polygon count and common-clear SAR support are different
quantities and are recorded separately.

The browser made three local GET requests for the assessment, linked SAR
measurement, and selected challenge. External HTTP/HTTPS requests were blocked;
there were no provider calls, writes, or page errors. An initial harness pass
used the wrong thousands-separator and expected optical values in the collapsed
challenge summary; the checks were corrected to follow the displayed number
formats and explicitly open the relevant sections. No application code changed.

## Interactive spatial sensitivity controls — 2026-11-13 09:21 UTC

In the same packaged, read-only browser workflow, the SAR / optical layer
selector and common-WTR-support slider were exercised after opening the
spatial-sensitivity disclosure. At the default 50% support threshold, the map
showed 826 signed-SAR cells from the 1,254-cell retained window. Selecting the
optical water-fraction layer and raising the threshold to 75% showed 738 cells
from that same retained window. The UI updated the readout, SVG visibility,
ARIA description, and legend consistently. All six checks passed.

The threshold filters the retained common-support observations and the selected
layer controls the displayed per-cell value. This browser check does not
recompute the underlying assessment, perform a provider read, or validate a
physical explanation. It makes the existing sensitivity display interactive;
it does not create new measurement evidence.

## Challenge-to-workspace handoff — 2026-11-13 09:31 UTC

A browser check of the handoff exposed an accessibility regression: after the
challenge layer rendered and its diagnostic labels appeared, area-control
synchronization replaced the map's descriptive `aria-label` with the generic
catalog-map label. The drawn data and visible QA warning were intact, but the
map description no longer identified the diagnostic layer or unresolved QA.

`mapAccessibilityDescription()` now supplies one shared description to both
map rendering and area-control synchronization. It reports the active
diagnostic measurements, the current common-support cell count, unresolved
provider QA, and that the map is not a validated finding; it also preserves
the area-selection instructions when that mode is active. A regression check
was added to `tests/test_map_geography.py`.

The updated application was built into a fresh wheel
(`echo_sar_investigation-0.1.0-py3-none-any.whl`, 418,551 bytes,
SHA-256 `1d95c04945b96aff93dea1aa3aacd9e1dacc33a300cb4b5050265b74bd603093`).
The packaged `echo/static/app.js` SHA-256 matches the source file:
`ab1b5a182648c74da174594f83ddf78998669fb0627af6fd064d7385235fd3d6`.
Firefox 158 exercised that installed wheel against the retained T163 bundle in
server-enforced `CURATED_READ_ONLY` mode; external browser traffic was blocked
and loopback ECHO traffic remained available.

- The initial SAR layer rendered 826 common-support cells and its accessible
  description stated diagnostic status and unresolved provider QA.
- Selecting DSWx water-fraction change and setting minimum support to 75%
  displayed 738 cells; the map description updated to that count and retained
  the QA limitation.
- Selecting a cell exposed its SAR value (`-1.912 dB`), DSWx water-fraction
  difference (`0.000`), 100% common support, and diagnostic-only status.
- Returning to the case map removed the challenge layer and restored the
  general map description.
- The 65-file evidence bundle's deterministic tree hash remained
  `e1508fb78347fe6e1198293a32803de9018477c7a7ffedce56322327450dac08` before
  and after the interaction. No provider operation or evidence write occurred.
- Focused geography tests: **3 passed**. Full suite: **534 passed in 41.66 s**.

The layer remains a descriptive, diagnostic spatial association. This test
does not validate provider QA, flood extent, or physical cause.

## Retained OPERA observations in the case timeline — 2026-11-13 09:51 UTC

A six-case Firefox pass found that the two Rio Grande do Sul investigation
cases had real retained OPERA comparisons but showed “No acquisitions in this
catalog query” in the main observation sequence. The catalog is correctly
empty, but this presentation hid the case-linked acquisitions and left
catalog-pair controls visible despite there being no catalog candidates.

The timeline now renders those retained acquisitions separately from ASF
catalog records, labels them as case-linked, and says they are not catalog
results. For T024 it uses the three acquisition timestamps in the
validated, checksum-linked OPERA temporal-series record. For T163, which has
no temporal-series sidecar, it decodes the two UTC acquisition timestamps
embedded in the exact before/after OPERA scene IDs already linked by the case
review. Both sequences are explicitly marked `CASE-LINKED · DIAGNOSTIC`; catalog
comparison controls are hidden for those cases, and the note points to the
existing investigation/series controls for evidence and QA. No catalog
features, measurements, or QA dispositions were added or changed.

Firefox 158 exercised all six registered cases at 1366 × 900 using a fresh
local wheel (419,550 bytes, SHA-256
`5fa83ceb0dd9ffc95147017c2df9b37afb1128efd4d1c6214610df2ec9aefd36`). The
T024 timeline showed 2024-05-11, 2024-06-04, and 2025-06-23; T163 showed
2024-05-08 and 2024-06-01. Each UI label identifies the observations as
case-linked and not ASF catalog results. Mozambique, Iraq, Istanbul, and Nepal retained
their existing catalog observations and comparison controls. External
HTTP/HTTPS traffic was blocked. The browser submitted no provider request or
write. Focused case/timeline tests: **7 passed**; final full suite: **535 passed
in 41.22 s**.

The retained markers are chronology and source-identification context. They do
not imply that OPERA products are NASA NISAR measurements, that their QA is
cleared, or that an event cause or boundary has been validated.

## Timeline-to-investigation interaction — 2026-11-13 10:04 UTC

The retained timeline markers now open the comparison they represent. For the
T024 series, selecting the first or third acquisition selects the matching
adjacent interval (`adjacent:0` or `adjacent:1`), activates the series layer on
the map, and updates the existing measurement inspector. For T163, selecting a
retained acquisition opens the linked case investigation. These controls use
the retained case records and do not query ASF or change any QA disposition.

Firefox exercised the fresh 419,935-byte wheel
(`43b33ef79db874db002d10355a6a269484dfbb2e5e686df519ac4647a3f99da1`) against
the local case registry. T024 rendered three selectable case-linked dates;
the first and third selections opened the expected adjacent comparisons and
the map-layer control showed the active series layer. T163 rendered two
selectable dates; selecting one opened the investigation dialog, whose content
retained its QA and diagnostic wording. External HTTP/HTTPS browser requests
were sent to a closed loopback proxy; the test made no provider request or
evidence write. The run covered timeline event handling and the interface
handoff only; it does not validate OPERA provider QA or a physical
interpretation.

The current full automated suite passed: **535 tests in 41.20 seconds**.
`git diff --check` also passed.

## Retained timeline selection feedback — 2026-11-13 10:14 UTC

Selecting a retained acquisition now leaves an explicit selected state on its
timeline button (`aria-pressed` and the existing selected styling). The state
is cleared when the user chooses a comparison directly from the series
selector, where no single acquisition is the selection anchor. This connects
the active comparison or investigation to the chronology without changing any
measurement or QA state.

Firefox 158 exercised the current interactive workbench with external browser
HTTP/HTTPS blocked. In T024, the first marker selected `adjacent:0`, activated
the series map layer, and became the sole pressed marker; the third marker
selected `adjacent:1` and became the sole pressed marker. In T163, the second
marker became the sole pressed marker and opened the linked investigation with
its QA and diagnostic wording intact. No provider action was triggered.
A separate T024 browser check chose a first-acquisition baseline directly
from the comparison selector and confirmed that no timeline date remained
pressed, since that baseline selection has no single date anchor.

A fresh offline-built wheel is retained at
`/tmp/echo-wheel-selection-out-v7f6mbwe/echo_sar_investigation-0.1.0-py3-none-any.whl`
(420,037 bytes; SHA-256
`e542dc4754100080d2995eeb36e6120b4a405e6be3c0f8b3a61211d4e28b9e8b`). Its
packaged `app.js` and `context.css` match the checkout byte-for-byte. The full
suite passed **535 tests in 41.77 seconds** after this change, and
`git diff --check` passed.

## Latest local wheel verification — 2026-11-13

The wheel was rebuilt from the current checkout at `f6e16fa` using the
system's already-installed setuptools backend and without dependency
resolution or fetching external packages. The artifact is
`echo_sar_investigation-0.1.0-py3-none-any.whl` (420,468 bytes; SHA-256
`42b1a5e9c6a082a87b12e15712149f30af40cc9fcf280ed1a92b6c740696215a`). It was
installed into a temporary target directory outside the checkout. Its
`web.py`, CLI, application JavaScript, HTML, and CSS matched the installed
wheel contents byte-for-byte. The server was launched from `/tmp` using that
installed entry point and the retained Iraq case bundle.

Firefox 158 opened the installed wheel's read-only Iraq NISAR case. The
observation challenge retained all expected boundaries: no change finding,
pair QA `FAIL`, no temporal change computed, and one QA-held diagnostic
observation. The map rendered, the challenge used one local GET, and no page
JavaScript errors were reported. Separate direct checks confirmed the
read-only service returns HTTP 403 for `GET /api/investigation-drafts` and
`POST /api/catalog`. No provider action or evidence write was performed.

The full local suite after this checkpoint passed **535 tests in 42.20 s**.
This verifies a fresh wheel on the same laptop with the existing runtime
dependencies; it does not verify a separately provisioned machine, a clean
dependency installation, a new scientific measurement, or NISAR temporal
change validity.

## Limits

This is not a separate Ubuntu account or machine, a freshly resolved dependency
environment, an external distribution, or a data-licensing review. No new
satellite product was retrieved and no scientific measurement was recomputed.
The earlier wheel smoke record remains a historical Iraq-case check; this run
uses the current wheel and T163 evidence bundle.

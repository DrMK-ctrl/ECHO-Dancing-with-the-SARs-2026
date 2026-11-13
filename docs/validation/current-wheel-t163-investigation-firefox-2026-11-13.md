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

## Limits

This is not a separate Ubuntu account or machine, a freshly resolved dependency
environment, an external distribution, or a data-licensing review. No new
satellite product was retrieved and no scientific measurement was recomputed.
The earlier wheel smoke record remains a historical Iraq-case check; this run
uses the current wheel and T163 evidence bundle.

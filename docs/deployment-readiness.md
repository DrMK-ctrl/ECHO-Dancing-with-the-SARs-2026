# ECHO local and judge-access readiness

**Reviewed:** 2026-11-12
**Status:** Local development launch and a loopback-only, single-case curated read-only mode are available. No independently hosted judge build is implemented or deployed.

## Verification recorded for this revision

- The full suite passed **460 tests**, including curated-mode route, loopback-bind, and data-root guard checks.
- Firefox headless opened the live Iraq case in read-only mode. The banner became visible, the selector contained one case and was disabled, two acquisitions rendered, and the case status showed `QA HOLD`.
- A live HTTP smoke check returned `200` for the case registry and retained case record, and `403 READ_ONLY_DEMO` for draft listing and catalog POST. The active test also verifies the provider search function is not called.
- The mode runs only on loopback and accepts a case catalog resolved inside the repository's `data/cases` directory. It does not provide remote authentication or an immutable packaged data bundle.
- Full offline behavior is not verified; optional GIBS basemap images can still be fetched by the browser.

## What can be run now

From the repository root on Ubuntu, with the project environment installed:

```bash
.venv/bin/echo serve --case-file data/cases/iraq-2026-nisar-diagnostic/catalog.json
```

Open `http://127.0.0.1:8765/`; stop the server with Ctrl+C. The default bind is loopback. Other retained cases can be opened by changing `--case-file`, for example the Mozambique pilot or the Rio Grande do Sul T163 diagnostic case. The `README.md` contains the current case walkthroughs and scientific boundaries.

For a single retained case that cannot perform catalog/provider requests or access local investigation drafts, use:

```bash
.venv/bin/echo serve --read-only-demo \
  --case-file data/cases/iraq-2026-nisar-diagnostic/catalog.json
```

This mode is restricted to localhost or a loopback IP, exposes only the selected case, denies every HTTP POST and draft-list/read endpoint, and shows a read-only banner. The case's retained evidence remains inspectable. Optional NASA GIBS basemap imagery may still be requested by the browser; this is not an offline mode. Requests rejected by the server return HTTP 403 with code `READ_ONLY_DEMO`.

The base Python environment is pinned in `requirements.lock`; Python 3.11 or newer is required. Authenticated NISAR/OPERA data reads and QA retrieval use the optional dependencies pinned in `requirements-nisar.lock` and Earthdata Login configuration in the user's local `~/.netrc`. Keep credentials out of case bundles, logs, screenshots, and this repository. The app does not need Earthdata credentials for retained case records or catalog metadata search. Some map layers and live requests require an internet connection; the interface has map-grid fallback behavior, but the whole application has not been verified as an offline package.

## Read-only and exposure boundary

The default server mode remains interactive and has POST operations for catalog searches, on-demand QA and raster retrieval, case-specific analysis, and local investigation-draft creation/revision. The `--read-only-demo` mode blocks these operations server-side and limits the case registry to the selected case. The app still has no deployment-grade user authentication layer; the curated mode's loopback-bind check is not remote access control. The Bhoonidhi credential route has its own loopback, same-origin check, which does not secure the application as a whole.

Do not port-forward, reverse-proxy, or bind the current app to a public or shared network. A read-only filesystem alone would not make the service safe: write-capable routes and live provider requests need an explicit application-level policy, and a proxy would need to authenticate users and constrain requests.

## Recommended judge-access sequence

1. **Near-term, user-operated demonstration:** run ECHO on the project lead's Ubuntu laptop with `--read-only-demo`. Preselect one retained case, rehearse its actual data and QA state, and keep Earthdata credentials local. Clearly disclose optional GIBS network imagery and which cases are diagnostic or QA-held.
2. **Prepare a distributable curated bundle:** the server-side read-only gate and endpoint tests now exist. Before handing a bundle to judges, freeze one case and its linked evidence, verify each path and checksum, review redistribution rights and attribution, and test startup from a clean Ubuntu account with no credentials. The repository currently remains the data source; a separately packaged minimal case bundle has not been built or license-reviewed.
3. **Only if independent remote access is needed and later authorized:** deploy an isolated copy of that curated mode behind TLS and access control, with no Earthdata or Bhoonidhi secrets, no writable source/data mount, bounded request resources, and logs that exclude credentials. Review data and asset redistribution rights before packaging. Validate the exact URL, account flow, network policy, backup, rollback, and shutdown procedure before any external access.

The current code supports step 1 and the application-level controls in step 2. Bundle assembly, clean-account acceptance, and steps for remote hosting remain outstanding. No public endpoint, remote judge account, release, or deployment has been created.

## Verification checklist before a judge build

- [ ] Confirm competition eligibility, team registration, submission terms, and the exact local Beirut presentation requirements from organizer sources; do not treat private repository access as submission permission.
- [ ] Select one scientifically meaningful case whose actual data, quality disposition, and limitations are explicit. Keep Iraq NISAR QA-held and OPERA T163 diagnostic unless their evidence gates change.
- [ ] Reproduce the case from a clean Ubuntu account using documented pinned dependencies; verify startup, shutdown, expected map state, acquisition timeline, source inspector, and failure messages.
- [ ] Test supported actions in browser and API, including QA-held products, missing network, provider errors, invalid/oversized requests, and resource limits.
- [ ] Before distributing a read-only bundle, enumerate every HTTP route and prove by tests that all writes, revision/import actions, and provider retrieval endpoints are disabled; verify only reviewed case paths and checksum-validated linked artifacts can be read.
- [ ] Inspect package contents for credentials, local user data, unreviewed artifacts, licenses, attribution, and unintended source/history exposure.
- [ ] Verify map/layer provenance, acquisition timestamps, processing records, QA disposition, and distinction between measured values, derived values, hypotheses, and unresolved findings.
- [ ] Record the exact build revision, dependency lock hashes, case-bundle hash, browser/OS versions, and verification results.
- [ ] Obtain explicit project-lead approval for any external deployment, account sharing, release, or publication. None is authorized by this readiness note.

## Current readiness assessment

ECHO is suitable for a guided local technical walkthrough, not yet for unattended judge access. The map, retained evidence, live catalog search, bounded measurement preview, QA-first comparison path, and case-specific investigation flow are connected in the local interface. The `--read-only-demo` server mode has route-level tests; a bundled, clean-account judge build has not yet been verified. Current scientific evidence does not include a QA-cleared NISAR temporal change result. The QA-held Iraq and Nepal scenes can demonstrate source inspection and gate behavior; the OPERA case can demonstrate a diagnostic, multi-source investigation, but neither should be presented as a validated causal finding. See [`PROJECT_CHARTER.md`](PROJECT_CHARTER.md), [`2026-11-11-p05036-gcov-qa-root-cause.md`](research/2026-11-11-p05036-gcov-qa-root-cause.md), and [`2026-11-11-incremental-nisar-gcov-screen.md`](research/2026-11-11-incremental-nisar-gcov-screen.md).

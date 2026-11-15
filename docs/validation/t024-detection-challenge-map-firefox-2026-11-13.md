# T024 measurement-to-challenge-to-map workflow — Firefox validation

**Date:** November 13, 2026
**Application:** current local interactive workbench at 127.0.0.1:8766
**Browser:** Firefox headless through W3C WebDriver
**Result:** PASS for the tested path

## Workflow verified

Starting from the retained T024 Rio Grande do Sul case, Firefox opened the
source-linked assessment and challenged
H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE. The progressive-disclosure section
was opened to inspect the linked temporal-baseline calculations. The browser
then followed the 408-day first-acquisition baseline action back to the map.
The map inspector displayed the matching dates, measurement, source, and QA
boundary.

The challenge reproduced these measurements on the linked series' 1,034-cell
all-date support (1,199 AOI centers total):

| Comparison | Interval | Mean γ⁰ log-ratio | Median γ⁰ log-ratio |
| --- | ---: | ---: | ---: |
| Adjacent acquisitions, May–June 2024 | 24 days | −2.344 dB | −1.408 dB |
| Adjacent acquisitions, June 2024–June 2025 | 384 days | +0.188 dB | +0.177 dB |
| First acquisition to June 2025 | 408 days | −2.156 dB | −1.252 dB |

The handoff retained the temporal-series SHA-256
191cac49a1718c3b5c0fd85d2c7ee814c37c484e8ba7462e92aa9cd2c1bae738,
comparison key baseline:0, and the exact acquisition timestamps. The browser
reported no page errors and made one local read-only challenge API request.

The first draft of this browser check expected the sensitivity table to be
immediately visible. It timed out because the table is intentionally inside a
collapsed disclosure. Opening the disclosure revealed the expected content;
no application defect was found. The reusable check explicitly opens it.

## Reproduce

Start the local interactive workbench, then run:

    .venv/bin/python tools/validation/check_t024_baseline_challenge_browser.py \
      --url 'http://127.0.0.1:8766/?case_id=rio-grande-do-sul-cross-sensor-diagnostic-2024'

The browser check is read-only. It submits no provider request and creates no
investigation draft or review note.

## Interpretation limits

This verifies a real user flow from an existing descriptive SAR comparison
through ECHO's evidence challenge and back to the corresponding map layer. It
shows what the investigation workflow adds to a change display in this case:
it exposes how the measured response varies across selected temporal
comparisons and preserves the linked evidence and limitations.

The observations are Sentinel-1-derived NASA OPERA RTC-S1, not NISAR. Provider
product QA has no consolidated PASS/FAIL disposition. The comparison remains
diagnostic; its intervals reuse observations, differ in duration, and are not
independent tests. This check does not validate a flood boundary, event cause,
or physical interpretation, and it does not establish superior accuracy over
a conventional change-detection method.

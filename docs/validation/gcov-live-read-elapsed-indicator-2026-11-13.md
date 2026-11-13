# GCOV retrieval wait feedback — browser verification

**Date:** 2026-11-13  
**Application:** local interactive workbench at `127.0.0.1:8766`  
**Browser:** Firefox 158.0.1, headless, through W3C WebDriver

## Behavior

Bounded NISAR HDF5 reads can take a minute or more. The preview status already
described this expected delay, but provided no indication that the request was
still active. While a matching request is pending, the status now shows elapsed
time in seconds and then minutes/seconds. It makes no percentage or remaining-
time estimate. The read's existing identity checks prevent a stale request from
updating the timer after the selected scene, AOI, case, frequency, or layer
changes. Success and failure cleanup remove the timer, and the changing value is
hidden from assistive technology to avoid repeated live announcements.

## Browser check

Firefox opened the Iraq NISAR case and loaded its two retained catalog records.
The preview handler was exercised with a delayed, intercepted HTTP 502 response;
the test sent no provider request and read no new measurement.

- During the pending response, the read status remained `loading`, the preview
  button was busy, and the elapsed label advanced to `Elapsed: 1s`.
- When the controlled error arrived, the interface showed its ordinary
  retrieval-error message, removed the elapsed label, and cleared the button's
  busy state.
- The elapsed label is `aria-hidden`; the surrounding status remains the
  existing polite live region.

The automated regression assertion is
`test_gcov_preview_loading_shows_elapsed_time_without_claiming_progress`.
`tests/test_web.py` passed **61 tests**; the full suite passed **509 tests in
36.69 seconds**. This verifies wait and failure feedback only. It is not a live
ASF read, latency benchmark, or new satellite measurement.

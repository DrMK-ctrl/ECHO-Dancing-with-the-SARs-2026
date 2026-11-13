# GCOV preview failure and retry — Firefox verification

**Date:** 2026-11-13  
**Application:** local interactive workbench at `127.0.0.1:8766`  
**Browser:** Firefox 158.0.1, headless, through W3C WebDriver

## Procedure and result

The browser opened the Iraq NISAR case, selected the retained October 20
acquisition in the visible timeline, and activated **Load Backscatter**. The
browser intercepted the preview request and returned a controlled HTTP 502.
It then repeated the same user action and replayed the exact retained
measurement record from
[`nisar-iraq-p05023-hhhh-preview-2026-11-08.json`](../../data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json).
The browser sent no ASF request; all other fetches were blocked and none were
attempted during the test.

- The first attempt displayed the controlled error and cleared the busy state
  and elapsed-time indicator.
- The retry loaded the selected scene and restored the **Hide Backscatter**
  state; the read status closed and the busy state cleared.
- The interface continued to show provider QA `FAIL` and
  `QA_HELD_DIAGNOSTIC_PREVIEW`.
- No paired analysis, change result, or event interpretation was created.

This exercises the existing browser handler and retry path with a retained,
authentic measurement record. It does not represent a second measurement
retrieval or a live ASF transaction.

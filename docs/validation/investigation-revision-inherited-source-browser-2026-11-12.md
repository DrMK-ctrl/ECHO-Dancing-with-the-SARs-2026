# Investigation revision inherited-source browser check

## Scope

Checked the actual local application after adding an expandable history disclosure for staged catalog and provider-QA records carried into a new investigation round.

## Browser result

A loopback ECHO server loaded a saved revision in headless Firefox. The controlled draft used a QA-held SAR fixture, an attached catalog metadata fixture linked to H1, and a revised follow-up targeting H2. The rendered source row identified the inherited search as **not a result for the current test**. The disclosure showed the original H1 target, follow-up ID, test-design checksum, expected observation, and weakening condition. The active draft showed the H2 target.

The draft loaded through the local snapshot picker and its status reported that snapshot integrity and current case links were rechecked. The temporary local server and browser session were stopped after the check.

Automated follow-up: the focused investigation, draft, store, and web suites passed **151 tests**; the full suite passed **484 tests**. The browser JavaScript parsed, Python compilation passed, and `git diff --check` passed.

## Limits

This is a controlled software and interface fixture, not a satellite observation, source suitability evaluation, or scientific finding. The check verified rendered content and interactions, not visual styling at multiple viewport sizes. No screenshot was retained.

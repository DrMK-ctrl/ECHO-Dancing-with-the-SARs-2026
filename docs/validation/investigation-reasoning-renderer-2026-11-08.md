# Reusable investigation reasoning renderer — 2026-11-08

## Change

The hypothesis, evidence-relationship, shared-source, evidence-lineage, and follow-up workstream markup is now produced by `echo/static/investigation.js`, independent of mission- or product-specific observation cards. `index.html` loads it before `app.js`; the local server exposes it at `/investigation.js` under the existing same-origin Content Security Policy. Existing source-inspection and analyst-challenge event handlers continue to bind to the generated markup.

## Verification

- Full software suite: **297 passed**; Python compilation and `git diff --check` passed.
- The local web test confirms that the page references the new script and the server returns it as JavaScript.
- The renderer source executed in the available V8 runtime with both retained assessment records. T024 produced 6 hypothesis cards, 5 follow-up cards, and 5 evidence dependency rows. T163 produced 6 hypothesis cards, 10 follow-up cards, and 20 evidence dependency rows. Both rendered the shared-evidence comparison.
- A synthetic `<script>` string inserted into a copied hypothesis statement was HTML-escaped in the generated markup and did not create a script element.

## Limits

The V8 check covers the renderer's output against the current case data, not browser layout, accessibility, or click interactions. A fresh Firefox session could not be created in this environment, which already has active Firefox/geckodriver sessions. Product-specific measurement cards and acquisition chronology remain in the T163-oriented view; this change does not create case selection or a generalized observation adapter. No measurement, QA status, evidence relationship, or scientific conclusion changed.

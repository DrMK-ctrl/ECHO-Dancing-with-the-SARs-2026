# Investigation hypothesis source coverage

Date: 2026-11-09

## Change

Each hypothesis card now has a collapsible source-coverage disclosure. It lists artifacts in the same investigation that have no recorded relationship for that hypothesis and links them to the existing source inspector. The copy explicitly says that those records are unassessed in this hypothesis and do not count as negative evidence, irrelevant evidence, or independent corroboration. When no records are unlinked, the interface says only that every currently listed record has a relationship and that the source set may still be incomplete.

No assessment records, relationships, or hypothesis states were changed. This is an evidence-review aid, not an automatic evaluator.

## Verification

- GJS executed the shared renderer against retained T024 and T163 assessment records: 6 hypothesis cards rendered for each, with 17 and 24 source artifacts respectively. Every hypothesis has unlinked records in these cases: 12–16 for T024 and 18–23 for T163.
- A controlled renderer input with one linked and one unlinked source produced the expected `1 LINKED · 1 OTHER SOURCE` summary, the unassessed and non-negative-evidence explanation, and a `data-evidence-id` source-inspector link for the unlinked record.
- The web static-asset test checks that the disclosure and its styling are served with the investigation renderer.
- `git diff --check` passed.
- A live browser layout and click walkthrough was not performed because several Firefox/geckodriver sessions were already active. The markup reuses the existing `.investigation-source-link` handler; this is code-path evidence, not a browser interaction result.

The assessment records remain diagnostically scoped and scientifically unresolved as previously documented. This presentation change adds no measurement or evidentiary support.

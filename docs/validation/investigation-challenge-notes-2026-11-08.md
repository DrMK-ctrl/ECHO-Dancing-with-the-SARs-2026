# Structured investigation challenge notes: browser validation

**Result:** Firefox interaction passed; human challenge notes remain non-scientific input

## Procedure and observations

Using the local interface served with the retained T163 case:

1. Opened NASA OPERA DSWx-HLS context and the linked cross-sensor assessment.
2. Opened the challenge form for a specific hypothesis.
3. Exported two challenge notes: one linked to the explicit missing-evidence option and one linked to the retained `SAR-RTC-S1-PAIR` evidence artifact.
4. Confirmed that each note displayed its hypothesis, challenge, proposed test, and either its source record ID or the explicit missing-source state under `UNASSESSED HUMAN REVIEW`; the causal assessment remained `CAUSAL INTERPRETATION UNRESOLVED`.
5. Intercepted the browser's JSON download and checked `ECHO_SESSION_INVESTIGATION_CHALLENGE_NOTES`, both hypothesis identifiers and `UNASSESSED_HUMAN_INPUT` statuses, the missing-source null value, the source evidence ID and checksum, the exported filename, and both 64-character assessment SHA-256 values.

The challenge note links to the assessment's evidence artifact identifiers, roles, and checksums. It does not claim that the proposed alternative is supported, does not change the saved hypothesis state, and does not add an evidence artifact. Closing or refreshing the page discards notes that were not exported.

## Verification boundary

This validates the local interaction and export contract in Firefox. The typed scenario is reviewer input, not a tested scientific explanation. It does not validate the OPERA RTC-S1 result, NASA optical classifications, the proposed soil-moisture test, or an autonomous investigation capability.

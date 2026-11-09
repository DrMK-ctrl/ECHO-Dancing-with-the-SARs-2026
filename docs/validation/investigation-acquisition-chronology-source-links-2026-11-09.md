# Acquisition chronology source links

Date: 2026-11-09

## Change

The shared investigation renderer now receives normalized acquisition-pair rows and handles timestamp placement, pair intervals, time-span labeling, and fallback for missing or reversed dates. Each row offers an `INSPECT SOURCE` link to its retained evidence record. Product-specific adapters continue to obtain acquisition timestamps from their own observation records; the shared renderer does not interpret measurement compatibility.

## Verification

- GJS rendered actual T024 and T163 assessment data: 5 and 4 chronology tracks respectively. Every adapter source ID matched an artifact registered in the corresponding assessment.
- GJS checked that invalid dates produce the unavailable state and that labels/source identifiers are HTML-escaped.
- Isolated Firefox browser walkthroughs loaded both cases and activated every chronology source link: all 5 T024 and 4 T163 links opened the corresponding source record with its SHA-256 provenance visible.
- The local static-asset test verifies that the application serves the shared chronology renderer and uses it for the case adapters.

This validates the current T024/T163 presentation and source links. It does not establish scientific suitability, temporal compatibility, generalized case authoring, or the accuracy of analyst-assigned relationships.

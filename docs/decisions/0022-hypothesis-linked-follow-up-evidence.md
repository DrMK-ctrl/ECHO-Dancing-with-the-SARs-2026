# Decision 0022: Link follow-up evidence to unresolved hypotheses

**Date:** 2026-11-07
**Status:** Implemented for the retained diagnostic investigation; source discovery remains pending

## Context

The investigation assessment had a static list of follow-up ideas without identifying which hypothesis each item could test or whether candidate data had been searched for. That obscured the difference between a quality gate, an actual observation, and an unverified data-availability assumption.

## Decision

- Represent each follow-up with target hypothesis identifiers, purpose, availability state, action, discriminating question, possible interpretation, and a reason it is relevant now.
- Use `QUALITY_GATE` for provider disposition work and `DISCRIMINATING_OBSERVATION` for candidate scientific observations.
- Record `NOT_SEARCHED`, `PROVIDER_RESPONSE_REQUIRED`, or `RETRIEVED_QUALITY_LIMITED` only when the corresponding state is supported. Retrieval does not imply suitability or discriminating value.
- Keep follow-up candidates explicitly unranked. A rationale explains relevance; it is not an information-value score or claim of optimality.
- Validate target identifiers and required fields. Display the plan beside the hypotheses, with each action linked to the explanations it could test.

## Current case and limits

The current assessment requires provider QA resolution for the exact RTC-S1 pair and further evidence about alternative surface drivers. The closer-optical-context search is now complete: NASA CMR returned 13 metadata candidates across two seven-day search windows, and the nearest Sentinel-2 DSWx-HLS products were extracted for the same AOI with CMR MD5 verification. The selected earlier product has zero common valid WTR pixels; all 329 earlier WTR-2 water-coded cells have cloud/snow flags. It is recorded as retrieved but quality limited, and does not resolve the water explanation. The alternative-driver search remains unperformed. Even a compatible follow-up observation may remain nondiscriminating and cannot alone establish causation.

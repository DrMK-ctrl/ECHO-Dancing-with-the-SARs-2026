# Decision 0041: retain the HLS Sentinel-2 screen as quality-limited context

**Status:** Implemented as a bounded, descriptive evidence screen; no causal test passed
**Date:** 2026-11-08

## Context

The T163 investigation had an open, preregistered search for independent surface-state evidence. The first optical branch used NASA/USGS HLS Landsat L30, but its shared clear-land support was limited. HLS S30 provides harmonized Sentinel-2 optical measurements on the same 30 m grid and allows an independently acquired optical pair to be screened over the same AOI and SAR dates.

## Decision

Retain the exact-AOI NASA LP DAAC HLS S30 v2.0 observations as complementary optical evidence. Use red B04 and narrow near-infrared B8A reflectance with Fmask to calculate NDVI only for pixels valid and clear on both dates; retain the source subsets, product identities, acquisition times, QA counts, processing configuration, and checksums. Relate the S30 record and descriptive native-grid spatial association to H3 as `DOES_NOT_DISTINGUISH`.

The screen is insufficient for a vegetation test: only 25 of 1,152 AOI pixel centers (2.17%) are common clear-land pixels. At the declared 75% optical-area threshold, 11 SAR cells remain. Their descriptive Pearson r of −0.411 is not an inferential result: the sample is very small and spatially dependent, NDVI and SAR backscatter are different physical measurements, and RTC-S1 provider QA remains unresolved. The near-zero median NDVI difference (+0.00047) does not establish absence of vegetation change outside this sparse support.

The acquisitions are `HLS.S30.T22JDM.2024129T132241.v2.0` (Sentinel-2A, 2024-05-08 13:30:53.463 UTC) and `HLS.S30.T22JDM.2024154T132239.v2.0` (Sentinel-2B, 2024-06-02 13:30:52.554 UTC). Their offsets from the paired SAR observations are −8.61 and +15.39 hours. This is NASA/USGS optical context, not NASA SAR, ground truth, or validation of the SAR result.

The completed candidate screen remains visible in the follow-up evidence chain. A separate search remains open for a source that can meet the preregistered quality, timing, and common-coverage gates; the same S30 acquisitions should not be retried as though the coverage limitation were unresolved software behavior.

## Verification and provenance

- Screen record: `data/research/hls-s30-vegetation-screen-T163-349925-2026-11-08.json` (SHA-256 `255c5c19c1b8f13a81c4cbf73251b347943094c39a7a1e273888c35d5aa673e9`).
- Association record: `data/research/hls-s30-rtc-ndvi-association-T163-349925-2026-11-08.json` (SHA-256 `74428f08252a0c48832a37097d479b3842088558c8fa0de3c8dc715aeda24f3b`). It links the exact SAR pair and optical screen by checksum and lists its transformations and software versions.
- Official product and method references are retained in the screen record: [HLS S30 v2.0](https://lpdaac.usgs.gov/products/hlss30v020/), [HLS L30 v2.0](https://lpdaac.usgs.gov/products/hlsl30v020/), and the [HLS User Guide](https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf).
- The assessment API validates product identity, case linkage, lineage, source hashes, and bounded pixel-subset hashes before serving evidence. The map-linked assessment displays acquisition chronology, support counts, limitations, and source-inspection actions.

## Consequences

The screen advances ECHO's ability to connect a candidate observation to an explanation and record why that evidence is insufficient. It does not resolve H3, change the causal disposition, clear RTC-S1 QA, establish a flood boundary, or add a NISAR measurement. The next search should prioritize a genuinely better-supported independent observation rather than another correlation on the same sparse sample.

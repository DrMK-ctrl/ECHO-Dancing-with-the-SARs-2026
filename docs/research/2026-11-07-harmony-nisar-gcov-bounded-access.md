# NASA Harmony support for bounded NISAR GCOV access

## Question

Can NASA Harmony deliver a geographically bounded NISAR GCOV measurement window and reduce ECHO's current ASF HDF5 range-read cost?

## Live collection capability check

At `2026-11-07T16:21:05Z`, ECHO queried the public Harmony collection-capabilities endpoint for `NISAR_L2_GCOV_V1`. Harmony resolved it to CMR collection `C3622241360-ASF`.

The response advertises variable selection, but reports bounding-box, shape, dimension, and temporal subsetting as unsupported. Its `net2cog` service advertises GeoTIFF output and variable selection, with no spatial subsetting. The `asf/nisar-py` service advertises PNG output and no subsetting. The full response is preserved in [`harmony-nisar-gcov-capabilities-2026-11-07.json`](../../data/research/harmony-nisar-gcov-capabilities-2026-11-07.json).

NASA's [Harmony API documentation](https://harmony.earthdata.nasa.gov/docs) describes the capabilities endpoint as the collection-specific record of supported operations and lists the `bboxSubset`, `shapeSubset`, and output-format fields. The live result is therefore sufficient to rule out Harmony as a currently supported bounded-window path for this collection. No Harmony data job was submitted, avoiding a potentially full-product transformation/download.

## Decision

Do not replace ECHO's bounded ASF HDF5 range reader with Harmony for this GCOV window milestone. Harmony does not advertise spatial subsetting for the collection. Its variable selection or GeoTIFF output may still be useful for a different full-product workflow, but would not satisfy the bounded geographic request established for ECHO.

This is a service-capability finding, not a measurement or QA result. It does not change any NISAR product disposition.

## OPERA paired-read status at initial check

At this initial check, Earthdata authentication completed, but ASF returned HTTP 401 through its Cumulus login flow. A follow-up request to ASF's documented credential endpoint returned HTTP 403 `invalid_token` with `EULA Acceptance Failure`. No measurement bytes were consumed then. This was an ASF EULA/application-access gate, not evidence that the catalog candidates were unsuitable.

## Later access and processing result

After the user reviewed the ASF authorization/EULA state, a fresh HTTPS range check returned HTTP 206. ECHO subsequently read and compared one bounded real OPERA RTC-S1 pair; the provider QA status remains `NOT_RETRIEVED`, and the result is diagnostic only. See the [live access and pair validation](../validation/opera-rtc-live-pair-2026-11-07.md). This does not change any NISAR QA status.

## References

- NASA Earthdata, [Harmony documentation and service capabilities](https://harmony.earthdata.nasa.gov/docs).
- Live collection result: `https://harmony.earthdata.nasa.gov/capabilities?shortName=NISAR_L2_GCOV_V1` (captured in the accompanying JSON record).

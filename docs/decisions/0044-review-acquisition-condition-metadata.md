# Decision 0044: Review acquisition-condition metadata in the investigation

Date: 2026-11-08

## Context

The T024 and T163 assessments listed acquisition conditions as an untested alternative even though the linked RTC-S1 pair records retained checksum-linked ASF HDF5 sidecar metadata for both exact scenes. The metadata could be compared reproducibly, but the available fields cannot establish spatial correspondence between a per-burst diagnostic and the AOI backscatter response.

## Decision

Generate a derived comparison record from the retained pair record. Compare only documented product, platform, acquisition-configuration, processing, geometric-accuracy, RFI-burst, and input fields. Link the derived record to the exact source-pair checksum and both sidecar checksums. Do not convert the comparison into a causal score or QA disposition.

The resulting evidence is classified `DOES_NOT_DISTINGUISH` for H5 and `NOT_TESTABLE_WITH_RETAINED_EVIDENCE`. Record the acquisition-condition follow-up as retrieved but quality-limited. Keep H5 `UNRESOLVED`.

## T024 and T163 observations

Both pairs report matching Sentinel-1A platform, ascending direction, IW mode/burst, VV/VH polarization, RTC algorithm and parameters, DEM source, and reported geometric-accuracy metadata. Each pair has a difference in its retained RFI burst ratio; those single-burst values are not spatially matched to the measured AOI response. The retained metadata extract has no incidence-angle fields. Matching geometric-accuracy values do not demonstrate temporal co-registration. Neither pair has a consolidated provider QA verdict.

## Consequences and limits

This evaluates one competing explanation using real source metadata and advances the investigation from an unperformed review to a traceable, limited comparison. It does not establish that acquisition conditions caused or did not cause the backscatter response, validate the measurements, or clear product QA. A stronger test would need authoritative geometry fields and quality diagnostics with spatial support relevant to the AOI.

See [the acquisition-condition review validation](../validation/opera-rtc-acquisition-condition-review-2026-11-08.md).

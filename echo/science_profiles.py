"""Product-scoped measurement semantics for source inspection.

These profiles describe what a product contains and which ECHO paths exist.
They do not assess a particular acquisition's QA, suitability, or findings.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_PROFILES: dict[str, dict[str, Any]] = {
    "NISAR_L2_GCOV": {
        "profile_id": "NISAR_L2_GCOV",
        "title": "NISAR L2 GCOV · calibrated backscatter",
        "source_class": "NASA-ISRO NISAR mission SAR",
        "measurement_domain": (
            "L-band, geocoded polarimetric covariance/backscatter layers. "
            "The exact layer and units come from the selected product metadata."
        ),
        "implemented_paths": [
            {
                "name": "Single-observation geographic preview",
                "state": "IMPLEMENTED_DIAGNOSTIC",
                "requirements": ["bounded geographic window", "product QA remains visible"],
            },
            {
                "name": "Repeat-pass backscatter comparison",
                "state": "IMPLEMENTED_WITH_GATES",
                "requirements": [
                    "provider QA and product maturity accepted for the intended use",
                    "matching measurement layer and polarization",
                    "compatible acquisition geometry and product specification",
                    "validated common grid and common valid support",
                ],
            },
        ],
        "not_supported": [
            "Interferometric phase or displacement derived from GCOV covariance layers.",
            "A QA-held preview is not an accepted scientific measurement.",
        ],
        "pair_boundary": (
            "A matching GCOV product label does not establish temporal compatibility, "
            "QA acceptance, registration, or scientific suitability."
        ),
        "source_url": "https://nisar-docs.asf.alaska.edu/data-products/level-2/gcov/",
    },
    "NISAR_L2_GUNW": {
        "profile_id": "NISAR_L2_GUNW",
        "title": "NISAR L2 GUNW · interferometric phase",
        "source_class": "NASA-ISRO NISAR mission SAR",
        "measurement_domain": (
            "Repeat-pass unwrapped interferometric phase, coherence, and supporting "
            "quality/geometric layers on product-defined grids. Phase is not displacement."
        ),
        "implemented_paths": [
            {
                "name": "Bounded phase/coherence window inspection",
                "state": "IMPLEMENTED_DIAGNOSTIC",
                "requirements": [
                    "product-specific mask and reference/secondary metadata inspection",
                    "grid-aware interpretation of phase and geometry arrays",
                ],
            },
        ],
        "not_supported": [
            "Operational displacement estimation or event interpretation.",
            "Treating finite phase values as valid without checking product masks and support.",
        ],
        "pair_boundary": (
            "GUNW phase analysis requires product-specific reference/secondary compatibility, "
            "valid mask support, and geometry checks; GCOV comparison rules do not apply."
        ),
        "source_url": "https://nisar-docs.asf.alaska.edu/data-products/level-2/gunw/",
    },
    "OPERA_RTC_S1": {
        "profile_id": "OPERA_RTC_S1",
        "title": "OPERA RTC-S1 · Sentinel-1-derived backscatter",
        "source_class": "NASA/JPL OPERA product using ESA Sentinel-1 observations",
        "measurement_domain": (
            "Burst-based radiometrically terrain-corrected gamma-zero backscatter power "
            "and a validity/layover/shadow mask; nominal pixel spacing is 30 m."
        ),
        "implemented_paths": [
            {
                "name": "Masked same-burst repeat-pass backscatter comparison",
                "state": "IMPLEMENTED_DIAGNOSTIC",
                "requirements": [
                    "matching burst, polarization, and processing version",
                    "exact grid compatibility and product mask review",
                    "product-specific quality review; no consolidated provider verdict is currently retained",
                ],
            },
        ],
        "not_supported": [
            "Interferometric phase or displacement from RTC-S1 backscatter COGs.",
            "Treating a diagnostic log-ratio as a validated flood boundary or causal result.",
        ],
        "pair_boundary": (
            "RTC-S1 is Sentinel-1-derived and remains distinct from NISAR. "
            "Its local mask checks do not replace a provider scene-quality disposition."
        ),
        "source_url": "https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/",
    },
    "OPERA_DSWX_HLS": {
        "profile_id": "OPERA_DSWX_HLS",
        "title": "OPERA DSWx-HLS · optical water classification context",
        "source_class": "NASA/JPL OPERA product from Landsat and Sentinel-2 optical observations",
        "measurement_domain": (
            "Water-classification and quality/mask layers derived from Harmonized Landsat "
            "and Sentinel-2 surface reflectance; not a SAR measurement."
        ),
        "implemented_paths": [
            {
                "name": "Temporal water-class context and native-grid spatial comparison",
                "state": "IMPLEMENTED_CONTEXT_ONLY",
                "requirements": [
                    "use product class definitions and quality masks",
                    "report acquisition timing and common valid support",
                ],
            },
        ],
        "not_supported": [
            "Using optical classifications as ground truth for an SAR-derived boundary.",
            "Using cloud, snow/ice, ocean, or fill classes as a no-water observation.",
        ],
        "pair_boundary": (
            "DSWx-HLS can add time-qualified optical context; it cannot clear SAR QA "
            "or independently validate SAR change."
        ),
        "source_url": "https://www.earthdata.nasa.gov/s3fs-public/2025-01/OPERA-DSWx_revised_Nov2024.pdf",
    },
}

_RECORD_PROFILE = {
    "ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW": "NISAR_L2_GCOV",
    "ECHO_GCOV_PAIR_ANALYSIS": "NISAR_L2_GCOV",
    "ECHO_GUNW_BOUNDED_PIXEL_WINDOW_REVIEW": "NISAR_L2_GUNW",
    "ECHO_GUNW_TEMPORAL_AOI_QUALITY_COMPARISON": "NISAR_L2_GUNW",
    "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS": "OPERA_RTC_S1",
    "ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS": "OPERA_RTC_S1",
    "ECHO_OPERA_RTC_S1_SCOPED_QUALITY_REVIEW": "OPERA_RTC_S1",
    "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON": "OPERA_DSWX_HLS",
    "ECHO_DSWX_HLS_TEMPORAL_CONTEXT_CATALOG_SCREEN": "OPERA_DSWX_HLS",
}


def product_scope_for_record_type(record_type: str) -> dict[str, Any] | None:
    """Return a copy of the registered product scope for a retained record type."""
    if not isinstance(record_type, str):
        return None
    profile_id = _RECORD_PROFILE.get(record_type)
    profile = _PROFILES.get(profile_id) if profile_id else None
    return deepcopy(profile) if profile is not None else None

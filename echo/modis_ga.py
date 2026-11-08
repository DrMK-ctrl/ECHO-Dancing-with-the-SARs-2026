"""Quality gates for daily MODIS MOD09GA reflectance used in case screening."""

from __future__ import annotations

def decode_mod09ga_band_qa(value: int) -> dict[str, int]:
    """Decode C6.1 QC_500m fields relevant to red/NIR NDVI bands."""
    raw = int(value)
    if not 0 <= raw <= 0xFFFFFFFF:
        raise ValueError("MOD09GA QC_500m value must be an unsigned 32-bit integer")
    return {
        "modland_quality": raw & 0b11,
        "band1_quality": (raw >> 2) & 0b1111,
        "band2_quality": (raw >> 6) & 0b1111,
        "atmospheric_correction_performed": (raw >> 30) & 1,
        "adjacency_correction_performed": (raw >> 31) & 1,
    }


def decode_mod09ga_state_qa(value: int) -> dict[str, int]:
    """Decode C6.1 state_1km_1 fields; these flags have 1 km support."""
    raw = int(value)
    if not 0 <= raw <= 0xFFFF:
        raise ValueError("MOD09GA state QA value must be an unsigned 16-bit integer")
    return {
        "cloud_state": raw & 0b11,
        "cloud_shadow": (raw >> 2) & 1,
        "land_water_class": (raw >> 3) & 0b111,
        "aerosol_quantity": (raw >> 6) & 0b11,
        "cirrus": (raw >> 8) & 0b11,
        "internal_cloud": (raw >> 10) & 1,
        "snow": (raw >> 12) & 1,
        "adjacent_cloud": (raw >> 13) & 1,
        "salt_pan": (raw >> 14) & 1,
        "internal_snow": (raw >> 15) & 1,
    }


def mod09ga_vegetation_sample_accepted(
    red_raw: int,
    nir_raw: int,
    band_qa_raw: int,
    state_qa_1km_raw: int,
) -> bool:
    """Apply a conservative common-support screen for vegetation interpretation.

    The measurement bands are 500 m, while the product's state flags are 1 km.
    A source adapter must associate each 500 m sample with its containing 1 km
    state cell and retain that support mismatch in the evidence record.
    """
    red, nir = int(red_raw), int(nir_raw)
    if red == -28672 or nir == -28672 or not (-100 <= red <= 16000 and -100 <= nir <= 16000):
        return False
    band = decode_mod09ga_band_qa(band_qa_raw)
    state = decode_mod09ga_state_qa(state_qa_1km_raw)
    return (
        band["modland_quality"] == 0
        and band["band1_quality"] == 0
        and band["band2_quality"] == 0
        and state["cloud_state"] == 0
        and state["cloud_shadow"] == 0
        and state["land_water_class"] == 1
        and state["cirrus"] == 0
        and state["internal_cloud"] == 0
        and state["snow"] == 0
        and state["adjacent_cloud"] == 0
        and state["internal_snow"] == 0
    )


def normalized_difference_vegetation_index(red_raw: int, nir_raw: int) -> float | None:
    """Return NDVI from valid MOD09GA red/NIR integer reflectances."""
    red, nir = int(red_raw), int(nir_raw)
    if red == -28672 or nir == -28672 or not (-100 <= red <= 16000 and -100 <= nir <= 16000):
        return None
    total = red + nir
    if total == 0:
        return None
    return (nir - red) / total

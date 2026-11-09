#!/usr/bin/env python3
"""Build an evidence-linked, fail-closed assessment from retained ECHO records."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from echo.investigation import (
    EvidenceAssessment,
    EvidenceRelation,
    evaluate_hypothesis,
    validate_evidence_lineage,
    validate_follow_up_plan,
    validate_hypotheses,
)
from echo.opera_rtc_conditions import (
    RECORD_STATUS as RTC_CONDITION_REVIEW_STATUS,
    RECORD_TYPE as RTC_CONDITION_REVIEW_TYPE,
    validate_acquisition_condition_review,
)
from echo.modis_vi import (
    RECORD_TYPE as MODIS_VI_SCREEN_TYPE,
    validate_mod13q1_candidate_screen,
)
from echo.opera_rtc_analysis import (
    OperaRtcS1AnalysisError,
    validate_opera_rtc_s1_series_record,
)
if __package__:
    from tools.research.build_gpm_interacquisition_context import (
        InteracquisitionContextError,
        build_interacquisition_context,
    )
    from tools.research.screen_smap_l4_context import summarize_subset as summarize_smap_l4_subset
else:
    from build_gpm_interacquisition_context import (
        InteracquisitionContextError,
        build_interacquisition_context,
    )
    from screen_smap_l4_context import summarize_subset as summarize_smap_l4_subset


class AssessmentError(ValueError):
    """Raised when source records cannot support this assessment."""


def _read_json(path: Path, record_type: str) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssessmentError(f"cannot read source record: {path}") from exc
    if not isinstance(record, dict) or record.get("record_type") != record_type:
        raise AssessmentError(f"unexpected record type in {path}")
    return record


def _validate_guaiba_event_context(
    record: dict[str, Any],
    *,
    case_id: str,
    pair: dict[str, Any],
) -> dict[str, Any]:
    """Validate official narrative chronology without treating it as gauge data."""
    source = record.get("source", {})
    claim = record.get("reported_context", {})
    period = claim.get("period_local_dates", {})
    limits = record.get("interpretation_limits", [])
    if (
        record.get("record_type") != "ECHO_ANA_GUAIBA_FLOOD_STAGE_CONTEXT"
        or record.get("status") != "OFFICIAL_NARRATIVE_CONTEXT_NOT_PRIMARY_STATION_MEASUREMENTS"
        or record.get("case_id") != case_id
        or source.get("provider") != "Agência Nacional de Águas e Saneamento Básico (ANA)"
        or source.get("url") != "https://conjuntura2025.ana.gov.br/agua-e-clima.html"
        or claim.get("station_code") != "87444000"
        or claim.get("station_name") != "Usina do Gasômetro (CHEIA 2024)"
        or claim.get("above_flood_stage") is not True
        or claim.get("reported_duration_days") != 30
        or period.get("start_date") != "2024-05-02"
        or period.get("end_date") != "2024-06-01"
        or claim.get("timestamped_readings_retrieved") is not False
        or not isinstance(limits, list)
        or not limits
        or any(not isinstance(value, str) or not value.strip() for value in limits)
    ):
        raise AssessmentError("ANA Guaíba event context identity or narrative-only boundary is invalid")
    try:
        start = date.fromisoformat(period["start_date"])
        end = date.fromisoformat(period["end_date"])
        acquisitions = [
            date.fromisoformat(item["acquisition_start_utc"][:10])
            for item in pair["source_products"].values()
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise AssessmentError("ANA Guaíba context dates or SAR acquisition timestamps are invalid") from exc
    if len(acquisitions) != 2 or not all(start <= acquired <= end for acquired in acquisitions):
        raise AssessmentError("ANA Guaíba reported period does not cover both SAR acquisition dates")
    if not any("not a measurement of water extent" in value.lower() for value in limits):
        raise AssessmentError("ANA Guaíba context must state that it does not measure AOI water extent")
    return {
        "station_code": claim["station_code"],
        "station_name": claim["station_name"],
        "above_flood_stage": True,
        "period_local_dates": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "reported_duration_days": claim["reported_duration_days"],
        "timestamped_readings_retrieved": False,
        "interpretation_role": "official regional hydrologic event context; not a primary gauge series, AOI water observation, SAR validation, or causal finding",
    }


def _validate_guaiba_access_screen(
    record: dict[str, Any], *, case_id: str, pair: dict[str, Any]
) -> None:
    """Check that the access record describes this pair without claiming retrieval."""
    expected_dates = [
        pair["source_products"][role]["acquisition_start_utc"]
        for role in ("before", "after")
    ]
    targets = record.get("target_observations", [])
    sources = record.get("sources")
    station = record.get("station")
    access = record.get("access_review", {})
    limits = record.get("interpretation_limits")
    if (
        not isinstance(targets, list)
        or len(targets) != 2
        or any(not isinstance(item, dict) for item in targets)
        or not isinstance(sources, list)
        or any(not isinstance(item, dict) or not isinstance(item.get("url"), str) for item in sources)
        or not isinstance(station, dict)
        or not isinstance(access, dict)
        or not isinstance(access.get("authorization_route"), str)
        or not isinstance(limits, list)
    ):
        raise AssessmentError("Guaiba primary-series access screen structure is invalid")
    source_urls = {item.get("url") for item in sources}
    if (
        record.get("record_type") != "ECHO_ANA_GUAIBA_PRIMARY_SERIES_ACCESS_SCREEN"
        or record.get("status") != "ACCESS_REQUIRED_OFFICIAL_ARCHIVE_RECORDED"
        or record.get("case_id") != case_id
        or station.get("station_code") != "87444000"
        or station.get("series_identity")
        != "Emergency-gauge observations in the original, uncorrected vertical reference"
        or [item.get("sar_acquisition_utc") for item in targets] != expected_dates
        or any(item.get("requested_station_code") != "87444000" for item in targets)
        or "https://www.gov.br/ana/pt-br/assuntos/monitoramento-e-eventos-criticos/monitoramento-hidrologico/orientacoes-manuais/manuais/manual-hidrowebservice_publica.pdf/%40%40download/file" not in source_urls
        or "https://rigeo.sgb.gov.br/bitstream/doc/24911/4/nota_institucional_conjunta_ana_sgb_gasometro.pdf" not in source_urls
        or access.get("authorization_request_sent") is not False
        or access.get("credentials_or_tokens_collected") is not False
        or access.get("series_retrieved") is not False
        or "hidro@ana.gov.br" not in access.get("authorization_route", "")
        or "CPF or CNPJ" not in access.get("authorization_route", "")
        or len(limits) < 4
    ):
        raise AssessmentError("Guaiba primary-series access screen identity or limits are invalid")


def _artifact(path: Path, record: dict[str, Any], evidence_id: str, role: str) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "role": role,
        "record_type": record["record_type"],
        "status": record.get("status"),
        "relative_path": str(path),
        "sha256": sha256(path.read_bytes()).hexdigest(),
        "lineage": {
            "derived_from_evidence_ids": [],
            "shares_source_observations_with": [],
        },
    }


def _read_case_availability_screen(
    path: Path | None,
    *,
    record_type: str,
    case_id: str,
    pair: dict[str, Any],
) -> dict[str, Any] | None:
    if path is None:
        return None
    record = _read_json(path, record_type)
    acquisitions = record.get("target", {}).get("sar_acquisitions")
    pair_acquisitions = [
        pair.get("source_products", {}).get(key, {}).get("acquisition_start_utc")
        for key in ("before", "after")
    ]
    if record.get("case_id") != case_id:
        raise AssessmentError(f"availability screen is linked to a different case: {path}")
    if not isinstance(acquisitions, list) or len(acquisitions) != 2:
        raise AssessmentError(f"availability screen must identify both SAR acquisition intervals: {path}")
    if any(
        not isinstance(interval, str)
        or interval.split("/", 1)[0] != acquisition
        for interval, acquisition in zip(acquisitions, pair_acquisitions, strict=True)
    ):
        raise AssessmentError(f"availability screen SAR acquisition times do not match the case pair: {path}")
    return record


def _open_observation_test_design(
    hypothesis_id: str,
    known_hypothesis_ids: set[str],
    mechanism_branch: str,
) -> dict[str, Any]:
    """Declare outcomes and scope before an evidence search is performed."""
    return {
        "mechanism_branch": mechanism_branch,
        "hypothesis_under_test_id": hypothesis_id,
        "expected_observation": "A quality-accepted observation with suitable timing and native spatial support shows the prespecified pattern on the declared common support.",
        "would_weaken_if": "Suitable, quality-accepted observations cover the required dates and area but do not show the prespecified pattern; this weakens only this hypothesis within scope.",
        "inconclusive_if": "Required dates, acceptable quality, useful native spatial support, or sufficient common coverage are absent.",
        "acceptance_gates": [
            "Identify the measured variable and its semantics before retrieval.",
            "Retain provider identity, acquisition timestamps, quality flags, and processing metadata.",
            "Compare native support and valid coverage without resampling incompatible measurements to force agreement.",
        ],
        "does_not_test_hypothesis_ids": sorted(known_hypothesis_ids - {hypothesis_id}),
        "interpretation_limit": "A compatible association can make this explanation more plausible within scope but does not establish causation or validate the diagnostic SAR pair.",
    }


def _link_evidence_lineage(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach known calculation and acquisition relationships to this assessment."""
    by_id = {item["evidence_id"]: item for item in artifacts}
    derivations = {
        "NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW": ["SAR-RTC-S1-PAIR"],
        "NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN": ["SAR-RTC-S1-PAIR"],
        "NASA-MOD09GA-VEGETATION-CANDIDATE-SCREEN": ["SAR-RTC-S1-PAIR"],
        "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT": [
            "SAR-RTC-S1-PAIR", "NASA-OPERA-DSWX-HLS",
        ],
        "NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT": [
            "NASA-OPERA-RTC-S1-VH-PAIR", "NASA-OPERA-DSWX-HLS",
        ],
        "NASA-OPERA-RTC-POLARIZATION-SENSITIVITY": [
            "SAR-RTC-S1-PAIR",
            "NASA-OPERA-RTC-S1-VH-PAIR",
            "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT",
            "NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT",
        ],
        "NASA-HLS-L30-NDVI-SAR-ASSOCIATION": [
            "SAR-RTC-S1-PAIR",
            "NASA-HLS-L30-VEGETATION-SCREEN",
        ],
        "NASA-HLS-S30-NDVI-SAR-ASSOCIATION": [
            "SAR-RTC-S1-PAIR",
            "NASA-HLS-S30-VEGETATION-SCREEN",
        ],
        "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY": [
            "SAR-RTC-S1-PAIR",
            "NASA-GPM-IMERG-INTERVENING-DAILY-CONTEXT",
            "NASA-GPM-IMERG-AFTER-PRE-SAR",
        ],
        "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN": ["SAR-RTC-S1-PAIR"],
    }
    shared_observations = {
        "NASA-OPERA-RTC-S1-TEMPORAL-SERIES": ["SAR-RTC-S1-PAIR"],
        "NASA-OPERA-RTC-S1-VH-PAIR": ["SAR-RTC-S1-PAIR"],
        "NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT": [
            "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT",
        ],
    }
    for evidence_id, parents in derivations.items():
        if evidence_id in by_id:
            by_id[evidence_id]["lineage"]["derived_from_evidence_ids"] = [
                parent for parent in parents if parent in by_id
            ]
    for evidence_id, related in shared_observations.items():
        if evidence_id in by_id:
            by_id[evidence_id]["lineage"]["shares_source_observations_with"] = [
                parent for parent in related if parent in by_id
            ]
    return validate_evidence_lineage(artifacts)


def _validate_smap_screen(
    record: dict[str, Any],
    *,
    case_id: str,
    bounds: list[float],
    evidence_root: Path,
) -> None:
    source = record.get("source", {})
    comparison = record.get("comparison", {})
    observations = record.get("observations")
    if (
        record.get("record_type") != "ECHO_SMAP_SENTINEL_SOIL_MOISTURE_CANDIDATE_SCREEN"
        or record.get("status") != "CANDIDATE_RETRIEVED_QUALITY_LIMITED_NOT_USABLE_FOR_CAUSAL_TEST"
        or record.get("case_id") != case_id
        or source.get("provider") != "NASA NSIDC DAAC"
        or source.get("short_name") != "SPL2SMAP_S"
        or source.get("version") != "003"
        or source.get("doi") != "10.5067/ASB0EQO2LYJV"
        or record.get("query", {}).get("bbox_west_south_east_north") != bounds
        or record.get("query", {}).get("same_grid_before_after") is not True
        or comparison.get("paired_quality_eligible_cells") != 0
        or not isinstance(observations, list)
        or len(observations) != 2
    ):
        raise AssessmentError("SMAP/Sentinel-1 candidate screen identity or case bounds are unsupported")
    root = evidence_root.resolve()
    for observation in observations:
        moisture = observation.get("soil_moisture", {})
        flags = observation.get("quality_flags", {})
        asset = observation.get("asset", {})
        asset_path_text = asset.get("relative_path")
        asset_hash = asset.get("sha256")
        if (
            observation.get("grid_shape") != [1, 1]
            or moisture.get("quality_eligible_cell_count") != 0
            or flags.get("retrieval_flag_zero_good_cell_count") != 0
            or flags.get("retrieval_quality_compromised_bit_0_cell_count") != 1
            or flags.get("disaggregated_brightness_temperature_bad_bit_6_cell_count") != 1
            or not isinstance(asset_path_text, str)
            or not isinstance(asset_hash, str)
            or len(asset_hash) != 64
        ):
            raise AssessmentError("SMAP/Sentinel-1 subset does not meet its retained quality-screen result")
        asset_path = Path(asset_path_text)
        if asset_path.is_absolute():
            raise AssessmentError("SMAP/Sentinel-1 source-subset paths must be relative")
        resolved = (root / asset_path).resolve()
        if not resolved.is_relative_to(root):
            raise AssessmentError("SMAP/Sentinel-1 source-subset path escapes the project root")
        try:
            payload = resolved.read_bytes()
        except OSError as exc:
            raise AssessmentError("SMAP/Sentinel-1 source subset is unavailable") from exc
        if len(payload) > 2 * 1024 * 1024 or sha256(payload).hexdigest() != asset_hash:
            raise AssessmentError("SMAP/Sentinel-1 source-subset checksum or size validation failed")


def _validate_smap_l4_context(
    record: dict[str, Any],
    *,
    case_id: str,
    bounds: list[float],
    pair: dict[str, Any],
    evidence_root: Path,
) -> dict[str, Any]:
    source = record.get("source", {})
    query = record.get("query", {})
    observations = record.get("observations")
    if (
        record.get("record_type") != "ECHO_SMAP_L4_REGIONAL_SOIL_MOISTURE_CONTEXT_SCREEN"
        or record.get("status") != "SCREENED_REGIONAL_MODEL_CONTEXT_NOT_SUITABLE_FOR_AOI_SCALE_DISCRIMINATION"
        or record.get("case_id") != case_id
        or source.get("provider") != "NASA National Snow and Ice Data Center DAAC"
        or source.get("short_name") != "SPL4SMAU"
        or source.get("version") != "008"
        or source.get("collection_concept_id") != "C3480440639-NSIDC_CPRD"
        or source.get("doi") != "10.5067/02LGW4DGJYRX"
        or source.get("measurement_role") != "model-assimilated regional context; not direct soil-moisture measurement or ECHO-accepted evidence for the AOI-scale hypothesis test"
        or query.get("bounds_wgs84") != bounds
        or query.get("grid_posting_m") != 9000.0
        or query.get("same_native_grid_before_after") is not True
        or query.get("aoi_smaller_than_one_grid_cell") is not True
        or not isinstance(observations, list)
        or len(observations) != 2
        or record.get("upstream_dependencies", {}).get("potential_input_overlap")
        != ["NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY"]
        or record.get("processing", {}).get("statistical_significance_test") is not False
    ):
        raise AssessmentError("SMAP L4 context screen identity, scale, or interpretation boundary is invalid")
    root = evidence_root.resolve()
    pair_times = [
        pair.get("source_products", {}).get(role, {}).get("acquisition_start_utc")
        for role in ("before", "after")
    ]
    if any(not isinstance(value, str) for value in pair_times):
        raise AssessmentError("SMAP L4 context cannot be linked to missing SAR acquisition timestamps")
    cmr_queries = query.get("cmr_queries", [])
    if (
        len(cmr_queries) != 2
        or any(
            item.get("hit_count") != item.get("result_count")
            or not isinstance(item.get("response_sha256"), str)
            or len(item["response_sha256"]) != 64
            for item in cmr_queries
        )
    ):
        raise AssessmentError("SMAP L4 CMR search is incomplete or missing response provenance")
    summaries = []
    for observation, target_time in zip(observations, pair_times, strict=True):
        catalog = observation.get("catalog", {})
        asset = observation.get("asset", {})
        relative = asset.get("relative_path")
        digest = asset.get("sha256")
        acquisition = catalog.get("acquisition_time_utc")
        if (
            observation.get("granule_id") != catalog.get("granule_id")
            or
            catalog.get("target_time_utc") != target_time
            or catalog.get("collection_version") != "008"
            or catalog.get("short_name") != "SPL4SMAU"
            or not isinstance(catalog.get("offset_minutes"), (int, float))
            or isinstance(catalog.get("offset_minutes"), bool)
            or catalog["offset_minutes"] > 90
            or not isinstance(acquisition, str)
            or not isinstance(relative, str)
            or Path(relative).is_absolute()
            or not isinstance(digest, str)
            or len(digest) != 64
            or asset.get("format") != "NetCDF-4"
        ):
            raise AssessmentError("SMAP L4 granule identity, acquisition alignment, or subset provenance is incomplete")
        try:
            acquired = datetime.fromisoformat(acquisition.replace("Z", "+00:00"))
            target = datetime.fromisoformat(target_time.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AssessmentError("SMAP L4 and SAR timestamps are invalid") from exc
        if acquired.tzinfo is None or target.tzinfo is None or abs((acquired - target).total_seconds()) > 90 * 60:
            raise AssessmentError("SMAP L4 analysis time is outside the declared matching window")
        if not np.isclose(catalog["offset_minutes"], abs((acquired - target).total_seconds()) / 60, rtol=0, atol=1e-9):
            raise AssessmentError("SMAP L4 acquisition offset does not match the retained timestamps")
        resolved = (root / relative).resolve()
        if not resolved.is_relative_to(root):
            raise AssessmentError("SMAP L4 bounded-subset path escapes the project root")
        try:
            payload = resolved.read_bytes()
        except OSError as exc:
            raise AssessmentError("SMAP L4 bounded source subset is unavailable") from exc
        if len(payload) > 2 * 1024 * 1024 or len(payload) != asset.get("size_bytes") or sha256(payload).hexdigest() != digest:
            raise AssessmentError("SMAP L4 source-subset checksum or size validation failed")
        try:
            rebuilt = summarize_smap_l4_subset(
                resolved,
                observation.get("granule_id", ""),
                project_root=root,
            )
        except (OSError, ValueError, KeyError) as exc:
            raise AssessmentError(f"SMAP L4 source subset cannot reproduce its retained record: {exc}") from exc
        for field in ("asset", "grid", "variables", "harmony_history"):
            if observation.get(field) != rebuilt.get(field):
                raise AssessmentError(f"SMAP L4 source subset does not reproduce its retained {field}")
        summaries.append(rebuilt)
    comparison = record.get("comparison", {})
    before_grid = observations[0].get("grid", {})
    after_grid = observations[1].get("grid", {})
    if before_grid.get("coordinate_grid_sha256") != after_grid.get("coordinate_grid_sha256"):
        raise AssessmentError("SMAP L4 comparison falsely implies accepted QA or incompatible grids")
    grid_lat = np.asarray(before_grid["cell_lat"], dtype=np.float64)
    grid_lon = np.asarray(before_grid["cell_lon"], dtype=np.float64)
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    lat1, lat2 = np.radians(center_lat), np.radians(grid_lat)
    delta_lon = np.radians(grid_lon - center_lon)
    distance_factor = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(delta_lon / 2) ** 2
    nearest = np.unravel_index(int(np.nanargmin(distance_factor)), grid_lat.shape)
    moisture_key = "Analysis_Data/sm_surface_analysis"
    uncertainty_key = "Analysis_Data/sm_surface_analysis_ensstd"
    tb_keys = ("Observations_Data/tb_h_obs_assim", "Observations_Data/tb_v_obs_assim")
    expected_before = observations[0]["variables"][moisture_key]["values"][nearest[0]][nearest[1]]
    expected_after = observations[1]["variables"][moisture_key]["values"][nearest[0]][nearest[1]]
    expected_before_spread = observations[0]["variables"][uncertainty_key]["values"][nearest[0]][nearest[1]]
    expected_after_spread = observations[1]["variables"][uncertainty_key]["values"][nearest[0]][nearest[1]]
    expected_tb_counts = [
        sum(observation["variables"][name]["valid_cell_count"] for name in tb_keys)
        for observation in observations
    ]
    nearest_distance_km = 6371.0088 * 2 * math.asin(math.sqrt(float(distance_factor[nearest])))
    expected_numeric = {
        "before_surface_soil_moisture_model_analysis_m3_m3": expected_before,
        "after_surface_soil_moisture_model_analysis_m3_m3": expected_after,
        "after_minus_before_model_analysis_m3_m3": expected_after - expected_before,
        "before_ensemble_standard_deviation_m3_m3": expected_before_spread,
        "after_ensemble_standard_deviation_m3_m3": expected_after_spread,
        "nearest_cell_center_distance_from_aoi_center_km": nearest_distance_km,
    }
    numeric_matches = comparison.get("nearest_cell_index_row_column") == [int(nearest[0]), int(nearest[1])]
    for field, expected in expected_numeric.items():
        value = comparison.get(field)
        numeric_matches = numeric_matches and isinstance(value, (int, float)) and not isinstance(value, bool) and np.isclose(value, expected)
    if (
        not numeric_matches
        or comparison.get("valid_assimilated_brightness_temperature_values_by_date") != expected_tb_counts
        or expected_tb_counts != [0, 0]
        or "not treated as a QA pass" not in comparison.get("provider_quality_gate", "")
    ):
        raise AssessmentError("SMAP L4 comparison does not reproduce from the retained subsets or overstates quality")
    return {
        "before_granule": observations[0]["granule_id"],
        "after_granule": observations[1]["granule_id"],
        "analysis_times_utc": [item["catalog"]["acquisition_time_utc"] for item in observations],
        "analysis_offsets_minutes": [item["catalog"]["offset_minutes"] for item in observations],
        "nearest_cell_center_wgs84": comparison["nearest_cell_center_wgs84"],
        "nearest_cell_center_distance_from_aoi_center_km": comparison["nearest_cell_center_distance_from_aoi_center_km"],
        "before_surface_soil_moisture_model_analysis_m3_m3": comparison["before_surface_soil_moisture_model_analysis_m3_m3"],
        "after_surface_soil_moisture_model_analysis_m3_m3": comparison["after_surface_soil_moisture_model_analysis_m3_m3"],
        "after_minus_before_model_analysis_m3_m3": comparison["after_minus_before_model_analysis_m3_m3"],
        "before_ensemble_standard_deviation_m3_m3": comparison["before_ensemble_standard_deviation_m3_m3"],
        "after_ensemble_standard_deviation_m3_m3": comparison["after_ensemble_standard_deviation_m3_m3"],
        "interpretation_role": "checksum-verified model-derived regional context; no direct matched brightness-temperature values, no AOI-scale discrimination, no QA acceptance, and no independent corroboration of the GPM input",
    }


def _validate_hls_association(
    vegetation: dict[str, Any],
    association: dict[str, Any],
    *,
    case_id: str,
    bounds: list[float],
    pair: dict[str, Any],
    pair_path: Path,
    vegetation_path: Path,
    product_variant: str = "L30",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observations = vegetation.get("observations")
    sources = association.get("sources", {})
    if (
        vegetation.get("record_type") != f"ECHO_HLS_{product_variant}_VEGETATION_CONTEXT_SCREEN"
        or vegetation.get("status") != "DESCRIPTIVE_OPTICAL_CONTEXT_NOT_CAUSAL_TEST"
        or vegetation.get("case_id") != case_id
        or vegetation.get("query", {}).get("bbox_west_south_east_north") != bounds
        or not isinstance(observations, list)
        or len(observations) != 2
        or association.get("record_type") != f"ECHO_RTC_HLS_{product_variant}_NDVI_SPATIAL_ASSOCIATION"
        or association.get("status") != "DIAGNOSTIC_SPATIAL_ASSOCIATION"
        or association.get("case_id") != case_id
        or sources.get("sar_pair_record_sha256") != sha256(pair_path.read_bytes()).hexdigest()
        or sources.get("hls_vegetation_record_sha256") != sha256(vegetation_path.read_bytes()).hexdigest()
        or sources.get("sar_scene_ids") != [
            item.get("scene_id") for item in pair.get("source_products", {}).values()
        ]
        or sources.get("optical_granule_ids") != [item.get("granule_id") for item in observations]
        or sources.get("optical_acquisition_times_utc") != [item.get("temporal_extent_utc", {}).get("BeginningDateTime") for item in observations]
        or sources.get("sar_acquisition_times_utc") != [item.get("acquisition_start_utc") for item in pair.get("source_products", {}).values()]
        or sources.get("sar_provider_qa", {}).get("status")
        != pair.get("provider_qa", {}).get("status")
    ):
        raise AssessmentError("HLS association identity or source-record links do not match the investigation")
    root = vegetation_path.resolve().parents[2]
    for observation in observations:
        asset = observation.get("asset", {})
        relative = asset.get("relative_path")
        expected_hash = asset.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise AssessmentError("HLS bounded source-subset provenance is incomplete")
        asset_path = Path(relative)
        if asset_path.is_absolute():
            raise AssessmentError("HLS bounded source-subset paths must be relative")
        resolved = (root / asset_path).resolve()
        if not resolved.is_relative_to(root):
            raise AssessmentError("HLS bounded source-subset path escapes the project root")
        try:
            payload = resolved.read_bytes()
        except OSError as exc:
            raise AssessmentError("HLS bounded source subset is unavailable") from exc
        if len(payload) > 64 * 1024 * 1024 or len(payload) != asset.get("size_bytes") or sha256(payload).hexdigest() != expected_hash:
            raise AssessmentError("HLS bounded source-subset checksum or size validation failed")
    sensitivity = association.get("coverage_sensitivity")
    thresholds = association.get("method", {}).get("coverage_thresholds")
    if (
        not isinstance(thresholds, list)
        or not thresholds
        or sensitivity is None
        or [item.get("minimum_common_clear_land_ndvi_area_fraction") for item in sensitivity if isinstance(item, dict)] != thresholds
    ):
        raise AssessmentError("HLS association coverage sensitivity does not match its declared thresholds")
    previous_count = math.inf
    for item in sensitivity:
        if not isinstance(item, dict):
            raise AssessmentError("HLS association coverage sensitivity row is invalid")
        count = item.get("sar_cells")
        correlation = item.get("descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db")
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < 3
            or count > previous_count
            or isinstance(correlation, bool)
            or not isinstance(correlation, (int, float))
            or not math.isfinite(correlation)
            or abs(correlation) > 1
            or item.get("inferential_statistics") != "NOT_COMPUTED; neighboring cells are spatially dependent and RTC-S1 provider QA is diagnostic"
        ):
            raise AssessmentError("HLS association coverage sensitivity violates the descriptive-only contract")
        previous_count = count
    selected = [
        item for item in sensitivity or []
        if isinstance(item, dict) and item.get("minimum_common_clear_land_ndvi_area_fraction") == 0.75
    ]
    if len(selected) != 1:
        raise AssessmentError("HLS association must contain one 0.75 common-support summary")
    computed_offsets = []
    try:
        for optical_time, sar_time in zip(sources["optical_acquisition_times_utc"], sources["sar_acquisition_times_utc"], strict=True):
            optical_dt = datetime.fromisoformat(optical_time.replace("Z", "+00:00"))
            sar_dt = datetime.fromisoformat(sar_time.replace("Z", "+00:00"))
            if optical_dt.tzinfo is None or sar_dt.tzinfo is None:
                raise ValueError("timezone is missing")
            computed_offsets.append((optical_dt - sar_dt).total_seconds() / 3600)
    except (AttributeError, TypeError, ValueError) as exc:
        raise AssessmentError("HLS/SAR acquisition timestamp provenance is invalid") from exc
    recorded_offsets = sources.get("optical_minus_sar_offsets_hours")
    if not isinstance(recorded_offsets, list) or len(recorded_offsets) != 2 or not np.allclose(recorded_offsets, computed_offsets, rtol=0, atol=1e-9):
        raise AssessmentError("HLS/SAR acquisition offsets do not match the recorded timestamps")
    summary = selected[0]
    for field in (
        "sar_cells",
        "median_area_weighted_ndvi_change",
        "descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db",
    ):
        value = summary.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
            raise AssessmentError(f"HLS association metric is missing or invalid: {field}")
    if summary["sar_cells"] < 3 or association.get("method", {}).get("inferential_statistics") not in (None, "NOT_COMPUTED"):
        raise AssessmentError("HLS association does not meet the descriptive-only analysis contract")
    try:
        if __package__:
            from tools.research.evaluate_rtc_hls_ndvi_association import evaluate_association
        else:
            from evaluate_rtc_hls_ndvi_association import evaluate_association

        reproduced = evaluate_association(
            pair,
            vegetation,
            pair_path.read_bytes(),
            vegetation_path.read_bytes(),
        )
        recorded = dict(association)
        expected = dict(reproduced)
        recorded.pop("created_at_utc", None)
        expected.pop("created_at_utc", None)
        sensor_label = recorded.get("sources", {}).get("optical_input_sensor", "")
        expected_sensor_label = f"NASA/USGS HLS {product_variant}"
        if expected_sensor_label not in sensor_label:
            raise AssessmentError("HLS association optical input label does not match its product variant")
        recorded["sources"] = dict(recorded.get("sources", {}))
        expected["sources"] = dict(expected.get("sources", {}))
        recorded["sources"].pop("optical_input_sensor", None)
        expected["sources"].pop("optical_input_sensor", None)
    except Exception as exc:
        raise AssessmentError("HLS association could not be reproduced from its linked source observations") from exc
    if recorded != expected:
        raise AssessmentError("HLS association does not reproduce from its linked source observations")
    return summary, sensitivity


def build_assessment(
    pair_path: Path,
    optical_path: Path,
    nearer_optical_path: Path | None = None,
    catalog_screen_path: Path | None = None,
    case_id: str = "rio-grande-do-sul-cross-sensor-diagnostic-2024",
    spatial_support_path: Path | None = None,
    polarization_vh_pair_path: Path | None = None,
    polarization_vh_spatial_path: Path | None = None,
    polarization_sensitivity_path: Path | None = None,
    gpm_before_path: Path | None = None,
    gpm_after_path: Path | None = None,
    smap_screen_path: Path | None = None,
    hls_vegetation_path: Path | None = None,
    hls_association_path: Path | None = None,
    gpm_intervening_path: Path | None = None,
    gpm_interacquisition_path: Path | None = None,
    smap_radiometer_screen_path: Path | None = None,
    guaiba_context_path: Path | None = None,
    hls_s30_vegetation_path: Path | None = None,
    hls_s30_association_path: Path | None = None,
    acquisition_conditions_path: Path | None = None,
    mod13q1_screen_path: Path | None = None,
    mod09ga_screen_path: Path | None = None,
    ecostress_sm_screen_path: Path | None = None,
    ismn_station_screen_path: Path | None = None,
    sar_temporal_series_path: Path | None = None,
    smap_l4_context_path: Path | None = None,
    guaiba_access_screen_path: Path | None = None,
) -> dict[str, Any]:
    if nearer_optical_path is not None and catalog_screen_path is None:
        raise AssessmentError("the nearer optical record requires its CMR screen")
    pair = _read_json(pair_path, "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS")
    optical = _read_json(optical_path, "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON")
    sar_temporal_series = (
        _read_json(sar_temporal_series_path, "ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS")
        if sar_temporal_series_path is not None
        else None
    )
    sar_temporal_summary = None
    if sar_temporal_series is not None:
        try:
            sar_temporal_summary = validate_opera_rtc_s1_series_record(
                sar_temporal_series,
                pair_record=pair,
            )
        except OperaRtcS1AnalysisError as exc:
            raise AssessmentError(f"OPERA RTC-S1 temporal series is not compatible with the linked pair: {exc}") from exc
    ecostress_sm_screen = _read_case_availability_screen(
        ecostress_sm_screen_path,
        record_type="ECHO_CATALOG_AVAILABILITY_SCREEN",
        case_id=case_id,
        pair=pair,
    )
    ismn_station_screen = _read_case_availability_screen(
        ismn_station_screen_path,
        record_type="ECHO_STATION_CATALOG_AVAILABILITY_SCREEN",
        case_id=case_id,
        pair=pair,
    )
    mod13q1_screen = (
        _read_json(mod13q1_screen_path, MODIS_VI_SCREEN_TYPE)
        if mod13q1_screen_path is not None
        else None
    )
    if mod13q1_screen is not None:
        try:
            validate_mod13q1_candidate_screen(
                mod13q1_screen,
                pair_record=pair,
                pair_record_sha256=sha256(pair_path.read_bytes()).hexdigest(),
                case_id=case_id,
            )
        except ValueError as exc:
            raise AssessmentError(f"MOD13Q1 candidate screen is not linked to this case: {exc}") from exc
    mod09ga_screen = (
        _read_json(mod09ga_screen_path, "ECHO_MOD09GA_VEGETATION_CANDIDATE_SCREEN")
        if mod09ga_screen_path is not None
        else None
    )
    if mod09ga_screen is not None:
        expected_scene_ids = [
            pair["source_products"][role]["scene_id"] for role in ("before", "after")
        ]
        if (
            mod09ga_screen.get("case_id") != case_id
            or mod09ga_screen.get("source", {}).get("source_pair_record_sha256")
            != sha256(pair_path.read_bytes()).hexdigest()
            or mod09ga_screen.get("source", {}).get("sar_scene_ids") != expected_scene_ids
            or mod09ga_screen.get("observations", {}).get("common_strict_accepted_count")
            != len(mod09ga_screen.get("observations", {}).get("paired_ndvi", []))
        ):
            raise AssessmentError("MOD09GA candidate screen is not linked to this case pair or has inconsistent paired results")
    acquisition_conditions = (
        _read_json(acquisition_conditions_path, RTC_CONDITION_REVIEW_TYPE)
        if acquisition_conditions_path is not None
        else None
    )
    if acquisition_conditions is not None:
        if (
            acquisition_conditions.get("case_id") != case_id
            or acquisition_conditions.get("status") != RTC_CONDITION_REVIEW_STATUS
        ):
            raise AssessmentError("acquisition-condition review case or status is invalid")
        try:
            validate_acquisition_condition_review(
                acquisition_conditions,
                pair_record=pair,
                pair_record_sha256=sha256(pair_path.read_bytes()).hexdigest(),
                case_id=case_id,
            )
        except ValueError as exc:
            raise AssessmentError(f"acquisition-condition review is not linked to this SAR pair: {exc}") from exc
    guaiba_context = (
        _read_json(guaiba_context_path, "ECHO_ANA_GUAIBA_FLOOD_STAGE_CONTEXT")
        if guaiba_context_path is not None
        else None
    )
    if guaiba_context is not None:
        guaiba_observation = _validate_guaiba_event_context(
            guaiba_context,
            case_id=case_id,
            pair=pair,
        )
    else:
        guaiba_observation = None
    guaiba_access_screen = (
        _read_json(guaiba_access_screen_path, "ECHO_ANA_GUAIBA_PRIMARY_SERIES_ACCESS_SCREEN")
        if guaiba_access_screen_path is not None
        else None
    )
    if guaiba_access_screen is not None:
        if guaiba_context is None:
            raise AssessmentError("Guaiba series access screen requires the linked official event context")
        _validate_guaiba_access_screen(guaiba_access_screen, case_id=case_id, pair=pair)
    nearer_optical = (
        _read_json(nearer_optical_path, "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON")
        if nearer_optical_path is not None
        else None
    )
    catalog_screen = (
        _read_json(catalog_screen_path, "ECHO_DSWX_HLS_TEMPORAL_CONTEXT_CATALOG_SCREEN")
        if catalog_screen_path is not None
        else None
    )
    spatial_support = (
        _read_json(spatial_support_path, "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC")
        if spatial_support_path is not None
        else None
    )
    polarization_sensitivity = (
        _read_json(polarization_sensitivity_path, "ECHO_RTC_POLARIZATION_SENSITIVITY_DIAGNOSTIC")
        if polarization_sensitivity_path is not None
        else None
    )
    if (gpm_before_path is None) != (gpm_after_path is None):
        raise AssessmentError("GPM temporal context requires both pre-acquisition windows")
    if (gpm_intervening_path is None) != (gpm_interacquisition_path is None):
        raise AssessmentError("GPM inter-acquisition context requires its daily-source and chronology records")
    if gpm_interacquisition_path is not None and (gpm_before_path is None or gpm_after_path is None):
        raise AssessmentError("GPM inter-acquisition chronology requires both SAR-adjacent context windows")
    gpm_contexts = []
    if gpm_before_path is not None and gpm_after_path is not None:
        for path, expected_role, sar_timestamp in (
            (gpm_before_path, "before", pair.get("source_products", {}).get("before", {}).get("acquisition_start_utc")),
            (gpm_after_path, "after", pair.get("source_products", {}).get("after", {}).get("acquisition_start_utc")),
        ):
            context = _read_json(path, "ECHO_GPM_IMERG_DAILY_CONTEXT")
            if context.get("status") != "NASA_REGIONAL_PRECIPITATION_CONTEXT_NOT_CAUSAL_EVIDENCE":
                raise AssessmentError("GPM context does not have its non-causal disposition")
            if context.get("case_id") != case_id:
                raise AssessmentError("GPM context belongs to a different investigation case")
            source = context.get("source", {})
            if (
                source.get("provider") != "NASA GES DISC"
                or source.get("mission") != "Global Precipitation Measurement (GPM)"
                or source.get("short_name") != "GPM_3IMERGDF"
                or source.get("version") != "07"
                or source.get("doi") != "10.5067/GPM/IMERGDF/DAY/07"
                or source.get("units") != "mm/day"
            ):
                raise AssessmentError("GPM source identity or measurement units are unsupported")
            start_text = context.get("query", {}).get("start_date_utc")
            end_text = context.get("query", {}).get("end_date_utc")
            try:
                start_date = datetime.fromisoformat(start_text).date()
                end_date = datetime.fromisoformat(end_text).date()
                acquisition_date = datetime.fromisoformat(sar_timestamp.replace("Z", "+00:00")).date()
            except (AttributeError, TypeError, ValueError) as exc:
                raise AssessmentError("GPM context or SAR acquisition dates are invalid") from exc
            daily = context.get("daily_observations")
            if (
                end_date != acquisition_date - timedelta(days=1)
                or (end_date - start_date).days != 6
                or not isinstance(daily, list) or len(daily) != 7
            ):
                raise AssessmentError("GPM context must contain seven complete days strictly before its SAR acquisition")
            expected_dates = [(start_date + timedelta(days=index)).isoformat() for index in range(7)]
            if [item.get("date_utc") for item in daily] != expected_dates:
                raise AssessmentError("GPM daily context dates are missing, duplicated, or out of order")
            for day in daily:
                sample = day.get("aoi_nearest_cell", {})
                asset = day.get("asset", {})
                asset_path = Path(asset.get("relative_path", ""))
                if (
                    not sample.get("full_day_sample_complete")
                    or sample.get("valid_half_hourly_samples") != 48
                    or isinstance(sample.get("precipitation_mm_per_day"), bool)
                    or not isinstance(sample.get("precipitation_mm_per_day"), (int, float))
                    or not np.isfinite(sample["precipitation_mm_per_day"])
                    or sample["precipitation_mm_per_day"] < 0
                    or asset_path.is_absolute()
                    or not asset_path.is_file()
                    or sha256(asset_path.read_bytes()).hexdigest() != asset.get("sha256")
                ):
                    raise AssessmentError("GPM context has incomplete daily coverage or an invalid source-subset checksum")
            if context.get("summary", {}).get("days_with_48_valid_samples_at_nearest_cell") != 7:
                raise AssessmentError("GPM context summary does not confirm seven complete nearest-cell days")
            summed_daily_estimates = sum(
                item["aoi_nearest_cell"]["precipitation_mm_per_day"] for item in daily
            )
            if not np.isclose(
                summed_daily_estimates,
                context.get("summary", {}).get("nearest_cell_complete_day_sum_mm"),
                rtol=1e-9,
                atol=1e-9,
            ):
                raise AssessmentError("GPM context aggregate does not match its daily observations")
            gpm_contexts.append((path, context, expected_role))
    gpm_intervening = None
    gpm_interacquisition = None
    if gpm_intervening_path is not None and gpm_interacquisition_path is not None:
        gpm_intervening = _read_json(gpm_intervening_path, "ECHO_GPM_IMERG_DAILY_CONTEXT")
        gpm_interacquisition = _read_json(
            gpm_interacquisition_path,
            "ECHO_GPM_IMERG_INTERACQUISITION_CHRONOLOGY",
        )
        after_context = next((context for _, context, role in gpm_contexts if role == "after"), None)
        if after_context is None:
            raise AssessmentError("GPM inter-acquisition chronology is missing its trailing SAR-adjacent context")
        try:
            rebuilt_gpm_interacquisition = build_interacquisition_context(
                sar_record=pair,
                sar_payload=pair_path.read_bytes(),
                interval_record=gpm_intervening,
                interval_payload=gpm_intervening_path.read_bytes(),
                after_context_record=after_context,
                after_context_payload=gpm_after_path.read_bytes(),
                case_id=case_id,
                project_root=Path(__file__).resolve().parents[2],
            )
        except InteracquisitionContextError as exc:
            raise AssessmentError(f"GPM inter-acquisition source evidence is invalid: {exc}") from exc
        for field in (
            "record_type",
            "status",
            "case_id",
            "source",
            "sar_interval",
            "sources",
            "query",
            "daily_observations",
            "summary",
        ):
            if gpm_interacquisition.get(field) != rebuilt_gpm_interacquisition.get(field):
                raise AssessmentError(f"GPM inter-acquisition chronology does not reproduce from retained sources: {field}")
    smap_screen = (
        _read_json(smap_screen_path, "ECHO_SMAP_SENTINEL_SOIL_MOISTURE_CANDIDATE_SCREEN")
        if smap_screen_path is not None
        else None
    )
    smap_radiometer_screen = (
        _read_json(smap_radiometer_screen_path, "ECHO_SMAP_RADIOMETER_CANDIDATE_SCREEN")
        if smap_radiometer_screen_path is not None
        else None
    )
    smap_l4_context = (
        _read_json(smap_l4_context_path, "ECHO_SMAP_L4_REGIONAL_SOIL_MOISTURE_CONTEXT_SCREEN")
        if smap_l4_context_path is not None
        else None
    )
    if smap_radiometer_screen is not None:
        aoi_bounds = optical.get("aoi", {}).get("bounds_west_south_east_north")
        spatial = smap_radiometer_screen.get("spatial_suitability", {})
        query = smap_radiometer_screen.get("query", {})
        source = smap_radiometer_screen.get("source", {})
        if (
            smap_radiometer_screen.get("status") != "SCREENED_SPATIALLY_TOO_COARSE_FOR_AOI_SCALE_TEST"
            or smap_radiometer_screen.get("case_id") != case_id
            or source.get("short_name") != "SPL3SMP_E"
            or source.get("version") != "006"
            or source.get("instrument") != "L-band radiometer"
            or source.get("source_independence") != "Radiometer-only SMAP product; does not use Sentinel-1 radar inputs."
            or query.get("bounds_wgs84") != aoi_bounds
            or query.get("cmr_hit_count") != query.get("cmr_result_count")
            or query.get("cmr_result_count") != len(smap_radiometer_screen.get("screened_daily_granules", []))
            or spatial.get("radiometer_native_footprint_km_approx") != 36
            or spatial.get("product_grid_posting_km") != 9
            or smap_radiometer_screen.get("retrieval", {}).get("data_files_downloaded") is not False
            or smap_radiometer_screen.get("retrieval", {}).get("pixel_values_read") is not False
        ):
            raise AssessmentError("SMAP radiometer candidate screen is inconsistent with the case, source, or no-retrieval disposition")
    if (hls_vegetation_path is None) != (hls_association_path is None):
        raise AssessmentError("HLS vegetation context requires its linked spatial-association record")
    hls_vegetation = (
        _read_json(hls_vegetation_path, "ECHO_HLS_L30_VEGETATION_CONTEXT_SCREEN")
        if hls_vegetation_path is not None
        else None
    )
    hls_association = (
        _read_json(hls_association_path, "ECHO_RTC_HLS_L30_NDVI_SPATIAL_ASSOCIATION")
        if hls_association_path is not None
        else None
    )
    if (hls_s30_vegetation_path is None) != (hls_s30_association_path is None):
        raise AssessmentError("HLS S30 vegetation context requires its linked spatial-association record")
    hls_s30_vegetation = (
        _read_json(hls_s30_vegetation_path, "ECHO_HLS_S30_VEGETATION_CONTEXT_SCREEN")
        if hls_s30_vegetation_path is not None
        else None
    )
    hls_s30_association = (
        _read_json(hls_s30_association_path, "ECHO_RTC_HLS_S30_NDVI_SPATIAL_ASSOCIATION")
        if hls_s30_association_path is not None
        else None
    )
    vh_pair = (
        _read_json(polarization_vh_pair_path, "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS")
        if polarization_vh_pair_path is not None
        else None
    )
    vh_spatial = (
        _read_json(polarization_vh_spatial_path, "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC")
        if polarization_vh_spatial_path is not None
        else None
    )
    if pair.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON":
        raise AssessmentError("the retained RTC-S1 record is not the expected diagnostic comparison")
    if optical.get("status") != "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION":
        raise AssessmentError("the DSWx-HLS record does not have its optical-context-only disposition")
    if spatial_support is not None:
        sources = spatial_support.get("sources", {})
        if spatial_support.get("status") != "DIAGNOSTIC_SPATIAL_ASSOCIATION":
            raise AssessmentError("the spatial-support record does not have its diagnostic disposition")
        if (
            sources.get("sar_pair_record_sha256") != sha256(pair_path.read_bytes()).hexdigest()
            or sources.get("optical_context_record_sha256") != sha256(optical_path.read_bytes()).hexdigest()
        ):
            raise AssessmentError("the spatial-support record was built from different source records")
        if (
            sources.get("sar_scene_ids") != [
                item.get("scene_id") for item in pair.get("source_products", {}).values()
            ]
            or sources.get("optical_granule_ids") != [
                optical.get("source_products", {}).get(role, {}).get("granule_id")
                for role in ("before", "after")
            ]
        ):
            raise AssessmentError("the spatial-support record identifies different source observations")
        sensitivity = spatial_support.get("summary", {}).get("coverage_sensitivity")
        if not isinstance(sensitivity, list) or not sensitivity:
            raise AssessmentError("the spatial-support record has no coverage-sensitivity summary")
        selected_summary = [
            item for item in sensitivity
            if isinstance(item, dict)
            and item.get("minimum_common_valid_wtr_area_fraction") == 0.75
        ]
        if len(selected_summary) != 1:
            raise AssessmentError("the spatial-support record must contain one 0.75 coverage summary")
        spatial_summary = selected_summary[0]
        numeric_fields = (
            "sar_cells",
            "water_fraction_increased_by_more_than_0_05",
            "water_fraction_decreased_by_more_than_0_05",
            "water_fraction_changed_by_at_most_0_05",
            "descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db",
        )
        if any(
            isinstance(spatial_summary.get(field), bool)
            or not isinstance(spatial_summary.get(field), (int, float))
            or not np.isfinite(spatial_summary[field])
            for field in numeric_fields
        ):
            raise AssessmentError("the spatial-support summary has missing or non-finite metrics")
        if sum(spatial_summary[field] for field in numeric_fields[1:4]) != spatial_summary["sar_cells"]:
            raise AssessmentError("the spatial-support change counts do not match the selected cell count")
    if polarization_sensitivity is not None:
        if vh_pair is None or polarization_vh_pair_path is None or vh_spatial is None or polarization_vh_spatial_path is None or spatial_support_path is None:
            raise AssessmentError("the polarization comparison requires linked VV and VH pair and spatial records")
        sensitivity_sources = polarization_sensitivity.get("sources", {})
        sensitivity_summary = polarization_sensitivity.get("summary", {})
        if polarization_sensitivity.get("status") != "DIAGNOSTIC_SENSITIVITY_ONLY":
            raise AssessmentError("the polarization comparison is not labeled diagnostic")
        if (
            sensitivity_sources.get("vv_pair_record_sha256") != sha256(pair_path.read_bytes()).hexdigest()
            or sensitivity_sources.get("optical_context_record_sha256") != sha256(optical_path.read_bytes()).hexdigest()
            or sensitivity_sources.get("sar_scene_ids") != [
                item.get("scene_id") for item in pair.get("source_products", {}).values()
            ]
            or sensitivity_sources.get("optical_granule_ids") != [
                optical.get("source_products", {}).get(role, {}).get("granule_id")
                for role in ("before", "after")
            ]
            or sensitivity_sources.get("vh_pair_record_sha256") != sha256(polarization_vh_pair_path.read_bytes()).hexdigest()
            or sensitivity_sources.get("vv_spatial_record_sha256") != sha256(spatial_support_path.read_bytes()).hexdigest()
            or sensitivity_sources.get("vh_spatial_record_sha256") != sha256(polarization_vh_spatial_path.read_bytes()).hexdigest()
        ):
            raise AssessmentError("the polarization comparison references different source observations")
        if (
            vh_pair.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"
            or vh_pair.get("measurement", {}).get("polarization") != "VH"
            or vh_pair.get("provider_qa", {}).get("status") != pair.get("provider_qa", {}).get("status")
            or [item.get("scene_id") for item in vh_pair.get("source_products", {}).values()]
            != [item.get("scene_id") for item in pair.get("source_products", {}).values()]
        ):
            raise AssessmentError("the linked VH pair is incompatible with the primary VV observations")
        vh_spatial_sources = vh_spatial.get("sources", {})
        if (
            vh_spatial.get("status") != "DIAGNOSTIC_SPATIAL_ASSOCIATION"
            or vh_spatial_sources.get("sar_polarization") != "VH"
            or vh_spatial_sources.get("sar_pair_record_sha256") != sha256(polarization_vh_pair_path.read_bytes()).hexdigest()
            or vh_spatial_sources.get("optical_context_record_sha256") != sha256(optical_path.read_bytes()).hexdigest()
        ):
            raise AssessmentError("the linked VH spatial overlay references incompatible source records")
        if sensitivity_summary.get("common_cells", 0) < 3 or polarization_sensitivity.get("method", {}).get("minimum_common_valid_wtr_area_fraction") != 0.75:
            raise AssessmentError("the polarization comparison does not meet the retained common-support contract")
        for key in (
            "vv_pearson_r_water_change_vs_log_ratio",
            "vh_pearson_r_water_change_vs_log_ratio",
            "vv_vh_pearson_r_log_ratio",
            "vh_minus_vv_median_db",
        ):
            value = sensitivity_summary.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
                raise AssessmentError(f"polarization comparison metric is missing or invalid: {key}")

    pair_bounds = pair.get("grid", {}).get("window", {}).get("bounds_wgs84")
    optical_bounds = optical.get("aoi", {}).get("bounds_west_south_east_north")
    if not isinstance(pair_bounds, list) or pair_bounds != optical_bounds:
        raise AssessmentError("the RTC-S1 and DSWx-HLS records do not describe the same WGS84 AOI")
    smap_l4_context_summary = None
    if smap_l4_context is not None and smap_l4_context_path is not None:
        smap_l4_context_summary = _validate_smap_l4_context(
            smap_l4_context,
            case_id=case_id,
            bounds=pair_bounds,
            pair=pair,
            evidence_root=smap_l4_context_path.resolve().parents[2],
        )
    if smap_screen is not None and smap_screen_path is not None:
        _validate_smap_screen(
            smap_screen,
            case_id=case_id,
            bounds=pair_bounds,
            evidence_root=smap_screen_path.resolve().parents[2],
        )
    hls_association_summary = None
    if hls_vegetation is not None and hls_association is not None and hls_vegetation_path is not None and hls_association_path is not None:
        hls_association_summary, hls_association_sensitivity = _validate_hls_association(
            hls_vegetation,
            hls_association,
            case_id=case_id,
            bounds=pair_bounds,
            pair=pair,
            pair_path=pair_path,
            vegetation_path=hls_vegetation_path,
        )
    else:
        hls_association_sensitivity = None
    hls_s30_association_summary = None
    if (
        hls_s30_vegetation is not None
        and hls_s30_association is not None
        and hls_s30_vegetation_path is not None
        and hls_s30_association_path is not None
    ):
        source = hls_s30_vegetation.get("source", {})
        query = hls_s30_vegetation.get("query", {})
        comparison = hls_s30_vegetation.get("comparison", {})
        count = comparison.get("common_clear_land_ndvi_pixel_count")
        aoi_count = comparison.get("aoi_center_pixel_count")
        fraction = comparison.get("common_clear_land_aoi_fraction")
        if (
            source.get("provider") != "NASA LP DAAC"
            or source.get("product_variant") != "S30"
            or source.get("short_name") != "HLSS30"
            or source.get("version") != "2.0"
            or source.get("collection_id") != "C2021957295-LPCLOUD"
            or query.get("product_variant") != "S30"
            or query.get("nir_band") != "B8A"
            or query.get("requested_assets") != ["B04", "B8A", "Fmask"]
            or query.get("bbox_west_south_east_north") != pair_bounds
            or hls_s30_vegetation.get("case_id") != case_id
            or not isinstance(count, int)
            or not isinstance(aoi_count, int)
            or aoi_count <= 0
            or count < 0
            or count > aoi_count
            or not isinstance(fraction, (int, float))
            or not math.isclose(fraction, count / aoi_count, rel_tol=0, abs_tol=1e-12)
        ):
            raise AssessmentError("HLS S30 source identity, AOI, or valid-support summary is inconsistent")
        observations = hls_s30_vegetation.get("observations")
        if not isinstance(observations, list) or len(observations) != 2 or any(
            not isinstance(item, dict)
            or item.get("collection_id") != "C2021957295-LPCLOUD"
            or not item.get("granule_id", "").startswith("HLS.S30.")
            or not item.get("granule_id", "").endswith(".v2.0")
            for item in observations
        ):
            raise AssessmentError("HLS S30 granule identity or collection metadata is invalid")
        hls_s30_association_summary, _ = _validate_hls_association(
            hls_s30_vegetation,
            hls_s30_association,
            case_id=case_id,
            bounds=pair_bounds,
            pair=pair,
            pair_path=pair_path,
            vegetation_path=hls_s30_vegetation_path,
            product_variant="S30",
        )
    if gpm_contexts:
        expected_center = None
        for _, context, _ in gpm_contexts:
            query = context.get("query", {})
            if query.get("aoi_west_south_east_north") != pair_bounds:
                raise AssessmentError("GPM context does not describe the SAR and optical AOI")
            request_bounds = query.get("bbox_west_south_east_north")
            if not isinstance(request_bounds, list) or len(request_bounds) != 4:
                raise AssessmentError("GPM request bounds are missing or invalid")
            west, south, east, north = request_bounds
            if west > pair_bounds[0] or south > pair_bounds[1] or east < pair_bounds[2] or north < pair_bounds[3]:
                raise AssessmentError("GPM request bounds do not cover the investigation AOI")
            cell_center = query.get("aoi_nearest_native_cell_center")
            if not isinstance(cell_center, list) or len(cell_center) != 2:
                raise AssessmentError("GPM nearest native cell location is missing")
            if expected_center is not None and cell_center != expected_center:
                raise AssessmentError("GPM comparison windows use different nearest native cells")
            expected_center = cell_center
    if catalog_screen is not None:
        if catalog_screen.get("status") != "METADATA_ONLY_NO_PIXEL_QA":
            raise AssessmentError("the DSWx-HLS catalog screen has an unsupported disposition")
        if catalog_screen.get("bounds_wgs84") != pair_bounds:
            raise AssessmentError("the DSWx-HLS catalog screen does not describe the SAR AOI")
    if nearer_optical is not None:
        nearer_bounds = nearer_optical.get("aoi", {}).get("bounds_west_south_east_north")
        if nearer_optical.get("status") != "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION":
            raise AssessmentError("the nearer DSWx-HLS record is not labeled optical context only")
        if nearer_bounds != pair_bounds:
            raise AssessmentError("the follow-up records do not describe the same WGS84 AOI")

    measurement = pair.get("measurement", {})
    values = np.asarray(measurement.get("values_db"), dtype=np.float64)
    valid = np.asarray(measurement.get("valid_mask"), dtype=bool)
    common_clear = np.asarray(measurement.get("common_clear_mask"), dtype=bool)
    if values.shape != valid.shape or values.shape != common_clear.shape:
        raise AssessmentError("measurement values and validity masks have different shapes")
    valid &= common_clear & np.isfinite(values)
    samples = values[valid]
    measured_count = int(measurement.get("measured_pixel_count", -1))
    if samples.size == 0 or samples.size != measured_count:
        raise AssessmentError("valid diagnostic measurement count does not match the source record")
    if samples.size != int(measurement.get("common_clear_pixel_count", -1)):
        raise AssessmentError("common-clear count does not match the diagnostic measurement samples")

    before = pair.get("source_products", {}).get("before", {})
    after = pair.get("source_products", {}).get("after", {})
    if not before.get("scene_id") or not after.get("scene_id"):
        raise AssessmentError("RTC-S1 source scene identifiers are missing")
    transitions = optical.get("transitions", {})
    wtr = transitions.get("WTR", {})
    wtr2 = transitions.get("WTR-2", {})
    overlap = optical.get("wtr2_confidence_quality_overlap", {})
    if not wtr or not wtr2 or not overlap.get("before") or not overlap.get("after"):
        raise AssessmentError("optical water and confidence-context summaries are incomplete")

    evidence = [
        _artifact(pair_path, pair, "SAR-RTC-S1-PAIR", "DIAGNOSTIC_SAR_MEASUREMENT"),
        _artifact(optical_path, optical, "NASA-OPERA-DSWX-HLS", "OPTICAL_PRODUCT_CONTEXT"),
    ]
    if sar_temporal_series is not None and sar_temporal_series_path is not None:
        evidence.append(
            _artifact(
                sar_temporal_series_path,
                sar_temporal_series,
                "NASA-OPERA-RTC-S1-TEMPORAL-SERIES",
                "DIAGNOSTIC_SAR_TEMPORAL_ANALYSIS",
            )
        )
    if acquisition_conditions is not None and acquisition_conditions_path is not None:
        evidence.append(
            _artifact(
                acquisition_conditions_path,
                acquisition_conditions,
                "NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW",
                "DERIVED_ACQUISITION_METADATA_COMPARISON",
            )
        )
    if guaiba_context is not None and guaiba_context_path is not None:
        evidence.append(
            _artifact(
                guaiba_context_path,
                guaiba_context,
                "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY",
                "OFFICIAL_HYDROLOGIC_EVENT_CONTEXT",
            )
        )
    if guaiba_access_screen is not None and guaiba_access_screen_path is not None:
        evidence.append(
            _artifact(
                guaiba_access_screen_path,
                guaiba_access_screen,
                "ANA-GUAIBA-PRIMARY-SERIES-ACCESS-SCREEN",
                "PRIMARY_GAUGE_SERIES_ACCESS_METADATA_ONLY",
            )
        )
    screen_evidence_id = None
    if catalog_screen is not None:
        screen_evidence_id = (
            "NASA-CMR-DSWX-FOLLOWUP-SCREEN"
            if nearer_optical is not None
            else "NASA-CMR-DSWX-TEMPORAL-SCREEN"
        )
        evidence.append(_artifact(catalog_screen_path, catalog_screen, screen_evidence_id, "CATALOG_DISCOVERY_ONLY"))
    nearer_context = None
    if nearer_optical is not None and catalog_screen is not None:
        query_results = catalog_screen.get("query_results", [])
        nearest_by_reference = {
            item.get("reference_label"): item.get("nearest_candidate", {}).get("granule_id")
            for item in query_results
            if isinstance(item, dict) and isinstance(item.get("nearest_candidate"), dict)
        }
        nearer_before = nearer_optical.get("source_products", {}).get("before", {})
        nearer_after = nearer_optical.get("source_products", {}).get("after", {})
        if (
            nearer_before.get("granule_id") != nearest_by_reference.get("before")
            or nearer_after.get("granule_id") != nearest_by_reference.get("after")
        ):
            raise AssessmentError("the follow-up optical products do not match the nearest CMR candidates")
        nearer_transitions = nearer_optical.get("transitions", {})
        nearer_wtr = nearer_transitions.get("WTR", {})
        nearer_wtr2 = nearer_transitions.get("WTR-2", {})
        nearer_overlap = nearer_optical.get("wtr2_confidence_quality_overlap", {})
        if not nearer_wtr or not nearer_wtr2 or not nearer_overlap.get("before"):
            raise AssessmentError("the nearer optical record lacks class or quality summaries")
        earlier_water = int(nearer_wtr2.get("water_class_pixels_before_on_common_valid", -1))
        flagged_water = int(
            nearer_overlap["before"].get("wtr2_water_pixels_with_conf_cloud_or_snow_flag", -1)
        )
        if nearer_wtr.get("common_valid_pixel_count") != 0 or earlier_water <= 0 or flagged_water != earlier_water:
            raise AssessmentError("the selected nearer product pair does not match its quality-limited review")
        evidence.extend(
            [
                _artifact(
                    nearer_optical_path,
                    nearer_optical,
                    "NASA-OPERA-DSWX-NEARER-CONTEXT",
                    "OPTICAL_CONTEXT_QUALITY_LIMITED",
                ),
            ]
        )
        nearer_context = {
            "before_granule": nearer_before["granule_id"],
            "after_granule": nearer_after["granule_id"],
            "before_acquisition_utc": nearer_before["acquisition_time_utc"],
            "after_acquisition_utc": nearer_after["acquisition_time_utc"],
            "offset_from_rtc_before_days": nearer_optical["temporal_relationship"][
                "optical_before_minus_rtc_before_days"
            ],
            "offset_from_rtc_after_days": nearer_optical["temporal_relationship"][
                "optical_after_minus_rtc_after_days"
            ],
            "wtr_common_valid_count": int(nearer_wtr["common_valid_pixel_count"]),
            "wtr2_water_class_counts_before_after": [
                int(nearer_wtr2["water_class_pixels_before_on_common_valid"]),
                int(nearer_wtr2["water_class_pixels_after_on_common_valid"]),
            ],
            "wtr2_cloud_or_snow_flagged_water_before_after": [
                flagged_water,
                int(
                    nearer_overlap.get("after", {}).get(
                        "wtr2_water_pixels_with_conf_cloud_or_snow_flag", 0
                    )
                ),
            ],
            "interpretation_role": "nearest metadata candidates retrieved and checksum-verified; WTR has no shared valid pixels and earlier WTR-2 water classes are all cloud/snow flagged",
        }
    if spatial_support is not None and spatial_support_path is not None:
        evidence.append(
            _artifact(
                spatial_support_path,
                spatial_support,
                "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT",
                "DIAGNOSTIC_CROSS_SENSOR_SPATIAL_ASSOCIATION",
            )
        )
    if polarization_sensitivity is not None and polarization_sensitivity_path is not None:
        evidence.append(
            _artifact(
                polarization_vh_spatial_path,
                vh_spatial,
                "NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT",
                "DIAGNOSTIC_CROSS_SENSOR_SPATIAL_ASSOCIATION",
            )
        )
        evidence.append(
            _artifact(
                polarization_vh_pair_path,
                vh_pair,
                "NASA-OPERA-RTC-S1-VH-PAIR",
                "DIAGNOSTIC_SAR_MEASUREMENT",
            )
        )
        evidence.append(
            _artifact(
                polarization_sensitivity_path,
                polarization_sensitivity,
                "NASA-OPERA-RTC-POLARIZATION-SENSITIVITY",
                "DIAGNOSTIC_POLARIZATION_SENSITIVITY",
            )
        )
    for path, context, role in gpm_contexts:
        evidence.append(
            _artifact(
                path,
                context,
                f"NASA-GPM-IMERG-{role.upper()}-PRE-SAR",
                "NASA_REGIONAL_PRECIPITATION_CONTEXT",
            )
        )
    if gpm_intervening is not None and gpm_intervening_path is not None and gpm_interacquisition is not None and gpm_interacquisition_path is not None:
        evidence.extend([
            _artifact(
                gpm_intervening_path,
                gpm_intervening,
                "NASA-GPM-IMERG-INTERVENING-DAILY-CONTEXT",
                "NASA_REGIONAL_PRECIPITATION_DAILY_SOURCE",
            ),
            _artifact(
                gpm_interacquisition_path,
                gpm_interacquisition,
                "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY",
                "DERIVED_REGIONAL_PRECIPITATION_CHRONOLOGY",
            ),
        ])
    if smap_screen is not None and smap_screen_path is not None:
        evidence.append(
            _artifact(
                smap_screen_path,
                smap_screen,
                "NASA-SPL2SMAP-S-CANDIDATE-SCREEN",
                "NASA_CONTEXT_QUALITY_LIMITED_SCREEN",
            )
        )
    if smap_radiometer_screen is not None and smap_radiometer_screen_path is not None:
        evidence.append(
            _artifact(
                smap_radiometer_screen_path,
                smap_radiometer_screen,
                "NASA-SMAP-SPL3SMP-E-RESOLUTION-SCREEN",
                "NASA_CONTEXT_SPATIAL_SUITABILITY_SCREEN",
            )
        )
    if smap_l4_context is not None and smap_l4_context_path is not None:
        evidence.append(
            _artifact(
                smap_l4_context_path,
                smap_l4_context,
                "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN",
                "NASA_MODEL_ASSIMILATED_REGIONAL_SOIL_MOISTURE_CONTEXT",
            )
        )
    if hls_vegetation is not None and hls_association is not None and hls_vegetation_path is not None and hls_association_path is not None:
        evidence.extend([
            _artifact(hls_vegetation_path, hls_vegetation, "NASA-HLS-L30-VEGETATION-SCREEN", "NASA_LANDSAT_OPTICAL_MEASUREMENT_CONTEXT"),
            _artifact(hls_association_path, hls_association, "NASA-HLS-L30-NDVI-SAR-ASSOCIATION", "DIAGNOSTIC_CROSS_SENSOR_SPATIAL_ASSOCIATION"),
        ])
    if (
        hls_s30_vegetation is not None
        and hls_s30_association is not None
        and hls_s30_vegetation_path is not None
        and hls_s30_association_path is not None
    ):
        evidence.extend([
            _artifact(hls_s30_vegetation_path, hls_s30_vegetation, "NASA-HLS-S30-VEGETATION-SCREEN", "NASA_SENTINEL2_OPTICAL_MEASUREMENT_CONTEXT"),
            _artifact(hls_s30_association_path, hls_s30_association, "NASA-HLS-S30-NDVI-SAR-ASSOCIATION", "DIAGNOSTIC_CROSS_SENSOR_SPATIAL_ASSOCIATION"),
        ])
    if mod13q1_screen is not None and mod13q1_screen_path is not None:
        evidence.append(
            _artifact(
                mod13q1_screen_path,
                mod13q1_screen,
                "NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN",
                "NASA_CONTEXT_QUALITY_AND_TEMPORAL_SUPPORT_LIMITED_SCREEN",
            )
        )
    if mod09ga_screen is not None and mod09ga_screen_path is not None:
        evidence.append(
            _artifact(
                mod09ga_screen_path,
                mod09ga_screen,
                "NASA-MOD09GA-VEGETATION-CANDIDATE-SCREEN",
                "NASA_DAILY_SURFACE_REFLECTANCE_QUALITY_LIMITED_SCREEN",
            )
        )
    if ecostress_sm_screen is not None and ecostress_sm_screen_path is not None:
        evidence.append(
            _artifact(
                ecostress_sm_screen_path,
                ecostress_sm_screen,
                "NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN",
                "NASA_MODEL_DERIVED_SOIL_MOISTURE_CATALOG_SCREEN",
            )
        )
    if ismn_station_screen is not None and ismn_station_screen_path is not None:
        evidence.append(
            _artifact(
                ismn_station_screen_path,
                ismn_station_screen,
                "ISMN-SOIL-MOISTURE-STATION-COVERAGE",
                "IN_SITU_STATION_CATALOG_AVAILABILITY_SCREEN",
            )
        )
    evidence = _link_evidence_lineage(evidence)
    sar = {
        "quantity": measurement["quantity"],
        "equation": measurement["equation"],
        "sensor": "Sentinel-1A via NASA OPERA RTC-S1; not NISAR",
        "polarization": measurement["polarization"],
        "units": measurement["units"],
        "acquisition_before_utc": before["acquisition_start_utc"],
        "acquisition_after_utc": after["acquisition_start_utc"],
        "scene_ids": [before["scene_id"], after["scene_id"]],
        "grid_crs": pair.get("grid", {}).get("crs"),
        "aoi_pixel_count": int(measurement["aoi_pixel_count"]),
        "common_clear_pixel_count": int(samples.size),
        "common_clear_fraction": samples.size / int(measurement["aoi_pixel_count"]),
        "mean_db": float(np.mean(samples)),
        "median_db": float(np.median(samples)),
        "p05_db": float(np.quantile(samples, 0.05)),
        "p95_db": float(np.quantile(samples, 0.95)),
        "minimum_db": float(np.min(samples)),
        "maximum_db": float(np.max(samples)),
        "negative_pixel_count": int(np.count_nonzero(samples < 0)),
        "positive_pixel_count": int(np.count_nonzero(samples > 0)),
        "provider_qa_state": pair.get("provider_qa", {}).get("status"),
        "analysis_disposition": pair["status"],
    }
    optical_before = optical["source_products"]["before"]
    optical_after = optical["source_products"]["after"]
    temporal = optical.get("temporal_relationship", {})
    before_offset = temporal.get("optical_before_minus_rtc_before_days")
    after_offset = temporal.get("optical_after_minus_rtc_after_days")
    if not isinstance(before_offset, (int, float)) or not isinstance(after_offset, (int, float)):
        raise AssessmentError("optical-to-SAR acquisition offsets are missing")
    timing_description = (
        f"The optical acquisitions are {before_offset:+.2f} and {after_offset:+.2f} days "
        "from their corresponding SAR acquisitions."
    )
    spatial_limit = (
        "The products use different native grids; exact area-weighted polygon overlap was evaluated without resampling."
        if spatial_support is not None
        else "The products use different native grids and no pixel-wise cross-sensor comparison was performed."
    )
    optical_context = {
        "product": "NASA OPERA L3 DSWx-HLS; optical HLS-derived classification",
        "before_granule": optical_before["granule_id"],
        "after_granule": optical_after["granule_id"],
        "before_acquisition_utc": optical_before["acquisition_time_utc"],
        "after_acquisition_utc": optical_after["acquisition_time_utc"],
        "wgs84_aoi": optical_bounds,
        "wtr_common_valid_count": wtr["common_valid_pixel_count"],
        "wtr_water_class_counts_before_after": [
            wtr["water_class_pixels_before_on_common_valid"],
            wtr["water_class_pixels_after_on_common_valid"],
        ],
        "wtr2_common_valid_count": wtr2["common_valid_pixel_count"],
        "wtr2_water_class_counts_before_after": [
            wtr2["water_class_pixels_before_on_common_valid"],
            wtr2["water_class_pixels_after_on_common_valid"],
        ],
        "wtr2_water_pixels_with_conf_cloud_or_snow_flags_before_after": [
            overlap["before"]["wtr2_water_pixels_with_conf_cloud_or_snow_flag"],
            overlap["after"]["wtr2_water_pixels_with_conf_cloud_or_snow_flag"],
        ],
        "interpretation_role": "product classification context only; not a field reference or SAR validation",
    }
    temporal = optical.get("temporal_relationship", {})
    evidence_ids = {item["evidence_id"] for item in evidence}
    known_hypothesis_ids = {
        "H1_OPTICAL_PRODUCT_CLASS_COUNTS_DECLINED",
        "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        "H3_SOIL_MOISTURE_CHANGE",
        "H4_VEGETATION_STATE_CHANGE",
        "H5_ACQUISITION_CONDITIONS_EFFECT",
        "H6_SAR_PRODUCT_QUALITY_EFFECT",
    }
    follow_up_items: list[dict[str, object]] = [
        {
            "follow_up_id": "F1_RTC_QA_RESOLUTION",
            "target_hypothesis_ids": [
                "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
                "H6_SAR_PRODUCT_QUALITY_EFFECT",
            ],
            "purpose": "QUALITY_GATE",
            "availability_state": "PROVIDER_RESPONSE_REQUIRED",
            "action": "Obtain an authoritative QA disposition or corrected reprocessing for both exact RTC-S1 granules.",
            "discriminating_question": "Does the provider resolve the product-level quality concerns for these exact observations?",
            "possible_interpretation": "A resolved disposition can remove or confirm a product-quality limitation for this comparison; it cannot establish that water change caused the radar response.",
            "priority_reason": "This comparison remains diagnostic while its provider QA status has no consolidated verdict.",
        },
    ]
    if nearer_context is not None:
        follow_up_items.append(
            {
                "follow_up_id": "F2_CLOSER_WATER_CONTEXT",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "RETRIEVED_QUALITY_LIMITED",
                "evidence_refs": ["NASA-CMR-DSWX-FOLLOWUP-SCREEN", "NASA-OPERA-DSWX-NEARER-CONTEXT"],
                "action": "Queried the nearest CMR candidates and retrieved the selected DSWx-HLS pair with asset checksum verification.",
                "discriminating_question": "Does spatially compatible water context co-vary with the radar-response pattern across closely timed acquisitions?",
                "possible_interpretation": f"This closer pair is quality limited: WTR has {nearer_context['wtr_common_valid_count']} common valid pixels; {nearer_context['wtr2_cloud_or_snow_flagged_water_before_after'][0]} of {nearer_context['wtr2_water_class_counts_before_after'][0]} earlier WTR-2 water-coded cells carry cloud/snow flags. It does not resolve the water explanation.",
                "priority_reason": "The nearest catalog candidates were tested; the earlier WTR-2 water classes are cloud/snow flagged and no shared WTR pixels are valid.",
            }
        )
    elif catalog_screen is not None:
        query_results = catalog_screen.get("query_results", [])
        nearest_candidates = {
            item.get("reference_label"): item.get("nearest_candidate")
            for item in query_results
            if isinstance(item, dict) and isinstance(item.get("nearest_candidate"), dict)
        }
        follow_up_items.append(
            {
                "follow_up_id": "F2_CLOSER_WATER_CONTEXT",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "CATALOG_SCREENED_CONTEXT_RETRIEVED",
                "evidence_refs": ["NASA-CMR-DSWX-TEMPORAL-SCREEN", "NASA-OPERA-DSWX-HLS"],
                "action": "Screened NASA CMR around each SAR acquisition and retrieved a bounded DSWx-HLS product pair.",
                "discriminating_question": "Do the closely timed optical classifications and SAR response share a spatial pattern on valid common support?",
                "possible_interpretation": (
                    "The area-weighted overlay on common valid support found few changed WTR fractions and a descriptive Pearson r of "
                    f"{spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}; this does not resolve the water explanation."
                    if spatial_support is not None
                    else "The optical classifications provide closely timed context, but different native grids and the absence of a common-support spatial comparison prevent this record from resolving the water explanation."
                ),
                "priority_reason": (
                    f"The date-anchored catalog screen returned {catalog_screen.get('unique_candidate_count', 0)} candidates. "
                    f"Nearest before: {nearest_candidates.get('before', {}).get('granule_id', 'none')}; "
                    f"nearest after: {nearest_candidates.get('after', {}).get('granule_id', 'none')}. "
                    f"{timing_description} {spatial_limit}"
                ),
            }
        )
    else:
        follow_up_items.append(
            {
                "follow_up_id": "F2_CLOSER_WATER_CONTEXT",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "NOT_SEARCHED",
                "action": "Search for quality-screened, temporally closer optical or water-context observations around the two SAR acquisitions.",
                "discriminating_question": "Does spatially compatible water context co-vary with the radar-response pattern across closely timed acquisitions?",
                "possible_interpretation": "A compatible spatial pattern could add contextual support; a mismatch could weaken this explanation. Neither outcome alone establishes causation.",
                "priority_reason": f"{timing_description} {spatial_limit}",
                "test_design": _open_observation_test_design(
                    "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
                    known_hypothesis_ids,
                    "Test whether quality-valid water observations at suitable dates and common spatial support show the prespecified spatial association with the diagnostic SAR response.",
                ),
            }
        )
    if spatial_support is not None:
        follow_up_items.append(
            {
                "follow_up_id": "F3_SPATIAL_ASSOCIATION_REVIEW",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "RETRIEVED_QUALITY_LIMITED",
                "evidence_refs": ["NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT"],
                "action": "Completed an exact area-weighted spatial overlay between native-grid DSWx-HLS WTR cells and the diagnostic RTC-S1 measurement.",
                "discriminating_question": "Does optical water-fraction change show a stable spatial association with the SAR response on common valid support?",
                "possible_interpretation": (
                    f"At the 0.75 coverage threshold, {spatial_summary['water_fraction_increased_by_more_than_0_05'] + spatial_summary['water_fraction_decreased_by_more_than_0_05']} cells show water-fraction change above 0.05 and the descriptive linear correlation is {spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}. "
                    "This does not distinguish the water explanation; unresolved RTC-S1 QA and optical-context limits remain."
                ),
                "priority_reason": "The geometric compatibility question is now tested on retained cells. The next useful evidence is provider-resolved RTC-S1 QA and a quality-valid, temporally appropriate water observation with enough spatial transitions.",
            }
        )
    if polarization_sensitivity is not None:
        follow_up_items.append(
            {
                "follow_up_id": "F4_POLARIZATION_SENSITIVITY_REVIEW" if spatial_support is not None else "F3_POLARIZATION_SENSITIVITY_REVIEW",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "RETRIEVED_QUALITY_LIMITED",
                "evidence_refs": ["NASA-OPERA-RTC-POLARIZATION-SENSITIVITY"],
                "action": "Compared VV and VH RTC-S1 log-ratios for the same acquisition pair on identical optical common support.",
                "discriminating_question": "Does the descriptive SAR-to-water-context relationship persist across the two available co-polarized and cross-polarized channels?",
                "possible_interpretation": (
                    f"On {polarization_sensitivity['summary']['common_cells']} shared cells, VV and VH correlations are "
                    f"{polarization_sensitivity['summary']['vv_pearson_r_water_change_vs_log_ratio']:.3f} and "
                    f"{polarization_sensitivity['summary']['vh_pearson_r_water_change_vs_log_ratio']:.3f}. "
                    "They are both weak descriptive associations and are not independent validation; this check does not distinguish the water explanation."
                ),
                "priority_reason": "This same-pair robustness check is complete. Further discrimination requires provider-resolved SAR QA and suitable independent observations; additional polarizations from these same acquisitions cannot establish cause.",
            }
        )
    if gpm_contexts:
        before_gpm = next(context for _, context, role in gpm_contexts if role == "before")
        after_gpm = next(context for _, context, role in gpm_contexts if role == "after")
        before_sum = before_gpm["summary"]["nearest_cell_complete_day_sum_mm"]
        after_sum = after_gpm["summary"]["nearest_cell_complete_day_sum_mm"]
        follow_up_items.append(
            {
                "follow_up_id": "F5_SOIL_MOISTURE_CONTEXT",
                "target_hypothesis_ids": ["H3_SOIL_MOISTURE_CHANGE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "RETRIEVED_QUALITY_LIMITED",
                "evidence_refs": ["NASA-GPM-IMERG-BEFORE-PRE-SAR", "NASA-GPM-IMERG-AFTER-PRE-SAR"],
                "action": "Retrieved seven-day, bounded NASA GPM IMERG Final Daily subsets before each SAR acquisition; all nearest-cell days have 48 of 48 valid half-hourly samples.",
                "discriminating_question": "Does independently measured precipitation context provide relevant temporal context for the soil-moisture hypothesis?",
                "possible_interpretation": (
                    f"The nearest ~0.1 degree cell sums to {before_sum:.1f} mm from "
                    f"{before_gpm['query']['start_date_utc']} through {before_gpm['query']['end_date_utc']} and "
                    f"{after_sum:.1f} mm from {after_gpm['query']['start_date_utc']} through "
                    f"{after_gpm['query']['end_date_utc']}. This documents different regional precipitation context, "
                    "but cannot establish AOI soil moisture, cause, or a flood boundary."
                ),
                "priority_reason": "The NASA product is now retrieved and sample-complete, but its native grid is far coarser than the SAR AOI and precipitation is not a direct soil-moisture measurement.",
            }
        )
        if gpm_interacquisition is not None:
            chronology = gpm_interacquisition["summary"]
            follow_up_items[-1]["evidence_refs"] = [
                "NASA-GPM-IMERG-BEFORE-PRE-SAR",
                "NASA-GPM-IMERG-AFTER-PRE-SAR",
                "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY",
            ]
            follow_up_items[-1]["action"] = (
                f"Retrieved and linked {chronology['days_with_complete_nearest_cell_samples']} complete daily NASA GPM IMERG estimates across the SAR interval; each day has 48/48 nearest-cell samples."
            )
            follow_up_items[-1]["possible_interpretation"] = (
                f"The coarse nearest cell totals {chronology['nearest_cell_cumulative_precipitation_mm']:.2f} mm across the inter-acquisition interval, peaking at {chronology['maximum_daily_precipitation_mm_per_day']:.2f} mm/day on {chronology['maximum_daily_precipitation_date_utc']}. This is regional rainfall context only; it does not measure AOI soil moisture or identify the SAR response mechanism."
            )
        if smap_screen is not None:
            before_smap, after_smap = smap_screen["observations"]
            before_quality = before_smap["soil_moisture"]["quality_eligible_cell_count"]
            after_quality = after_smap["soil_moisture"]["quality_eligible_cell_count"]
            follow_up_items.append(
                {
                    "follow_up_id": "F6_SMAP_SOIL_MOISTURE_QUALITY_SCREEN",
                    "target_hypothesis_ids": ["H3_SOIL_MOISTURE_CHANGE"],
                    "purpose": "DISCRIMINATING_OBSERVATION",
                    "availability_state": "RETRIEVED_QUALITY_LIMITED",
                    "evidence_refs": ["NASA-SPL2SMAP-S-CANDIDATE-SCREEN"],
                    "action": "Retrieved exact-AOI 3 km SMAP/Sentinel-1 soil-moisture candidate subsets through NASA Harmony and evaluated the product QA flags.",
                    "discriminating_question": "Do the exact-AOI paired estimates have acceptable product quality and independent enough inputs to test the surface-driver explanation?",
                    "possible_interpretation": f"No paired cells passed the declared quality screen ({before_quality} before, {after_quality} after). The candidate is not usable to test surface state, and its Sentinel-1 input prevents independent SAR validation.",
                    "priority_reason": "The candidate was retrieved at the exact AOI but fails the product quality screen; an independent surface-state source remains necessary.",
                }
            )
            follow_up_items.append(
                {
                    "follow_up_id": "F7_INDEPENDENT_SOIL_MOISTURE_SEARCH",
                    "target_hypothesis_ids": ["H3_SOIL_MOISTURE_CHANGE"],
                    "purpose": "DISCRIMINATING_OBSERVATION",
                    "availability_state": "NOT_SEARCHED",
                    "action": "Search for independent soil-moisture measurements with acceptable quality, AOI-scale support, and acquisition timing that brackets the SAR dates.",
                    "discriminating_question": "Do independent soil-moisture measurements with useful spatial and temporal support track the diagnostic SAR response?",
                    "possible_interpretation": "Suitable soil-moisture evidence may test this mechanism; coarse, invalid, or missing measurements remain inconclusive.",
                    "priority_reason": "The blended SMAP/Sentinel-1 candidate failed its quality screen and the independent radiometer candidate is too coarse; these findings do not test vegetation or acquisition effects.",
                    "test_design": {
                        "mechanism_branch": "Independent soil-moisture change.",
                        "hypothesis_under_test_id": "H3_SOIL_MOISTURE_CHANGE",
                        "expected_observation": "An independent, quality-accepted measurement of the selected surface-state variable changes between the SAR acquisition times and shows a spatial pattern compatible with the diagnostic SAR response on explicitly compared valid support.",
                        "would_weaken_if": "The selected variable is measured with suitable temporal and spatial support and quality, yet its change lacks the predicted association with the SAR response. This weakens only that selected mechanism branch.",
                        "inconclusive_if": "Either date is missing, quality fails, the acquisition timing is unsuitable, the native support cannot resolve or meaningfully compare the AOI, or valid coverage is insufficient.",
                        "acceptance_gates": [
                            "Identify one physical variable and its measurement semantics before retrieval.",
                            "Use an independently sourced product that does not incorporate Sentinel-1 observations or derived values.",
                            "Retain provider quality flags and require a documented acceptable disposition for the selected measurement.",
                            "Record acquisition timestamps and assess temporal offsets against both SAR acquisitions.",
                            "Compare native spatial support and valid coverage to the AOI and SAR analysis cells; do not resample incompatible data to force a match.",
                        ],
                        "does_not_test_hypothesis_ids": [
                            "H1_OPTICAL_PRODUCT_CLASS_COUNTS_DECLINED",
                            "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
                            "H4_VEGETATION_STATE_CHANGE",
                            "H5_ACQUISITION_CONDITIONS_EFFECT",
                            "H6_SAR_PRODUCT_QUALITY_EFFECT",
                        ],
                        "interpretation_limit": "A compatible soil-moisture association may make H3 more plausible within scope, but does not establish causation, validate the diagnostic SAR pair, or resolve other hypotheses.",
                    },
                }
            )
            if smap_radiometer_screen is not None:
                follow_up_items[-1]["evidence_refs"] = [
                    "NASA-SPL2SMAP-S-CANDIDATE-SCREEN",
                    "NASA-SMAP-SPL3SMP-E-RESOLUTION-SCREEN",
                ]
                follow_up_items[-1]["action"] = (
                    "The blended SMAP/Sentinel-1 candidate failed its pixel quality screen. A separate radiometer-only NASA SMAP L3 candidate has daily records on both SAR dates but a 36 km native footprint against this ~1 km AOI; no pixel data were retrieved. Continue the independent search with field observations or products whose native support can resolve this AOI."
                )
                follow_up_items[-1]["priority_reason"] = (
                    "The exact-AOI blended candidate is QA-limited, while the independent radiometer-only candidate is far too coarse for an AOI-scale test. The remaining search should prioritize scale-appropriate independent observations."
                )
        if smap_screen is None:
            follow_up_items.append(
                {
                    "follow_up_id": "F6_INDEPENDENT_SOIL_MOISTURE_SEARCH",
                    "target_hypothesis_ids": ["H3_SOIL_MOISTURE_CHANGE"],
                    "purpose": "DISCRIMINATING_OBSERVATION",
                    "availability_state": "NOT_SEARCHED",
                    "action": "Search for independent soil-moisture measurements whose support and acquisition timing can test the specific soil-moisture explanation; screen resolution and coverage before retrieval.",
                    "discriminating_question": "Is there an independent soil-moisture measurement with acceptable quality, AOI-scale support, and dates near both SAR observations?",
                    "possible_interpretation": "A suitable soil-moisture observation could test H3. Coarse, model-assisted, or mistimed context remains nondiscriminating.",
                    "priority_reason": "Regional precipitation context does not measure AOI soil moisture; no accepted soil-moisture observation currently tests this mechanism.",
                    "test_design": _open_observation_test_design(
                        "H3_SOIL_MOISTURE_CHANGE",
                        known_hypothesis_ids,
                        "Independent soil-moisture change; keep vegetation and acquisition-condition mechanisms as separate hypotheses.",
                    ),
                }
            )
        independent_search = next(
            (
                item for item in follow_up_items
                if item.get("target_hypothesis_ids") == ["H3_SOIL_MOISTURE_CHANGE"]
                and isinstance(item.get("test_design"), dict)
                and "SOIL_MOISTURE_SEARCH" in item.get("follow_up_id", "")
            ),
            None,
        )
        if smap_l4_context_summary is not None:
            if independent_search is None:
                raise AssessmentError("SMAP L4 regional context requires the open independent soil-moisture follow-up")
            independent_search["availability_state"] = "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
            independent_search["evidence_refs"] = ["NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN"]
            independent_search["action"] = (
                "Retrieved and checksum-verified matched-time NASA SMAP L4 Version 8 regional model context through Harmony. "
                "It was screened for temporal alignment, native support, and local assimilated brightness-temperature values."
            )
            independent_search["possible_interpretation"] = (
                "The nearest model-derived surface soil-moisture estimate changes by "
                f"{smap_l4_context_summary['after_minus_before_model_analysis_m3_m3']:.6f} m3/m3, "
                "but the 9 km model support does not resolve this approximately 1 km AOI, matched local brightness-temperature fields are fill values, "
                "and its precipitation forcing may overlap the GPM chronology. This does not test H3."
            )
            independent_search["priority_reason"] = (
                "The NASA L4 model product provides regional context only and shares an upstream precipitation source with the retained GPM chronology; "
                "an independent, scale-appropriate observation is still needed to test H3."
            )
        screened_source_routes = []
        if ecostress_sm_screen is not None:
            screened_source_routes.append(
                (
                    "NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN",
                    "NASA's ECOSTRESS downscaled soil-moisture product has no cataloged granules worldwide in the target April-June 2024 interval; its 70 m layer is a model-derived estimate, not a direct 70 m measurement.",
                )
            )
        if ismn_station_screen is not None:
            nearest = ismn_station_screen["inventory"]["nearest_station"]
            screened_source_routes.append(
                (
                    "ISMN-SOIL-MOISTURE-STATION-COVERAGE",
                    f"The ISMN inventory has no station within 100 km; its nearest station is {nearest['distance_to_aoi_center_km']:.1f} km away and its listed data end {nearest['listed_time_end'][:10]}.",
                )
            )
        if smap_l4_context_summary is not None:
            screened_source_routes.append(
                (
                    "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN",
                    "NASA SMAP L4 provides coarse model-derived regional context with potential upstream IMERG input overlap; it does not supply an independent AOI-scale soil-moisture measurement.",
                )
            )
        if screened_source_routes and independent_search is not None:
            independent_search["availability_state"] = "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
            independent_search["evidence_refs"] = [item[0] for item in screened_source_routes]
            independent_search["action"] = (
                "Screened the linked soil-moisture source routes. They do not supply an independent, quality-accepted measurement with sufficient support for this AOI and interval; the broader search remains open."
            )
            independent_search["possible_interpretation"] = (
                "These source-route results do not test H3. Continue seeking an independent, quality-accepted measurement with suitable timing and spatial support; H3 remains untested."
            )
            independent_search["priority_reason"] = (
                "Retained candidates are QA-limited, too coarse, model-derived, absent for the interval, or lack nearby station coverage; prioritize a scale-appropriate independent observation."
            )
    else:
        follow_up_items.append(
            {
                "follow_up_id": "F5_SOIL_MOISTURE_SEARCH" if polarization_sensitivity is not None and spatial_support is not None else "F4_SOIL_MOISTURE_SEARCH" if spatial_support is not None else "F3_SOIL_MOISTURE_SEARCH",
                "target_hypothesis_ids": ["H3_SOIL_MOISTURE_CHANGE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "RETRIEVED_QUALITY_LIMITED" if smap_screen is not None else "NOT_SEARCHED",
                **({"evidence_refs": ["NASA-SPL2SMAP-S-CANDIDATE-SCREEN"]} if smap_screen is not None else {}),
                "action": "Retrieved exact-AOI 3 km SMAP/Sentinel-1 candidate subsets and evaluated product quality flags." if smap_screen is not None else "Identify independent soil-moisture observations with spatial and temporal support adequate for this AOI.",
                "discriminating_question": "Do the exact-AOI paired estimates pass product quality checks and provide independent enough inputs to test soil-moisture change?" if smap_screen is not None else "Do independent soil-moisture measurements at useful support track the SAR-response pattern?",
                "possible_interpretation": "No paired cells passed the declared screen; the candidate cannot test soil-moisture change." if smap_screen is not None else "A suitable observation could test the soil-moisture mechanism; coarse or mistimed context remains nondiscriminating.",
                "priority_reason": "The retrieved candidate failed product QA and uses Sentinel-1 input; an independent source remains necessary." if smap_screen is not None else "These explanations currently have no corresponding measurements or controls in the retained records.",
                **(
                    {
                        "test_design": _open_observation_test_design(
                            "H3_SOIL_MOISTURE_CHANGE",
                            known_hypothesis_ids,
                            "Independent soil-moisture change; keep vegetation and acquisition-condition mechanisms as separate hypotheses.",
                        )
                    }
                    if smap_screen is None
                    else {}
                ),
            }
        )
    vegetation_evidence_refs: list[str] = []
    if hls_vegetation is not None and hls_association is not None:
        vegetation_evidence_refs.extend([
            "NASA-HLS-L30-VEGETATION-SCREEN",
            "NASA-HLS-L30-NDVI-SAR-ASSOCIATION",
        ])
    if hls_s30_vegetation is not None and hls_s30_association is not None:
        vegetation_evidence_refs.extend([
            "NASA-HLS-S30-VEGETATION-SCREEN",
            "NASA-HLS-S30-NDVI-SAR-ASSOCIATION",
        ])
    has_vegetation_candidates = bool(vegetation_evidence_refs)
    follow_up_items.append(
        {
            "follow_up_id": "F8_VEGETATION_STATE_SCREEN",
            "target_hypothesis_ids": ["H4_VEGETATION_STATE_CHANGE"],
            "purpose": "DISCRIMINATING_OBSERVATION",
            "availability_state": "RETRIEVED_QUALITY_LIMITED" if has_vegetation_candidates else "NOT_SEARCHED",
            "evidence_refs": vegetation_evidence_refs,
            "action": (
                "Reviewed the retained HLS vegetation screens and linked NDVI/SAR associations; their common clear support is insufficient to test vegetation causality."
                if has_vegetation_candidates
                else "Screen an independent vegetation-state observation for suitable acquisition timing, provider quality, and common valid support before retrieving pixel data."
            ),
            "discriminating_question": "Does an independent vegetation-state observation show a reproducible relationship to the SAR response on adequate common support?",
            "possible_interpretation": (
                "The retained HLS candidates are nondiscriminating; a better-supported observation may test H4, while another sparse or mistimed association remains inconclusive."
                if has_vegetation_candidates
                else "A candidate that passes quality, timing, and coverage gates may test H4; sparse or incompatible context remains inconclusive."
            ),
            "priority_reason": (
                "The retained HLS screens have limited common clear coverage; do not repeat these acquisitions. Search only for a candidate expected to materially improve support."
                if has_vegetation_candidates
                else "Vegetation is a distinct mechanism from soil moisture and acquisition geometry and needs its own predeclared evidence test."
            ),
            **({"test_design": _open_observation_test_design(
                "H4_VEGETATION_STATE_CHANGE",
                known_hypothesis_ids,
                "Independent vegetation-state change measured at suitable temporal and native spatial support.",
            )} if not has_vegetation_candidates else {}),
        }
    )
    if has_vegetation_candidates:
        modis_refs = []
        modis_actions = []
        if mod13q1_screen is not None:
            modis_refs.append("NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN")
            modis_actions.append(
                f"MOD13Q1 V6.1: {mod13q1_screen['observations']['common_strictly_accepted_pixel_count']} common strict land pixels; its 16-day composite dates are not all aligned with the SAR acquisitions."
            )
        if mod09ga_screen is not None:
            modis_refs.append("NASA-MOD09GA-VEGETATION-CANDIDATE-SCREEN")
            modis_actions.append(
                f"MOD09GA daily reflectance: {mod09ga_screen['observations']['common_pixel_center_count']} common 500 m centers but {mod09ga_screen['observations']['common_strict_accepted_count']} common strict land centers; the 1 km state flags classify retained centers as water or shoreline."
            )
        follow_up_items.append(
            {
                "follow_up_id": "F9_BETTER_SUPPORTED_VEGETATION_OBSERVATION",
                "target_hypothesis_ids": ["H4_VEGETATION_STATE_CHANGE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "RETRIEVED_QUALITY_LIMITED" if modis_refs else "NOT_SEARCHED",
                "evidence_refs": modis_refs,
                "action": (
                    "Screened independent NASA MODIS vegetation-context routes: " + " ".join(modis_actions)
                    if modis_refs
                    else "Identify an independent, time-matched vegetation observation with materially higher common clear support; avoid reprocessing the already screened HLS acquisitions as if the limitation were unresolved."
                ),
                "discriminating_question": "Can an independent vegetation product pass the preregistered quality, timing, and AOI-support gates?",
                "possible_interpretation": (
                    "The screened MODIS candidates do not test H4: no common strict land pixels remain, and MOD09GA's 1 km state flags provide coarser water/shoreline support than its 500 m reflectance bands."
                    if modis_refs
                    else "Adequate data may make the vegetation mechanism testable; missing, sparse, or mistimed observations remain inconclusive."
                ),
                "priority_reason": (
                    "The screened MODIS routes are retained as quality/support-limited evidence; continue only if a candidate can materially improve common land support and acquisition timing."
                    if modis_refs
                    else "The existing Landsat and Sentinel-2 candidates do not provide enough common clear support to test vegetation causality."
                ),
                "test_design": _open_observation_test_design(
                    "H4_VEGETATION_STATE_CHANGE",
                    known_hypothesis_ids,
                    "An independent vegetation-state observation with valid common support across dates.",
                ),
            }
        )
    follow_up_items.append(
        {
            "follow_up_id": "F10_ACQUISITION_CONDITION_REVIEW",
            "target_hypothesis_ids": ["H5_ACQUISITION_CONDITIONS_EFFECT"],
            "purpose": "DISCRIMINATING_OBSERVATION",
            "availability_state": "RETRIEVED_QUALITY_LIMITED" if acquisition_conditions is not None else "NOT_SEARCHED",
            **({"evidence_refs": ["NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW"]} if acquisition_conditions is not None else {}),
            "action": (
                "Compared checksum-linked per-acquisition ASF/OPERA metadata. Documented configuration and processing fields match; the burst RFI summary differs but is not spatially matched to the AOI response."
                if acquisition_conditions is not None
                else "Compare the exact acquisitions' geometry, sensor configuration, calibration and processing metadata, and spatial QA masks before attributing the response to a surface mechanism."
            ),
            "discriminating_question": "Do documented acquisition or processing differences align spatially or temporally with the observed SAR response?",
            "possible_interpretation": (
                "The metadata review does not distinguish an acquisition-condition contribution: retained RFI burst values lack AOI spatial correspondence, incidence-angle metadata are absent, and geometric accuracy values do not establish co-registration."
                if acquisition_conditions is not None
                else "A relevant difference can make an acquisition-effect explanation testable; absent metadata or a weak mismatch remains inconclusive."
            ),
            "priority_reason": (
                "A metadata-only screen is complete; resolving the acquisition-condition explanation would require suitable spatially relevant diagnostics and a provider QA disposition."
                if acquisition_conditions is not None
                else "No dedicated acquisition-condition comparison is recorded; evaluate retained per-acquisition metadata before searching for additional products."
            ),
            "test_design": {
                "mechanism_branch": "Per-acquisition imaging geometry, sensor configuration, calibration, and processing differences.",
                "hypothesis_under_test_id": "H5_ACQUISITION_CONDITIONS_EFFECT",
                "expected_observation": "A documented acquisition or processing difference coincides with the SAR response pattern on compatible spatial support.",
                "would_weaken_if": "Authoritative per-acquisition metadata are comparable and show no relevant change associated with the SAR response.",
                "inconclusive_if": "Required product metadata or quality fields are absent, incompatible, or lack spatial correspondence to the measured response.",
                "acceptance_gates": [
                    "Use exact source-product identifiers and authoritative per-acquisition metadata.",
                    "Compare geometry, sensor configuration, processing version, calibration, and quality masks where available.",
                    "Distinguish unavailable metadata from a verified absence of difference.",
                    "Relate any difference to the measured spatial response without inferring causation from temporal coincidence alone.",
                ],
                "does_not_test_hypothesis_ids": sorted(known_hypothesis_ids - {"H5_ACQUISITION_CONDITIONS_EFFECT"}),
                "interpretation_limit": "A metadata difference may identify a confounder but does not prove it caused the SAR response or validate the measurement.",
            },
        }
    )
    if guaiba_access_screen is not None:
        follow_up_items.append(
            {
                "follow_up_id": "F11_GUAIBA_PRIMARY_SERIES",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "ACCESS_REQUIRED",
                "evidence_refs": [
                    "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY",
                    "ANA-GUAIBA-PRIMARY-SERIES-ACCESS-SCREEN",
                ],
                "action": "Request approved ANA HidroWebService access, then retrieve the original-reference emergency-gauge readings for station 87444000 around both SAR acquisition times.",
                "discriminating_question": "What recorded river levels and quality flags are available at the nearby gauge around the two SAR acquisitions?",
                "possible_interpretation": "Timestamped gauge readings can refine nearby river-stage chronology. They cannot establish water extent in the SAR AOI or by themselves identify the cause of radar change.",
                "priority_reason": "ANA/SGB documents that the emergency-gauge archive preserves readings from 2024-05-03 through 2025-08-29. The legacy query returned no data and the current exact-code inventory has no entry; the current ANA API requires approved credentials. These access failures do not establish that the archived series is absent.",
                "test_design": {
                    "mechanism_branch": "Nearby river-stage chronology as contextual evidence for the water-change explanation.",
                    "hypothesis_under_test_id": "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
                    "expected_observation": "The original-reference 87444000 series provides timestamped, quality-flagged readings close to both SAR acquisition times, allowing the stage trajectory to be described without merging station identities.",
                    "would_weaken_if": "Recorded stage is materially stable across the two acquisition times; this weakens only the nearby point-stage change hypothesis and does not exclude local floodplain changes.",
                    "inconclusive_if": "Access is not granted, readings do not cover the dates, quality flags are unsuitable, the time reference is unclear, or the station/datum identity cannot be confirmed.",
                    "acceptance_gates": [
                        "Use an official ANA/SGB archive and preserve exact station code, timestamps, units, datum/reference, retrieval time, and quality flags.",
                        "Keep emergency station 87444000 distinct from corrected station 87450020.",
                        "Do not interpolate readings unless source cadence and the interpolation method are justified and recorded.",
                        "Treat the gauge as nearby point context; it cannot validate AOI-scale SAR or optical water extent.",
                    ],
                    "does_not_test_hypothesis_ids": sorted(known_hypothesis_ids - {"H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"}),
                    "interpretation_limit": "Gauge stage can add temporal context but cannot independently establish flood extent or explain the SAR response.",
                },
            }
        )
    follow_up_evidence = validate_follow_up_plan(
        follow_up_items,
        known_hypothesis_ids=known_hypothesis_ids,
        known_evidence_ids=evidence_ids,
    )

    def hypothesis(
        hypothesis_id: str,
        statement: str,
        assessments: list[EvidenceAssessment],
        *,
        scope_limit: str,
        expected_observation: str,
        would_weaken_if: str,
        testability_state: str,
        testability_reason: str,
        required_evidence: list[str],
    ) -> dict[str, Any]:
        evaluation = evaluate_hypothesis(assessments, known_evidence_ids=evidence_ids)
        return {
            "id": hypothesis_id,
            "statement": statement,
            "state": evaluation["disposition"],
            "evidence_refs": [item.evidence_id for item in assessments],
            "evidence_assessments": evaluation["evidence_assessments"],
            "scope_limit": scope_limit,
            "expected_observation": expected_observation,
            "would_weaken_if": would_weaken_if,
            "testability_state": testability_state,
            "testability_reason": testability_reason,
            "required_evidence": required_evidence,
        }

    summary = (
        "The records establish a diagnostic Sentinel-1-derived backscatter ratio and a decline in DSWx-HLS water-class counts over the same WGS84 AOI."
        + (
            f" An exact area-weighted native-grid overlay was completed. At the 0.75 coverage threshold, {spatial_summary['sar_cells']} cells were retained, {spatial_summary['water_fraction_changed_by_at_most_0_05']} had at most 0.05 water-fraction change, and descriptive Pearson r was {spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}."
            if spatial_support is not None
            else " They do not establish a pixel-level relationship."
        )
        + " The evidence does not establish a causal explanation or validated flood boundary."
    )
    if sar_temporal_summary is not None:
        first_interval, second_interval = sar_temporal_summary["intervals"]
        summary += (
            f" A checksum-linked three-acquisition RTC-S1 series on {sar_temporal_summary['common_support_count']} all-date pixels has adjacent VV median changes "
            f"{first_interval['summary_db']['median']:+.3f} dB and {second_interval['summary_db']['median']:+.3f} dB. "
            "The direction differs between intervals, but the series shares the primary pair's first two scenes, has no pre-May-2024 SAR baseline, and remains diagnostic; it does not distinguish the water explanation."
        )
    if guaiba_observation is not None:
        summary += (
            " ANA reports that the nearby Usina do Gasômetro station remained above flood stage across the two acquisition dates; "
            "this is regional narrative context, not a timestamped series or AOI-scale water observation, and it does not resolve the cause."
        )
    if nearer_context is not None:
        summary += (
            " The temporally nearer DSWx-HLS comparison does not resolve the interpretation: its WTR layer has no common valid AOI pixels, and all earlier WTR-2 water-coded cells are cloud/snow flagged."
        )
    if polarization_sensitivity is not None:
        summary += (
            f" A same-pair polarization sensitivity check on {polarization_sensitivity['summary']['common_cells']} shared cells found descriptive water-change correlations of "
            f"{polarization_sensitivity['summary']['vv_pearson_r_water_change_vs_log_ratio']:.3f} (VV) and "
            f"{polarization_sensitivity['summary']['vh_pearson_r_water_change_vs_log_ratio']:.3f} (VH); these related channels do not provide independent validation."
        )
    if gpm_contexts:
        before_gpm = next(context for _, context, role in gpm_contexts if role == "before")
        after_gpm = next(context for _, context, role in gpm_contexts if role == "after")
        summary += (
            f" NASA GPM IMERG Final Daily provides seven sample-complete regional days before each SAR acquisition; "
            f"the nearest native cell sums to {before_gpm['summary']['nearest_cell_complete_day_sum_mm']:.1f} mm and "
            f"{after_gpm['summary']['nearest_cell_complete_day_sum_mm']:.1f} mm, respectively. This coarse precipitation context does not establish a surface driver or explain the SAR response."
        )
    if gpm_interacquisition is not None:
        chronology = gpm_interacquisition["summary"]
        summary += (
            f" Across the {chronology['days_with_complete_nearest_cell_samples']} complete UTC days between the SAR acquisitions, NASA GPM IMERG estimates total {chronology['nearest_cell_cumulative_precipitation_mm']:.2f} mm at the nearest ~0.1 degree cell, peaking at {chronology['maximum_daily_precipitation_mm_per_day']:.2f} mm/day on {chronology['maximum_daily_precipitation_date_utc']}. This chronology adds temporal context, not AOI soil-moisture measurement or causal evidence."
        )
    if hls_association_summary is not None:
        summary += (
            f" NASA/USGS HLS Landsat L30 provides same-date optical context with {hls_vegetation['comparison']['common_clear_land_aoi_fraction']:.1%} common clear-land AOI support; "
            f"the native-grid NDVI/SAR association at 75% cell coverage is descriptive (r={hls_association_summary['descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db']:.3f}) and does not distinguish vegetation causality."
        )
    if hls_s30_association_summary is not None:
        common_pixels = hls_s30_vegetation["comparison"]["common_clear_land_ndvi_pixel_count"]
        aoi_pixels = hls_s30_vegetation["comparison"]["aoi_center_pixel_count"]
        summary += (
            f" NASA/USGS HLS Sentinel-2 S30 NDVI has {common_pixels} common clear-land pixels across the {aoi_pixels}-pixel AOI ({common_pixels / aoi_pixels:.1%}); "
            f"only {hls_s30_association_summary['sar_cells']} SAR cells meet the 75% optical-area screen, with descriptive r={hls_s30_association_summary['descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db']:.3f}. "
            "This sparse optical support does not distinguish vegetation causality."
        )

    gpm_observation_context = None
    if gpm_contexts:
        gpm_observation_context = {
            role: {
                "start_date_utc": context["query"]["start_date_utc"],
                "end_date_utc": context["query"]["end_date_utc"],
                "nearest_cell_center": context["query"]["aoi_nearest_native_cell_center"],
                "daily_mm_per_day": [item["aoi_nearest_cell"]["precipitation_mm_per_day"] for item in context["daily_observations"]],
                "complete_day_sum_mm": context["summary"]["nearest_cell_complete_day_sum_mm"],
                "complete_days": context["summary"]["days_with_48_valid_samples_at_nearest_cell"],
                "native_grid_spacing_degrees": context["daily_observations"][0]["native_grid"]["longitude_spacing_degrees"],
                "interpretation_role": "coarse NASA precipitation context; not soil moisture, causal evidence, or SAR validation",
            }
            for _, context, role in gpm_contexts
        }
        if gpm_interacquisition is not None:
            gpm_observation_context["interacquisition"] = {
                "start_date_utc": gpm_interacquisition["sar_interval"]["first_full_day_after_before_sar"],
                "end_date_utc": gpm_interacquisition["sar_interval"]["last_full_day_before_after_sar"],
                "nearest_cell_center": gpm_interacquisition["query"]["aoi_nearest_native_cell_center"],
                "daily_mm_per_day": [item["precipitation_mm_per_day"] for item in gpm_interacquisition["daily_observations"]],
                "complete_day_sum_mm": gpm_interacquisition["summary"]["nearest_cell_cumulative_precipitation_mm"],
                "complete_days": gpm_interacquisition["summary"]["days_with_complete_nearest_cell_samples"],
                "native_grid_spacing_degrees": gpm_interacquisition["summary"]["native_grid_spacing_degrees"],
                "peak_daily_precipitation_mm": gpm_interacquisition["summary"]["maximum_daily_precipitation_mm_per_day"],
                "peak_date_utc": gpm_interacquisition["summary"]["maximum_daily_precipitation_date_utc"],
                "interpretation_role": "coarse NASA precipitation chronology; not soil moisture, causal evidence, or SAR validation",
            }

    return {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "schema_version": 3 if hls_association_summary is not None else (2 if sar_temporal_summary is not None else 1),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "status": "CAUSAL_INTERPRETATION_UNRESOLVED",
        "question": "Do the available same-AOI observations establish that changing surface water caused the measured SAR backscatter response?",
        "evidence_artifacts": evidence,
        "observations": {
            "sar_diagnostic_measurement": sar,
            "sar_temporal_series": (
                {
                    "status": sar_temporal_series["status"],
                    "scene_ids": sar_temporal_summary["scene_ids"],
                    "acquisition_start_utc": [item["acquisition_start_utc"] for item in sar_temporal_series["observations"]],
                    "common_support_count": sar_temporal_summary["common_support_count"],
                    "aoi_pixel_count": sar_temporal_summary["aoi_pixel_count"],
                    "intervals": sar_temporal_summary["intervals"],
                    "temporal_direction_screen": sar_temporal_summary["temporal_direction_screen"],
                    "provider_qa_state": sar_temporal_series["provider_qa"]["status"],
                    "shares_source_observations_with": ["SAR-RTC-S1-PAIR"],
                    "interpretation_role": "descriptive temporal pattern only; shared source acquisitions, no pre-May-2024 SAR baseline, unresolved QA, and no physical cause inferred",
                }
                if sar_temporal_series is not None and sar_temporal_summary is not None
                else None
            ),
            "optical_product_classifications": optical_context,
            "nearer_optical_quality_context": nearer_context,
            "spatial_support_diagnostic": (
                {
                    "status": spatial_support["status"],
                    "coverage_sensitivity": spatial_support["summary"]["coverage_sensitivity"],
                    "interpretation_role": "diagnostic descriptive spatial association; not causal evidence or SAR validation",
                }
                if spatial_support is not None
                else None
            ),
            "polarization_sensitivity_diagnostic": (
                {
                    "status": polarization_sensitivity["status"],
                    "summary": polarization_sensitivity["summary"],
                    "interpretation_role": "same-acquisition sensitivity check; not independent evidence or causal support",
                }
                if polarization_sensitivity is not None
                else None
            ),
            "gpm_precipitation_context": gpm_observation_context,
            "smap_l4_regional_soil_moisture_context": smap_l4_context_summary,
            "official_hydrologic_event_context": guaiba_observation,
        "smap_sentinel_soil_moisture_screen": (
            {
                "product": smap_screen["source"]["product"],
                "version": smap_screen["source"]["version"],
                "before_granule": smap_screen["observations"][0]["granule_id"],
                "after_granule": smap_screen["observations"][1]["granule_id"],
                "before_quality_eligible_cells": smap_screen["observations"][0]["soil_moisture"]["quality_eligible_cell_count"],
                "after_quality_eligible_cells": smap_screen["observations"][1]["soil_moisture"]["quality_eligible_cell_count"],
                "paired_quality_eligible_cells": smap_screen["comparison"]["paired_quality_eligible_cells"],
                "interpretation_role": "retrieved NASA candidate rejected from analysis due product QA flags; blended Sentinel-1 input prevents independent SAR validation",
            }
            if smap_screen is not None
            else None
        ),
        "smap_radiometer_spatial_suitability_screen": (
            {
                "status": smap_radiometer_screen["status"],
                "product": smap_radiometer_screen["source"]["product_title"],
                "version": smap_radiometer_screen["source"]["version"],
                "independent_of_sentinel1": True,
                "aoi_width_km_approx": smap_radiometer_screen["spatial_suitability"]["aoi_width_km_approx"],
                "aoi_height_km_approx": smap_radiometer_screen["spatial_suitability"]["aoi_height_km_approx"],
                "grid_posting_km": smap_radiometer_screen["spatial_suitability"]["product_grid_posting_km"],
                "native_radiometer_footprint_km_approx": smap_radiometer_screen["spatial_suitability"]["radiometer_native_footprint_km_approx"],
                "selected_daily_granule_dates": [item["date_utc"] for item in smap_radiometer_screen["selected_daily_granules"]],
                "pixel_data_retrieved": False,
                "interpretation_role": "metadata-only independent-source candidate screen; unsuitable for within-AOI driver testing at the published radiometer footprint",
            }
            if smap_radiometer_screen is not None
            else None
        ),
        "hls_l30_vegetation_context": (
            {
                "provider": hls_vegetation["source"]["provider"],
                "product": hls_vegetation["source"]["product"],
                "before_granule": hls_vegetation["observations"][0]["granule_id"],
                "after_granule": hls_vegetation["observations"][1]["granule_id"],
                    "before_acquisition_utc": hls_vegetation["observations"][0]["temporal_extent_utc"]["BeginningDateTime"],
                    "after_acquisition_utc": hls_vegetation["observations"][1]["temporal_extent_utc"]["BeginningDateTime"],
                    "optical_minus_sar_offsets_hours": hls_association["sources"]["optical_minus_sar_offsets_hours"],
                "before_platform": hls_vegetation["observations"][0]["platforms"][0]["ShortName"],
                "after_platform": hls_vegetation["observations"][1]["platforms"][0]["ShortName"],
                "common_clear_land_aoi_fraction": hls_vegetation["comparison"]["common_clear_land_aoi_fraction"],
                "median_ndvi_change_after_minus_before": hls_vegetation["comparison"]["ndvi"]["common_clear_land_median_change_after_minus_before"],
                "ndvi_change_q10_q90": hls_vegetation["comparison"]["ndvi"]["common_clear_land_change_q10_q90"],
                "association_at_75_percent_common_support": hls_association_summary,
                "association_coverage_sensitivity": hls_association_sensitivity,
                "interpretation_role": "NASA/USGS Landsat optical context and descriptive association; limited common support; not causal evidence, ground truth, or SAR validation",
            }
            if hls_vegetation is not None and hls_association_summary is not None
            else None
        ),
            "hls_s30_vegetation_context": (
                {
                    "provider": hls_s30_vegetation["source"]["provider"],
                    "product": hls_s30_vegetation["source"]["product"],
                    "before_granule": hls_s30_vegetation["observations"][0]["granule_id"],
                    "after_granule": hls_s30_vegetation["observations"][1]["granule_id"],
                    "before_acquisition_utc": hls_s30_vegetation["observations"][0]["temporal_extent_utc"]["BeginningDateTime"],
                    "after_acquisition_utc": hls_s30_vegetation["observations"][1]["temporal_extent_utc"]["BeginningDateTime"],
                    "before_platform": hls_s30_vegetation["observations"][0]["platforms"][0]["ShortName"],
                    "after_platform": hls_s30_vegetation["observations"][1]["platforms"][0]["ShortName"],
                    "optical_minus_sar_offsets_hours": hls_s30_association["sources"]["optical_minus_sar_offsets_hours"],
                    "aoi_center_pixel_count": hls_s30_vegetation["comparison"]["aoi_center_pixel_count"],
                    "before_clear_land_pixel_count": hls_s30_vegetation["comparison"]["before_clear_land_ndvi_pixel_count"],
                    "after_clear_land_pixel_count": hls_s30_vegetation["comparison"]["after_clear_land_ndvi_pixel_count"],
                    "common_clear_land_pixel_count": hls_s30_vegetation["comparison"]["common_clear_land_ndvi_pixel_count"],
                    "common_clear_land_aoi_fraction": hls_s30_vegetation["comparison"]["common_clear_land_aoi_fraction"],
                    "median_ndvi_change_after_minus_before": hls_s30_vegetation["comparison"]["ndvi"]["common_clear_land_median_change_after_minus_before"],
                    "ndvi_change_q10_q90": hls_s30_vegetation["comparison"]["ndvi"]["common_clear_land_change_q10_q90"],
                    "association_at_75_percent_common_support": hls_s30_association_summary,
                    "interpretation_role": "Sentinel-2 optical candidate; only sparse common clear-land support and 11 SAR cells at the 75% overlay threshold; descriptive only, not causal evidence or SAR validation",
                }
                if hls_s30_vegetation is not None and hls_s30_association_summary is not None
                else None
            ),
            "mod13q1_vegetation_candidate_screen": (
                {
                    "source_granule_ids": [item["granule_id"] for item in mod13q1_screen["source"]["granules"]],
                    "native_crs": mod13q1_screen["query"]["native_grid"]["crs"],
                    "native_resolution_m": 231.656358,
                    "aoi_pixel_center_count": mod13q1_screen["observations"]["before"]["aoi_pixel_center_count"],
                    "before_good_summary_qa_count": mod13q1_screen["observations"]["before"]["good_summary_qa_count"],
                    "after_good_summary_qa_count": mod13q1_screen["observations"]["after"]["good_summary_qa_count"],
                    "before_land_class_count": mod13q1_screen["observations"]["before"]["valid_land_class_count"],
                    "after_land_class_count": mod13q1_screen["observations"]["after"]["valid_land_class_count"],
                    "common_strictly_accepted_pixel_count": mod13q1_screen["observations"]["common_strictly_accepted_pixel_count"],
                    "composite_observation_dates_before": mod13q1_screen["observations"]["before"]["composite_observation_dates"],
                    "composite_observation_dates_after": mod13q1_screen["observations"]["after"]["composite_observation_dates"],
                    "composite_observation_offsets_days_min_max": mod13q1_screen["observations"]["all_retained_composite_observation_offsets_days_min_max"],
                    "paired_timing_suitable": mod13q1_screen["observations"]["paired_timing_suitable_for_sar_date_comparison"],
                    "interpretation_role": "NASA vegetation product candidate; no accepted paired land support and per-pixel composite dates are not both aligned with SAR acquisition instants; no NDVI change or SAR association computed",
                }
                if mod13q1_screen is not None
                else None
            ),
            "mod09ga_vegetation_candidate_screen": (
                {
                    "source_granule_ids": [item["granule_id"] for item in mod09ga_screen["source"]["granules"]],
                    "before_pixel_center_count": mod09ga_screen["observations"]["before"]["pixel_center_count"],
                    "after_pixel_center_count": mod09ga_screen["observations"]["after"]["pixel_center_count"],
                    "common_pixel_center_count": mod09ga_screen["observations"]["common_pixel_center_count"],
                    "common_strict_accepted_count": mod09ga_screen["observations"]["common_strict_accepted_count"],
                    "state_qa_resolution_m": mod09ga_screen["query"]["state_qa_resolution_m"],
                    "interpretation_role": "daily NASA optical reflectance candidate; paired vegetation gate rejects all common centers because associated 1 km state QA marks shoreline or water, with additional earlier-date cloud/shadow flags; no NDVI difference or SAR association computed",
                }
                if mod09ga_screen is not None
                else None
            ),
            "acquisition_conditions_metadata_review": (
                {
                    "scene_ids": acquisition_conditions["source"]["scene_ids"],
                    "platform_configuration_matches": acquisition_conditions["summary"]["platform_configuration_matches"],
                    "documented_product_configuration_matches": acquisition_conditions["summary"]["documented_product_configuration_matches"],
                    "documented_processing_configuration_matches": acquisition_conditions["summary"]["documented_processing_configuration_matches"],
                    "reported_geometric_accuracy_metadata_match": acquisition_conditions["summary"]["reported_geometric_accuracy_metadata_match"],
                    "rfi_burst_metadata_comparison": acquisition_conditions["summary"]["rfi_burst_metadata_comparison"],
                    "rfi_power_ratio_before": acquisition_conditions["summary"]["rfi_power_ratio_before"],
                    "rfi_power_ratio_after": acquisition_conditions["summary"]["rfi_power_ratio_after"],
                    "incidence_angle_metadata_available": acquisition_conditions["summary"]["incidence_angle_metadata_available"],
                    "spatially_matched_rfi_evidence_available": acquisition_conditions["summary"]["spatially_matched_rfi_evidence_available"],
                    "interpretation_role": "metadata-only acquisition-condition comparison; nondiscriminating and not QA clearance",
                }
                if acquisition_conditions is not None
                else None
            ),
            "relative_acquisition_offsets_days": {
                "optical_before_minus_sar_before": temporal.get("optical_before_minus_rtc_before_days"),
                "optical_after_minus_sar_after": temporal.get("optical_after_minus_rtc_after_days"),
            },
        },
        "hypotheses": validate_hypotheses([
            hypothesis(
                "H1_OPTICAL_PRODUCT_CLASS_COUNTS_DECLINED",
                "In the retained DSWx-HLS pair, the later products classify fewer AOI cells as water than the earlier products.",
                [EvidenceAssessment(
                    "NASA-OPERA-DSWX-HLS",
                    EvidenceRelation.SUPPORTS,
                    f"The retained WTR counts change {wtr['water_class_pixels_before_on_common_valid']} to {wtr['water_class_pixels_after_on_common_valid']} and WTR-2 counts change {wtr2['water_class_pixels_before_on_common_valid']} to {wtr2['water_class_pixels_after_on_common_valid']} on their respective common-valid cells.",
                )],
                scope_limit="Supported only as a change in product class counts; this is not ground-truth water extent.",
                expected_observation="The retained DSWx-HLS products classify fewer common-valid AOI cells as water in the later product.",
                would_weaken_if="A recomputation from the retained arrays does not reproduce the reported count changes; this challenges the product-count statement, not ground-truth water extent.",
                testability_state="DESCRIPTIVE_ONLY",
                testability_reason="WTR and WTR-2 count changes are available on their respective common-valid centers, with differing valid support.",
                required_evidence=["Retained WTR and WTR-2 arrays and their product validity masks"],
            ),
            hypothesis(
                "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
                "The optical water-class change explains the measured Sentinel-1-derived backscatter ratio.",
                [
                    EvidenceAssessment(
                        "SAR-RTC-S1-PAIR",
                        EvidenceRelation.DOES_NOT_DISTINGUISH,
                        "The aggregate backscatter ratio measures radar-response change but does not by itself identify a physical cause.",
                    ),
                    EvidenceAssessment(
                        "NASA-OPERA-DSWX-HLS",
                        EvidenceRelation.LIMITS_INTERPRETATION,
                        f"{timing_description} {spatial_limit}",
                    ),
                    *(
                        [
                            EvidenceAssessment(
                                "NASA-OPERA-DSWX-NEARER-CONTEXT",
                                EvidenceRelation.LIMITS_INTERPRETATION,
                                "The nearest screened optical pair has zero shared valid WTR pixels; all earlier WTR-2 water-coded cells carry cloud/snow flags.",
                            )
                        ]
                        if nearer_context is not None
                        else []
                    ),
                    *(
                        [
                            EvidenceAssessment(
                                "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT",
                                EvidenceRelation.DOES_NOT_DISTINGUISH,
                                (
                                    f"At 0.75 common-valid WTR area coverage, {spatial_summary['sar_cells']} SAR cells remain; "
                                    f"{spatial_summary['water_fraction_changed_by_at_most_0_05']} have at most 0.05 water-fraction change, "
                                    f"and the descriptive Pearson r is {spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}. "
                                    "This non-inferential association does not distinguish a water driver; the RTC-S1 pair remains diagnostic."
                                ),
                            )
                        ]
                        if spatial_support is not None
                        else []
                    ),
                    *(
                        [
                            EvidenceAssessment(
                                "NASA-OPERA-RTC-POLARIZATION-SENSITIVITY",
                                EvidenceRelation.DOES_NOT_DISTINGUISH,
                                (
                                    f"Across {polarization_sensitivity['summary']['common_cells']} shared cells, the descriptive water-change correlations are "
                                    f"{polarization_sensitivity['summary']['vv_pearson_r_water_change_vs_log_ratio']:.3f} for VV and "
                                    f"{polarization_sensitivity['summary']['vh_pearson_r_water_change_vs_log_ratio']:.3f} for VH. "
                                    "Both are weak; the channels share acquisitions and processor and are not independent validation."
                                ),
                            )
                        ]
                        if polarization_sensitivity is not None
                        else []
                    ),
                    *(
                        [
                            EvidenceAssessment(
                                "NASA-OPERA-RTC-S1-TEMPORAL-SERIES",
                                EvidenceRelation.DOES_NOT_DISTINGUISH,
                                (
                                    f"On {sar_temporal_summary['common_support_count']} pixels shared by all three acquisitions, adjacent VV medians are "
                                    f"{sar_temporal_summary['intervals'][0]['summary_db']['median']:+.3f} dB and "
                                    f"{sar_temporal_summary['intervals'][1]['summary_db']['median']:+.3f} dB. "
                                    "The response differs across these intervals, but this series shares its first two acquisitions with the primary pair, has no earlier SAR baseline, and has unresolved product QA. It contains no independent water observation and does not distinguish the water explanation."
                                ),
                            )
                        ]
                        if sar_temporal_summary is not None
                        else []
                    ),
                    *(
                        [
                            EvidenceAssessment(
                                "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY",
                                EvidenceRelation.DOES_NOT_DISTINGUISH,
                                (
                                    f"The complete daily chronology records {gpm_interacquisition['summary']['nearest_cell_cumulative_precipitation_mm']:.2f} mm at the nearest approximately 0.1-degree cell over "
                                    f"{gpm_interacquisition['summary']['days_with_complete_nearest_cell_samples']} inter-acquisition days, peaking on {gpm_interacquisition['summary']['maximum_daily_precipitation_date_utc']}. "
                                    "This is regional precipitation context; it does not measure AOI surface-water extent, resolve local runoff, or establish a water-driven SAR response."
                                ),
                            )
                        ]
                        if gpm_interacquisition is not None
                        else []
                    ),
                    *(
                        [
                            EvidenceAssessment(
                                "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY",
                                EvidenceRelation.DOES_NOT_DISTINGUISH,
                                "ANA's official summary reports high river stage at a nearby point station over both SAR dates. It supplies regional event chronology but no timestamped readings, AOI water extent, or spatially matched observation; it does not distinguish why the SAR response changed or clear RTC-S1 QA.",
                            )
                        ]
                        if guaiba_observation is not None
                        else []
                    ),
                ],
                scope_limit="No causal attribution; RTC-S1 also lacks a consolidated provider QA verdict.",
                expected_observation="A quality-valid water transition is spatially associated with the SAR response at suitable temporal and common spatial support.",
                would_weaken_if="With adequate quality and coverage, valid water observations show no spatial relationship to the SAR response pattern; missing or masked coverage remains inconclusive.",
                testability_state="NOT_TESTABLE_WITH_RETAINED_EVIDENCE",
                testability_reason=(
                    ("The nearer WTR comparison has zero common valid AOI pixels and all earlier WTR-2 water-coded cells are cloud/snow flagged. " if nearer_context is not None else "")
                    + (
                        (
                            f"An exact area-weighted common-support overlay was completed; {spatial_summary['water_fraction_changed_by_at_most_0_05']} of {spatial_summary['sar_cells']} cells have at most 0.05 water-fraction change, and descriptive Pearson r is {spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}. "
                            "This does not test the physical explanation. "
                        )
                        if spatial_support is not None
                        else "The retained records do not contain a documented common-support pixel-wise cross-sensor test. "
                    )
                    + "The SAR pair also lacks a consolidated provider QA verdict."
                ),
                required_evidence=[
                    "Provider-resolved RTC-S1 product quality for both acquisitions",
                    "Temporally suitable water observations with valid spatial coverage",
                    "A documented common-support spatial comparison",
                ],
            ),
            hypothesis(
                "H3_SOIL_MOISTURE_CHANGE",
                "Soil-moisture change contributed to the SAR response.",
                ([
                    EvidenceAssessment(
                        "NASA-GPM-IMERG-BEFORE-PRE-SAR",
                        EvidenceRelation.DOES_NOT_DISTINGUISH,
                        "The sample-complete daily precipitation field documents regional rainfall before the earlier SAR acquisition, but its ~0.1 degree cells do not measure AOI soil moisture or establish a soil-moisture mechanism.",
                    ),
                    EvidenceAssessment(
                        "NASA-GPM-IMERG-AFTER-PRE-SAR",
                        EvidenceRelation.DOES_NOT_DISTINGUISH,
                        "The sample-complete daily precipitation field documents regional rainfall before the later SAR acquisition, but its ~0.1 degree cells do not measure AOI soil moisture or establish a soil-moisture mechanism.",
                    ),
                ] if gpm_contexts else []) + (
                    [EvidenceAssessment(
                        "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY",
                        EvidenceRelation.DOES_NOT_DISTINGUISH,
                        "The complete daily series documents regional rainfall timing between SAR acquisitions, but its ~0.1 degree grid does not measure AOI soil moisture or distinguish a soil-moisture effect.",
                    )] if gpm_interacquisition is not None else []
                ) + (
                    [EvidenceAssessment(
                        "NASA-SMAP-SPL3SMP-E-RESOLUTION-SCREEN",
                        EvidenceRelation.DOES_NOT_DISTINGUISH,
                        "CMR confirms radiometer-only daily granules on both SAR dates, but the approximately 36 km radiometer footprint and 9 km posting are much coarser than this ~1 km AOI. The metadata-only screen retrieved no soil-moisture values and cannot test an AOI-scale mechanism.",
                    )] if smap_radiometer_screen is not None else []
                ) + (
                    [EvidenceAssessment(
                        "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN",
                        EvidenceRelation.DOES_NOT_DISTINGUISH,
                        "The matched-time SPL4SMAU V8 values are model-assimilated regional estimates on a 9 km grid, not AOI-scale observations. The nearest estimate changes by "
                        f"{smap_l4_context_summary['after_minus_before_model_analysis_m3_m3']:.6f} m3/m3, while the matching local assimilated brightness-temperature fields contain no valid values; "
                        "ensemble spread is not a significance test, and the product uses IMERG precipitation forcing that may overlap the linked GPM chronology.",
                    )] if smap_l4_context_summary is not None else []
                ) + (
                    [EvidenceAssessment(
                        "NASA-SPL2SMAP-S-CANDIDATE-SCREEN",
                        EvidenceRelation.LIMITS_INTERPRETATION,
                        "The exact-AOI 3 km candidate has zero paired cells passing the declared valid-range and retrieval/surface-flag screen. It blends SMAP radiometry with Sentinel-1 radar and cannot independently validate the Sentinel-1 response.",
                    )]
                    if smap_screen is not None
                    else []
                ),
                scope_limit=(
                    (
                        "The screened SMAP/Sentinel-1 candidate failed product quality checks and reuses Sentinel-1 input. "
                        if smap_screen is not None
                        else ""
                    )
                    + ("An independent SMAP radiometer candidate covers both dates but is too coarse for this AOI; no pixel data were retrieved. " if smap_radiometer_screen is not None else "")
                    + ("NASA SMAP L4 supplies only coarse, model-derived context with potential upstream GPM input overlap. " if smap_l4_context_summary is not None else "")
                    + ("A complete inter-acquisition rainfall chronology is available, but its coarse spatial support remains nondiscriminating. " if gpm_interacquisition is not None else "")
                    + "No accepted AOI-scale soil-moisture measurements are retained."
                ),
                expected_observation="Independent, quality-accepted soil-moisture measurements at appropriate spatial and temporal support vary with the SAR response.",
                would_weaken_if="Adequate independent soil-moisture measurements show no predicted spatial or temporal relationship; coarse, failed, or missing measurements remain inconclusive.",
                testability_state="NOT_TESTABLE_WITH_RETAINED_EVIDENCE" if gpm_contexts or smap_screen is not None or smap_radiometer_screen is not None else "NOT_TESTED",
                testability_reason=(
                    ("NASA GPM provides coarse precipitation context, not soil-moisture measurements. " if gpm_contexts else "")
                    + ("The exact-AOI SMAP/Sentinel-1 candidate has no paired cells passing its quality screen and reuses Sentinel-1 input. " if smap_screen is not None else "")
                    + ("The independent SMAP radiometer candidate is too coarse and was screened without reading pixels. " if smap_radiometer_screen is not None else "")
                    + ("The SMAP L4 model context is too coarse for this AOI and shares an upstream precipitation source with the GPM context. " if smap_l4_context_summary is not None else "")
                    + ("No scale-appropriate independent soil-moisture observations remain in the retained records." if gpm_contexts or smap_screen is not None or smap_radiometer_screen is not None else "No independent soil-moisture observations are retained for this AOI and interval.")
                ),
                required_evidence=["Independent soil-moisture measurements with suitable quality, timing, and AOI-scale support"],
            ),
            hypothesis(
                "H4_VEGETATION_STATE_CHANGE",
                "Vegetation-state change contributed to the SAR response.",
                (
                    [EvidenceAssessment(
                        "NASA-HLS-L30-NDVI-SAR-ASSOCIATION",
                        EvidenceRelation.DOES_NOT_DISTINGUISH,
                        f"The native-grid association uses {hls_association_summary['sar_cells']} SAR cells at the 75% optical-support threshold (descriptive r={hls_association_summary['descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db']:.3f}); limited common clear support, spatial dependence, and different optical/SAR measurements do not test vegetation causality.",
                    )] if hls_association_summary is not None else []
                ) + (
                    [EvidenceAssessment(
                        "NASA-HLS-S30-NDVI-SAR-ASSOCIATION",
                        EvidenceRelation.DOES_NOT_DISTINGUISH,
                        f"Only {hls_s30_vegetation['comparison']['common_clear_land_ndvi_pixel_count']} of {hls_s30_vegetation['comparison']['aoi_center_pixel_count']} HLS S30 AOI pixels are clear on both dates; {hls_s30_association_summary['sar_cells']} SAR cells meet the 75% optical-area screen (descriptive r={hls_s30_association_summary['descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db']:.3f}). Sparse support and spatial dependence prevent causal discrimination.",
                    )] if hls_s30_association_summary is not None else []
                ) + (
                    [EvidenceAssessment(
                        "NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN",
                        EvidenceRelation.LIMITS_INTERPRETATION,
                        f"The native 250 m MOD13Q1 screen found {mod13q1_screen['observations']['common_strictly_accepted_pixel_count']} common pixels passing the declared paired QA and land gates; the actual per-pixel composite dates span offsets {mod13q1_screen['observations']['all_retained_composite_observation_offsets_days_min_max']} days from the two SAR acquisition dates. No NDVI difference or SAR association is computed, so this candidate cannot test vegetation causality.",
                    )] if mod13q1_screen is not None else []
                ) + (
                    [EvidenceAssessment(
                        "NASA-MOD09GA-VEGETATION-CANDIDATE-SCREEN",
                        EvidenceRelation.LIMITS_INTERPRETATION,
                        f"The daily MOD09GA screen retrieved {mod09ga_screen['observations']['common_pixel_center_count']} common 500 m centers; {mod09ga_screen['observations']['common_strict_accepted_count']} passed the paired land and state-QA gate. The 1 km state layer marks the retained centers as water or shoreline, so no NDVI difference or SAR association is computed.",
                    )] if mod09ga_screen is not None else []
                ),
                scope_limit=(
                    (f"HLS L30 common clear-land support is {hls_vegetation['comparison']['common_clear_land_aoi_fraction']:.1%} of the AOI. " if hls_association_summary is not None else "")
                    + (f"HLS S30 common clear-land support is {hls_s30_vegetation['comparison']['common_clear_land_aoi_fraction']:.2%} of the AOI, with {hls_s30_association_summary['sar_cells']} SAR cells at the 75% threshold. " if hls_s30_association_summary is not None else "")
                    + ("NASA MOD13Q1 has no paired accepted land pixels under the declared QA gate and its per-pixel composite days are not temporally aligned on both SAR dates. " if mod13q1_screen is not None else "")
                    + ("Daily NASA MOD09GA has no paired strict land centers; its 500 m reflectance is accompanied by 1 km state QA that classifies the case window as water or shoreline. " if mod09ga_screen is not None else "")
                    + "Optical NDVI association does not establish a physical vegetation driver or validate SAR."
                ),
                expected_observation="An independent vegetation measurement changes at compatible acquisition times and shows a reproducible spatial relationship with the SAR response on adequate common support.",
                would_weaken_if="Quality-accepted vegetation measurements with adequate coverage and timing show no prespecified association; sparse, masked, or mistimed comparisons remain inconclusive.",
                testability_state=("DESCRIPTIVE_ASSOCIATION_ONLY" if hls_association_summary is not None or hls_s30_association_summary is not None else "NOT_TESTED"),
                testability_reason=(
                    "HLS NDVI/SAR associations were computed, but their limited common support and spatial dependence do not test vegetation causality. "
                    + ("The NASA MODIS candidates add no accepted paired land support; MOD13Q1 composites are not aligned to both SAR dates and MOD09GA state QA classifies the case window as water or shoreline." if mod13q1_screen is not None or mod09ga_screen is not None else "")
                    if hls_association_summary is not None or hls_s30_association_summary is not None
                    else ("The NASA MODIS candidates are quality/support limited; no independent vegetation-state measurement with adequate paired land support is retained." if mod13q1_screen is not None or mod09ga_screen is not None else "No independent vegetation-state measurements are retained for this AOI and interval.")
                ),
                required_evidence=["Independent vegetation-state measurements with suitable quality, timing, and AOI-scale common support"],
            ),
            hypothesis(
                "H5_ACQUISITION_CONDITIONS_EFFECT",
                "Changes in acquisition geometry or sensor conditions contributed to the SAR response.",
                ([EvidenceAssessment(
                    "NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW",
                    EvidenceRelation.DOES_NOT_DISTINGUISH,
                    acquisition_conditions["interpretation"],
                )] if acquisition_conditions is not None else []),
                scope_limit=(
                    "Retained product metadata are compared, but available fields do not establish spatial relation to the response or validate the diagnostic measurement."
                    if acquisition_conditions is not None
                    else "No acquisition-condition comparison has been evaluated for this case."
                ),
                expected_observation="Documented changes in acquisition geometry or sensor conditions align with the measured spatial response.",
                would_weaken_if="Compatible acquisition metadata and quality diagnostics show no relevant differences; unavailable metadata leave the explanation unresolved.",
                testability_state=("NOT_TESTABLE_WITH_RETAINED_EVIDENCE" if acquisition_conditions is not None else "NOT_TESTED"),
                testability_reason=(
                    acquisition_conditions["interpretation"]
                    if acquisition_conditions is not None
                    else "The retained investigation has not compared incidence geometry, orbit-specific acquisition conditions, and relevant product processing settings as a targeted test."
                ),
                required_evidence=["Per-acquisition geometry and sensor/processing metadata compared on compatible spatial support"],
            ),
            hypothesis(
                "H6_SAR_PRODUCT_QUALITY_EFFECT",
                "Product quality or processing effects account for some or all of the SAR response.",
                [EvidenceAssessment(
                    "SAR-RTC-S1-PAIR",
                    EvidenceRelation.LIMITS_INTERPRETATION,
                    "Per-product metadata and masks are retained, but neither sidecar provides a consolidated PASS/FAIL disposition.",
                )],
                scope_limit="Unresolved pending provider QA clarification or corrected products.",
                expected_observation="Documented quality or processing anomalies are present and spatially or temporally associated with the measured SAR response.",
                would_weaken_if="Provider-resolved quality checks and processing metadata show no relevant anomaly; this would not exclude unmeasured error sources.",
                testability_state="NOT_TESTED",
                testability_reason="The sidecars retain selected metadata but provide neither acquisition a consolidated QA disposition, so a quality-effect test cannot be completed.",
                required_evidence=["Authoritative per-product QA disposition and relevant spatial quality diagnostics"],
            ),
        ], known_evidence_ids=evidence_ids),
        "assessment": {
            "summary": summary,
            "physical_cause": "UNRESOLVED",
            "event_extent": "NOT_ESTABLISHED",
            "nisar_measurement_present": False,
        },
        "follow_up_evidence": validate_follow_up_plan(
            follow_up_items,
            known_hypothesis_ids=known_hypothesis_ids,
            known_evidence_ids=evidence_ids,
        ),
        "processing": {
            "method": "Read the exact retained source records; verify record types, shared WGS84 AOI, measurement-mask shapes and counts; summarize valid log-ratio values; when linked, validate the source checksums and summarize an exact area-weighted polygon overlay of native-grid optical cells on SAR cells without resampling; validate hypothesis predictions, weakening conditions, evidence references, and testability-state fields without deciding their scientific correctness.",
            "software": {"numpy": np.__version__},
            "script": "tools/research/build_cross_sensor_investigation.py",
            "no_statistical_significance_claim": True,
            "no_probability_or_confidence_score": True,
            "smap_l4_context_validation": "Source subsets are checksum-verified and re-read to reproduce retained grids and arrays; this validates provenance and calculations, not the product's scientific suitability or ECHO's SAR QA gate.",
        },
        "interpretation_limits": [
            "OPERA RTC-S1 is Sentinel-1-derived and is not NISAR.",
            "The SAR result remains diagnostic because provider QA metadata contain no consolidated verdict.",
            "DSWx-HLS water classes are optical algorithm outputs, not ground truth.",
            "The two products use different native grids; polygon intersections provide area-weighted descriptive association, not pixel identity or causal evidence.",
            "No event boundary, damage, or physical cause is inferred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sar-record", required=True, type=Path)
    parser.add_argument("--optical-record", required=True, type=Path)
    parser.add_argument("--nearer-optical-record", type=Path)
    parser.add_argument("--catalog-screen-record", type=Path, help="optional CMR screen for the selected optical context")
    parser.add_argument("--spatial-support-record", type=Path, help="optional checksum-linked native-grid spatial overlay record")
    parser.add_argument("--polarization-vh-pair-record", type=Path, help="optional diagnostic VH pair corresponding to the primary VV observations")
    parser.add_argument("--polarization-vh-spatial-support-record", type=Path, help="optional source-linked VH native-grid spatial overlay")
    parser.add_argument("--polarization-sensitivity-record", type=Path, help="optional checksum-linked VV/VH sensitivity evaluation")
    parser.add_argument("--gpm-before-record", type=Path, help="optional NASA GPM daily context strictly before the earlier SAR acquisition")
    parser.add_argument("--gpm-after-record", type=Path, help="optional NASA GPM daily context strictly before the later SAR acquisition")
    parser.add_argument("--gpm-intervening-record", type=Path, help="optional daily NASA GPM source record spanning between SAR acquisitions")
    parser.add_argument("--gpm-interacquisition-record", type=Path, help="optional derived, checksum-linked inter-acquisition GPM chronology")
    parser.add_argument("--smap-screen-record", type=Path, help="optional quality-screened NASA SMAP/Sentinel-1 context candidate")
    parser.add_argument("--smap-radiometer-screen-record", type=Path, help="optional metadata-only screen of independent SMAP radiometer spatial suitability")
    parser.add_argument("--hls-vegetation-record", type=Path, help="optional NASA/USGS HLS Landsat vegetation context screen")
    parser.add_argument("--hls-association-record", type=Path, help="optional source-linked descriptive HLS NDVI/SAR spatial association")
    parser.add_argument("--hls-s30-vegetation-record", type=Path, help="optional NASA/USGS HLS Sentinel-2 vegetation context screen")
    parser.add_argument("--hls-s30-association-record", type=Path, help="optional source-linked descriptive HLS S30 NDVI/SAR association")
    parser.add_argument("--acquisition-conditions-record", type=Path, help="optional source-linked per-acquisition OPERA RTC-S1 metadata comparison")
    parser.add_argument("--mod13q1-screen-record", type=Path, help="optional source-linked NASA MODIS MOD13Q1 vegetation quality/date screen")
    parser.add_argument("--mod09ga-screen-record", type=Path, help="optional source-linked bounded NASA MODIS daily reflectance and state-QA screen")
    parser.add_argument("--ecostress-sm-screen-record", type=Path, help="optional source-linked ECOSTRESS soil-moisture catalog availability screen")
    parser.add_argument("--ismn-station-screen-record", type=Path, help="optional source-linked ISMN in-situ station coverage screen")
    parser.add_argument("--sar-temporal-series-record", type=Path, help="optional checksum-linked same-grid OPERA RTC-S1 temporal-series analysis")
    parser.add_argument("--smap-l4-context-record", type=Path, help="optional checksum-verified NASA SMAP L4 regional model-context screen")
    parser.add_argument("--guaiba-context-record", type=Path, help="optional official ANA Guaíba event chronology, narrative context only")
    parser.add_argument("--guaiba-access-screen-record", type=Path, help="optional official ANA Guaíba primary-series access requirement record")
    parser.add_argument("--case-id", default="rio-grande-do-sul-cross-sensor-diagnostic-2024")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = build_assessment(
        args.sar_record,
        args.optical_record,
        args.nearer_optical_record,
        args.catalog_screen_record,
        args.case_id,
        args.spatial_support_record,
        args.polarization_vh_pair_record,
        args.polarization_vh_spatial_support_record,
        args.polarization_sensitivity_record,
        args.gpm_before_record,
        args.gpm_after_record,
        args.smap_screen_record,
        args.hls_vegetation_record,
        args.hls_association_record,
        args.gpm_intervening_record,
        args.gpm_interacquisition_record,
        args.smap_radiometer_screen_record,
        args.guaiba_context_record,
        args.hls_s30_vegetation_record,
        args.hls_s30_association_record,
        args.acquisition_conditions_record,
        args.mod13q1_screen_record,
        args.mod09ga_screen_record,
        args.ecostress_sm_screen_record,
        args.ismn_station_screen_record,
        args.sar_temporal_series_record,
        args.smap_l4_context_record,
        args.guaiba_access_screen_record,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"status={record['status']}")
    print(f"evidence_artifacts={len(record['evidence_artifacts'])}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

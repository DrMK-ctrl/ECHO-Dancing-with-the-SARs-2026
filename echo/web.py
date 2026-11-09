"""Read-only local web interface for ECHO case metadata."""

from __future__ import annotations

from hashlib import sha256
import ipaddress
import json
import logging
import math
from dataclasses import asdict
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from echo.bhoonidhi import BhoonidhiError, authenticate, search_ssar_gcov
from echo.catalog import (
    CatalogQuery,
    CatalogQueryError,
    MAX_GCOV_CATALOG_RESULTS,
    build_catalog_record,
    search_gcov,
    search_gunw,
)
from echo.draft_store import DraftStoreError, LocalDraftStore, default_draft_store_dir
from echo.gcov_analysis import GcovPairAnalysisError, build_gcov_pair_analysis
from echo.gunw_access import GunwAccessError, _validated_gunw_product
from echo.gcov_preview import GcovPreviewError, build_gcov_preview
from echo.investigation import (
    is_non_directional_evidence,
    preview_evidence_relationship_change,
    validate_investigation_contract,
)
from echo.investigation_draft import (
    InvestigationDraftError,
    attach_followup_catalog_failure,
    attach_followup_catalog_screen,
    attach_followup_provider_qa_screen,
    followup_catalog_candidate,
    attach_validated_case_source,
    assess_investigation_draft,
    attach_unreviewed_source,
    build_investigation_draft,
    revise_investigation_draft,
    screen_followup_source,
    validate_investigation_draft,
)
from echo.nisar_access import NisarAccessError, _validated_product
from echo.modis_vi import validate_mod13q1_candidate_screen
from echo.hls_candidate_screen import validate_hls_candidate_screen
from echo.soil_moisture_sources import (
    validate_ecostress_availability_screen,
    validate_ismn_station_screen,
)
from echo.swot_riversp import SwotRiverSpError, validate_screen as validate_swot_riversp_screen
from echo.opera_rtc_conditions import validate_acquisition_condition_review
from echo.opera_rtc_quality import (
    OperaRtcQualityReviewError,
    build_opera_rtc_pair_quality_review,
)
from echo.opera_rtc_analysis import (
    OperaRtcS1AnalysisError,
    validate_opera_rtc_s1_series_record,
)
from echo.opera_rtc_catalog import (
    OperaRtcCatalogError,
    OperaRtcCatalogQuery,
    build_opera_rtc_catalog_record,
    search_opera_rtc_s1_with_pagination,
)
from echo.opera_rtc_pipeline import (
    OperaRtcS1PipelineError,
    build_opera_rtc_s1_pair_record,
)
from echo.qa import QASummaryError, read_qa_summary
from echo.science_profiles import product_scope_for_record_type


_STATIC = Path(__file__).with_name("static")
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MAX_CATALOG_REQUEST_BYTES = 8 * 1024
_MAX_BHOONIDHI_REQUEST_BYTES = 8 * 1024
_MAX_QA_SUMMARY_REQUEST_BYTES = 4 * 1024
_MAX_QA_EVIDENCE_EXPORT_REQUEST_BYTES = 256 * 1024
_MAX_GCOV_PREVIEW_REQUEST_BYTES = 16 * 1024
_MAX_GCOV_PAIR_REQUEST_BYTES = 32 * 1024
_MAX_OPERA_PAIR_REQUEST_BYTES = 64 * 1024
_MAX_DSWX_CONTEXT_BYTES = 2 * 1024 * 1024
_MAX_OPERA_TEMPORAL_SERIES_BYTES = 2 * 1024 * 1024
_MAX_INVESTIGATION_ASSESSMENT_BYTES = 256 * 1024
_MAX_INVESTIGATION_DRAFT_BYTES = 40 * 1024 * 1024
_MAX_INVESTIGATION_DRAFT_ATTACH_BYTES = 40 * 1024 * 1024
_MAX_INVESTIGATION_DRAFT_ASSESS_BYTES = 40 * 1024 * 1024 + 256 * 1024
_MAX_COUNTERFACTUAL_PREVIEW_REQUEST_BYTES = 8 * 1024
_MAX_LINKED_EVIDENCE_ARTIFACT_BYTES = 64 * 1024 * 1024
_MAX_CASE_EVIDENCE_IMPORT_REQUEST_BYTES = 40 * 1024 * 1024 + 256 * 1024


def _case_evidence_path(case_path: Path, evidence_name: str, evidence_root: Path) -> Path | None:
    manifest_path = case_path.with_name("investigation.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError):
        raise ValueError("Case investigation manifest is invalid")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Case investigation manifest has an unsupported schema")
    evidence = manifest.get("evidence_records")
    relative_path = evidence.get(evidence_name) if isinstance(evidence, dict) else None
    if not isinstance(relative_path, str) or not relative_path:
        return None
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError("Case evidence paths must be relative to the project root")
    root = evidence_root.resolve()
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Case evidence path escapes the project root")
    return resolved


def _read_case_review(case_path: Path) -> dict[str, object]:
    for name in ("case-review.json", "qa-review.json"):
        path = case_path.with_name(name)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}
    return {}


def _case_identifier(case_path: Path) -> str:
    review = _read_case_review(case_path)
    value = review.get("case_id")
    return value if isinstance(value, str) and value else case_path.parent.name


def _discover_case_registry(case_path: Path, evidence_root: Path) -> dict[str, Path]:
    """Discover local case folders without accepting paths from web requests."""
    case_path = case_path.resolve()
    root = evidence_root.resolve()
    registry = {_case_identifier(case_path): case_path}
    cases_root = root / "data" / "cases"
    try:
        if not case_path.is_relative_to(cases_root.resolve()):
            return registry
    except OSError:
        return registry
    if not cases_root.is_dir():
        return registry
    for candidate in sorted(cases_root.glob("*/catalog.json")):
        if not candidate.is_file():
            continue
        review = _read_case_review(candidate)
        if not review:
            continue
        case_id = review.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            case_id = candidate.parent.name
        registry[case_id] = candidate.resolve()
    return registry


def _validate_assessment_artifacts(record: dict[str, object], evidence_root: Path) -> set[str]:
    artifacts = record.get("evidence_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("assessment evidence artifacts are missing")
    root = evidence_root.resolve()
    evidence_ids: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("assessment evidence artifact is invalid")
        evidence_id = artifact.get("evidence_id")
        relative_path = artifact.get("relative_path")
        expected_hash = artifact.get("sha256")
        expected_type = artifact.get("record_type")
        expected_status = artifact.get("status")
        role = artifact.get("role")
        if (
            not isinstance(evidence_id, str)
            or not evidence_id
            or evidence_id in evidence_ids
            or not isinstance(relative_path, str)
            or not relative_path
            or not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(character not in "0123456789abcdef" for character in expected_hash)
            or not isinstance(expected_type, str)
            or not expected_type
            or not isinstance(expected_status, str)
            or not expected_status
            or not isinstance(role, str)
            or not role
        ):
            raise ValueError("assessment evidence artifact metadata is invalid")
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise ValueError("assessment evidence paths must be relative")
        artifact_path = (root / candidate).resolve()
        if not artifact_path.is_relative_to(root):
            raise ValueError("assessment evidence path escapes the project root")
        try:
            size = artifact_path.stat().st_size
            if not artifact_path.is_file() or size > _MAX_LINKED_EVIDENCE_ARTIFACT_BYTES:
                raise ValueError("assessment evidence artifact is missing or exceeds the size limit")
            payload = artifact_path.read_bytes()
        except OSError as exc:
            raise ValueError("assessment evidence artifact cannot be read") from exc
        if sha256(payload).hexdigest() != expected_hash:
            raise ValueError(f"assessment evidence checksum mismatch: {evidence_id}")
        try:
            source_record = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"assessment evidence record is invalid: {evidence_id}") from exc
        if (
            not isinstance(source_record, dict)
            or source_record.get("record_type") != expected_type
            or source_record.get("status") != expected_status
        ):
            raise ValueError(f"assessment evidence identity mismatch: {evidence_id}")
        if expected_type == "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS":
            if source_record.get("schema_version") == 2:
                try:
                    expected_review = build_opera_rtc_pair_quality_review(source_record)
                except OperaRtcQualityReviewError as exc:
                    raise ValueError(f"OPERA pair quality review is invalid: {evidence_id}") from exc
                if source_record.get("quality_review") != expected_review:
                    raise ValueError(f"OPERA pair quality review does not reproduce: {evidence_id}")
            elif "quality_review" in source_record:
                raise ValueError(f"OPERA schema version 1 cannot carry a scoped quality review: {evidence_id}")
        if expected_type == "ECHO_GPM_IMERG_DAILY_CONTEXT":
            days = source_record.get("daily_observations")
            query = source_record.get("query", {})
            try:
                start = date.fromisoformat(query.get("start_date_utc"))
                end = date.fromisoformat(query.get("end_date_utc"))
            except (TypeError, ValueError) as exc:
                raise ValueError("GPM evidence query dates are invalid") from exc
            expected_days = (end - start).days + 1
            if not isinstance(days, list) or not 1 <= len(days) <= 31 or len(days) != expected_days:
                raise ValueError("GPM evidence must retain 1 to 31 bounded daily source subsets matching its query interval")
            for day in days:
                asset = day.get("asset", {}) if isinstance(day, dict) else {}
                asset_path_text = asset.get("relative_path")
                asset_hash = asset.get("sha256")
                if not isinstance(asset_path_text, str) or not isinstance(asset_hash, str):
                    raise ValueError("GPM daily subset provenance is incomplete")
                asset_path = Path(asset_path_text)
                if asset_path.is_absolute():
                    raise ValueError("GPM daily subset paths must be relative")
                resolved_asset = (root / asset_path).resolve()
                if not resolved_asset.is_relative_to(root):
                    raise ValueError("GPM daily subset path escapes the project root")
                try:
                    asset_size = resolved_asset.stat().st_size
                    asset_payload = resolved_asset.read_bytes()
                except OSError as exc:
                    raise ValueError("GPM daily subset asset is unavailable") from exc
                if asset_size > 2 * 1024 * 1024 or sha256(asset_payload).hexdigest() != asset_hash:
                    raise ValueError("GPM daily subset checksum or size validation failed")
        if expected_type == "ECHO_GPM_IMERG_INTERACQUISITION_CHRONOLOGY":
            linked = {
                item.get("evidence_id"): item.get("sha256")
                for item in artifacts
                if isinstance(item, dict)
            }
            source_links = source_record.get("sources", {})
            days = source_record.get("daily_observations")
            summary = source_record.get("summary", {})
            if (
                source_record.get("case_id") != record.get("case_id")
                or source_links.get("sar_pair_record_sha256") != linked.get("SAR-RTC-S1-PAIR")
                or source_links.get("intervening_gpm_context_record_sha256") != linked.get("NASA-GPM-IMERG-INTERVENING-DAILY-CONTEXT")
                or source_links.get("trailing_gpm_context_record_sha256") != linked.get("NASA-GPM-IMERG-AFTER-PRE-SAR")
                or not isinstance(days, list)
                or len(days) != summary.get("days_requested")
                or len(days) != summary.get("days_with_complete_nearest_cell_samples")
                or len(days) > 31
                or summary.get("days_with_complete_nearest_cell_samples", 0) < 1
            ):
                raise ValueError("GPM inter-acquisition chronology has invalid case, lineage, or completeness metadata")
            try:
                values = [float(day["precipitation_mm_per_day"]) for day in days]
                dates = [date.fromisoformat(day["date_utc"]) for day in days]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("GPM inter-acquisition daily series is malformed") from exc
            if (
                any(not math.isfinite(value) or value < 0 for value in values)
                or any((right - left).days != 1 for left, right in zip(dates, dates[1:]))
                or not math.isclose(sum(values), summary.get("nearest_cell_cumulative_precipitation_mm", math.nan), rel_tol=1e-9, abs_tol=1e-8)
                or not math.isclose(max(values), summary.get("maximum_daily_precipitation_mm_per_day", math.nan), rel_tol=1e-9, abs_tol=1e-8)
            ):
                raise ValueError("GPM inter-acquisition values do not reproduce their recorded summary")
        if expected_type == "ECHO_SMAP_RADIOMETER_CANDIDATE_SCREEN":
            source = source_record.get("source", {})
            query = source_record.get("query", {})
            spatial = source_record.get("spatial_suitability", {})
            retrieval = source_record.get("retrieval", {})
            granules = source_record.get("screened_daily_granules")
            selected = source_record.get("selected_daily_granules")
            if not isinstance(granules, list) or not isinstance(selected, list):
                raise ValueError("SMAP radiometer screen must retain complete granule and selected-date lists")
            if (
                source_record.get("case_id") != record.get("case_id")
                or source.get("short_name") != "SPL3SMP_E"
                or source.get("version") != "006"
                or source.get("instrument") != "L-band radiometer"
                or source.get("source_independence") != "Radiometer-only SMAP product; does not use Sentinel-1 radar inputs."
                or source_record.get("status") != "SCREENED_SPATIALLY_TOO_COARSE_FOR_AOI_SCALE_TEST"
                or query.get("cmr_hit_count") != query.get("cmr_result_count")
                or query.get("cmr_result_count") != len(granules)
            ):
                raise ValueError("SMAP radiometer screen has invalid case, source, or CMR completeness metadata")
            dates = [item.get("date_utc") for item in granules if isinstance(item, dict)]
            selected_dates = [item.get("date_utc") for item in selected if isinstance(item, dict)] if isinstance(selected, list) else []
            if (
                len(dates) != len(granules)
                or dates != sorted(dates)
                or len(set(dates)) != len(dates)
                or len(selected_dates) < 2
                or len(set(selected_dates)) != len(selected_dates)
                or not all(day in dates for day in selected_dates)
                or spatial.get("product_grid_posting_km") != 9
                or spatial.get("radiometer_native_footprint_km_approx") != 36
                or not isinstance(spatial.get("aoi_width_km_approx"), (int, float))
                or not isinstance(spatial.get("aoi_height_km_approx"), (int, float))
                or spatial["aoi_width_km_approx"] <= 0
                or spatial["aoi_height_km_approx"] <= 0
                or retrieval.get("data_files_downloaded") is not False
                or retrieval.get("pixel_values_read") is not False
                or retrieval.get("provider_quality_flags_evaluated") is not False
            ):
                raise ValueError("SMAP radiometer screen has invalid temporal, scale, or no-retrieval disposition")
        if expected_type == "ECHO_SMAP_SENTINEL_SOIL_MOISTURE_CANDIDATE_SCREEN":
            if (
                source_record.get("case_id") != record.get("case_id")
                or source_record.get("comparison", {}).get("paired_quality_eligible_cells") != 0
            ):
                raise ValueError("SMAP/Sentinel-1 screen does not match the investigation case")
            observations = source_record.get("observations")
            if not isinstance(observations, list) or len(observations) != 2:
                raise ValueError("SMAP/Sentinel-1 screen must retain a before/after subset pair")
            for observation in observations:
                asset = observation.get("asset", {}) if isinstance(observation, dict) else {}
                asset_path_text = asset.get("relative_path")
                asset_hash = asset.get("sha256")
                if not isinstance(asset_path_text, str) or not isinstance(asset_hash, str):
                    raise ValueError("SMAP/Sentinel-1 subset provenance is incomplete")
                asset_path = Path(asset_path_text)
                if asset_path.is_absolute():
                    raise ValueError("SMAP/Sentinel-1 subset paths must be relative")
                resolved_asset = (root / asset_path).resolve()
                if not resolved_asset.is_relative_to(root):
                    raise ValueError("SMAP/Sentinel-1 subset path escapes the project root")
                try:
                    asset_size = resolved_asset.stat().st_size
                    asset_payload = resolved_asset.read_bytes()
                except OSError as exc:
                    raise ValueError("SMAP/Sentinel-1 subset is unavailable") from exc
                if asset_size > 2 * 1024 * 1024 or sha256(asset_payload).hexdigest() != asset_hash:
                    raise ValueError("SMAP/Sentinel-1 subset checksum or size validation failed")
        if expected_type == "ECHO_SMAP_L4_REGIONAL_SOIL_MOISTURE_CONTEXT_SCREEN":
            source = source_record.get("source", {})
            query = source_record.get("query", {})
            comparison = source_record.get("comparison", {})
            observations = source_record.get("observations")
            if (
                source_record.get("case_id") != record.get("case_id")
                or source_record.get("status") != "SCREENED_REGIONAL_MODEL_CONTEXT_NOT_SUITABLE_FOR_AOI_SCALE_DISCRIMINATION"
                or source.get("provider") != "NASA National Snow and Ice Data Center DAAC"
                or source.get("short_name") != "SPL4SMAU"
                or source.get("version") != "008"
                or source.get("collection_concept_id") != "C3480440639-NSIDC_CPRD"
                or source.get("doi") != "10.5067/02LGW4DGJYRX"
                or query.get("grid_posting_m") != 9000.0
                or query.get("same_native_grid_before_after") is not True
                or query.get("aoi_smaller_than_one_grid_cell") is not True
                or not isinstance(observations, list)
                or len(observations) != 2
                or comparison.get("valid_assimilated_brightness_temperature_values_by_date") != [0, 0]
                or "not treated as a QA pass" not in comparison.get("provider_quality_gate", "")
                or source_record.get("upstream_dependencies", {}).get("potential_input_overlap")
                != ["NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY"]
            ):
                raise ValueError("SMAP L4 source does not retain its model, scale, lineage, or QA limitations")
            for observation in observations:
                asset = observation.get("asset", {}) if isinstance(observation, dict) else {}
                asset_path_text = asset.get("relative_path")
                asset_hash = asset.get("sha256")
                if not isinstance(asset_path_text, str) or not isinstance(asset_hash, str):
                    raise ValueError("SMAP L4 subset provenance is incomplete")
                asset_path = Path(asset_path_text)
                if asset_path.is_absolute():
                    raise ValueError("SMAP L4 subset paths must be relative")
                resolved_asset = (root / asset_path).resolve()
                if not resolved_asset.is_relative_to(root):
                    raise ValueError("SMAP L4 subset path escapes the project root")
                try:
                    asset_size = resolved_asset.stat().st_size
                    asset_payload = resolved_asset.read_bytes()
                except OSError as exc:
                    raise ValueError("SMAP L4 subset is unavailable") from exc
                if (
                    asset_size > 2 * 1024 * 1024
                    or asset_size != asset.get("size_bytes")
                    or sha256(asset_payload).hexdigest() != asset_hash
                ):
                    raise ValueError("SMAP L4 subset checksum or size validation failed")
        if expected_type in {"ECHO_HLS_L30_VEGETATION_CONTEXT_SCREEN", "ECHO_HLS_S30_VEGETATION_CONTEXT_SCREEN"}:
            observations = source_record.get("observations")
            variant = "L30" if expected_type == "ECHO_HLS_L30_VEGETATION_CONTEXT_SCREEN" else "S30"
            expected_short_name = "HLSL30" if variant == "L30" else "HLSS30"
            expected_collection = "C2021957657-LPCLOUD" if variant == "L30" else "C2021957295-LPCLOUD"
            if (
                source_record.get("case_id") != record.get("case_id")
                or source_record.get("source", {}).get("product_variant") not in (None, variant)
                or source_record.get("source", {}).get("short_name") != expected_short_name
                or source_record.get("source", {}).get("collection_id") != expected_collection
                or not isinstance(observations, list)
                or len(observations) != 2
            ):
                raise ValueError("HLS vegetation screen does not match the investigation case")
            for observation in observations:
                asset = observation.get("asset", {}) if isinstance(observation, dict) else {}
                asset_path_text = asset.get("relative_path")
                asset_hash = asset.get("sha256")
                if not isinstance(asset_path_text, str) or not isinstance(asset_hash, str):
                    raise ValueError("HLS bounded subset provenance is incomplete")
                asset_path = Path(asset_path_text)
                if asset_path.is_absolute():
                    raise ValueError("HLS bounded subset paths must be relative")
                resolved_asset = (root / asset_path).resolve()
                if not resolved_asset.is_relative_to(root):
                    raise ValueError("HLS bounded subset path escapes the project root")
                try:
                    asset_size = resolved_asset.stat().st_size
                    asset_payload = resolved_asset.read_bytes()
                except OSError as exc:
                    raise ValueError("HLS bounded subset is unavailable") from exc
                if asset_size > 64 * 1024 * 1024 or asset_size != asset.get("size_bytes") or sha256(asset_payload).hexdigest() != asset_hash:
                    raise ValueError("HLS bounded subset checksum or size validation failed")
        evidence_ids.add(evidence_id)
    return evidence_ids


def _validate_assessment_record(record: dict[str, object], evidence_root: Path) -> set[str]:
    if (
        not isinstance(record, dict)
        or record.get("record_type") != "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT"
        or record.get("schema_version", 1) not in {1, 2, 3, 4, 5}
    ):
        raise ValueError("assessment schema is invalid")
    evidence_ids = _validate_assessment_artifacts(record, evidence_root)
    try:
        investigation = validate_investigation_contract(record)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"assessment investigation contract is invalid: {exc}") from exc
    if investigation["evidence_ids"] != evidence_ids:
        raise ValueError("assessment artifact and investigation evidence identifiers differ")
    artifacts = {
        item["evidence_id"]: item
        for item in record["evidence_artifacts"]
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    swot_artifact = artifacts.get("NASA-SWOT-RIVERSP-REACH-SCREEN")
    if swot_artifact is not None:
        pair_artifact = artifacts.get("SAR-RTC-S1-PAIR")
        if pair_artifact is None:
            raise ValueError("SWOT RiverSP screen is missing its linked SAR pair")
        try:
            swot_path = (evidence_root.resolve() / swot_artifact["relative_path"]).resolve()
            pair_path = (evidence_root.resolve() / pair_artifact["relative_path"]).resolve()
            swot_record = json.loads(swot_path.read_text(encoding="utf-8"))
            pair_record = json.loads(pair_path.read_text(encoding="utf-8"))
            validate_swot_riversp_screen(
                swot_record,
                pair_record=pair_record,
                case_id=str(record.get("case_id")),
                pair_record_sha256=str(pair_artifact.get("sha256")),
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, SwotRiverSpError) as exc:
            raise ValueError(f"SWOT RiverSP screen source link is invalid: {exc}") from exc
        if "SAR-RTC-S1-PAIR" not in swot_artifact.get("lineage", {}).get("derived_from_evidence_ids", []):
            raise ValueError("SWOT RiverSP search lineage omits the linked SAR AOI and acquisition window")
        water_hypothesis = next(
            (item for item in record.get("hypotheses", []) if item.get("id") == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"),
            None,
        )
        swot_relation = next(
            (
                item for item in water_hypothesis.get("evidence_assessments", [])
                if item.get("evidence_id") == "NASA-SWOT-RIVERSP-REACH-SCREEN"
            ),
            None,
        ) if isinstance(water_hypothesis, dict) else None
        if (
            swot_relation is None
            or swot_relation.get("relationship") != "LIMITS_INTERPRETATION"
            or "NASA-SWOT-RIVERSP-REACH-SCREEN" not in water_hypothesis.get("evidence_refs", [])
            or water_hypothesis.get("state") != "UNRESOLVED"
        ):
            raise ValueError("quality-limited SWOT context must only limit interpretation of the unresolved water hypothesis")
    if record.get("case_id") == "rio-grande-do-sul-cross-sensor-diagnostic-2024":
        soil_sources = {
            "NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN": validate_ecostress_availability_screen,
            "ISMN-SOIL-MOISTURE-STATION-COVERAGE": validate_ismn_station_screen,
        }
        linked_soil_sources = [(evidence_id, validator) for evidence_id, validator in soil_sources.items() if evidence_id in artifacts]
        if linked_soil_sources:
            pair_artifact = artifacts.get("SAR-RTC-S1-PAIR")
            optical_artifact = artifacts.get("NASA-OPERA-DSWX-HLS")
            if pair_artifact is None or optical_artifact is None:
                raise ValueError("T024 soil-moisture availability screen is missing the linked SAR pair or AOI record")
            try:
                pair_path = (evidence_root.resolve() / pair_artifact["relative_path"]).resolve()
                optical_path = (evidence_root.resolve() / optical_artifact["relative_path"]).resolve()
                pair_record = json.loads(pair_path.read_text(encoding="utf-8"))
                optical_record = json.loads(optical_path.read_text(encoding="utf-8"))
                for evidence_id, validator in linked_soil_sources:
                    source_path = (evidence_root.resolve() / artifacts[evidence_id]["relative_path"]).resolve()
                    source_record = json.loads(source_path.read_text(encoding="utf-8"))
                    validator(
                        source_record,
                        pair_record=pair_record,
                        optical_record=optical_record,
                        case_id=str(record["case_id"]),
                        evidence_root=evidence_root,
                    )
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"T024 soil-moisture source record is not reproducible: {exc}") from exc
    temporal_series_artifact = artifacts.get("NASA-OPERA-RTC-S1-TEMPORAL-SERIES")
    if temporal_series_artifact is not None:
        pair_artifact = artifacts.get("SAR-RTC-S1-PAIR")
        if pair_artifact is None:
            raise ValueError("OPERA temporal-series evidence is missing its linked SAR pair")
        try:
            series_path = (evidence_root.resolve() / temporal_series_artifact["relative_path"]).resolve()
            pair_path = (evidence_root.resolve() / pair_artifact["relative_path"]).resolve()
            series_record = json.loads(series_path.read_text(encoding="utf-8"))
            pair_record = json.loads(pair_path.read_text(encoding="utf-8"))
            series_validation = validate_opera_rtc_s1_series_record(series_record, pair_record=pair_record)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, OperaRtcS1AnalysisError) as exc:
            raise ValueError(f"OPERA temporal-series source link is invalid: {exc}") from exc
        observations_record = record.get("observations")
        recorded_series = (
            observations_record.get("sar_temporal_series")
            if isinstance(observations_record, dict)
            else None
        )
        recorded_direction_screen = (
            recorded_series.get("temporal_direction_screen")
            if isinstance(recorded_series, dict)
            else None
        )
        expected_direction_screen = series_validation["temporal_direction_screen"]
        if (
            (record.get("schema_version", 1) >= 2 and recorded_direction_screen is None)
            or (
                recorded_direction_screen is not None
                and recorded_direction_screen != expected_direction_screen
            )
        ):
            raise ValueError("OPERA temporal direction summary does not reproduce from its linked source series")
        if "SAR-RTC-S1-PAIR" not in temporal_series_artifact.get("lineage", {}).get("shares_source_observations_with", []):
            raise ValueError("OPERA temporal-series lineage must identify its shared SAR pair observations")
        water_hypothesis = next(
            (item for item in record.get("hypotheses", []) if item.get("id") == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"),
            None,
        )
        temporal_relation = next(
            (
                item for item in water_hypothesis.get("evidence_assessments", [])
                if item.get("evidence_id") == "NASA-OPERA-RTC-S1-TEMPORAL-SERIES"
            ),
            None,
        ) if isinstance(water_hypothesis, dict) else None
        if (
            temporal_relation is None
            or temporal_relation.get("relationship") != "DOES_NOT_DISTINGUISH"
            or "NASA-OPERA-RTC-S1-TEMPORAL-SERIES" not in water_hypothesis.get("evidence_refs", [])
            or water_hypothesis.get("state") != "UNRESOLVED"
        ):
            raise ValueError("OPERA temporal series must remain linked as non-distinguishing evidence to the unresolved water hypothesis")
    gpm_chronology_artifact = artifacts.get("NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY")
    water_hypothesis = next(
        (item for item in record.get("hypotheses", []) if item.get("id") == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"),
        None,
    )
    if gpm_chronology_artifact is not None and isinstance(water_hypothesis, dict) and any(
        item.get("evidence_id") == "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY"
        for item in water_hypothesis.get("evidence_assessments", [])
    ):
        rainfall_relation = next(
            (
                item for item in water_hypothesis.get("evidence_assessments", [])
                if item.get("evidence_id") == "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY"
            ),
            None,
        )
        if (
            rainfall_relation is None
            or rainfall_relation.get("relationship") != "DOES_NOT_DISTINGUISH"
            or "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY" not in water_hypothesis.get("evidence_refs", [])
            or water_hypothesis.get("state") != "UNRESOLVED"
        ):
            raise ValueError("GPM precipitation chronology must remain linked as non-distinguishing context to the unresolved water hypothesis")
    smap_l4_artifact = artifacts.get("NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN")
    if smap_l4_artifact is not None:
        soil_moisture_hypothesis = next(
            (item for item in record.get("hypotheses", []) if item.get("id") == "H3_SOIL_MOISTURE_CHANGE"),
            None,
        )
        l4_relation = next(
            (
                item for item in (soil_moisture_hypothesis or {}).get("evidence_assessments", [])
                if item.get("evidence_id") == "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN"
            ),
            None,
        )
        if (
            not isinstance(soil_moisture_hypothesis, dict)
            or l4_relation is None
            or l4_relation.get("relationship") != "DOES_NOT_DISTINGUISH"
            or "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN" not in soil_moisture_hypothesis.get("evidence_refs", [])
            or soil_moisture_hypothesis.get("state") != "UNRESOLVED"
            or soil_moisture_hypothesis.get("testability_state") != "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
        ):
            raise ValueError("SMAP L4 context must remain non-distinguishing and cannot resolve the soil-moisture hypothesis")
    acquisition_review_artifact = artifacts.get("NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW")
    if acquisition_review_artifact is not None:
        pair_artifact = artifacts.get("SAR-RTC-S1-PAIR")
        if pair_artifact is None:
            raise ValueError("acquisition-condition review is missing its linked SAR pair")
        try:
            review_path = (evidence_root.resolve() / acquisition_review_artifact["relative_path"]).resolve()
            review = json.loads(review_path.read_text(encoding="utf-8"))
            pair_path = (evidence_root.resolve() / pair_artifact["relative_path"]).resolve()
            pair = json.loads(pair_path.read_text(encoding="utf-8"))
            validate_acquisition_condition_review(
                review,
                pair_record=pair,
                pair_record_sha256=pair_artifact["sha256"],
                case_id=record.get("case_id"),
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"acquisition-condition review source link is invalid: {exc}") from exc
        if "SAR-RTC-S1-PAIR" not in acquisition_review_artifact.get("lineage", {}).get("derived_from_evidence_ids", []):
            raise ValueError("acquisition-condition review lineage omits its SAR pair source")
        h5 = next((item for item in record.get("hypotheses", []) if item.get("id") == "H5_ACQUISITION_CONDITIONS_EFFECT"), None)
        h5_refs = set(h5.get("evidence_refs", [])) if isinstance(h5, dict) else set()
        if "NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW" not in h5_refs:
            raise ValueError("acquisition-condition review is not linked to its hypothesis")
    modis_artifact = artifacts.get("NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN")
    if modis_artifact is not None:
        pair_artifact = artifacts.get("SAR-RTC-S1-PAIR")
        if pair_artifact is None:
            raise ValueError("MOD13Q1 screen is missing its linked SAR pair")
        try:
            screen_path = (evidence_root.resolve() / modis_artifact["relative_path"]).resolve()
            screen = json.loads(screen_path.read_text(encoding="utf-8"))
            pair_path = (evidence_root.resolve() / pair_artifact["relative_path"]).resolve()
            pair = json.loads(pair_path.read_text(encoding="utf-8"))
            validate_mod13q1_candidate_screen(
                screen,
                pair_record=pair,
                pair_record_sha256=pair_artifact["sha256"],
                case_id=record.get("case_id"),
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"MOD13Q1 screen source link is invalid: {exc}") from exc
        if "SAR-RTC-S1-PAIR" not in modis_artifact.get("lineage", {}).get("derived_from_evidence_ids", []):
            raise ValueError("MOD13Q1 screen lineage omits the AOI and timing source")
        h4 = next((item for item in record.get("hypotheses", []) if item.get("id") == "H4_VEGETATION_STATE_CHANGE"), None)
        h4_refs = set(h4.get("evidence_refs", [])) if isinstance(h4, dict) else set()
        if "NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN" not in h4_refs:
            raise ValueError("MOD13Q1 screen is not linked to the vegetation hypothesis")
    spatial_artifact = artifacts.get("NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT")
    if spatial_artifact is not None:
        try:
            spatial_path = (evidence_root.resolve() / spatial_artifact["relative_path"]).resolve()
            spatial_record = json.loads(spatial_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("spatial-support evidence record cannot be read") from exc
        sar_artifact = artifacts.get("SAR-RTC-S1-PAIR")
        optical_artifact = artifacts.get("NASA-OPERA-DSWX-HLS")
        spatial_sources = spatial_record.get("sources", {}) if isinstance(spatial_record, dict) else {}
        if (
            sar_artifact is None
            or optical_artifact is None
            or spatial_sources.get("sar_pair_record_sha256") != sar_artifact.get("sha256")
            or spatial_sources.get("optical_context_record_sha256") != optical_artifact.get("sha256")
        ):
            raise ValueError("spatial-support evidence does not reference the linked SAR and optical records")
    polarization_artifact = artifacts.get("NASA-OPERA-RTC-POLARIZATION-SENSITIVITY")
    if polarization_artifact is not None:
        vh_artifact = artifacts.get("NASA-OPERA-RTC-S1-VH-PAIR")
        vh_spatial_artifact = artifacts.get("NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT")
        vv_artifact = artifacts.get("SAR-RTC-S1-PAIR")
        optical_artifact = artifacts.get("NASA-OPERA-DSWX-HLS")
        if vh_artifact is None or vh_spatial_artifact is None or vv_artifact is None or optical_artifact is None:
            raise ValueError("polarization sensitivity is missing a linked source artifact")
        try:
            polarization_path = (evidence_root.resolve() / polarization_artifact["relative_path"]).resolve()
            polarization = json.loads(polarization_path.read_text(encoding="utf-8"))
            vh_path = (evidence_root.resolve() / vh_artifact["relative_path"]).resolve()
            vh_pair = json.loads(vh_path.read_text(encoding="utf-8"))
            vh_spatial_path = (evidence_root.resolve() / vh_spatial_artifact["relative_path"]).resolve()
            vh_spatial = json.loads(vh_spatial_path.read_text(encoding="utf-8"))
            vv_path = (evidence_root.resolve() / vv_artifact["relative_path"]).resolve()
            vv_pair = json.loads(vv_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("polarization sensitivity source records cannot be read") from exc
        sources = polarization.get("sources", {})
        summary = polarization.get("summary", {})
        expected_scenes = [
            item.get("scene_id")
            for item in vv_pair.get("source_products", {}).values()
        ]
        if (
            polarization.get("status") != "DIAGNOSTIC_SENSITIVITY_ONLY"
            or sources.get("vv_pair_record_sha256") != vv_artifact.get("sha256")
            or sources.get("vh_pair_record_sha256") != vh_artifact.get("sha256")
            or sources.get("optical_context_record_sha256") != optical_artifact.get("sha256")
            or sources.get("vv_spatial_record_sha256") != (spatial_artifact or {}).get("sha256")
            or sources.get("vh_spatial_record_sha256") != vh_spatial_artifact.get("sha256")
            or sources.get("sar_scene_ids") != expected_scenes
            or [item.get("scene_id") for item in vh_pair.get("source_products", {}).values()] != expected_scenes
            or vv_pair.get("measurement", {}).get("polarization") != "VV"
            or vh_pair.get("measurement", {}).get("polarization") != "VH"
            or vv_pair.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"
            or vh_pair.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"
            or vh_spatial.get("status") != "DIAGNOSTIC_SPATIAL_ASSOCIATION"
            or vh_spatial.get("sources", {}).get("sar_polarization") != "VH"
            or vh_spatial.get("sources", {}).get("sar_pair_record_sha256") != vh_artifact.get("sha256")
            or vh_spatial.get("sources", {}).get("optical_context_record_sha256") != optical_artifact.get("sha256")
            or vv_pair.get("provider_qa", {}).get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
            or vh_pair.get("provider_qa", {}).get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
            or isinstance(summary.get("common_cells"), bool)
            or not isinstance(summary.get("common_cells"), int)
            or summary.get("common_cells", 0) < 3
            or polarization.get("method", {}).get("minimum_common_valid_wtr_area_fraction") != 0.75
        ):
            raise ValueError("polarization sensitivity does not reference the linked VV, VH, and optical observations")
        for key in (
            "vv_pearson_r_water_change_vs_log_ratio",
            "vh_pearson_r_water_change_vs_log_ratio",
            "vv_vh_pearson_r_log_ratio",
        ):
            value = summary.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("polarization sensitivity metrics are invalid")
        if spatial_artifact is None:
            raise ValueError("polarization sensitivity does not reference the linked spatial-support evidence")
    hls_association_artifact = artifacts.get("NASA-HLS-L30-NDVI-SAR-ASSOCIATION")
    if hls_association_artifact is not None:
        hls_artifact = artifacts.get("NASA-HLS-L30-VEGETATION-SCREEN")
        sar_artifact = artifacts.get("SAR-RTC-S1-PAIR")
        if hls_artifact is None or sar_artifact is None:
            raise ValueError("HLS association is missing linked optical or SAR evidence")
        try:
            association_path = (evidence_root.resolve() / hls_association_artifact["relative_path"]).resolve()
            association = json.loads(association_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("HLS association record cannot be read") from exc
        sources = association.get("sources", {})
        if (
            association.get("status") != "DIAGNOSTIC_SPATIAL_ASSOCIATION"
            or sources.get("sar_pair_record_sha256") != sar_artifact.get("sha256")
            or sources.get("hls_vegetation_record_sha256") != hls_artifact.get("sha256")
        ):
            raise ValueError("HLS association does not reference the linked SAR and optical records")
        hls_context = record.get("observations", {}).get("hls_l30_vegetation_context", {})
        selected_sensitivity = [
            item for item in association.get("coverage_sensitivity", [])
            if isinstance(item, dict) and item.get("minimum_common_clear_land_ndvi_area_fraction") == 0.75
        ]
        if record.get("schema_version") >= 3 and (
            len(selected_sensitivity) != 1
            or hls_context.get("association_coverage_sensitivity") != association.get("coverage_sensitivity")
            or hls_context.get("association_at_75_percent_common_support") != selected_sensitivity[0]
        ):
            raise ValueError("HLS coverage sensitivity does not match its linked association source record")
    hls_s30_association_artifact = artifacts.get("NASA-HLS-S30-NDVI-SAR-ASSOCIATION")
    if hls_s30_association_artifact is not None:
        hls_s30_artifact = artifacts.get("NASA-HLS-S30-VEGETATION-SCREEN")
        sar_artifact = artifacts.get("SAR-RTC-S1-PAIR")
        if hls_s30_artifact is None or sar_artifact is None:
            raise ValueError("HLS S30 association is missing linked optical or SAR evidence")
        try:
            association_path = (evidence_root.resolve() / hls_s30_association_artifact["relative_path"]).resolve()
            association = json.loads(association_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("HLS S30 association record cannot be read") from exc
        sources = association.get("sources", {})
        if (
            association.get("record_type") != "ECHO_RTC_HLS_S30_NDVI_SPATIAL_ASSOCIATION"
            or association.get("status") != "DIAGNOSTIC_SPATIAL_ASSOCIATION"
            or sources.get("sar_pair_record_sha256") != sar_artifact.get("sha256")
            or sources.get("hls_vegetation_record_sha256") != hls_s30_artifact.get("sha256")
        ):
            raise ValueError("HLS S30 association does not reference the linked SAR and optical records")
        s30_context = record.get("observations", {}).get("hls_s30_vegetation_context", {})
        selected_sensitivity = [
            item for item in association.get("coverage_sensitivity", [])
            if isinstance(item, dict) and item.get("minimum_common_clear_land_ndvi_area_fraction") == 0.75
        ]
        if record.get("schema_version") >= 3 and (
            len(selected_sensitivity) != 1
            or s30_context.get("association_coverage_sensitivity") != association.get("coverage_sensitivity")
            or s30_context.get("association_at_75_percent_common_support") != selected_sensitivity[0]
        ):
            raise ValueError("HLS S30 coverage sensitivity does not match its linked association source record")
    if record.get("schema_version", 1) >= 3 and hls_association_artifact is None and hls_s30_association_artifact is None:
        raise ValueError("assessment schema 3 or later requires linked HLS coverage-sensitivity evidence")
    hls_candidate_artifact = artifacts.get("NASA-HLS-L30-EXTENDED-CANDIDATE-SCREEN")
    if record.get("schema_version") == 4 and hls_candidate_artifact is None:
        raise ValueError("assessment schema 4 requires its supplemental HLS candidate screen")
    if hls_candidate_artifact is not None:
        pair_artifact = artifacts.get("SAR-RTC-S1-PAIR")
        optical_artifact = artifacts.get("NASA-OPERA-DSWX-HLS")
        if (
            pair_artifact is None
            or optical_artifact is None
            or hls_candidate_artifact.get("role") != "NASA_HLS_CANDIDATE_COVERAGE_SCREEN"
            or "SAR-RTC-S1-PAIR" not in hls_candidate_artifact.get("lineage", {}).get("derived_from_evidence_ids", [])
        ):
            raise ValueError("supplemental HLS candidate screen is missing its non-directional role or linked case sources")
        try:
            candidate_path = (evidence_root.resolve() / hls_candidate_artifact["relative_path"]).resolve()
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            pair_path = (evidence_root.resolve() / pair_artifact["relative_path"]).resolve()
            pair = json.loads(pair_path.read_text(encoding="utf-8"))
            optical_path = (evidence_root.resolve() / optical_artifact["relative_path"]).resolve()
            optical = json.loads(optical_path.read_text(encoding="utf-8"))
            reproduced_summary = validate_hls_candidate_screen(
                candidate,
                pair_record=pair,
                case_id=record.get("case_id"),
                aoi_bounds=optical.get("aoi", {}).get("bounds_west_south_east_north"),
                evidence_root=evidence_root,
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"supplemental HLS candidate screen failed validation: {exc}") from exc
        if record.get("observations", {}).get("hls_l30_extended_candidate_screen") != reproduced_summary:
            raise ValueError("assessment HLS candidate summary does not reproduce from its linked screen")
        followup = next(
            (item for item in record.get("follow_up_evidence", []) if item.get("follow_up_id") == "F9_BETTER_SUPPORTED_VEGETATION_OBSERVATION"),
            None,
        )
        h4 = next((item for item in record.get("hypotheses", []) if item.get("id") == "H4_VEGETATION_STATE_CHANGE"), None)
        relation = next(
            (item for item in (h4 or {}).get("evidence_assessments", []) if item.get("evidence_id") == "NASA-HLS-L30-EXTENDED-CANDIDATE-SCREEN"),
            None,
        )
        if (
            not isinstance(followup, dict)
            or followup.get("availability_state") != "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
            or "NASA-HLS-L30-EXTENDED-CANDIDATE-SCREEN" not in followup.get("evidence_refs", [])
            or h4 is None
            or h4.get("state") != "UNRESOLVED"
            or relation is None
            or relation.get("relationship") != "LIMITS_INTERPRETATION"
        ):
            raise ValueError("supplemental HLS screen must remain a non-directional limit in the open vegetation follow-up")
    guaiba_artifact = artifacts.get("ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY")
    if guaiba_artifact is not None:
        try:
            guaiba_path = (evidence_root.resolve() / guaiba_artifact["relative_path"]).resolve()
            guaiba = json.loads(guaiba_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("ANA Guaíba context record cannot be read") from exc
        context = guaiba.get("reported_context", {})
        observations = record.get("observations", {})
        context_summary = observations.get("official_hydrologic_event_context")
        try:
            period = context.get("period_local_dates", {})
            period_start = date.fromisoformat(period.get("start_date"))
            period_end = date.fromisoformat(period.get("end_date"))
            sar = observations.get("sar_diagnostic_measurement", {})
            acquisition_dates = [
                date.fromisoformat(sar.get("acquisition_before_utc", "")[:10]),
                date.fromisoformat(sar.get("acquisition_after_utc", "")[:10]),
            ]
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("ANA Guaíba period or linked SAR acquisition dates are invalid") from exc
        h2 = next(
            (item for item in record.get("hypotheses", []) if isinstance(item, dict) and item.get("id") == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"),
            None,
        )
        h2_links = [
            item for item in (h2 or {}).get("evidence_assessments", [])
            if isinstance(item, dict) and item.get("evidence_id") == "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY"
        ]
        if (
            guaiba_artifact.get("role") != "OFFICIAL_HYDROLOGIC_EVENT_CONTEXT"
            or guaiba.get("case_id") != record.get("case_id")
            or guaiba.get("source", {}).get("provider") != "Agência Nacional de Águas e Saneamento Básico (ANA)"
            or guaiba.get("source", {}).get("url") != "https://conjuntura2025.ana.gov.br/agua-e-clima.html"
            or context.get("station_code") != "87444000"
            or context.get("timestamped_readings_retrieved") is not False
            or context.get("above_flood_stage") is not True
            or not isinstance(context.get("reported_duration_days"), int)
            or context.get("reported_duration_days") != 30
            or len(acquisition_dates) != 2
            or not all(period_start <= acquired <= period_end for acquired in acquisition_dates)
            or not isinstance(context_summary, dict)
            or context_summary.get("station_code") != context.get("station_code")
            or context_summary.get("above_flood_stage") is not True
            or context_summary.get("period_local_dates") != period
            or context_summary.get("reported_duration_days") != context.get("reported_duration_days")
            or context_summary.get("timestamped_readings_retrieved") is not False
            or len(h2_links) != 1
            or h2_links[0].get("relationship") != "DOES_NOT_DISTINGUISH"
        ):
            raise ValueError("ANA Guaíba context must remain narrative-only, case-linked, and nondiscriminating")
    return evidence_ids


def _assessment_integrity_impact(
    record: dict[str, object], evidence_root: Path
) -> dict[str, object] | None:
    """Identify investigation items affected by changed linked source records.

    This report is diagnostic only. It never validates or serves a changed
    artifact as evidence and does not revise the retained assessment.
    """
    artifacts = record.get("evidence_artifacts")
    if not isinstance(artifacts, list):
        return None
    root = evidence_root.resolve()
    by_id = {
        item.get("evidence_id"): item
        for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    issues: list[dict[str, object]] = []

    def nested_asset_references(value: object) -> list[dict[str, object]]:
        references: list[dict[str, object]] = []

        def visit(node: object) -> None:
            if isinstance(node, dict):
                if isinstance(node.get("relative_path"), str) and isinstance(node.get("sha256"), str):
                    references.append(node)
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)

        visit(value)
        return references

    for evidence_id, artifact in by_id.items():
        relative_path = artifact.get("relative_path")
        expected_hash = artifact.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
            continue
        candidate = Path(relative_path)
        if candidate.is_absolute():
            state = "UNSAFE_PATH"
            observed_hash = None
        else:
            artifact_path = (root / candidate).resolve()
            if not artifact_path.is_relative_to(root):
                state = "UNSAFE_PATH"
                observed_hash = None
            else:
                try:
                    if not artifact_path.is_file():
                        state = "MISSING"
                        observed_hash = None
                    elif artifact_path.stat().st_size > _MAX_LINKED_EVIDENCE_ARTIFACT_BYTES:
                        state = "SIZE_LIMIT_EXCEEDED"
                        observed_hash = None
                    else:
                        payload = artifact_path.read_bytes()
                        observed_hash = sha256(payload).hexdigest()
                        source = None
                        if observed_hash != expected_hash:
                            state = "CHECKSUM_MISMATCH"
                        else:
                            try:
                                source = json.loads(payload)
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                source = None
                            state = (
                                "IDENTITY_MISMATCH"
                                if not isinstance(source, dict)
                                or source.get("record_type") != artifact.get("record_type")
                                or source.get("status") != artifact.get("status")
                                else "VERIFIED"
                            )
                        if state == "VERIFIED":
                            try:
                                source = json.loads(payload)
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                source = None
                except OSError:
                    state = "UNREADABLE"
                    observed_hash = None
        if state != "VERIFIED":
            issues.append({
                "evidence_id": evidence_id,
                "role": artifact.get("role"),
                "integrity_state": state,
                "expected_sha256": expected_hash,
                "observed_sha256": observed_hash,
            })
            continue

        if not isinstance(source, dict):
            continue
        expected_type = artifact.get("record_type")
        if expected_type in {
            "ECHO_GPM_IMERG_DAILY_CONTEXT",
            "ECHO_SMAP_SENTINEL_SOIL_MOISTURE_CANDIDATE_SCREEN",
            "ECHO_SMAP_L4_REGIONAL_SOIL_MOISTURE_CONTEXT_SCREEN",
        }:
            nested_limit = 2 * 1024 * 1024
        elif expected_type in {
            "ECHO_HLS_L30_VEGETATION_CONTEXT_SCREEN",
            "ECHO_HLS_S30_VEGETATION_CONTEXT_SCREEN",
        }:
            nested_limit = 64 * 1024 * 1024
        else:
            nested_limit = _MAX_LINKED_EVIDENCE_ARTIFACT_BYTES
        for asset in nested_asset_references(source):
            asset_path_text = asset["relative_path"]
            asset_path = Path(asset_path_text)
            asset_expected_hash = asset["sha256"]
            asset_size_expected = asset.get("size_bytes")
            state = "VERIFIED"
            asset_observed_hash: str | None = None
            if asset_path.is_absolute():
                state = "UNSAFE_NESTED_PATH"
            else:
                resolved_asset = (root / asset_path).resolve()
                if not resolved_asset.is_relative_to(root):
                    state = "UNSAFE_NESTED_PATH"
                else:
                    try:
                        if not resolved_asset.is_file():
                            state = "NESTED_ASSET_MISSING"
                        else:
                            asset_size = resolved_asset.stat().st_size
                            if asset_size > nested_limit:
                                state = "NESTED_ASSET_SIZE_LIMIT_EXCEEDED"
                            elif isinstance(asset_size_expected, int) and asset_size != asset_size_expected:
                                state = "NESTED_ASSET_SIZE_MISMATCH"
                            else:
                                asset_observed_hash = sha256(resolved_asset.read_bytes()).hexdigest()
                                if asset_observed_hash != asset_expected_hash:
                                    state = "NESTED_ASSET_CHECKSUM_MISMATCH"
                    except OSError:
                        state = "NESTED_ASSET_UNREADABLE"
            if state != "VERIFIED":
                issues.append({
                    "evidence_id": evidence_id,
                    "role": artifact.get("role"),
                    "asset_path": asset_path_text,
                    "integrity_state": state,
                    "expected_sha256": asset_expected_hash,
                    "observed_sha256": asset_observed_hash,
                })
    if not issues:
        return None

    affected_ids = {item["evidence_id"] for item in issues}
    changed = True
    while changed:
        changed = False
        for evidence_id, artifact in by_id.items():
            lineage = artifact.get("lineage", {})
            derived = lineage.get("derived_from_evidence_ids", []) if isinstance(lineage, dict) else []
            derived_ids = {value for value in derived if isinstance(value, str)} if isinstance(derived, list) else set()
            if evidence_id not in affected_ids and affected_ids.intersection(derived_ids):
                affected_ids.add(evidence_id)
                changed = True

    affected_hypotheses = []
    hypothesis_ids: set[str] = set()
    hypotheses = record.get("hypotheses", [])
    if isinstance(hypotheses, list):
        for hypothesis in hypotheses:
            if not isinstance(hypothesis, dict):
                continue
            refs = hypothesis.get("evidence_refs", [])
            refs = {value for value in refs if isinstance(value, str)} if isinstance(refs, list) else set()
            if not affected_ids.intersection(refs):
                continue
            hypothesis_id = hypothesis.get("id")
            if isinstance(hypothesis_id, str):
                hypothesis_ids.add(hypothesis_id)
            affected_hypotheses.append({
                "hypothesis_id": hypothesis_id,
                "statement": hypothesis.get("statement"),
                "state": hypothesis.get("state"),
                "affected_evidence_ids": sorted(affected_ids.intersection(refs)),
            })

    affected_followups = []
    followups = record.get("follow_up_evidence", [])
    if isinstance(followups, list):
        for followup in followups:
            if not isinstance(followup, dict):
                continue
            refs = followup.get("evidence_refs", [])
            targets = followup.get("target_hypothesis_ids", [])
            refs = {value for value in refs if isinstance(value, str)} if isinstance(refs, list) else set()
            targets = {value for value in targets if isinstance(value, str)} if isinstance(targets, list) else set()
            touched_evidence = affected_ids.intersection(refs)
            touched_hypotheses = hypothesis_ids.intersection(targets)
            if touched_evidence or touched_hypotheses:
                affected_followups.append({
                    "follow_up_id": followup.get("follow_up_id"),
                    "action": followup.get("action"),
                    "affected_evidence_ids": sorted(touched_evidence),
                    "affected_hypothesis_ids": sorted(touched_hypotheses),
                })

    return {
        "record_type": "ECHO_INVESTIGATION_EVIDENCE_INTEGRITY_IMPACT",
        "status": "REASSESSMENT_REQUIRED",
        "interpretation_limit": (
            "The prior assessment is not current for affected items. Changed or missing source records "
            "were not accepted as evidence. Restore the expected source or rebuild and review the assessment."
        ),
        "changed_evidence": issues,
        "affected_evidence_ids": sorted(affected_ids),
        "affected_hypotheses": affected_hypotheses,
        "affected_follow_ups": affected_followups,
    }


def _validated_case_source_context(
    case_path: Path,
    active_case_id: str,
    draft: dict[str, object],
    evidence_root: Path,
    *,
    require_unassessed: bool = True,
) -> dict[str, object]:
    """Load directly linked case sources only after validating the case assessment and exact SAR pair."""
    validate_investigation_draft(draft)
    if require_unassessed and draft.get("status") != "DRAFT_NOT_ASSESSED":
        raise ValueError("case evidence can only be imported into an unassessed draft")
    manifest_assessment_path = _case_evidence_path(case_path, "cross_sensor_assessment", evidence_root)
    if manifest_assessment_path is None or not manifest_assessment_path.is_file():
        return _validated_case_manifest_source_context(case_path, active_case_id, draft, evidence_root)
    try:
        assessment_bytes = manifest_assessment_path.read_bytes()
        assessment = json.loads(assessment_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("the selected case assessment cannot be read") from exc
    try:
        linked_ids = _validate_assessment_record(assessment, evidence_root)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"the selected case assessment failed validation: {exc}") from exc
    if assessment.get("case_id") != _case_identifier(case_path):
        raise ValueError("the selected case assessment identifier does not match the active case")

    draft_primary = next(
        artifact for artifact in draft["evidence_artifacts"]
        if artifact["role"] in {
            "SAR_PAIR_HELD_AT_PROVIDER_QA",
            "SAR_PAIR_HELD_AT_PRODUCT_MATURITY",
            "SAR_PAIR_HELD_AT_PRODUCT_IDENTITY",
            "DESCRIPTIVE_NISAR_SAR_MEASUREMENT",
            "DESCRIPTIVE_NISAR_SINGLE_OBSERVATION",
            "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_MEASUREMENT",
            "OPERA_PAIR_WITH_NO_COMMON_CLEAR_MEASUREMENT",
        }
    )
    pair_record_value = draft["source_records"][draft_primary["evidence_id"]]
    if isinstance(pair_record_value, str):
        try:
            pair_record = json.loads(pair_record_value)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise ValueError("draft SAR pair source JSON is invalid") from exc
    else:
        pair_record = pair_record_value
    if not isinstance(pair_record, dict):
        raise ValueError("draft SAR pair source record is invalid")
    if pair_record.get("record_type") != "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS":
        raise ValueError("case evidence import currently requires a matching OPERA RTC-S1 pair")
    case_artifacts = assessment.get("evidence_artifacts")
    if not isinstance(case_artifacts, list):
        raise ValueError("case assessment evidence list is invalid")
    pair_artifact = next((item for item in case_artifacts if item.get("evidence_id") == "SAR-RTC-S1-PAIR"), None)
    if not isinstance(pair_artifact, dict) or pair_artifact["evidence_id"] not in linked_ids:
        raise ValueError("validated case assessment has no primary SAR pair")
    source_root = evidence_root.resolve()
    pair_path = (source_root / pair_artifact["relative_path"]).resolve()
    if not pair_path.is_relative_to(source_root):
        raise ValueError("case SAR pair path escapes the project root")
    try:
        case_pair = json.loads(pair_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("validated case SAR pair cannot be read") from exc
    draft_products = pair_record.get("source_products", {})
    case_products = case_pair.get("source_products", {})
    draft_scenes = [draft_products.get(role, {}).get("scene_id") for role in ("before", "after")]
    case_scenes = [case_products.get(role, {}).get("scene_id") for role in ("before", "after")]
    if not all(isinstance(value, str) and value for value in draft_scenes) or draft_scenes != case_scenes:
        raise ValueError("case evidence does not match the exact before/after SAR scene identifiers in this draft")

    options: list[dict[str, object]] = []
    records_by_id: dict[str, dict[str, object]] = {}
    for artifact in case_artifacts:
        if not isinstance(artifact, dict) or artifact.get("evidence_id") == "SAR-RTC-S1-PAIR":
            continue
        lineage = artifact.get("lineage", {})
        if (
            not isinstance(lineage, dict)
            or lineage.get("derived_from_evidence_ids", [])
            or lineage.get("shares_source_observations_with", [])
        ):
            continue
        evidence_id = artifact.get("evidence_id")
        if not isinstance(evidence_id, str) or evidence_id not in linked_ids:
            continue
        relative_path = artifact.get("relative_path")
        if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
            continue
        source_path = (source_root / relative_path).resolve()
        if not source_path.is_relative_to(source_root):
            continue
        try:
            payload = source_path.read_bytes()
            source_record = json.loads(payload)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if (
            not isinstance(source_record, dict)
            or sha256(payload).hexdigest() != artifact.get("sha256")
            or source_record.get("record_type") != artifact.get("record_type")
            or source_record.get("status") != artifact.get("status")
        ):
            continue
        options.append({
            "evidence_id": evidence_id,
            "role": artifact.get("role"),
            "record_type": artifact.get("record_type"),
            "status": artifact.get("status"),
        })
        records_by_id[evidence_id] = {
            "artifact": artifact,
            "relative_path": relative_path,
            "source_sha256": sha256(payload).hexdigest(),
            "source_json": payload.decode("utf-8"),
            "source_record": source_record,
        }
    return {
        "import_mode": "VALIDATED_CASE_ASSESSMENT",
        "active_case_id": active_case_id,
        "case_id": assessment["case_id"],
        "assessment": assessment,
        "assessment_relative_path": manifest_assessment_path.resolve().relative_to(source_root).as_posix(),
        "assessment_sha256": sha256(assessment_bytes).hexdigest(),
        "options": options,
        "records_by_id": records_by_id,
    }


def _validated_case_manifest_source_context(
    case_path: Path,
    active_case_id: str,
    draft: dict[str, object],
    evidence_root: Path,
) -> dict[str, object]:
    """Validate source records from a case manifest when no linked assessment exists."""
    source_root = evidence_root.resolve()
    review_path = case_path.with_name("case-review.json").resolve()
    if not review_path.is_relative_to(source_root):
        raise ValueError("case review path escapes the project root")
    try:
        review_bytes = review_path.read_bytes()
        review = json.loads(review_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("the selected case has no readable source manifest") from exc
    manifest = review.get("case_source_manifest") if isinstance(review, dict) else None
    if (
        not isinstance(manifest, dict)
        or manifest.get("record_type") != "ECHO_CASE_SOURCE_MANIFEST"
        or manifest.get("schema_version") != 1
        or manifest.get("case_id") != active_case_id
    ):
        raise ValueError("the selected case has no supported source manifest")

    primary_artifacts = [
        artifact for artifact in draft.get("evidence_artifacts", [])
        if isinstance(artifact, dict) and artifact.get("role") == "DESCRIPTIVE_NISAR_SINGLE_OBSERVATION"
    ]
    if len(primary_artifacts) != 1:
        raise ValueError("case source manifest import requires one NISAR single-observation draft")
    primary_artifact = primary_artifacts[0]
    primary_id = primary_artifact.get("evidence_id")
    primary_value = draft.get("source_records", {}).get(primary_id)
    if isinstance(primary_value, str):
        try:
            primary_record = json.loads(primary_value)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise ValueError("draft NISAR observation source JSON is invalid") from exc
    else:
        primary_record = primary_value
    if (
        not isinstance(primary_record, dict)
        or primary_record.get("record_type") != "ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW"
        or primary_record.get("scientific_disposition") != "QA_HELD_DIAGNOSTIC_PREVIEW"
    ):
        raise ValueError("case source manifest import requires the retained QA-held NISAR diagnostic preview")
    scene_id = primary_record.get("source", {}).get("scene_id")
    if not isinstance(scene_id, str) or manifest.get("primary_scene_id") != scene_id:
        raise ValueError("case source manifest does not match the exact NISAR scene in this draft")

    declared_sources = manifest.get("sources")
    if not isinstance(declared_sources, list) or not declared_sources:
        raise ValueError("case source manifest has no source entries")
    options: list[dict[str, object]] = []
    records_by_id: dict[str, dict[str, object]] = {}
    source_ids: set[str] = set()
    allowed_roles = {
        "NISAR_CATALOG_SCREEN_METADATA_ONLY",
        "NISAR_PROVIDER_QA_SCREEN_METADATA_ONLY",
        "NISAR_PROVIDER_QA_REPORT_METADATA_ONLY",
    }
    for entry in declared_sources:
        if not isinstance(entry, dict):
            raise ValueError("case source manifest contains an invalid source entry")
        source_id = entry.get("source_id")
        relative_path = entry.get("relative_path")
        expected_hash = entry.get("sha256")
        role = entry.get("role")
        record_type = entry.get("record_type")
        status = entry.get("status")
        related_scene_ids = entry.get("related_scene_ids")
        if (
            not isinstance(source_id, str) or not source_id or source_id in source_ids
            or not isinstance(relative_path, str) or Path(relative_path).is_absolute()
            or not isinstance(expected_hash, str) or len(expected_hash) != 64
            or any(character not in "0123456789abcdef" for character in expected_hash)
            or role not in allowed_roles
            or not isinstance(record_type, str) or not isinstance(status, str)
            or not isinstance(related_scene_ids, list) or scene_id not in related_scene_ids
        ):
            raise ValueError("case source manifest entry is incomplete or does not link the draft observation")
        source_path = (source_root / relative_path).resolve()
        if not source_path.is_relative_to(source_root):
            raise ValueError("case source manifest path escapes the project root")
        try:
            source_bytes = source_path.read_bytes()
            source_record = json.loads(source_bytes)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"case source record cannot be read: {source_id}") from exc
        digest = sha256(source_bytes).hexdigest()
        if (
            not isinstance(source_record, dict)
            or digest != expected_hash
            or source_record.get("record_type") != record_type
            or (source_record.get("status") or "SOURCE_STATUS_NOT_RECORDED") != status
        ):
            raise ValueError(f"case source record failed manifest checksum or identity validation: {source_id}")
        if role == "NISAR_CATALOG_SCREEN_METADATA_ONLY":
            scene_ids = {
                item.get("properties", {}).get("fileID")
                for item in source_record.get("features", [])
                if isinstance(item, dict) and isinstance(item.get("properties"), dict)
            }
        elif role == "NISAR_PROVIDER_QA_SCREEN_METADATA_ONLY":
            scene_ids = set(source_record.get("products", {}))
        else:
            report_scene = source_record.get("scene_id")
            scene_ids = {report_scene} if isinstance(report_scene, str) else set()
        if not set(related_scene_ids).issubset(scene_ids):
            raise ValueError(f"case source manifest scene links do not match source content: {source_id}")
        source_ids.add(source_id)
        options.append({
            "evidence_id": source_id,
            "role": role,
            "record_type": record_type,
            "status": status,
        })
        records_by_id[source_id] = {
            "entry": entry,
            "relative_path": relative_path,
            "source_sha256": digest,
            "source_json": source_bytes.decode("utf-8"),
            "source_record": source_record,
            "shared_observation_scene_ids": list(related_scene_ids),
        }
    return {
        "import_mode": "CASE_SOURCE_MANIFEST",
        "active_case_id": active_case_id,
        "case_id": active_case_id,
        "manifest": manifest,
        "manifest_relative_path": review_path.relative_to(source_root).as_posix(),
        "manifest_sha256": sha256(review_bytes).hexdigest(),
        "manifest_primary_scene_id": scene_id,
        "primary_evidence_id": primary_id,
        "options": options,
        "records_by_id": records_by_id,
    }


def _validate_draft_case_sources(draft: dict[str, object], context: dict[str, object]) -> None:
    records_by_id = context["records_by_id"]
    for artifact in draft.get("evidence_artifacts", []):
        if not isinstance(artifact, dict):
            continue
        method = artifact.get("ingest_method")
        if method not in {"VALIDATED_LOCAL_CASE_ASSESSMENT", "VALIDATED_LOCAL_CASE_SOURCE_MANIFEST"}:
            continue
        provenance = artifact.get("case_provenance")
        if not isinstance(provenance, dict):
            raise ValueError("draft case-source provenance is missing")
        original_id = provenance.get("source_evidence_id")
        bundle = records_by_id.get(original_id) if isinstance(original_id, str) else None
        if not isinstance(bundle, dict):
            raise ValueError("case source is no longer available in the current validated case record")
        if method == "VALIDATED_LOCAL_CASE_ASSESSMENT":
            if context.get("import_mode") != "VALIDATED_CASE_ASSESSMENT":
                raise ValueError("draft assessment-backed source does not match the active case source contract")
            assessment = context["assessment"]
            source_artifact = bundle["artifact"]
            expected = {
                "active_case_id": context["active_case_id"],
                "case_id": assessment["case_id"],
                "assessment_record_type": assessment["record_type"],
                "assessment_status": assessment["status"],
                "assessment_relative_path": context["assessment_relative_path"],
                "assessment_sha256": context["assessment_sha256"],
                "source_evidence_id": original_id,
                "source_relative_path": bundle["relative_path"],
                "source_sha256": bundle["source_sha256"],
                "source_record_type": source_artifact["record_type"],
                "source_status": source_artifact["status"],
                "source_role": source_artifact["role"],
                "source_content_sha256": bundle["source_sha256"],
            }
        else:
            if context.get("import_mode") != "CASE_SOURCE_MANIFEST":
                raise ValueError("draft manifest-backed source does not match the active case source contract")
            source_entry = bundle["entry"]
            expected = {
                "active_case_id": context["active_case_id"],
                "case_id": context["case_id"],
                "manifest_record_type": context["manifest"]["record_type"],
                "manifest_relative_path": context["manifest_relative_path"],
                "manifest_sha256": context["manifest_sha256"],
                "manifest_primary_scene_id": context["manifest_primary_scene_id"],
                "source_evidence_id": original_id,
                "source_relative_path": bundle["relative_path"],
                "source_sha256": bundle["source_sha256"],
                "source_record_type": source_entry["record_type"],
                "source_status": source_entry["status"],
                "source_role": source_entry["role"],
                "source_content_sha256": bundle["source_sha256"],
                "shared_observation_scene_ids": bundle["shared_observation_scene_ids"],
            }
        if any(provenance.get(key) != value for key, value in expected.items()):
            raise ValueError("draft case-source provenance no longer matches the current case manifest and source")
        if draft.get("source_records", {}).get(artifact.get("evidence_id")) != bundle["source_json"]:
            raise ValueError("embedded case source content differs from the current validated case record")


def make_handler(
    case_path: Path,
    *,
    evidence_root: Path = _PROJECT_ROOT,
    case_registry: dict[str, Path] | None = None,
    draft_store_dir: Path | None = None,
) -> type[BaseHTTPRequestHandler]:
    default_case_path = case_path.expanduser().resolve()
    registered_cases = case_registry or _discover_case_registry(default_case_path, evidence_root)
    registered_cases = {key: Path(value).expanduser().resolve() for key, value in registered_cases.items()}
    default_case_id = _case_identifier(default_case_path)
    if default_case_id not in registered_cases:
        registered_cases[default_case_id] = default_case_path
    draft_store = LocalDraftStore(draft_store_dir or default_draft_store_dir())

    class Handler(BaseHTTPRequestHandler):
        server_version = "ECHO/0.1"

        def _select_case(self) -> bool:
            query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
            requested = query.get("case_id", [default_case_id])
            if len(requested) != 1 or not requested[0]:
                self._send_json({"error": "Exactly one nonempty case_id is allowed"}, 400)
                return False
            case_id = requested[0]
            selected = registered_cases.get(case_id)
            if selected is None:
                self._send_json({"error": "Unknown investigation case"}, 404)
                return False
            self.case_id = case_id
            self.case_path = selected
            return True

        def _send_case_registry(self) -> None:
            cases = []
            for case_id, catalog_path in registered_cases.items():
                review = _read_case_review(catalog_path)
                event = review.get("event", {})
                event_name = event.get("name") if isinstance(event, dict) else None
                status = review.get("status") or review.get("review_status") or "CATALOG_ONLY"
                cases.append({
                    "case_id": case_id,
                    "name": event_name if isinstance(event_name, str) and event_name else case_id.replace("-", " "),
                    "status": status,
                    "status_label": review.get("status_label") or str(status).replace("_", " "),
                    "location_label": review.get("location_label", ""),
                    "has_investigation_assessment": _case_evidence_path(
                        catalog_path, "cross_sensor_assessment", evidence_root
                    ) is not None,
                })
            self._send_json({
                "record_type": "ECHO_LOCAL_CASE_REGISTRY",
                "default_case_id": default_case_id,
                "cases": cases,
            }, 200)

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            path = urlsplit(self.path).path
            if path == "/api/cases":
                self._send_case_registry()
                return
            if not self._select_case():
                return
            if path == "/api/investigation-drafts":
                self._list_local_investigation_drafts()
                return
            if path.startswith("/api/investigation-drafts/"):
                self._load_local_investigation_draft(path.rsplit("/", 1)[-1])
                return
            if path == "/api/case":
                self._send_case()
                return
            if path == "/api/qa":
                self._send_file(
                    self.case_path.with_name("qa-review.json"),
                    "application/json; charset=utf-8",
                )
                return
            if path == "/api/review":
                review_path = self.case_path.with_name("case-review.json")
                if not review_path.is_file():
                    review_path = self.case_path.with_name("qa-review.json")
                self._send_file(review_path, "application/json; charset=utf-8")
                return
            if path == "/api/qa-reports":
                self._send_qa_reports()
                return
            if path == "/api/dswx-context":
                self._send_case_evidence("dswx_context", _MAX_DSWX_CONTEXT_BYTES)
                return
            if path == "/api/cross-sensor-assessment":
                self._send_case_evidence("cross_sensor_assessment", _MAX_INVESTIGATION_ASSESSMENT_BYTES)
                return
            if path == "/api/opera-temporal-series":
                self._send_opera_temporal_series()
                return
            if path == "/api/investigation-evidence":
                query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                query.pop("case_id", None)
                if set(query) != {"evidence_id"} or len(query["evidence_id"]) != 1:
                    self._send_json({"error": "Exactly one evidence_id is required"}, 400)
                    return
                self._send_linked_assessment_artifact(query["evidence_id"][0])
                return
            if path == "/api/product-scope":
                query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                query.pop("case_id", None)
                if set(query) != {"record_type"} or len(query["record_type"]) != 1:
                    self._send_json({"error": "Exactly one record_type is required"}, 400)
                    return
                record_type = query["record_type"][0]
                if len(record_type) > 96:
                    self._send_json({"error": "record_type is too long"}, 400)
                    return
                profile = product_scope_for_record_type(record_type)
                if profile is None:
                    self._send_json({"error": "No registered product scope for this record type"}, 404)
                    return
                self._send_json({
                    "record_type": "ECHO_PRODUCT_SCOPE_GUIDE",
                    "schema_version": 1,
                    "profile": profile,
                    "interpretation_limit": (
                        "This guide describes product-level data and ECHO method coverage only. "
                        "It does not assess the linked acquisition's QA, suitability, or conclusions."
                    ),
                }, 200)
                return
            if path in {"/", "/index.html"}:
                self._send_file(_STATIC / "index.html", "text/html; charset=utf-8")
                return
            if path == "/styles.css":
                self._send_file(_STATIC / "styles.css", "text/css; charset=utf-8")
                return
            if path == "/context.css":
                self._send_file(_STATIC / "context.css", "text/css; charset=utf-8")
                return
            if path == "/product-scope.css":
                self._send_file(_STATIC / "product-scope.css", "text/css; charset=utf-8")
                return
            if path == "/app.js":
                self._send_file(_STATIC / "app.js", "text/javascript; charset=utf-8")
                return
            if path == "/investigation.js":
                self._send_file(_STATIC / "investigation.js", "text/javascript; charset=utf-8")
                return
            if path == "/eesar-systems-horizontal.jpg":
                self._send_file(_STATIC / "eesar-systems-horizontal.jpg", "image/jpeg")
                return
            self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if not self._select_case():
                return
            path = urlsplit(self.path).path
            if path == "/api/gunw-catalog":
                self._search_gunw_catalog()
                return
            if path == "/api/opera-catalog":
                self._search_opera_catalog()
                return
            if path == "/api/bhoonidhi-catalog":
                self._search_bhoonidhi_catalog()
                return
            if path == "/api/gcov-preview":
                self._build_gcov_preview()
                return
            if path == "/api/gcov-pair-analysis":
                self._build_gcov_pair_analysis()
                return
            if path == "/api/opera-pair-analysis":
                self._build_opera_pair_analysis()
                return
            if path == "/api/investigation-draft":
                self._build_investigation_draft()
                return
            if path == "/api/investigation-drafts":
                self._save_local_investigation_draft()
                return
            if path == "/api/investigation-drafts/revise":
                self._revise_local_investigation_draft()
                return
            if path == "/api/investigation-draft/restore":
                self._restore_investigation_draft()
                return
            if path == "/api/investigation-draft/screen-followup":
                self._screen_investigation_followup()
                return
            if path == "/api/investigation-draft/attach-source":
                self._attach_investigation_draft_source()
                return
            if path == "/api/investigation-draft/attach-catalog-screen":
                self._attach_investigation_followup_catalog_screen()
                return
            if path == "/api/investigation-draft/attach-catalog-failure":
                self._attach_investigation_followup_catalog_failure()
                return
            if path == "/api/investigation-draft/attach-provider-qa":
                self._attach_investigation_followup_provider_qa()
                return
            if path == "/api/investigation-draft/import-case-evidence":
                self._import_case_evidence_into_draft()
                return
            if path == "/api/investigation-draft/assess":
                self._assess_investigation_draft()
                return
            if path == "/api/qa-summary":
                self._retrieve_qa_summary()
                return
            if path == "/api/qa-evidence-export":
                self._export_qa_evidence()
                return
            if path == "/api/investigation-counterfactual-preview":
                self._preview_counterfactual_reassessment()
                return
            if path != "/api/catalog":
                self.send_error(404)
                return
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_CATALOG_REQUEST_BYTES:
                self._send_json({"error": "Catalog query body is too large"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "Catalog query must be valid JSON"}, 400)
                return
            required_fields = {
                "longitude",
                "latitude",
                "start_date",
                "end_date",
                "maturity",
            }
            if not isinstance(payload, dict) or set(payload) not in (
                required_fields,
                required_fields | {"bounds_wgs84"},
            ):
                self._send_json({"error": "Catalog query fields are invalid"}, 400)
                return

            query = CatalogQuery(
                longitude=payload["longitude"],
                latitude=payload["latitude"],
                start_date=payload["start_date"],
                end_date=payload["end_date"],
                maturity=payload["maturity"],
                max_results=MAX_GCOV_CATALOG_RESULTS,
                bounds_wgs84=payload.get("bounds_wgs84"),
            )
            try:
                query.validate()
            except CatalogQueryError as exc:
                self._send_json({"error": str(exc)}, 400)
                return
            attempted_at_utc = datetime.now(timezone.utc)
            try:
                features = search_gcov(query)
                record = build_catalog_record(query, features)
            except CatalogQueryError:
                completed_at_utc = datetime.now(timezone.utc)
                self._send_json(
                    {
                        "error": "ASF catalog search failed; try again later",
                        "failure_record": {
                            "schema_version": 1,
                            "observer": "ECHO",
                            "provider": "ASF",
                            "service": "ASF_CMR_GCOV_CATALOG",
                            "outcome": "REQUEST_FAILED_NO_RESULT",
                            "failure_code": "CATALOG_REQUEST_FAILED",
                            "retryable": True,
                            "attempted_at_utc": attempted_at_utc.isoformat(),
                            "completed_at_utc": completed_at_utc.isoformat(),
                            "query": {
                                "dataset": "NISAR",
                                "processing_level": "GCOV",
                                "data_maturity": query.maturity,
                                "longitude": query.longitude,
                                "latitude": query.latitude,
                                "bounds_wgs84": list(query.bounds_wgs84) if query.bounds_wgs84 else None,
                                "start_date": query.start_date,
                                "end_date": query.end_date,
                                "result_limit": query.max_results,
                            },
                        },
                    },
                    502,
                )
                return
            self._send_json(record, 200)

        def _search_bhoonidhi_catalog(self) -> None:
            """Proxy one bounded catalog search from a same-origin loopback session."""
            try:
                bind_ip = ipaddress.ip_address(self.server.server_address[0])
                client_ip = ipaddress.ip_address(self.client_address[0])
                request_host = self.headers.get("Host", "")
                host_parts = urlsplit(f"http://{request_host}")
                origin = urlsplit(self.headers.get("Origin", ""))
                origin_name = origin.hostname or ""
                origin_loopback = origin_name == "localhost" or ipaddress.ip_address(
                    origin_name
                ).is_loopback
                origin_port = origin.port
                host_port = host_parts.port
            except (ValueError, TypeError):
                self._send_json({"error": "Bhoonidhi search requires a local same-origin session"}, 403)
                return
            if (
                not bind_ip.is_loopback
                or not client_ip.is_loopback
                or origin.scheme != "http"
                or not origin_loopback
                or origin.netloc.lower() != request_host.lower()
                or origin_port != host_port
            ):
                self._send_json(
                    {"error": "Bhoonidhi credentials are accepted only from the local ECHO interface"},
                    403,
                )
                return
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_BHOONIDHI_REQUEST_BYTES:
                self._send_json({"error": "Bhoonidhi search request body is too large"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "Bhoonidhi search request must be valid JSON"}, 400)
                return
            expected_fields = {
                "user_id", "password", "bounds_wgs84", "start", "end", "limit", "max_pages"
            }
            if not isinstance(payload, dict) or set(payload) != expected_fields:
                self._send_json({"error": "Bhoonidhi search request fields are invalid"}, 400)
                return
            if (
                not isinstance(payload["user_id"], str)
                or not payload["user_id"].strip()
                or len(payload["user_id"]) > 256
                or not isinstance(payload["password"], str)
                or not payload["password"]
                or len(payload["password"]) > 1024
                or not isinstance(payload["start"], str)
                or not isinstance(payload["end"], str)
                or not isinstance(payload["bounds_wgs84"], list)
                or not isinstance(payload["limit"], int)
                or isinstance(payload["limit"], bool)
                or not isinstance(payload["max_pages"], int)
                or isinstance(payload["max_pages"], bool)
            ):
                self._send_json({"error": "Bhoonidhi search parameters are invalid"}, 400)
                return
            bounds = payload["bounds_wgs84"]
            if (
                len(bounds) != 4
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    for value in bounds
                )
                or not (
                    -180 <= bounds[0] < bounds[2] <= 180
                    and -90 <= bounds[1] < bounds[3] <= 90
                )
                or not 1 <= payload["limit"] <= 500
                or not 1 <= payload["max_pages"] <= 20
            ):
                self._send_json({"error": "Bhoonidhi bounds or result limits are invalid"}, 400)
                return
            try:
                start = datetime.fromisoformat(payload["start"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(payload["end"].replace("Z", "+00:00"))
            except ValueError:
                self._send_json({"error": "Bhoonidhi dates must be timezone-aware ISO timestamps"}, 400)
                return
            if start.tzinfo is None or end.tzinfo is None or start > end:
                self._send_json({"error": "Bhoonidhi dates must be ordered and timezone-aware"}, 400)
                return
            user_id = payload["user_id"]
            password = payload["password"]
            try:
                token = authenticate(user_id, password)
            except BhoonidhiError as exc:
                status = 401 if "HTTP 401" in str(exc) else 502
                self._send_json({"error": str(exc)}, status)
                return
            finally:
                payload["user_id"] = ""
                payload["password"] = ""
                password = ""
            try:
                record = search_ssar_gcov(
                    token,
                    bounds_wgs84=payload["bounds_wgs84"],
                    start=payload["start"],
                    end=payload["end"],
                    limit=payload["limit"],
                    max_pages=payload["max_pages"],
                )
            except BhoonidhiError as exc:
                status = 401 if "HTTP 401" in str(exc) else 502
                self._send_json({"error": str(exc)}, status)
                return
            finally:
                token = ""
                user_id = ""
            self._send_json(record, 200)

        def _build_gcov_preview(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_GCOV_PREVIEW_REQUEST_BYTES:
                self._send_json({"error": "GCOV preview request body is too large"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "GCOV preview request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {
                "feature",
                "bounds_wgs84",
                "frequency",
                "layer",
            }:
                self._send_json({"error": "GCOV preview request fields are invalid"}, 400)
                return
            feature = payload["feature"]
            if (
                not isinstance(feature, dict)
                or set(feature) != {"properties"}
                or not isinstance(feature["properties"], dict)
            ):
                self._send_json({"error": "NISAR GCOV catalog feature is invalid"}, 400)
                return
            properties = feature["properties"]
            required = {"fileID", "url", "processingLevel", "collectionName"}
            allowed = required | {
                "startTime",
                "stopTime",
                "crid",
                "orbit",
                "productionConfiguration",
                "pathNumber",
                "frameNumber",
                "frameCoverage",
                "flightDirection",
                "mainBandPolarization",
                "sideBandPolarization",
                "rangeBandwidth",
            }
            if (
                not required.issubset(properties)
                or not set(properties).issubset(allowed)
                or any(not isinstance(properties[key], str) for key in required)
            ):
                self._send_json({"error": "NISAR GCOV catalog feature fields are invalid"}, 400)
                return
            try:
                record = build_gcov_preview(
                    feature,
                    bounds_wgs84=payload["bounds_wgs84"],
                    frequency=payload["frequency"],
                    layer=payload["layer"],
                )
            except (GcovPreviewError, NisarAccessError) as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except Exception as exc:
                self.log_error("GCOV preview failed: %s", type(exc).__name__)
                self._send_json(
                    {"error": "GCOV preview could not be retrieved or transformed"},
                    502,
                )
                return
            self._send_json(record, 200)

        def _build_gcov_pair_analysis(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_GCOV_PAIR_REQUEST_BYTES:
                self._send_json({"error": "GCOV pair request body is too large"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "GCOV pair request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {
                "before",
                "after",
                "bounds_wgs84",
                "frequency",
                "layer",
            }:
                self._send_json({"error": "GCOV pair request fields are invalid"}, 400)
                return
            feature_fields = {
                "fileID",
                "url",
                "processingLevel",
                "collectionName",
                "startTime",
                "stopTime",
                "crid",
                "orbit",
                "productionConfiguration",
                "pathNumber",
                "frameNumber",
                "frameCoverage",
                "flightDirection",
                "mainBandPolarization",
                "sideBandPolarization",
                "rangeBandwidth",
            }
            for role in ("before", "after"):
                feature = payload[role]
                if (
                    not isinstance(feature, dict)
                    or set(feature) != {"properties"}
                    or not isinstance(feature["properties"], dict)
                    or not {
                        "fileID",
                        "url",
                        "processingLevel",
                        "collectionName",
                    }.issubset(feature["properties"])
                    or not set(feature["properties"]).issubset(feature_fields)
                ):
                    self._send_json(
                        {"error": f"{role} NISAR GCOV catalog feature is invalid"},
                        400,
                    )
                    return
            try:
                record = build_gcov_pair_analysis(
                    payload["before"],
                    payload["after"],
                    bounds_wgs84=payload["bounds_wgs84"],
                    frequency=payload["frequency"],
                    layer=payload["layer"],
                )
            except GcovPairAnalysisError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except Exception as exc:
                self.log_error("GCOV pair analysis failed: %s", type(exc).__name__)
                self._send_json(
                    {"error": "GCOV pair analysis could not be completed"}, 502
                )
                return
            self._send_json(record, 200)

        def _build_investigation_draft(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_BYTES:
                self._send_json({"error": "Investigation draft request exceeds the 40 MiB limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Investigation draft request must be valid JSON"}, 400)
                return
            required_fields = {"source_record", "question", "hypotheses", "next_observation"}
            if not isinstance(payload, dict) or set(payload) not in (required_fields, required_fields | {"source_record_json"}):
                self._send_json({"error": "Investigation draft request fields are invalid"}, 400)
                return
            try:
                draft = build_investigation_draft(
                    payload["source_record"],
                    source_record_json=payload.get("source_record_json"),
                    question=payload["question"],
                    hypotheses=payload["hypotheses"],
                    next_observation=payload["next_observation"],
                )
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            self._send_json(draft, 200)

        def _restore_investigation_draft(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_ASSESS_BYTES:
                self._send_json({"error": "Saved draft exceeds the 40 MiB request limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Saved investigation draft must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {"draft"}:
                self._send_json({"error": "Saved draft request fields are invalid"}, 400)
                return
            draft = payload["draft"]
            try:
                validate_investigation_draft(draft)
                draft_store.verify_revision_parent(draft)
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except DraftStoreError as exc:
                self._send_json({"error": str(exc)}, 409)
                return
            if not self._validate_draft_case_links(draft):
                return
            self._send_json(draft, 200)

        def _validate_draft_case_links(self, draft: dict[str, object]) -> bool:
            if not any(
                isinstance(artifact, dict)
                and artifact.get("ingest_method") in {
                    "VALIDATED_LOCAL_CASE_ASSESSMENT",
                    "VALIDATED_LOCAL_CASE_SOURCE_MANIFEST",
                }
                for artifact in draft.get("evidence_artifacts", [])
            ):
                return True
            try:
                provenance = next(
                    artifact["case_provenance"]
                    for artifact in draft["evidence_artifacts"]
                    if isinstance(artifact, dict)
                    and artifact.get("ingest_method") in {
                        "VALIDATED_LOCAL_CASE_ASSESSMENT",
                        "VALIDATED_LOCAL_CASE_SOURCE_MANIFEST",
                    }
                )
                if provenance.get("active_case_id") != self.case_id:
                    raise ValueError("saved draft case evidence belongs to a different active case")
                context = _validated_case_source_context(
                    self.case_path, self.case_id, draft, evidence_root, require_unassessed=False
                )
                _validate_draft_case_sources(draft, context)
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return False
            except (OSError, TypeError, ValueError, KeyError, StopIteration) as exc:
                self._send_json({"error": str(exc)}, 409)
                return False
            return True

        def _list_local_investigation_drafts(self) -> None:
            if not self._is_loopback_client():
                self._send_json({"error": "Local investigation storage is available only over loopback"}, 403)
                return
            try:
                records = draft_store.list()
            except DraftStoreError as exc:
                self._send_json({"error": str(exc)}, 503)
                return
            self._send_json({"record_type": "ECHO_LOCAL_INVESTIGATION_DRAFTS", "records": records}, 200)

        def _load_local_investigation_draft(self, draft_id: str) -> None:
            if not self._is_loopback_client():
                self._send_json({"error": "Local investigation storage is available only over loopback"}, 403)
                return
            try:
                draft = draft_store.load(draft_id)
            except DraftStoreError as exc:
                self._send_json({"error": str(exc)}, 404)
                return
            if not self._validate_draft_case_links(draft):
                return
            self._send_json(draft, 200)

        def _save_local_investigation_draft(self) -> None:
            if not self._is_loopback_client():
                self._send_json({"error": "Local investigation storage is available only over loopback"}, 403)
                return
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_ASSESS_BYTES:
                self._send_json({"error": "Investigation draft exceeds the 40 MiB local storage request limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Investigation draft must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {"draft"}:
                self._send_json({"error": "Local draft save request fields are invalid"}, 400)
                return
            draft = payload["draft"]
            try:
                validate_investigation_draft(draft)
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            if not self._validate_draft_case_links(draft):
                return
            try:
                saved = draft_store.save(draft)
            except DraftStoreError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            self._send_json({"record_type": "ECHO_LOCAL_INVESTIGATION_DRAFT_SAVE", **saved}, 201)

        def _revise_local_investigation_draft(self) -> None:
            if not self._is_loopback_client():
                self._send_json({"error": "Local investigation storage is available only over loopback"}, 403)
                return
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_ASSESS_BYTES:
                self._send_json({"error": "Investigation revision request exceeds the 40 MiB limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Investigation revision request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) not in (
                {"parent_draft_id", "next_observation"},
                {"parent_draft_id", "next_observation", "question"},
            ):
                self._send_json({"error": "Investigation revision request fields are invalid"}, 400)
                return
            try:
                parent = draft_store.load(payload["parent_draft_id"])
                if not self._validate_draft_case_links(parent):
                    return
                revision = revise_investigation_draft(
                    parent,
                    next_observation=payload["next_observation"],
                    question=payload.get("question"),
                )
                if revision["revision"]["parent_draft_sha256"] != payload["parent_draft_id"]:
                    raise InvestigationDraftError("parent snapshot identifier does not match its canonical content")
                if not self._validate_draft_case_links(revision):
                    return
            except DraftStoreError as exc:
                self._send_json({"error": str(exc)}, 404)
                return
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except (OSError, TypeError, ValueError, KeyError, StopIteration) as exc:
                self._send_json({"error": str(exc)}, 409)
                return
            self._send_json(revision, 201)

        def _is_loopback_client(self) -> bool:
            try:
                return ipaddress.ip_address(self.client_address[0]).is_loopback
            except (ValueError, IndexError):
                return False

        def _screen_investigation_followup(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_ASSESS_BYTES:
                self._send_json({"error": "Draft follow-up screen exceeds the 40 MiB request limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Follow-up screen request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {
                "draft", "evidence_id", "gate_results", "review_basis", "limitations"
            }:
                self._send_json({"error": "Follow-up screen request fields are invalid"}, 400)
                return
            draft = payload["draft"]
            try:
                validate_investigation_draft(draft)
                if any(
                    isinstance(artifact, dict)
                    and artifact.get("ingest_method") in {
                        "VALIDATED_LOCAL_CASE_ASSESSMENT",
                        "VALIDATED_LOCAL_CASE_SOURCE_MANIFEST",
                    }
                    for artifact in draft.get("evidence_artifacts", [])
                ):
                    context = _validated_case_source_context(self.case_path, self.case_id, draft, evidence_root)
                    _validate_draft_case_sources(draft, context)
                updated = screen_followup_source(
                    draft,
                    evidence_id=payload["evidence_id"],
                    gate_results=payload["gate_results"],
                    review_basis=payload["review_basis"],
                    limitations=payload["limitations"],
                )
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except (OSError, TypeError, ValueError, KeyError, StopIteration) as exc:
                self._send_json({"error": str(exc)}, 409)
                return
            self._send_json(updated, 200)

        def _attach_investigation_draft_source(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_ATTACH_BYTES:
                self._send_json({"error": "Draft and attached source exceed the 40 MiB request limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Source attachment request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) not in (
                {"draft", "source_record"},
                {"draft", "source_record", "lineage"},
            ):
                self._send_json({"error": "Source attachment request fields are invalid"}, 400)
                return
            try:
                updated = attach_unreviewed_source(
                    payload["draft"],
                    payload["source_record"],
                    lineage=payload.get("lineage"),
                )
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            self._send_json(updated, 200)

        def _attach_investigation_followup_catalog_screen(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_ATTACH_BYTES:
                self._send_json({"error": "Draft and catalog response exceed the 40 MiB request limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Catalog-screen request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {"draft", "catalog_record"}:
                self._send_json({"error": "Catalog-screen request fields are invalid"}, 400)
                return
            try:
                updated = attach_followup_catalog_screen(payload["draft"], payload["catalog_record"])
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            self._send_json(updated, 200)

        def _attach_investigation_followup_catalog_failure(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_ATTACH_BYTES:
                self._send_json({"error": "Draft and failure record exceed the 40 MiB request limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Catalog-failure request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {"draft", "failure_record"}:
                self._send_json({"error": "Catalog-failure request fields are invalid"}, 400)
                return
            try:
                updated = attach_followup_catalog_failure(payload["draft"], payload["failure_record"])
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            self._send_json(updated, 200)

        def _attach_investigation_followup_provider_qa(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_ATTACH_BYTES:
                self._send_json({"error": "Draft and provider-QA record exceed the 40 MiB request limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Provider-QA attachment request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {
                "draft", "catalog_availability_evidence_id", "scene_id"
            }:
                self._send_json({"error": "Provider-QA attachment request fields are invalid"}, 400)
                return
            try:
                feature = followup_catalog_candidate(
                    payload["draft"],
                    catalog_availability_evidence_id=payload["catalog_availability_evidence_id"],
                    scene_id=payload["scene_id"],
                )
                _validated_product(feature)
                qa_summary = read_qa_summary(feature, product_metadata={})
                provider_qa_record = {
                    "record_type": "ECHO_PROVIDER_QA_INSPECTION",
                    "record_version": 1,
                    "exported_at_utc": datetime.now(timezone.utc).isoformat(),
                    "source_catalog": {
                        "provider": "Alaska Satellite Facility DAAC",
                        "query": payload["draft"]["source_records"][payload["catalog_availability_evidence_id"]]["catalog_record"]["query"],
                        "feature": feature,
                    },
                    "provider_qa_summary": asdict(qa_summary),
                    "interpretation_limits": [
                        "Provider QA disposition is not an ECHO scientific suitability determination.",
                        "This inspection did not re-read product HDF5 identification metadata or radar measurement arrays.",
                        "The provider CSV does not establish valid study-area coverage, cross-date alignment, or event cause.",
                    ],
                }
                updated = attach_followup_provider_qa_screen(
                    payload["draft"],
                    catalog_availability_evidence_id=payload["catalog_availability_evidence_id"],
                    provider_qa_record=provider_qa_record,
                    retrieval_verified_at_attachment=True,
                )
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except QASummaryError as exc:
                self._send_json({"error": str(exc)}, 502)
                return
            except NisarAccessError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            self._send_json(updated, 200)

        def _import_case_evidence_into_draft(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_CASE_EVIDENCE_IMPORT_REQUEST_BYTES:
                self._send_json({"error": "Draft and case evidence request exceed the 40 MiB limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Case evidence import request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) not in ({"draft"}, {"draft", "evidence_id"}):
                self._send_json({"error": "Case evidence import request fields are invalid"}, 400)
                return
            try:
                context = _validated_case_source_context(self.case_path, self.case_id, payload["draft"], evidence_root)
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except (OSError, TypeError, ValueError, KeyError, StopIteration) as exc:
                self._send_json({"error": str(exc)}, 409)
                return
            if "evidence_id" not in payload:
                response = {
                    "record_type": "ECHO_VALIDATED_CASE_EVIDENCE_OPTIONS",
                    "status": "DIRECT_CASE_SOURCES_ONLY",
                    "import_mode": context["import_mode"],
                    "case_id": context["case_id"],
                    "options": context["options"],
                }
                if context["import_mode"] == "CASE_SOURCE_MANIFEST":
                    response.update({
                        "manifest_sha256": context["manifest_sha256"],
                        "interpretation_limit": (
                            "Options come from a local case source manifest whose exact paths, checksums, record identities, and scene links were validated. "
                            "These source records share the primary NISAR observation or its metadata; they are not independent corroboration. "
                            "Provider authenticity and source fitness are not established by these integrity checks."
                        ),
                    })
                else:
                    response.update({
                        "assessment_sha256": context["assessment_sha256"],
                        "interpretation_limit": "Options come from a case assessment whose linked artifacts and exact SAR scene IDs were validated. Records with declared derivation or shared-observation links are excluded; absence of recorded links does not establish independence. Provider authenticity and suitability for a new hypothesis are not implied.",
                    })
                self._send_json(response, 200)
                return
            evidence_id = payload["evidence_id"]
            bundle = context["records_by_id"].get(evidence_id) if isinstance(evidence_id, str) else None
            if not isinstance(bundle, dict):
                self._send_json({"error": "Selected evidence is not a direct validated source in this case"}, 404)
                return
            try:
                if context["import_mode"] == "CASE_SOURCE_MANIFEST":
                    source_entry = bundle["entry"]
                    provenance = {
                        "active_case_id": context["active_case_id"],
                        "case_id": context["case_id"],
                        "manifest_record_type": context["manifest"]["record_type"],
                        "manifest_relative_path": context["manifest_relative_path"],
                        "manifest_sha256": context["manifest_sha256"],
                        "manifest_primary_scene_id": context["manifest_primary_scene_id"],
                        "source_evidence_id": evidence_id,
                        "source_relative_path": bundle["relative_path"],
                        "source_sha256": bundle["source_sha256"],
                        "source_record_type": source_entry["record_type"],
                        "source_status": source_entry["status"],
                        "source_role": source_entry["role"],
                        "shared_observation_scene_ids": bundle["shared_observation_scene_ids"],
                    }
                    updated = attach_validated_case_source(
                        payload["draft"], bundle["source_record"], source_record_json=bundle["source_json"],
                        case_provenance=provenance, source_role=source_entry["role"],
                        shares_source_observations_with=[context["primary_evidence_id"]],
                    )
                else:
                    source_artifact = bundle["artifact"]
                    provenance = {
                        "active_case_id": context["active_case_id"],
                        "case_id": context["case_id"],
                        "assessment_record_type": context["assessment"]["record_type"],
                        "assessment_status": context["assessment"]["status"],
                        "assessment_relative_path": context["assessment_relative_path"],
                        "assessment_sha256": context["assessment_sha256"],
                        "source_evidence_id": evidence_id,
                        "source_relative_path": bundle["relative_path"],
                        "source_sha256": bundle["source_sha256"],
                        "source_record_type": source_artifact["record_type"],
                        "source_status": source_artifact["status"],
                        "source_role": source_artifact["role"],
                    }
                    updated = attach_validated_case_source(
                        payload["draft"], bundle["source_record"], source_record_json=bundle["source_json"],
                        case_provenance=provenance, source_role=source_artifact["role"],
                    )
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            self._send_json(updated, 200)

        def _assess_investigation_draft(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_INVESTIGATION_DRAFT_ASSESS_BYTES:
                self._send_json({"error": "Investigation draft and assessment exceed the 40 MiB request limit"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json({"error": "Investigation assessment request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {"draft", "assessments"}:
                self._send_json({"error": "Investigation assessment request fields are invalid"}, 400)
                return
            try:
                draft = payload["draft"]
                if isinstance(draft, dict) and any(
                    isinstance(item, dict) and item.get("ingest_method") in {
                        "VALIDATED_LOCAL_CASE_ASSESSMENT",
                        "VALIDATED_LOCAL_CASE_SOURCE_MANIFEST",
                    }
                    for item in draft.get("evidence_artifacts", [])
                ):
                    case_context = _validated_case_source_context(self.case_path, self.case_id, draft, evidence_root)
                    _validate_draft_case_sources(draft, case_context)
                updated = assess_investigation_draft(draft, payload["assessments"])
            except InvestigationDraftError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except (OSError, TypeError, ValueError, KeyError, StopIteration) as exc:
                self._send_json({"error": str(exc)}, 409)
                return
            self._send_json(updated, 200)

        def _search_opera_catalog(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_CATALOG_REQUEST_BYTES:
                self._send_json({"error": "OPERA catalog query body is too large"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "OPERA catalog query must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {
                "bounds_wgs84",
                "start_date",
                "end_date",
            }:
                self._send_json({"error": "OPERA catalog query fields are invalid"}, 400)
                return
            query = OperaRtcCatalogQuery(
                bounds_wgs84=payload["bounds_wgs84"],
                start_date=payload["start_date"],
                end_date=payload["end_date"],
            )
            try:
                query.validate()
                features, pages_retrieved = search_opera_rtc_s1_with_pagination(query)
                record = build_opera_rtc_catalog_record(
                    query, features, pages_retrieved=pages_retrieved
                )
            except OperaRtcCatalogError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except Exception as exc:
                self.log_error("OPERA catalog search failed: %s", type(exc).__name__)
                self._send_json({"error": "ASF OPERA catalog search failed"}, 502)
                return
            self._send_json(record, 200)

        def _build_opera_pair_analysis(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_OPERA_PAIR_REQUEST_BYTES:
                self._send_json({"error": "OPERA pair request body is too large"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "OPERA pair request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {
                "before",
                "after",
                "bounds_wgs84",
                "polarization",
            }:
                self._send_json({"error": "OPERA pair request fields are invalid"}, 400)
                return
            try:
                record = build_opera_rtc_s1_pair_record(
                    payload["before"],
                    payload["after"],
                    bounds_wgs84=payload["bounds_wgs84"],
                    polarization=payload["polarization"],
                )
            except OperaRtcS1PipelineError as exc:
                self._send_json({"error": str(exc)}, 422)
                return
            except Exception as exc:
                self.log_error("OPERA pair analysis failed: %s", type(exc).__name__)
                self._send_json(
                    {"error": "OPERA RTC-S1 pair analysis could not be completed"},
                    502,
                )
                return
            self._send_json(record, 200)

        def _search_gunw_catalog(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_CATALOG_REQUEST_BYTES:
                self._send_json({"error": "Catalog query body is too large"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "Catalog query must be valid JSON"}, 400)
                return
            required_fields = {
                "longitude",
                "latitude",
                "start_date",
                "end_date",
                "maturity",
            }
            if not isinstance(payload, dict) or set(payload) not in (
                required_fields,
                required_fields | {"bounds_wgs84"},
            ):
                self._send_json({"error": "Catalog query fields are invalid"}, 400)
                return
            query = CatalogQuery(
                longitude=payload["longitude"],
                latitude=payload["latitude"],
                start_date=payload["start_date"],
                end_date=payload["end_date"],
                maturity=payload["maturity"],
                max_results=100,
                bounds_wgs84=payload.get("bounds_wgs84"),
            )
            try:
                query.validate()
                if query.maturity not in {"PROVISIONAL", "VALIDATED"}:
                    raise CatalogQueryError(
                        "GUNW maturity must be PROVISIONAL or VALIDATED"
                    )
            except CatalogQueryError as exc:
                self._send_json({"error": str(exc)}, 400)
                return
            try:
                raw_features = search_gunw(query)
            except CatalogQueryError:
                self._send_json(
                    {"error": "ASF GUNW catalog search failed; try again later"}, 502
                )
                return

            features = []
            for feature in raw_features[:100]:
                if not isinstance(feature, dict) or not isinstance(
                    feature.get("geometry"), dict
                ):
                    continue
                try:
                    scene_id, product_url = _validated_gunw_product(feature)
                except (GunwAccessError, TypeError, AttributeError):
                    continue
                properties = feature["properties"]
                features.append(
                    {
                        "type": "Feature",
                        "geometry": feature["geometry"],
                        "properties": {
                            key: properties[key]
                            for key in (
                                "fileID",
                                "url",
                                "processingLevel",
                                "collectionName",
                                "startTime",
                                "stopTime",
                                "crid",
                                "orbit",
                                "pathNumber",
                                "frameNumber",
                                "flightDirection",
                                "polarization",
                            )
                            if key in properties
                        },
                    }
                )
                features[-1]["properties"]["fileID"] = scene_id
                features[-1]["properties"]["url"] = product_url
            self._send_json(
                {
                    "record_type": "ECHO_GUNW_CATALOG_QUERY",
                    "schema_version": 1,
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "source": {
                        "provider": "Alaska Satellite Facility DAAC",
                        "dataset": "NISAR L2 GUNW",
                        "metadata_only": True,
                        "query": asdict(query),
                        "result_limit": 100,
                        "returned_feature_count": len(features),
                        "potentially_truncated": len(raw_features) >= 100,
                        "interpretation_limit": (
                            "Catalog metadata only. Results do not establish pixel "
                            "availability, product quality, or scientific suitability."
                        ),
                    },
                    "features": features,
                },
                200,
            )

        def _retrieve_qa_summary(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_QA_SUMMARY_REQUEST_BYTES:
                self._send_json({"error": "QA summary request body is too large"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "QA summary request must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {"feature"}:
                self._send_json({"error": "QA summary request fields are invalid"}, 400)
                return
            feature = payload["feature"]
            if (
                not isinstance(feature, dict)
                or set(feature) != {"properties"}
                or not isinstance(feature["properties"], dict)
                or set(feature["properties"])
                != {"fileID", "url", "processingLevel", "collectionName"}
                or any(not isinstance(value, str) for value in feature["properties"].values())
            ):
                self._send_json({"error": "NISAR catalog feature fields are invalid"}, 400)
                return
            try:
                _validated_product(feature)
            except NisarAccessError as exc:
                self._send_json({"error": str(exc)}, 400)
                return
            try:
                record = read_qa_summary(feature, product_metadata={})
            except QASummaryError as exc:
                self._send_json({"error": str(exc)}, 502)
                return
            self._send_json(asdict(record), 200)

        def _preview_counterfactual_reassessment(self) -> None:
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_COUNTERFACTUAL_PREVIEW_REQUEST_BYTES:
                self._send_json({"error": "Counterfactual preview request is too large"}, 413)
                return
            try:
                request = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "Counterfactual preview request must be valid JSON"}, 400)
                return
            required = {
                "case_id",
                "assessment_sha256",
                "hypothesis_id",
                "evidence_id",
                "proposed_relationship",
            }
            if (
                not isinstance(request, dict)
                or set(request) != required
                or any(not isinstance(request[field], str) or not request[field] for field in required)
            ):
                self._send_json({"error": "Counterfactual preview fields are invalid"}, 400)
                return
            try:
                assessment_path = _case_evidence_path(
                    self.case_path, "cross_sensor_assessment", evidence_root
                )
                if assessment_path is None:
                    self._send_json({"error": "This case has no linked investigation assessment"}, 404)
                    return
                assessment_bytes = assessment_path.read_bytes()
                if len(assessment_bytes) > _MAX_INVESTIGATION_ASSESSMENT_BYTES:
                    self._send_json({"error": "Case assessment exceeds the response limit"}, 413)
                    return
                assessment = json.loads(assessment_bytes)
                _validate_assessment_record(assessment, evidence_root)
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                self._send_json({"error": f"Case assessment failed validation: {exc}"}, 503)
                return
            if request["case_id"] != assessment.get("case_id"):
                self._send_json({"error": "Counterfactual case does not match the selected assessment"}, 409)
                return
            actual_sha256 = sha256(assessment_bytes).hexdigest()
            if request["assessment_sha256"] != actual_sha256:
                self._send_json({"error": "Assessment changed; reload it before previewing a counterfactual"}, 409)
                return
            hypothesis = next(
                (
                    item for item in assessment.get("hypotheses", [])
                    if item.get("id") == request["hypothesis_id"]
                ),
                None,
            )
            if hypothesis is None:
                self._send_json({"error": "Hypothesis is not part of the selected assessment"}, 400)
                return
            try:
                preview = preview_evidence_relationship_change(
                    hypothesis,
                    evidence_id=request["evidence_id"],
                    proposed_relationship=request["proposed_relationship"],
                    known_evidence_ids={
                        item["evidence_id"] for item in assessment.get("evidence_artifacts", [])
                    },
                    non_directional_evidence_ids={
                        item["evidence_id"]
                        for item in assessment.get("evidence_artifacts", [])
                        if is_non_directional_evidence(item)
                    },
                )
            except (KeyError, TypeError, ValueError) as exc:
                self._send_json({"error": f"Counterfactual preview is invalid: {exc}"}, 400)
                return
            self._send_json(
                {
                    "record_type": "ECHO_COUNTERFACTUAL_EVIDENCE_RECLASSIFICATION_PREVIEW",
                    "schema_version": 1,
                    "status": "COUNTERFACTUAL_ONLY",
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "case_id": assessment["case_id"],
                    "assessment_sha256": actual_sha256,
                    **preview,
                },
                200,
            )

        def _export_qa_evidence(self) -> None:
            if self.headers.get_content_type() != "application/x-www-form-urlencoded":
                self._send_json({"error": "Evidence export must use a form submission"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_QA_EVIDENCE_EXPORT_REQUEST_BYTES:
                self._send_json({"error": "Evidence export request body is too large"}, 413)
                return
            try:
                form = parse_qs(
                    self.rfile.read(content_length).decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                    max_num_fields=1,
                )
                values = form.get("evidence_record", [])
                if set(form) != {"evidence_record"} or len(values) != 1:
                    raise ValueError("Evidence export form fields are invalid")
                record = json.loads(values[0])
            except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
                self._send_json({"error": "Evidence export record is invalid"}, 400)
                return
            if not isinstance(record, dict) or set(record) != {
                "record_type",
                "record_version",
                "exported_at_utc",
                "source_catalog",
                "provider_qa_summary",
                "interpretation_limits",
            }:
                self._send_json({"error": "Evidence export record fields are invalid"}, 400)
                return
            if (
                record["record_type"] != "ECHO_PROVIDER_QA_INSPECTION"
                or record["record_version"] != 1
                or not isinstance(record["exported_at_utc"], str)
                or not isinstance(record["interpretation_limits"], list)
                or any(not isinstance(item, str) for item in record["interpretation_limits"])
            ):
                self._send_json({"error": "Evidence export record header is invalid"}, 400)
                return
            source = record["source_catalog"]
            summary = record["provider_qa_summary"]
            if (
                not isinstance(source, dict)
                or set(source) != {"provider", "query", "feature"}
                or source["provider"] != "Alaska Satellite Facility DAAC"
                or not isinstance(source["query"], dict)
                or not isinstance(summary, dict)
                or not isinstance(summary.get("evidence"), dict)
            ):
                self._send_json({"error": "Evidence export source records are invalid"}, 400)
                return
            feature = source["feature"]
            evidence = summary["evidence"]
            status = evidence.get("status")
            try:
                scene_id, product_uri, _instrument = _validated_product(feature)
            except (NisarAccessError, TypeError, AttributeError) as exc:
                self._send_json({"error": f"Evidence export product is invalid: {exc}"}, 400)
                return
            expected_summary_uri = product_uri.rsplit("/", 1)[0] + f"/{scene_id}_QA_SUMMARY.csv"
            if (
                summary.get("scene_id") != scene_id
                or summary.get("artifact_uri") != expected_summary_uri
                or evidence.get("scene_id") != scene_id
                or evidence.get("artifact_uri") != expected_summary_uri
                or evidence.get("artifact_sha256") != summary.get("artifact_sha256")
                or not isinstance(status, str)
                or status not in {"PASS", "FAIL", "INDETERMINATE"}
                or isinstance(record["record_version"], bool)
            ):
                self._send_json({"error": "Evidence export source identifiers do not agree"}, 400)
                return
            record["exported_at_utc"] = datetime.now(timezone.utc).isoformat()
            body = (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            filename = f"{scene_id}_provider-qa-evidence.json"
            self._send_response(
                body,
                "application/json; charset=utf-8",
                200,
                extra_headers=(("Content-Disposition", f'attachment; filename="{filename}"'),),
            )

        def _send_case(self) -> None:
            try:
                body = self.case_path.read_bytes()
                json.loads(body)
            except (OSError, json.JSONDecodeError):
                self.send_error(503, "Catalog metadata is unavailable or invalid")
                return
            self._send_bytes(body, "application/json; charset=utf-8")

        def _send_case_evidence(self, evidence_name: str, maximum_bytes: int) -> None:
            try:
                evidence_path = _case_evidence_path(self.case_path, evidence_name, evidence_root)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, 503)
                return
            if evidence_path is None or not evidence_path.is_file():
                self._send_json({"error": "This case has no configured evidence record for this view"}, 404)
                return
            if evidence_path.stat().st_size > maximum_bytes:
                self._send_json({"error": "Case evidence record exceeds the response limit"}, 413)
                return
            if evidence_name == "cross_sensor_assessment":
                assessment_payload = b""
                record: object = None
                try:
                    assessment_payload = evidence_path.read_bytes()
                    record = json.loads(assessment_payload)
                    _validate_assessment_record(record, evidence_root)
                except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                    impact = (
                        _assessment_integrity_impact(record, evidence_root)
                        if isinstance(record, dict)
                        else None
                    )
                    if impact is not None:
                        impact["assessment_sha256"] = sha256(assessment_payload).hexdigest()
                        self._send_json({
                            "error": f"Case assessment failed evidence integrity validation: {exc}",
                            "integrity_impact": impact,
                        }, 409)
                        return
                    self._send_json({"error": f"Case assessment failed validation: {exc}"}, 503)
                    return
            self._send_file(evidence_path, "application/json; charset=utf-8")

        def _send_opera_temporal_series(self) -> None:
            """Serve the retained T024 RTC series only while its case-manifest hash matches."""
            try:
                evidence_path = _case_evidence_path(self.case_path, "opera_temporal_series", evidence_root)
                if evidence_path is None or not evidence_path.is_file():
                    self._send_json({"error": "This case has no retained OPERA temporal-series record"}, 404)
                    return
                manifest = json.loads(self.case_path.with_name("investigation.json").read_text(encoding="utf-8"))
                expected_hash = manifest.get("evidence_sha256", {}).get("opera_temporal_series")
                payload = evidence_path.read_bytes()
                if len(payload) > _MAX_OPERA_TEMPORAL_SERIES_BYTES:
                    self._send_json({"error": "OPERA temporal-series record exceeds the response limit"}, 413)
                    return
                record = json.loads(payload)
                if (
                    not isinstance(expected_hash, str)
                    or sha256(payload).hexdigest() != expected_hash
                    or not isinstance(record, dict)
                    or record.get("record_type") != "ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS"
                    or record.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES"
                    or len(record.get("observations", [])) < 3
                    or len(record.get("adjacent_intervals", [])) != len(record.get("observations", [])) - 1
                ):
                    self._send_json({"error": "OPERA temporal-series record failed case-link, hash, or schema validation"}, 409)
                    return
            except (OSError, json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
                self._send_json({"error": f"OPERA temporal-series record is unavailable or invalid: {exc}"}, 503)
                return
            self._send_bytes(
                payload,
                "application/json; charset=utf-8",
                extra_headers=(
                    ("X-ECHO-Content-SHA256", expected_hash),
                    ("X-ECHO-Source-Path", str(evidence_path.relative_to(evidence_root.resolve()))),
                ),
            )

        def _send_linked_assessment_artifact(self, evidence_id: str) -> None:
            try:
                assessment_path = _case_evidence_path(self.case_path, "cross_sensor_assessment", evidence_root)
                if assessment_path is None or not assessment_path.is_file():
                    self._send_json({"error": "This case has no linked investigation assessment"}, 404)
                    return
                assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
                evidence_ids = _validate_assessment_record(assessment, evidence_root)
                if evidence_id not in evidence_ids:
                    self._send_json({"error": "Evidence identifier is not linked to this case assessment"}, 404)
                    return
                artifact = next(
                    item for item in assessment["evidence_artifacts"]
                    if item["evidence_id"] == evidence_id
                )
                candidate = Path(artifact["relative_path"])
                if candidate.is_absolute():
                    raise ValueError("assessment evidence paths must be relative")
                root = evidence_root.resolve()
                artifact_path = (root / candidate).resolve()
                if not artifact_path.is_relative_to(root):
                    raise ValueError("assessment evidence path escapes the project root")
                payload = artifact_path.read_bytes()
                if len(payload) > _MAX_LINKED_EVIDENCE_ARTIFACT_BYTES:
                    self._send_json({"error": "Linked evidence artifact exceeds the response limit"}, 413)
                    return
                if sha256(payload).hexdigest() != artifact["sha256"]:
                    raise ValueError("assessment evidence checksum mismatch")
                source_record = json.loads(payload)
                if (
                    not isinstance(source_record, dict)
                    or source_record.get("record_type") != artifact["record_type"]
                    or source_record.get("status") != artifact["status"]
                ):
                    raise ValueError("assessment evidence identity mismatch")
            except (OSError, json.JSONDecodeError, TypeError, ValueError, StopIteration) as exc:
                self._send_json({"error": f"Linked evidence failed validation: {exc}"}, 503)
                return
            self._send_bytes(payload, "application/json; charset=utf-8")

        def _send_qa_reports(self) -> None:
            review_path = self.case_path.with_name("case-review.json")
            if not review_path.is_file():
                review_path = self.case_path.with_name("qa-review.json")
            try:
                review = json.loads(review_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                self._send_json({"schema_version": 1, "records": []}, 200)
                return
            except (OSError, json.JSONDecodeError):
                self.send_error(503, "Case review metadata is unavailable or invalid")
                return
            if not isinstance(review, dict) or not isinstance(review.get("products", []), list):
                self.send_error(503, "Case review metadata has an invalid shape")
                return

            scene_ids = {
                item.get("scene_id")
                for item in review.get("products", [])
                if isinstance(item, dict) and isinstance(item.get("scene_id"), str)
            }
            candidate = review.get("candidate_pair", {})
            if isinstance(candidate, dict):
                for position in ("before", "after"):
                    scene = candidate.get(position)
                    if isinstance(scene, dict) and isinstance(scene.get("scene_id"), str):
                        scene_ids.add(scene["scene_id"])

            records = []
            for position in ("before", "after"):
                report_path = self.case_path.parent / f"qa-report-{position}.json"
                if not report_path.is_file():
                    continue
                try:
                    record = json.loads(report_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    self.send_error(503, "QA report evidence is invalid")
                    return
                if not isinstance(record, dict) or not isinstance(record.get("scene_id"), str):
                    self.send_error(503, "QA report evidence has an invalid shape")
                    return
                if record["scene_id"] in scene_ids:
                    records.append(record)
            self._send_json({"schema_version": 1, "records": records}, 200)

        def _send_file(self, path: Path, content_type: str) -> None:
            try:
                body = path.read_bytes()
                if content_type.startswith("application/json"):
                    json.loads(body)
                self._send_bytes(body, content_type)
            except OSError:
                self.send_error(500, "Interface asset is missing")
            except json.JSONDecodeError:
                self.send_error(503, "JSON evidence is invalid")

        def _send_bytes(
            self,
            body: bytes,
            content_type: str,
            *,
            extra_headers: tuple[tuple[str, str], ...] = (),
        ) -> None:
            self._send_response(body, content_type, 200, extra_headers=extra_headers)

        def _send_json(self, record: dict[str, object], status: int) -> None:
            body = json.dumps(record, separators=(",", ":")).encode("utf-8")
            self._send_response(body, "application/json; charset=utf-8", status)

        def _send_response(
            self,
            body: bytes,
            content_type: str,
            status: int,
            *,
            extra_headers: tuple[tuple[str, str], ...] = (),
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self'; script-src 'self'; "
                "img-src 'self' data: https://gibs.earthdata.nasa.gov; connect-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'",
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            for name, value in extra_headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            logging.info("%s - %s", self.address_string(), fmt % args)

    return Handler


def serve(*, host: str, port: int, case_file: Path) -> int:
    case_path = case_file.expanduser().resolve()
    if not case_path.is_file():
        print(f"echo: catalog file not found: {case_path}")
        return 2
    try:
        server = ThreadingHTTPServer((host, port), make_handler(case_path))
    except OSError as exc:
        print(f"echo: cannot start local interface: {exc}")
        return 2
    print(f"ECHO investigation interface: http://{host}:{server.server_port}/")
    print(f"Catalog source: {case_path}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

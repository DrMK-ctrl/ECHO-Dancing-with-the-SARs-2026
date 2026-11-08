"""Read-only local web interface for ECHO case metadata."""

from __future__ import annotations

from hashlib import sha256
import json
import logging
import math
from dataclasses import asdict
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from echo.catalog import (
    CatalogQuery,
    CatalogQueryError,
    MAX_GCOV_CATALOG_RESULTS,
    build_catalog_record,
    search_gcov,
    search_gunw,
)
from echo.gcov_analysis import GcovPairAnalysisError, build_gcov_pair_analysis
from echo.gunw_access import GunwAccessError, _validated_gunw_product
from echo.gcov_preview import GcovPreviewError, build_gcov_preview
from echo.investigation import (
    preview_evidence_relationship_change,
    validate_investigation_contract,
)
from echo.nisar_access import NisarAccessError, _validated_product
from echo.modis_vi import validate_mod13q1_candidate_screen
from echo.opera_rtc_conditions import validate_acquisition_condition_review
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


_STATIC = Path(__file__).with_name("static")
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MAX_CATALOG_REQUEST_BYTES = 8 * 1024
_MAX_QA_SUMMARY_REQUEST_BYTES = 4 * 1024
_MAX_QA_EVIDENCE_EXPORT_REQUEST_BYTES = 256 * 1024
_MAX_GCOV_PREVIEW_REQUEST_BYTES = 16 * 1024
_MAX_GCOV_PAIR_REQUEST_BYTES = 32 * 1024
_MAX_OPERA_PAIR_REQUEST_BYTES = 64 * 1024
_MAX_DSWX_CONTEXT_BYTES = 2 * 1024 * 1024
_MAX_INVESTIGATION_ASSESSMENT_BYTES = 256 * 1024
_MAX_COUNTERFACTUAL_PREVIEW_REQUEST_BYTES = 8 * 1024
_MAX_LINKED_EVIDENCE_ARTIFACT_BYTES = 64 * 1024 * 1024


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


def make_handler(
    case_path: Path,
    *,
    evidence_root: Path = _PROJECT_ROOT,
    case_registry: dict[str, Path] | None = None,
) -> type[BaseHTTPRequestHandler]:
    default_case_path = case_path.expanduser().resolve()
    registered_cases = case_registry or _discover_case_registry(default_case_path, evidence_root)
    registered_cases = {key: Path(value).expanduser().resolve() for key, value in registered_cases.items()}
    default_case_id = _case_identifier(default_case_path)
    if default_case_id not in registered_cases:
        registered_cases[default_case_id] = default_case_path

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
            if path == "/api/investigation-evidence":
                query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                if set(query) != {"evidence_id"} or len(query["evidence_id"]) != 1:
                    self._send_json({"error": "Exactly one evidence_id is required"}, 400)
                    return
                self._send_linked_assessment_artifact(query["evidence_id"][0])
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
            if path == "/api/gcov-preview":
                self._build_gcov_preview()
                return
            if path == "/api/gcov-pair-analysis":
                self._build_gcov_pair_analysis()
                return
            if path == "/api/opera-pair-analysis":
                self._build_opera_pair_analysis()
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
            try:
                features = search_gcov(query)
                record = build_catalog_record(query, features)
            except CatalogQueryError:
                self._send_json(
                    {"error": "ASF catalog search failed; try again later"}, 502
                )
                return
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
                try:
                    record = json.loads(evidence_path.read_text(encoding="utf-8"))
                    _validate_assessment_record(record, evidence_root)
                except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                    self._send_json({"error": f"Case assessment failed validation: {exc}"}, 503)
                    return
            self._send_file(evidence_path, "application/json; charset=utf-8")

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

        def _send_bytes(self, body: bytes, content_type: str) -> None:
            self._send_response(body, content_type, 200)

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

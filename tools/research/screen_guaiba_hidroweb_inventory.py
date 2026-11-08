#!/usr/bin/env python3
"""Screen the public ANA/SGB HidroWeb station inventory for Guaiba gauge IDs.

This checks inventory metadata only. It does not request or validate a time
series and an absent inventory record does not prove archived observations do
not exist.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE_URL = (
    "https://www.snirh.gov.br/arcgis/rest/services/Hidroweb_BH/"
    "INVENTARIOS_ESTACOES/MapServer/0/query"
)
OUT_DIR = ROOT / "data/research"
ARTIFACT_DIR = OUT_DIR / "source-artifacts"
STATION_CODES = ("87444000", "87450020")
CONTROL_STATION_CODE = "87450003"
FIELDS = (
    "OBJECTID,EST_ID,EST_CD_FLU,EST_NM,EST_TP,OPERANDO,"
    "POSSUI_DADOS,ULTIMAATUALIZACAO"
)


def fetch_query(label: str, params: dict[str, str]) -> dict[str, Any]:
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ECHO research inventory screen/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
        status = response.status
        content_type = response.headers.get("Content-Type", "")
    payload = json.loads(body)
    artifact_path = ARTIFACT_DIR / f"ana-sgb-guaiba-inventory-{label}-2026-11-08.json"
    artifact_path.write_bytes(body)
    return {
        "label": label,
        "request_url": url,
        "http_status": status,
        "content_type": content_type,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "response_artifact": artifact_path.relative_to(ROOT).as_posix(),
        "feature_count": len(payload.get("features", [])),
        "features": payload.get("features", []),
    }


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    queries = []
    for code in (*STATION_CODES, CONTROL_STATION_CODE):
        where = f"EST_ID = {int(code)} OR EST_CD_FLU = '{code}'"
        queries.append(
            fetch_query(
                code,
                {
                    "where": where,
                    "outFields": FIELDS,
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "json",
                },
            )
        )
    queries.append(
        fetch_query(
            "guaiba-aoi",
            {
                "where": "1=1",
                "geometry": "-51.26,-30.06,-51.22,-30.01",
                "geometryType": "esriGeometryEnvelope",
                "spatialRel": "esriSpatialRelIntersects",
                "inSR": "4326",
                "outFields": FIELDS,
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            },
        )
    )
    record = {
        "record_type": "ECHO_ANA_SGB_HIDROWEB_STATION_INVENTORY_SCREEN",
        "status": "INVENTORY_METADATA_ONLY",
        "retrieved_at_utc": retrieved_at,
        "provider": "Agência Nacional de Águas e Saneamento Básico (ANA) / Serviço Geológico do Brasil (SGB)",
        "dataset": "HidroWeb station inventory ArcGIS MapServer layer 0",
        "service_url": "https://www.snirh.gov.br/arcgis/rest/services/Hidroweb_BH/INVENTARIOS_ESTACOES/MapServer/0",
        "queries": queries,
        "interpretation": {
            "station_code_query_result": {
                item["label"]: item["feature_count"]
                for item in queries
                if item["label"] in (*STATION_CODES, CONTROL_STATION_CODE)
            },
            "known_station_control": CONTROL_STATION_CODE,
            "guaiba_aoi_inventory_record_count": queries[-1]["feature_count"],
            "limitation": "This service is an inventory, not a time-series endpoint. Missing station IDs here do not show that historic observations are absent from the archive.",
            "case_disposition": "No series values or new evidence relationships were added to the T163 assessment.",
        },
        "references": [
            "https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs/nota-institucional-conjunta-ana-sgb-gasometro-final.pdf",
            "https://apps.sgb.gov.br/hidro-series/",
        ],
    }
    output = OUT_DIR / "ana-sgb-guaiba-inventory-screen-2026-11-08.json"
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix(), "query_results": {item["label"]: item["feature_count"] for item in queries}}))


if __name__ == "__main__":
    main()

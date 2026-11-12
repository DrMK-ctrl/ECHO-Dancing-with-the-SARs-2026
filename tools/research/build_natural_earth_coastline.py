#!/usr/bin/env python3
"""Convert the retained Natural Earth 1:110m coastline shapefile to GeoJSON."""

from __future__ import annotations

import hashlib
import json
import struct
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/basemap/natural-earth-110m-coastline.zip"
OUTPUT = ROOT / "echo/static/natural-earth-coastline-110m.json"
MAX_SOURCE_BYTES = 2_000_000
MAX_RECORDS = 10_000
MAX_POINTS = 100_000


def _parse_shapefile(content: bytes) -> list[list[list[list[float]]]]:
    if len(content) < 100 or len(content) > MAX_SOURCE_BYTES:
        raise ValueError("Natural Earth shapefile size is invalid")
    file_code = struct.unpack_from(">i", content, 0)[0]
    version, shape_type = struct.unpack_from("<ii", content, 28)
    if file_code != 9994 or version != 1000 or shape_type != 3:
        raise ValueError("Natural Earth source is not a polyline shapefile")

    result: list[list[list[list[float]]]] = []
    offset = 100
    total_points = 0
    while offset < len(content):
        if offset + 8 > len(content):
            raise ValueError("Natural Earth shapefile has a truncated record header")
        _, content_words = struct.unpack_from(">ii", content, offset)
        record_bytes = content_words * 2
        offset += 8
        end = offset + record_bytes
        if record_bytes < 44 or end > len(content):
            raise ValueError("Natural Earth shapefile record length is invalid")
        record = content[offset:end]
        record_type = struct.unpack_from("<i", record, 0)[0]
        if record_type != 3:
            raise ValueError("Natural Earth coastline record is not a polyline")
        part_count, point_count = struct.unpack_from("<ii", record, 36)
        if part_count < 1 or point_count < 2 or point_count > MAX_POINTS:
            raise ValueError("Natural Earth coastline geometry size is invalid")
        parts_end = 44 + 4 * part_count
        expected_end = parts_end + 16 * point_count
        if expected_end != len(record):
            raise ValueError("Natural Earth coastline record has inconsistent offsets")
        starts = list(struct.unpack_from(f"<{part_count}i", record, 44))
        if starts[0] != 0 or any(a >= b for a, b in zip(starts, starts[1:])):
            raise ValueError("Natural Earth coastline part offsets are invalid")
        if starts[-1] >= point_count:
            raise ValueError("Natural Earth coastline part starts outside its point array")
        points = list(struct.iter_unpack("<dd", record[parts_end:]))
        total_points += point_count
        if total_points > MAX_POINTS:
            raise ValueError("Natural Earth coastline exceeds the point budget")
        stops = starts[1:] + [point_count]
        lines = []
        for start, stop in zip(starts, stops):
            line = []
            for raw_lon, raw_lat in points[start:stop]:
                lon, lat = float(raw_lon), float(raw_lat)
                if not (-180.00001 <= lon <= 180.00001 and -90.00001 <= lat <= 90.00001):
                    raise ValueError("Natural Earth coastline contains invalid WGS84 coordinates")
                # The source has a few sub-microdegree floating-point overshoots at 180°.
                line.append([max(-180.0, min(180.0, lon)), max(-90.0, min(90.0, lat))])
            if len(line) < 2:
                raise ValueError("Natural Earth coastline contains an incomplete line")
            lines.append(line)
        result.append(lines)
        if len(result) > MAX_RECORDS:
            raise ValueError("Natural Earth coastline exceeds the feature budget")
        offset = end
    if offset != len(content) or not result:
        raise ValueError("Natural Earth coastline shapefile is empty or malformed")
    return result


def build() -> dict[str, object]:
    source_bytes = SOURCE.read_bytes()
    if len(source_bytes) > MAX_SOURCE_BYTES:
        raise ValueError("Natural Earth archive exceeds the byte budget")
    with zipfile.ZipFile(SOURCE) as archive:
        shp_names = [name for name in archive.namelist() if name.lower().endswith(".shp")]
        if len(shp_names) != 1:
            raise ValueError("Natural Earth archive must contain one shapefile")
        geometries = _parse_shapefile(archive.read(shp_names[0]))
    return {
        "type": "FeatureCollection",
        "name": "Natural Earth 1:110m coastline",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": {"type": "MultiLineString", "coordinates": lines}}
            for lines in geometries
        ],
    }


def main() -> None:
    record = build()
    encoded = (json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
    OUTPUT.write_bytes(encoded)
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(encoded)} bytes)")
    print(f"source sha256 {hashlib.sha256(SOURCE.read_bytes()).hexdigest()}")
    print(f"derived sha256 {hashlib.sha256(encoded).hexdigest()}")


if __name__ == "__main__":
    main()

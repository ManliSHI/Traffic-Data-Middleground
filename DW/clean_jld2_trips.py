#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
from array import array
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import h5py
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


UTC = "UTC"
TRIP_COLUMNS = [
    "source_file",
    "trip_id",
    "devid",
    "point_count",
    "matched_segment_count",
    "route_edge_count",
    "gps_start_ts",
    "gps_end_ts",
    "gps_start_time_utc",
    "gps_end_time_utc",
    "matched_start_ts",
    "matched_end_ts",
    "matched_start_time_utc",
    "matched_end_time_utc",
    "has_matched_segments",
    "is_valid_trip",
    "invalid_reason",
    "lon_min",
    "lon_max",
    "lat_min",
    "lat_max",
]
SEGMENT_COLUMNS = [
    "source_file",
    "trip_id",
    "devid",
    "segment_index",
    "road_id",
    "match_ts",
    "match_time_utc",
    "frac",
    "frac_clipped",
    "is_frac_imputed",
    "route_geom_wkt",
    "segment_is_valid",
    "segment_invalid_reason",
]
GPS_POINT_COLUMNS = [
    "source_file",
    "trip_id",
    "devid",
    "point_index",
    "lon",
    "lat",
    "tms",
    "gps_time_utc",
    "point_is_valid",
    "point_invalid_reason",
]
ROUTE_EDGE_COLUMNS = [
    "source_file",
    "trip_id",
    "devid",
    "route_index",
    "route_road_id",
    "route_heading",
    "route_edge_is_valid",
    "route_edge_invalid_reason",
]
ROUTE_GEOM_COLUMNS = [
    "source_file",
    "trip_id",
    "devid",
    "route_geom_index",
    "route_geom_wkt",
    "route_geom_is_valid",
    "route_geom_invalid_reason",
]
TRIP_SCHEMA = pa.schema(
    [
        pa.field("source_file", pa.string()),
        pa.field("trip_id", pa.string()),
        pa.field("devid", pa.int64()),
        pa.field("point_count", pa.int32()),
        pa.field("matched_segment_count", pa.int32()),
        pa.field("route_edge_count", pa.int32()),
        pa.field("gps_start_ts", pa.int64()),
        pa.field("gps_end_ts", pa.int64()),
        pa.field("gps_start_time_utc", pa.timestamp("ns", tz=UTC)),
        pa.field("gps_end_time_utc", pa.timestamp("ns", tz=UTC)),
        pa.field("matched_start_ts", pa.int64()),
        pa.field("matched_end_ts", pa.int64()),
        pa.field("matched_start_time_utc", pa.timestamp("ns", tz=UTC)),
        pa.field("matched_end_time_utc", pa.timestamp("ns", tz=UTC)),
        pa.field("has_matched_segments", pa.bool_()),
        pa.field("is_valid_trip", pa.bool_()),
        pa.field("invalid_reason", pa.string()),
        pa.field("lon_min", pa.float64()),
        pa.field("lon_max", pa.float64()),
        pa.field("lat_min", pa.float64()),
        pa.field("lat_max", pa.float64()),
    ]
)
SEGMENT_SCHEMA = pa.schema(
    [
        pa.field("source_file", pa.string()),
        pa.field("trip_id", pa.string()),
        pa.field("devid", pa.int64()),
        pa.field("segment_index", pa.int32()),
        pa.field("road_id", pa.int64()),
        pa.field("match_ts", pa.int64()),
        pa.field("match_time_utc", pa.timestamp("ns", tz=UTC)),
        pa.field("frac", pa.float64()),
        pa.field("frac_clipped", pa.float64()),
        pa.field("is_frac_imputed", pa.bool_()),
        pa.field("route_geom_wkt", pa.string()),
        pa.field("segment_is_valid", pa.bool_()),
        pa.field("segment_invalid_reason", pa.string()),
    ]
)
GPS_POINT_SCHEMA = pa.schema(
    [
        pa.field("source_file", pa.string()),
        pa.field("trip_id", pa.string()),
        pa.field("devid", pa.int64()),
        pa.field("point_index", pa.int32()),
        pa.field("lon", pa.float64()),
        pa.field("lat", pa.float64()),
        pa.field("tms", pa.int64()),
        pa.field("gps_time_utc", pa.timestamp("ns", tz=UTC)),
        pa.field("point_is_valid", pa.bool_()),
        pa.field("point_invalid_reason", pa.string()),
    ]
)
ROUTE_EDGE_SCHEMA = pa.schema(
    [
        pa.field("source_file", pa.string()),
        pa.field("trip_id", pa.string()),
        pa.field("devid", pa.int64()),
        pa.field("route_index", pa.int32()),
        pa.field("route_road_id", pa.int64()),
        pa.field("route_heading", pa.string()),
        pa.field("route_edge_is_valid", pa.bool_()),
        pa.field("route_edge_invalid_reason", pa.string()),
    ]
)
ROUTE_GEOM_SCHEMA = pa.schema(
    [
        pa.field("source_file", pa.string()),
        pa.field("trip_id", pa.string()),
        pa.field("devid", pa.int64()),
        pa.field("route_geom_index", pa.int32()),
        pa.field("route_geom_wkt", pa.string()),
        pa.field("route_geom_is_valid", pa.bool_()),
        pa.field("route_geom_invalid_reason", pa.string()),
    ]
)
INT_COLUMNS = {
    "devid",
    "point_count",
    "matched_segment_count",
    "route_edge_count",
    "gps_start_ts",
    "gps_end_ts",
    "matched_start_ts",
    "matched_end_ts",
    "segment_index",
    "road_id",
    "match_ts",
    "point_index",
    "tms",
    "route_index",
    "route_road_id",
    "route_geom_index",
}
FLOAT_COLUMNS = {"lon_min", "lon_max", "lat_min", "lat_max", "frac", "frac_clipped", "lon", "lat"}
BOOL_COLUMNS = {
    "has_matched_segments",
    "is_valid_trip",
    "is_frac_imputed",
    "segment_is_valid",
    "point_is_valid",
    "route_edge_is_valid",
    "route_geom_is_valid",
}
STRING_COLUMNS = {
    "source_file",
    "trip_id",
    "invalid_reason",
    "route_geom_wkt",
    "segment_invalid_reason",
    "point_invalid_reason",
    "route_heading",
    "route_edge_invalid_reason",
    "route_geom_invalid_reason",
}
TIME_COLUMNS = {
    "gps_start_time_utc": "gps_start_ts",
    "gps_end_time_utc": "gps_end_ts",
    "matched_start_time_utc": "matched_start_ts",
    "matched_end_time_utc": "matched_end_ts",
    "match_time_utc": "match_ts",
    "gps_time_utc": "tms",
}
REFERENCE_TYPE = h5py.h5r.Reference


@dataclass
class FileStats:
    total_trips: int = 0
    valid_trips: int = 0
    invalid_trips: int = 0
    empty_matched_trips: int = 0
    total_points: int = 0
    total_segments: int = 0
    total_route_edges: int = 0
    total_route_geometries: int = 0
    frac_missing: int = 0
    frac_out_of_range: int = 0
    point_length_mismatch: int = 0
    matched_length_mismatch: int = 0
    coord_out_of_range: int = 0
    non_finite_coord: int = 0
    non_finite_time: int = 0
    non_monotonic_time: int = 0
    route_geom_length_mismatch: int = 0


class BufferedParquetWriter:
    def __init__(
        self,
        path: Path,
        columns: list[str],
        schema: pa.Schema,
        batch_size: int,
    ) -> None:
        self.path = path
        self.columns = columns
        self.schema = schema
        self.batch_size = batch_size
        self.writer: pq.ParquetWriter | None = None
        self.buffer = {column: [] for column in columns}
        self.row_count = 0

    def append(self, row: dict[str, Any]) -> None:
        for column in self.columns:
            self.buffer[column].append(row.get(column))
        self.row_count += 1
        if self.row_count >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        if self.row_count == 0:
            return
        frame = build_frame(self.buffer, self.columns)
        table = pa.Table.from_pandas(frame, schema=self.schema, preserve_index=False)
        if self.writer is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.writer = pq.ParquetWriter(self.path, self.schema, compression="snappy")
        self.writer.write_table(table)
        self.buffer = {column: [] for column in self.columns}
        self.row_count = 0

    def close(self) -> None:
        self.flush()
        if self.writer is not None:
            self.writer.close()


def build_frame(buffer: dict[str, list[Any]], columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(buffer, columns=columns)
    for column in columns:
        if column in INT_COLUMNS:
            frame[column] = pd.array(frame[column], dtype="Int64")
        elif column in FLOAT_COLUMNS:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("float64")
        elif column in BOOL_COLUMNS:
            frame[column] = pd.array(frame[column], dtype="boolean")
        elif column in STRING_COLUMNS:
            frame[column] = pd.array(frame[column], dtype="string")
    for time_column, source_column in TIME_COLUMNS.items():
        if time_column in frame.columns:
            numeric_ts = pd.to_numeric(frame[source_column], errors="coerce").astype("float64")
            frame[time_column] = pd.to_datetime(
                numeric_ts,
                unit="s",
                utc=True,
                errors="coerce",
                cache=False,
            )
    return frame


def decode_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def scalar_or_none(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return value


def to_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return int(round(numeric))


def join_reasons(reasons: Iterable[str]) -> str | None:
    unique = []
    seen = set()
    for reason in reasons:
        if reason and reason not in seen:
            unique.append(reason)
            seen.add(reason)
    return ";".join(unique) if unique else None


def is_non_decreasing(values: np.ndarray) -> bool:
    if values.size <= 1:
        return True
    return bool(np.all(np.diff(values) >= 0))


def has_non_finite(values: np.ndarray) -> bool:
    return bool(values.size and not np.isfinite(values).all())


def array_item_or_none(values: np.ndarray, index: int) -> Any:
    if index < 0 or index >= values.shape[0]:
        return None
    return scalar_or_none(values[index])


def list_item_or_none(values: list[Any], index: int) -> Any:
    if index < 0 or index >= len(values):
        return None
    return values[index]


def read_scalar_dataset(file_handle: h5py.File, ref: Any) -> Any:
    value = file_handle[ref][()]
    return scalar_or_none(value)


def read_numeric_array(file_handle: h5py.File, ref: Any, dtype: Any) -> np.ndarray:
    values = np.asarray(file_handle[ref][()])
    if values.size == 0:
        return np.asarray([], dtype=dtype)
    return values.astype(dtype, copy=False)


def read_frac_array(file_handle: h5py.File, ref: Any) -> np.ndarray:
    dataset = file_handle[ref]
    if dataset.size == 0:
        return np.asarray([], dtype="float64")
    if dataset.dtype != object:
        return np.asarray(dataset[()], dtype="float64")
    values = np.empty(dataset.shape[0], dtype="float64")
    for idx, item in enumerate(dataset[()]):
        deref = item
        if isinstance(item, REFERENCE_TYPE):
            deref = read_scalar_dataset(file_handle, item)
        deref = scalar_or_none(deref)
        try:
            values[idx] = float(deref)
        except (TypeError, ValueError):
            values[idx] = np.nan
    return values


def read_text_array(file_handle: h5py.File, ref: Any) -> list[str]:
    dataset = file_handle[ref]
    raw = np.asarray(dataset[()]).reshape(-1)
    values: list[str] = []
    for item in raw:
        if isinstance(item, REFERENCE_TYPE):
            item = read_scalar_dataset(file_handle, item)
        text = decode_text(item)
        if text is not None:
            values.append(text)
    return values


def align_route_geometries(route_geom: list[str], road_count: int) -> tuple[list[str | None], bool]:
    if road_count == 0:
        return [], False
    if not route_geom:
        return [None] * road_count, False
    if len(route_geom) == road_count:
        return [geom or None for geom in route_geom], False
    if len(route_geom) == road_count - 1:
        aligned: list[str | None] = [None]
        aligned.extend(geom or None for geom in route_geom)
        return aligned, False
    return [None] * road_count, True


def summarize_numeric(values: array) -> dict[str, float | int] | None:
    if len(values) == 0:
        return None
    arr = np.asarray(values, dtype="float64")
    return {
        "count": int(arr.size),
        "min": float(arr.min()),
        "p50": float(np.quantile(arr, 0.5)),
        "p95": float(np.quantile(arr, 0.95)),
        "max": float(arr.max()),
        "mean": float(arr.mean()),
    }


def discover_input_files(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("*.jld2"))


def process_trip(
    file_handle: h5py.File,
    source_file: str,
    trip_index: int,
    trip_writer: BufferedParquetWriter,
    gps_point_writer: BufferedParquetWriter,
    segment_writer: BufferedParquetWriter,
    route_edge_writer: BufferedParquetWriter,
    route_geom_writer: BufferedParquetWriter,
    file_stats: FileStats,
    invalid_reason_counter: Counter[str],
    point_counts: array,
    matched_counts: array,
) -> None:
    trips_dataset = file_handle["trips"]
    record = file_handle[trips_dataset[trip_index]][()]
    trip_id = f"{source_file}:{trip_index}"

    lon = read_numeric_array(file_handle, record["lon"], "float64")
    lat = read_numeric_array(file_handle, record["lat"], "float64")
    tms = read_numeric_array(file_handle, record["tms"], "float64")
    roads = read_numeric_array(file_handle, record["roads"], "int64")
    match_time = read_numeric_array(file_handle, record["time"], "int64")
    frac = read_frac_array(file_handle, record["frac"])
    route = read_numeric_array(file_handle, record["route"], "int64")
    route_heading = read_text_array(file_handle, record["route_heading"])
    route_geom = read_text_array(file_handle, record["route_geom"])
    route_edge_count = int(max(route.shape[0], len(route_heading)))
    devid = to_int_or_none(read_scalar_dataset(file_handle, record["devid"]))

    point_count = int(max(lon.shape[0], lat.shape[0], tms.shape[0]))
    matched_segment_count = int(max(roads.shape[0], match_time.shape[0], frac.shape[0]))
    point_counts.append(point_count)
    matched_counts.append(matched_segment_count)
    file_stats.total_trips += 1
    file_stats.total_points += point_count

    trip_reasons: list[str] = []
    if not (point_count == lat.shape[0] == tms.shape[0]):
        trip_reasons.append("point_length_mismatch")
        file_stats.point_length_mismatch += 1
    if not (matched_segment_count == match_time.shape[0] == frac.shape[0]):
        trip_reasons.append("matched_length_mismatch")
        file_stats.matched_length_mismatch += 1
    if has_non_finite(lon) or has_non_finite(lat):
        trip_reasons.append("non_finite_coord")
        file_stats.non_finite_coord += 1
    if has_non_finite(tms) or has_non_finite(match_time.astype("float64", copy=False)):
        trip_reasons.append("non_finite_time")
        file_stats.non_finite_time += 1
    if lon.size and (
        np.any(lon < -180) or np.any(lon > 180) or np.any(lat < -90) or np.any(lat > 90)
    ):
        trip_reasons.append("coord_out_of_range")
        file_stats.coord_out_of_range += 1
    if tms.size and not is_non_decreasing(tms):
        trip_reasons.append("non_monotonic_time")
    if match_time.size and not is_non_decreasing(match_time.astype("float64", copy=False)):
        if "non_monotonic_time" not in trip_reasons:
            trip_reasons.append("non_monotonic_time")
    if "non_monotonic_time" in trip_reasons:
        file_stats.non_monotonic_time += 1

    is_valid_trip = not trip_reasons
    if is_valid_trip:
        file_stats.valid_trips += 1
    else:
        file_stats.invalid_trips += 1
        for reason in trip_reasons:
            invalid_reason_counter[reason] += 1

    if matched_segment_count == 0:
        file_stats.empty_matched_trips += 1

    gps_start_ts = to_int_or_none(tms[0]) if tms.size else None
    gps_end_ts = to_int_or_none(tms[-1]) if tms.size else None
    matched_start_ts = to_int_or_none(match_time[0]) if match_time.size else None
    matched_end_ts = to_int_or_none(match_time[-1]) if match_time.size else None

    lon_min = float(np.nanmin(lon)) if lon.size else np.nan
    lon_max = float(np.nanmax(lon)) if lon.size else np.nan
    lat_min = float(np.nanmin(lat)) if lat.size else np.nan
    lat_max = float(np.nanmax(lat)) if lat.size else np.nan

    trip_writer.append(
        {
            "source_file": source_file,
            "trip_id": trip_id,
            "devid": devid,
            "point_count": point_count,
            "matched_segment_count": matched_segment_count,
            "route_edge_count": route_edge_count,
            "gps_start_ts": gps_start_ts,
            "gps_end_ts": gps_end_ts,
            "gps_start_time_utc": None,
            "gps_end_time_utc": None,
            "matched_start_ts": matched_start_ts,
            "matched_end_ts": matched_end_ts,
            "matched_start_time_utc": None,
            "matched_end_time_utc": None,
            "has_matched_segments": matched_segment_count > 0,
            "is_valid_trip": is_valid_trip,
            "invalid_reason": join_reasons(trip_reasons),
            "lon_min": lon_min,
            "lon_max": lon_max,
            "lat_min": lat_min,
            "lat_max": lat_max,
        }
    )

    for point_index in range(point_count):
        point_reasons: list[str] = []
        lon_raw = array_item_or_none(lon, point_index)
        lat_raw = array_item_or_none(lat, point_index)
        tms_raw = array_item_or_none(tms, point_index)
        lon_value = float(lon_raw) if lon_raw is not None else np.nan
        lat_value = float(lat_raw) if lat_raw is not None else np.nan
        tms_value = float(tms_raw) if tms_raw is not None else np.nan
        if lon_raw is None or lat_raw is None:
            point_reasons.append("point_length_mismatch")
        if not math.isfinite(lon_value) or not math.isfinite(lat_value):
            point_reasons.append("non_finite_coord")
        if math.isfinite(lon_value) and (lon_value < -180.0 or lon_value > 180.0):
            point_reasons.append("coord_out_of_range")
        if math.isfinite(lat_value) and (lat_value < -90.0 or lat_value > 90.0):
            if "coord_out_of_range" not in point_reasons:
                point_reasons.append("coord_out_of_range")
        if not math.isfinite(tms_value):
            point_reasons.append("non_finite_time")
        if tms_raw is None and "point_length_mismatch" not in point_reasons:
            point_reasons.append("point_length_mismatch")

        gps_point_writer.append(
            {
                "source_file": source_file,
                "trip_id": trip_id,
                "devid": devid,
                "point_index": point_index,
                "lon": lon_value if math.isfinite(lon_value) else np.nan,
                "lat": lat_value if math.isfinite(lat_value) else np.nan,
                "tms": to_int_or_none(tms_value),
                "gps_time_utc": None,
                "point_is_valid": len(point_reasons) == 0,
                "point_invalid_reason": join_reasons(point_reasons),
            }
        )

    route_heading_mismatch = len(route_heading) != route.shape[0]
    for route_index in range(route_edge_count):
        route_reasons: list[str] = []
        heading_value = list_item_or_none(route_heading, route_index)
        route_road_id = array_item_or_none(route, route_index)
        if route_heading_mismatch:
            route_reasons.append("route_heading_length_mismatch")
        if heading_value is None:
            route_reasons.append("missing_route_heading")
        if route_road_id is None:
            route_reasons.append("missing_route_road_id")

        route_edge_writer.append(
            {
                "source_file": source_file,
                "trip_id": trip_id,
                "devid": devid,
                "route_index": route_index,
                "route_road_id": to_int_or_none(route_road_id),
                "route_heading": heading_value,
                "route_edge_is_valid": len(route_reasons) == 0,
                "route_edge_invalid_reason": join_reasons(route_reasons),
            }
        )
    file_stats.total_route_edges += route_edge_count

    for route_geom_index, geom_value in enumerate(route_geom):
        route_geom_writer.append(
            {
                "source_file": source_file,
                "trip_id": trip_id,
                "devid": devid,
                "route_geom_index": route_geom_index,
                "route_geom_wkt": geom_value,
                "route_geom_is_valid": geom_value is not None,
                "route_geom_invalid_reason": None if geom_value is not None else "missing_route_geom",
            }
        )
    file_stats.total_route_geometries += len(route_geom)

    if matched_segment_count == 0:
        return

    aligned_geom, geom_mismatch = align_route_geometries(route_geom, matched_segment_count)
    if geom_mismatch:
        file_stats.route_geom_length_mismatch += 1

    trip_level_segment_reasons = list(trip_reasons)
    for segment_index in range(matched_segment_count):
        road_id = array_item_or_none(roads, segment_index)
        match_time_value = array_item_or_none(match_time, segment_index)
        frac_value = array_item_or_none(frac, segment_index)
        raw_frac = float(frac_value) if frac_value is not None else np.nan
        frac_missing = not math.isfinite(raw_frac)
        frac_clipped = np.clip(raw_frac, 0.0, 1.0) if not frac_missing else np.nan
        frac_out_of_range = not frac_missing and (raw_frac < 0.0 or raw_frac > 1.0)
        if frac_missing:
            file_stats.frac_missing += 1
        if frac_out_of_range:
            file_stats.frac_out_of_range += 1

        segment_reasons = list(trip_level_segment_reasons)
        if geom_mismatch:
            segment_reasons.append("route_geom_length_mismatch")
        if road_id is None or match_time_value is None or frac_value is None:
            segment_reasons.append("matched_length_mismatch")
        route_geom_wkt = aligned_geom[segment_index] if segment_index < len(aligned_geom) else None

        segment_writer.append(
            {
                "source_file": source_file,
                "trip_id": trip_id,
                "devid": devid,
                "segment_index": segment_index,
                "road_id": to_int_or_none(road_id),
                "match_ts": to_int_or_none(match_time_value),
                "match_time_utc": None,
                "frac": raw_frac if not frac_missing else np.nan,
                "frac_clipped": frac_clipped,
                "is_frac_imputed": False,
                "route_geom_wkt": route_geom_wkt,
                "segment_is_valid": len(segment_reasons) == 0,
                "segment_invalid_reason": join_reasons(segment_reasons),
            }
        )
        file_stats.total_segments += 1


def format_report(
    file_reports: dict[str, FileStats],
    invalid_reason_counter: Counter[str],
    point_counts: array,
    matched_counts: array,
) -> dict[str, Any]:
    total = FileStats()
    for stats in file_reports.values():
        total.total_trips += stats.total_trips
        total.valid_trips += stats.valid_trips
        total.invalid_trips += stats.invalid_trips
        total.empty_matched_trips += stats.empty_matched_trips
        total.total_points += stats.total_points
        total.total_segments += stats.total_segments
        total.total_route_edges += stats.total_route_edges
        total.total_route_geometries += stats.total_route_geometries
        total.frac_missing += stats.frac_missing
        total.frac_out_of_range += stats.frac_out_of_range
        total.point_length_mismatch += stats.point_length_mismatch
        total.matched_length_mismatch += stats.matched_length_mismatch
        total.coord_out_of_range += stats.coord_out_of_range
        total.non_finite_coord += stats.non_finite_coord
        total.non_finite_time += stats.non_finite_time
        total.non_monotonic_time += stats.non_monotonic_time
        total.route_geom_length_mismatch += stats.route_geom_length_mismatch

    file_summaries = {}
    for file_name, stats in file_reports.items():
        file_summaries[file_name] = {
            "total_trips": stats.total_trips,
            "valid_trips": stats.valid_trips,
            "invalid_trips": stats.invalid_trips,
            "empty_matched_trips": stats.empty_matched_trips,
            "total_points": stats.total_points,
            "total_segments": stats.total_segments,
            "total_route_edges": stats.total_route_edges,
            "total_route_geometries": stats.total_route_geometries,
            "frac_missing": stats.frac_missing,
            "frac_out_of_range": stats.frac_out_of_range,
            "point_length_mismatch": stats.point_length_mismatch,
            "matched_length_mismatch": stats.matched_length_mismatch,
            "coord_out_of_range": stats.coord_out_of_range,
            "non_finite_coord": stats.non_finite_coord,
            "non_finite_time": stats.non_finite_time,
            "non_monotonic_time": stats.non_monotonic_time,
            "route_geom_length_mismatch": stats.route_geom_length_mismatch,
        }

    return {
        "summary": {
            "total_trips": total.total_trips,
            "valid_trips": total.valid_trips,
            "invalid_trips": total.invalid_trips,
            "empty_matched_trips": total.empty_matched_trips,
            "total_points": total.total_points,
            "total_segments": total.total_segments,
            "total_route_edges": total.total_route_edges,
            "total_route_geometries": total.total_route_geometries,
            "frac_missing": total.frac_missing,
            "frac_out_of_range": total.frac_out_of_range,
            "point_length_mismatch": total.point_length_mismatch,
            "matched_length_mismatch": total.matched_length_mismatch,
            "coord_out_of_range": total.coord_out_of_range,
            "non_finite_coord": total.non_finite_coord,
            "non_finite_time": total.non_finite_time,
            "non_monotonic_time": total.non_monotonic_time,
            "route_geom_length_mismatch": total.route_geom_length_mismatch,
        },
        "invalid_reason_distribution": dict(invalid_reason_counter),
        "point_count_distribution": summarize_numeric(point_counts),
        "matched_segment_distribution": summarize_numeric(matched_counts),
        "files": file_summaries,
    }


def print_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("Cleaning summary")
    print(f"  total_trips: {summary['total_trips']}")
    print(f"  valid_trips: {summary['valid_trips']}")
    print(f"  invalid_trips: {summary['invalid_trips']}")
    print(f"  empty_matched_trips: {summary['empty_matched_trips']}")
    print(f"  total_points: {summary['total_points']}")
    print(f"  total_segments: {summary['total_segments']}")
    print(f"  total_route_edges: {summary['total_route_edges']}")
    print(f"  total_route_geometries: {summary['total_route_geometries']}")
    print(f"  frac_missing: {summary['frac_missing']}")
    print(f"  frac_out_of_range: {summary['frac_out_of_range']}")
    point_dist = report["point_count_distribution"]
    if point_dist:
        print(
            "  point_count_distribution:"
            f" min={point_dist['min']:.0f}"
            f" p50={point_dist['p50']:.0f}"
            f" p95={point_dist['p95']:.0f}"
            f" max={point_dist['max']:.0f}"
        )
    matched_dist = report["matched_segment_distribution"]
    if matched_dist:
        print(
            "  matched_segment_distribution:"
            f" min={matched_dist['min']:.0f}"
            f" p50={matched_dist['p50']:.0f}"
            f" p95={matched_dist['p95']:.0f}"
            f" max={matched_dist['max']:.0f}"
        )


def run(args: argparse.Namespace) -> None:
    input_files = discover_input_files(args.input_dir)
    if not input_files:
        raise FileNotFoundError(f"No .jld2 files found in {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trip_writer = BufferedParquetWriter(
        path=args.output_dir / "trips_clean.parquet",
        columns=TRIP_COLUMNS,
        schema=TRIP_SCHEMA,
        batch_size=args.trip_batch_size,
    )
    gps_point_writer = BufferedParquetWriter(
        path=args.output_dir / "gps_points_clean.parquet",
        columns=GPS_POINT_COLUMNS,
        schema=GPS_POINT_SCHEMA,
        batch_size=args.gps_point_batch_size,
    )
    segment_writer = BufferedParquetWriter(
        path=args.output_dir / "matched_segments_clean.parquet",
        columns=SEGMENT_COLUMNS,
        schema=SEGMENT_SCHEMA,
        batch_size=args.segment_batch_size,
    )
    route_edge_writer = BufferedParquetWriter(
        path=args.output_dir / "route_edges_clean.parquet",
        columns=ROUTE_EDGE_COLUMNS,
        schema=ROUTE_EDGE_SCHEMA,
        batch_size=args.route_edge_batch_size,
    )
    route_geom_writer = BufferedParquetWriter(
        path=args.output_dir / "route_geometries_clean.parquet",
        columns=ROUTE_GEOM_COLUMNS,
        schema=ROUTE_GEOM_SCHEMA,
        batch_size=args.route_geom_batch_size,
    )

    point_counts = array("I")
    matched_counts = array("I")
    invalid_reason_counter: Counter[str] = Counter()
    file_reports: dict[str, FileStats] = {}

    try:
        for input_file in input_files:
            source_file = input_file.name
            file_reports[source_file] = FileStats()
            with h5py.File(input_file, "r") as file_handle:
                trip_count = int(file_handle["trips"].shape[0])
                if args.max_trips_per_file is not None:
                    trip_count = min(trip_count, args.max_trips_per_file)
                print(f"Processing {source_file} ({trip_count} trips)")
                for trip_index in range(trip_count):
                    process_trip(
                        file_handle=file_handle,
                        source_file=source_file,
                        trip_index=trip_index,
                        trip_writer=trip_writer,
                        gps_point_writer=gps_point_writer,
                        segment_writer=segment_writer,
                        route_edge_writer=route_edge_writer,
                        route_geom_writer=route_geom_writer,
                        file_stats=file_reports[source_file],
                        invalid_reason_counter=invalid_reason_counter,
                        point_counts=point_counts,
                        matched_counts=matched_counts,
                    )
                    if args.progress_every and (trip_index + 1) % args.progress_every == 0:
                        print(f"  processed {trip_index + 1}/{trip_count} trips")
    finally:
        trip_writer.close()
        gps_point_writer.close()
        segment_writer.close()
        route_edge_writer.close()
        route_geom_writer.close()

    report = format_report(
        file_reports=file_reports,
        invalid_reason_counter=invalid_reason_counter,
        point_counts=point_counts,
        matched_counts=matched_counts,
    )
    report_path = args.output_dir / "cleaning_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print_report(report)
    print(f"Wrote {args.output_dir / 'trips_clean.parquet'}")
    print(f"Wrote {args.output_dir / 'gps_points_clean.parquet'}")
    print(f"Wrote {args.output_dir / 'matched_segments_clean.parquet'}")
    print(f"Wrote {args.output_dir / 'route_edges_clean.parquet'}")
    print(f"Wrote {args.output_dir / 'route_geometries_clean.parquet'}")
    print(f"Wrote {report_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read map-matched JLD2 trip files, clean them, and write standardized parquet tables."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory containing .jld2 files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "cleaned_output",
        help="Directory for cleaned parquet outputs.",
    )
    parser.add_argument(
        "--trip-batch-size",
        type=int,
        default=50000,
        help="Number of trip rows buffered before flushing to parquet.",
    )
    parser.add_argument(
        "--segment-batch-size",
        type=int,
        default=200000,
        help="Number of segment rows buffered before flushing to parquet.",
    )
    parser.add_argument(
        "--gps-point-batch-size",
        type=int,
        default=300000,
        help="Number of gps point rows buffered before flushing to parquet.",
    )
    parser.add_argument(
        "--route-edge-batch-size",
        type=int,
        default=300000,
        help="Number of route edge rows buffered before flushing to parquet.",
    )
    parser.add_argument(
        "--route-geom-batch-size",
        type=int,
        default=200000,
        help="Number of route geometry rows buffered before flushing to parquet.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=50000,
        help="Print progress every N trips. Use 0 to disable.",
    )
    parser.add_argument(
        "--max-trips-per-file",
        type=int,
        default=None,
        help="Optional cap for smoke tests.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())

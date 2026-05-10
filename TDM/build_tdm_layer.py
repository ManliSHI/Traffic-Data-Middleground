from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb


ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "tdm_output"
TEMP_DIR = OUTPUT_DIR / "_duckdb_tmp"

TRIPS_PATH = (ROOT_DIR / "trips_clean.parquet").as_posix()
GPS_PATH = (ROOT_DIR / "gps_points_clean.parquet").as_posix()
MATCHED_PATH = (ROOT_DIR / "matched_segments_clean.parquet").as_posix()
ROUTE_EDGES_PATH = (ROOT_DIR / "route_edges_clean.parquet").as_posix()

EXPECTED_ROW_COUNTS = {
    "tdm_trip_profile": 1_199_531,
    "tdm_vehicle_day_profile": 55_265,
    "tdm_vehicle_5d_profile": 12_472,
    "tdm_vehicle_road_preference_5d": 124_573,
    "tdm_road_day_profile": 83_478,
    "tdm_time_slot_day_profile": 120,
    "tdm_region_grid_day_profile": 2_241,
}

OUTPUT_FILES = {
    "tdm_trip_profile": OUTPUT_DIR / "tdm_trip_profile.parquet",
    "tdm_vehicle_day_profile": OUTPUT_DIR / "tdm_vehicle_day_profile.parquet",
    "tdm_vehicle_5d_profile": OUTPUT_DIR / "tdm_vehicle_5d_profile.parquet",
    "tdm_vehicle_road_preference_5d": OUTPUT_DIR / "tdm_vehicle_road_preference_5d.parquet",
    "tdm_road_day_profile": OUTPUT_DIR / "tdm_road_day_profile.parquet",
    "tdm_time_slot_day_profile": OUTPUT_DIR / "tdm_time_slot_day_profile.parquet",
    "tdm_region_grid_day_profile": OUTPUT_DIR / "tdm_region_grid_day_profile.parquet",
    "tdm_tag_definition": OUTPUT_DIR / "tdm_tag_definition.csv",
    "tdm_build_summary": OUTPUT_DIR / "tdm_build_summary.json",
}

SOURCE_FILES = [
    "trips_clean.parquet",
    "gps_points_clean.parquet",
    "matched_segments_clean.parquet",
    "route_edges_clean.parquet",
    "route_geometries_clean.parquet",
]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def sql_literal(path: Path | str) -> str:
    if isinstance(path, Path):
        return path.as_posix().replace("'", "''")
    return str(path).replace("'", "''")


def time_period_case(hour_expr: str) -> str:
    return f"""
        CASE
            WHEN {hour_expr} IN (22, 23, 0, 1, 2, 3, 4, 5) THEN 'night'
            WHEN {hour_expr} IN (7, 8, 9) THEN 'morning_peak'
            WHEN {hour_expr} IN (17, 18, 19) THEN 'evening_peak'
            WHEN {hour_expr} IN (10, 11, 12, 13, 14, 15, 16) THEN 'daytime'
            ELSE 'shoulder'
        END
    """


@dataclass(frozen=True)
class TagDefinition:
    object_type: str
    table_name: str
    tag_code: str
    tag_name: str
    tag_value_type: str
    tag_level: str
    calc_logic: str
    source_table: str
    refresh_cycle: str = "batch_once_for_homework"


def build_tag_definitions(output_path: Path) -> int:
    tags = [
        TagDefinition("trip", "tdm_trip_profile", "stat_date", "统计日期", "date", "trip", "从 source_file 的 trips_YYMMDD.jld2 解析业务日期", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "biz_start_time", "业务开始时间", "timestamp", "trip", "优先取 matched_start_time_utc，无匹配时取 gps_start_time_utc - 8 小时", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "biz_end_time", "业务结束时间", "timestamp", "trip", "优先取 matched_end_time_utc，无匹配时取 gps_end_time_utc - 8 小时", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "biz_start_hour", "业务开始小时", "integer", "trip", "extract(hour from biz_start_time)", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "biz_end_hour", "业务结束小时", "integer", "trip", "extract(hour from biz_end_time)", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "time_period_type", "出行时段类型", "string", "trip", "按 biz_start_hour 映射为 night、morning_peak、evening_peak、daytime、shoulder", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "trip_duration_min", "行程时长分钟数", "double", "trip", "(gps_end_ts - gps_start_ts) / 60.0", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "trip_distance_km", "行程距离公里数", "double", "trip", "同 trip 相邻 GPS 点按 haversine 计算并过滤异常 step 后求和", "gps_points_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "avg_speed_kmh", "平均速度", "double", "trip", "trip_distance_km / (trip_duration_min / 60.0)，时长非正时为空", "trips_clean.parquet;gps_points_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "unique_road_cnt", "唯一路段数", "integer", "trip", "valid matched segments 上 count(distinct road_id)", "matched_segments_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "road_repeat_ratio", "路段重复比", "double", "trip", "1 - unique_road_cnt / matched_segment_count，空匹配时记 0", "matched_segments_clean.parquet;trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "forward_edge_cnt", "正向边数量", "integer", "trip", "valid route edges 中 route_heading = forward 的数量", "route_edges_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "backward_edge_cnt", "反向边数量", "integer", "trip", "valid route edges 中 route_heading = backward 的数量", "route_edges_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "forward_edge_ratio", "正向边占比", "double", "trip", "forward_edge_cnt / (forward_edge_cnt + backward_edge_cnt)，分母为 0 时为空", "route_edges_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "night_trip_flag", "夜间出行标记", "boolean", "trip", "biz_start_hour 属于 22,23,0-5", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "morning_peak_trip_flag", "早高峰出行标记", "boolean", "trip", "biz_start_hour 属于 7,8,9", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "evening_peak_trip_flag", "晚高峰出行标记", "boolean", "trip", "biz_start_hour 属于 17,18,19", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "peak_trip_flag", "高峰出行标记", "boolean", "trip", "morning_peak_trip_flag 或 evening_peak_trip_flag", "trips_clean.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "trip_distance_level", "行程距离分层", "string", "trip", "按阈值 2.89、5.74、11.46 划分 short、medium、long、extra_long", "tdm_trip_profile.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "trip_duration_level", "行程时长分层", "string", "trip", "按阈值 9.15、16.22、31.30 划分 short、medium、long、extra_long", "tdm_trip_profile.parquet"),
        TagDefinition("trip", "tdm_trip_profile", "trip_speed_level", "行程速度分层", "string", "trip", "按阈值 16.04、20.41、25.35 划分 slow、normal、fast、very_fast", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "trip_cnt", "当日出行次数", "integer", "vehicle_day", "设备在 stat_date 的 trip 数", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "matched_trip_cnt", "当日有匹配出行次数", "integer", "vehicle_day", "设备在 stat_date 且 has_matched_segments = true 的 trip 数", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "matched_trip_ratio", "当日有匹配出行占比", "double", "vehicle_day", "matched_trip_cnt / trip_cnt", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "total_distance_km", "当日总里程", "double", "vehicle_day", "当日 trip_distance_km 求和", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "total_duration_min", "当日总时长分钟数", "double", "vehicle_day", "当日 trip_duration_min 求和", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "avg_trip_distance_km", "当日平均单次里程", "double", "vehicle_day", "total_distance_km / trip_cnt", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "avg_trip_duration_min", "当日平均单次时长", "double", "vehicle_day", "total_duration_min / trip_cnt", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "avg_speed_kmh", "当日综合平均速度", "double", "vehicle_day", "total_distance_km / (total_duration_min / 60.0)", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "active_hour_cnt", "当日活跃小时数", "integer", "vehicle_day", "count(distinct biz_start_hour)", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "road_coverage_cnt", "当日覆盖路段数", "integer", "vehicle_day", "valid matched segments 上 count(distinct road_id)", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "night_trip_cnt", "当日夜间出行次数", "integer", "vehicle_day", "night_trip_flag = true 的 trip 数", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "night_trip_ratio", "当日夜间出行占比", "double", "vehicle_day", "night_trip_cnt / trip_cnt", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "morning_peak_trip_cnt", "当日早高峰出行次数", "integer", "vehicle_day", "morning_peak_trip_flag = true 的 trip 数", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "evening_peak_trip_cnt", "当日晚高峰出行次数", "integer", "vehicle_day", "evening_peak_trip_flag = true 的 trip 数", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "peak_trip_cnt", "当日高峰出行次数", "integer", "vehicle_day", "peak_trip_flag = true 的 trip 数", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "peak_trip_ratio", "当日高峰出行占比", "double", "vehicle_day", "peak_trip_cnt / trip_cnt", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "dominant_time_period", "当日主导时段", "string", "vehicle_day", "trip 数最多的 time_period_type，并按字典序做并列打破", "tdm_trip_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "trip_frequency_level", "当日出行频次分层", "string", "vehicle_day", "按阈值 14、20、28 划分 low、medium、high、very_high", "tdm_vehicle_day_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "night_activity_flag", "夜间活跃标记", "boolean", "vehicle_day", "night_trip_ratio >= 0.22", "tdm_vehicle_day_profile.parquet"),
        TagDefinition("vehicle_day", "tdm_vehicle_day_profile", "peak_activity_flag", "高峰活跃标记", "boolean", "vehicle_day", "peak_trip_ratio >= 0.39", "tdm_vehicle_day_profile.parquet"),
    ]

    tags.extend(
        [
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "active_day_cnt", "活跃天数", "integer", "vehicle_5d", "count(distinct stat_date)", "tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "total_trip_cnt", "五天总出行次数", "integer", "vehicle_5d", "五天 trip 数", "tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "avg_daily_trip_cnt", "日均出行次数", "double", "vehicle_5d", "total_trip_cnt / active_day_cnt", "tdm_vehicle_5d_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "total_distance_km", "五天总里程", "double", "vehicle_5d", "五天 trip_distance_km 求和", "tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "total_duration_min", "五天总时长分钟数", "double", "vehicle_5d", "五天 trip_duration_min 求和", "tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "avg_trip_distance_km", "五天平均单次里程", "double", "vehicle_5d", "total_distance_km / total_trip_cnt", "tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "avg_speed_kmh", "五天综合平均速度", "double", "vehicle_5d", "total_distance_km / (total_duration_min / 60.0)", "tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "night_trip_ratio_5d", "五天夜间出行占比", "double", "vehicle_5d", "五天夜间 trip 数 / total_trip_cnt", "tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "peak_trip_ratio_5d", "五天高峰出行占比", "double", "vehicle_5d", "五天高峰 trip 数 / total_trip_cnt", "tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "road_coverage_cnt_5d", "五天覆盖路段数", "integer", "vehicle_5d", "valid matched segments 上五天 count(distinct road_id)", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "dominant_time_period_5d", "五天主导时段", "string", "vehicle_5d", "五天累计 trip 数最多的 time_period_type，并按字典序做并列打破", "tdm_trip_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "driver_activity_level", "司机活跃度分层", "string", "vehicle_5d", "按阈值 65、84、116 划分 low、medium、high、core", "tdm_vehicle_5d_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "core_driver_flag", "核心司机标记", "boolean", "vehicle_5d", "total_trip_cnt >= 116", "tdm_vehicle_5d_profile.parquet"),
            TagDefinition("vehicle_5d", "tdm_vehicle_5d_profile", "full_attendance_flag", "满勤标记", "boolean", "vehicle_5d", "active_day_cnt = 5", "tdm_vehicle_5d_profile.parquet"),
            TagDefinition("vehicle_road_preference_5d", "tdm_vehicle_road_preference_5d", "rank_in_device", "设备内道路排名", "integer", "vehicle_road_preference_5d", "按 pass_cnt desc, road_id asc 排名", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("vehicle_road_preference_5d", "tdm_vehicle_road_preference_5d", "pass_cnt", "通行次数", "integer", "vehicle_road_preference_5d", "五天 valid matched segments 上 count(*)", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("vehicle_road_preference_5d", "tdm_vehicle_road_preference_5d", "pass_ratio", "通行占比", "double", "vehicle_road_preference_5d", "pass_cnt / 设备五天有效 segment 总数", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("vehicle_road_preference_5d", "tdm_vehicle_road_preference_5d", "active_day_cnt_on_road", "道路活跃天数", "integer", "vehicle_road_preference_5d", "count(distinct stat_date)", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("vehicle_road_preference_5d", "tdm_vehicle_road_preference_5d", "preference_level", "道路偏好级别", "string", "vehicle_road_preference_5d", "rank 1-3 为 core_route，4-10 为 frequent_route", "tdm_vehicle_road_preference_5d.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "pass_cnt", "路段通行次数", "integer", "road_day", "road_id + stat_date 上 valid matched segments count(*)", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "vehicle_cnt", "路段通行车辆数", "integer", "road_day", "road_id + stat_date 上 count(distinct devid)", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "trip_cnt", "路段涉及行程数", "integer", "road_day", "road_id + stat_date 上 count(distinct trip_id)", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "morning_peak_pass_cnt", "早高峰通行次数", "integer", "road_day", "morning_peak_trip_flag = true 的 valid matched segments 数", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "evening_peak_pass_cnt", "晚高峰通行次数", "integer", "road_day", "evening_peak_trip_flag = true 的 valid matched segments 数", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "night_pass_cnt", "夜间通行次数", "integer", "road_day", "night_trip_flag = true 的 valid matched segments 数", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "peak_pass_ratio", "高峰通行占比", "double", "road_day", "(morning_peak_pass_cnt + evening_peak_pass_cnt) / pass_cnt", "tdm_road_day_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "forward_edge_cnt", "正向边数量", "integer", "road_day", "road_id + stat_date 上 valid route edges 中 forward 数量", "route_edges_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "backward_edge_cnt", "反向边数量", "integer", "road_day", "road_id + stat_date 上 valid route edges 中 backward 数量", "route_edges_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "forward_ratio", "正向边占比", "double", "road_day", "forward_edge_cnt / (forward_edge_cnt + backward_edge_cnt)", "tdm_road_day_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "direction_bias", "方向偏向类型", "string", "road_day", "forward_ratio >= 0.80 为 mainly_forward，<= 0.20 为 mainly_backward，否则 balanced", "tdm_road_day_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "road_activity_level", "路段活跃度分层", "string", "road_day", "按 pass_cnt 阈值 13、91、454 划分 long_tail、normal、active、hot", "tdm_road_day_profile.parquet"),
            TagDefinition("road_day", "tdm_road_day_profile", "peak_bias_type", "时段偏向类型", "string", "road_day", "比较 morning_peak、evening_peak、night、offpeak 的 pass 数并按指定优先级选最大", "tdm_road_day_profile.parquet"),
        ]
    )

    tags.extend(
        [
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "time_range_id", "时间范围标识", "string", "time_slot_day", "YYYY-MM-DD_HH", "tdm_time_slot_day_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "time_period_type", "小时所属时段类型", "string", "time_slot_day", "按 biz_hour 映射为 night、morning_peak、evening_peak、daytime、shoulder", "tdm_time_slot_day_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "trip_cnt", "小时行程数", "integer", "time_slot_day", "stat_date + biz_hour 上 trip 数", "tdm_trip_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "matched_trip_cnt", "小时有匹配行程数", "integer", "time_slot_day", "stat_date + biz_hour 上 has_matched_segments = true 的 trip 数", "tdm_trip_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "vehicle_cnt", "小时活跃车辆数", "integer", "time_slot_day", "stat_date + biz_hour 上 count(distinct devid)", "tdm_trip_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "total_distance_km", "小时总里程", "double", "time_slot_day", "stat_date + biz_hour 上 trip_distance_km 求和", "tdm_trip_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "total_duration_min", "小时总时长分钟数", "double", "time_slot_day", "stat_date + biz_hour 上 trip_duration_min 求和", "tdm_trip_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "avg_trip_distance_km", "小时平均单次里程", "double", "time_slot_day", "total_distance_km / trip_cnt", "tdm_time_slot_day_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "avg_trip_duration_min", "小时平均单次时长", "double", "time_slot_day", "total_duration_min / trip_cnt", "tdm_time_slot_day_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "avg_speed_kmh", "小时综合平均速度", "double", "time_slot_day", "total_distance_km / (total_duration_min / 60.0)", "tdm_time_slot_day_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "road_coverage_cnt", "小时覆盖路段数", "integer", "time_slot_day", "stat_date + biz_hour 上 valid matched segments 的 distinct road_id 数", "matched_segments_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("time_slot_day", "tdm_time_slot_day_profile", "slot_activity_level", "小时活跃度分层", "string", "time_slot_day", "按 trip_cnt 阈值 5936、9612、15022 划分 low、medium、high、hot", "tdm_time_slot_day_profile.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "grid_center_lon", "网格中心经度", "double", "region_grid_day", "grid_x = floor(lon / 0.01)，中心经度为 (grid_x + 0.5) * 0.01", "gps_points_clean.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "grid_center_lat", "网格中心纬度", "double", "region_grid_day", "grid_y = floor(lat / 0.01)，中心纬度为 (grid_y + 0.5) * 0.01", "gps_points_clean.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "pickup_trip_cnt", "上车次数", "integer", "region_grid_day", "pickup 端落在该网格的 trip 数", "gps_points_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "dropoff_trip_cnt", "下车次数", "integer", "region_grid_day", "dropoff 端落在该网格的 trip 数", "gps_points_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "total_od_trip_cnt", "OD 总次数", "integer", "region_grid_day", "pickup_trip_cnt + dropoff_trip_cnt", "tdm_region_grid_day_profile.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "active_vehicle_cnt", "活跃车辆数", "integer", "region_grid_day", "网格 OD 事件上的 distinct devid 数", "gps_points_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "night_od_trip_cnt", "夜间 OD 次数", "integer", "region_grid_day", "night_trip_flag = true 的 pickup/dropoff 事件数", "gps_points_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "peak_od_trip_cnt", "高峰 OD 次数", "integer", "region_grid_day", "peak_trip_flag = true 的 pickup/dropoff 事件数", "gps_points_clean.parquet;tdm_trip_profile.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "pickup_ratio", "上车占比", "double", "region_grid_day", "pickup_trip_cnt / total_od_trip_cnt", "tdm_region_grid_day_profile.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "grid_role_bias", "网格角色偏向", "string", "region_grid_day", "pickup_ratio >= 0.60 为 pickup_dominant，<= 0.40 为 dropoff_dominant，否则 balanced", "tdm_region_grid_day_profile.parquet"),
            TagDefinition("region_grid_day", "tdm_region_grid_day_profile", "grid_activity_level", "网格活跃度分层", "string", "region_grid_day", "按 total_od_trip_cnt 阈值 26、171、1127 划分 long_tail、normal、active、hotspot", "tdm_region_grid_day_profile.parquet"),
        ]
    )

    fieldnames = [
        "object_type",
        "table_name",
        "tag_code",
        "tag_name",
        "tag_value_type",
        "tag_level",
        "calc_logic",
        "source_table",
        "refresh_cycle",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for tag in tags:
            writer.writerow(tag.__dict__)
    return len(tags)


def execute(conn: duckdb.DuckDBPyConnection, query: str, message: str) -> None:
    log(message)
    conn.execute(query)


def copy_table(conn: duckdb.DuckDBPyConnection, table_name: str, output_path: Path) -> None:
    log(f"Writing {output_path.name}")
    conn.execute(
        f"COPY (SELECT * FROM {table_name}) TO '{sql_literal(output_path)}' "
        "(FORMAT PARQUET, COMPRESSION ZSTD)"
    )


def setup_connection() -> duckdb.DuckDBPyConnection:
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)
    conn = duckdb.connect()
    conn.execute("PRAGMA threads=4")
    conn.execute(f"PRAGMA temp_directory='{sql_literal(TEMP_DIR)}'")
    conn.execute("PRAGMA enable_progress_bar=false")
    return conn


def create_base_views(conn: duckdb.DuckDBPyConnection) -> None:
    execute(
        conn,
        f"""
        CREATE OR REPLACE TEMP VIEW trips_src AS
        SELECT * FROM read_parquet('{TRIPS_PATH}')
        """,
        "Loading trip source view",
    )
    execute(
        conn,
        f"""
        CREATE OR REPLACE TEMP VIEW gps_src AS
        SELECT * FROM read_parquet('{GPS_PATH}')
        """,
        "Loading GPS source view",
    )
    execute(
        conn,
        f"""
        CREATE OR REPLACE TEMP VIEW matched_src AS
        SELECT * FROM read_parquet('{MATCHED_PATH}')
        """,
        "Loading matched-segment source view",
    )
    execute(
        conn,
        f"""
        CREATE OR REPLACE TEMP VIEW route_edges_src AS
        SELECT * FROM read_parquet('{ROUTE_EDGES_PATH}')
        """,
        "Loading route-edge source view",
    )


def build_trip_intermediates(conn: duckdb.DuckDBPyConnection) -> None:
    execute(
        conn,
        f"""
        CREATE OR REPLACE TEMP TABLE trip_base AS
        WITH base AS (
            SELECT
                source_file,
                trip_id,
                devid,
                point_count,
                matched_segment_count,
                route_edge_count,
                has_matched_segments,
                gps_start_ts,
                gps_end_ts,
                gps_start_time_utc,
                gps_end_time_utc,
                matched_start_time_utc,
                matched_end_time_utc,
                CAST(
                    strptime(
                        regexp_extract(source_file, 'trips_(\\d{{6}})\\.jld2', 1),
                        '%y%m%d'
                    ) AS DATE
                ) AS stat_date,
                COALESCE(matched_start_time_utc, gps_start_time_utc - INTERVAL 8 HOUR) AS biz_start_time,
                COALESCE(matched_end_time_utc, gps_end_time_utc - INTERVAL 8 HOUR) AS biz_end_time,
                (gps_end_ts - gps_start_ts) / 60.0 AS trip_duration_min
            FROM trips_src
        )
        SELECT
            source_file,
            trip_id,
            devid,
            point_count,
            matched_segment_count,
            route_edge_count,
            has_matched_segments,
            gps_start_ts,
            gps_end_ts,
            gps_start_time_utc,
            gps_end_time_utc,
            matched_start_time_utc,
            matched_end_time_utc,
            stat_date,
            biz_start_time,
            biz_end_time,
            CAST(EXTRACT(HOUR FROM biz_start_time) AS INTEGER) AS biz_start_hour,
            CAST(EXTRACT(HOUR FROM biz_end_time) AS INTEGER) AS biz_end_hour,
            {time_period_case("CAST(EXTRACT(HOUR FROM biz_start_time) AS INTEGER)")} AS time_period_type,
            trip_duration_min,
            CAST({time_period_case("CAST(EXTRACT(HOUR FROM biz_start_time) AS INTEGER)")} = 'night' AS BOOLEAN) AS night_trip_flag,
            CAST({time_period_case("CAST(EXTRACT(HOUR FROM biz_start_time) AS INTEGER)")} = 'morning_peak' AS BOOLEAN) AS morning_peak_trip_flag,
            CAST({time_period_case("CAST(EXTRACT(HOUR FROM biz_start_time) AS INTEGER)")} = 'evening_peak' AS BOOLEAN) AS evening_peak_trip_flag,
            CAST(
                {time_period_case("CAST(EXTRACT(HOUR FROM biz_start_time) AS INTEGER)")} IN ('morning_peak', 'evening_peak')
                AS BOOLEAN
            ) AS peak_trip_flag
        FROM base
        """,
        "Building trip_base",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE trip_distance_base AS
        WITH ordered_points AS (
            SELECT
                trip_id,
                point_index,
                lon,
                lat,
                tms,
                point_is_valid,
                LAG(lon) OVER (PARTITION BY trip_id ORDER BY point_index) AS prev_lon,
                LAG(lat) OVER (PARTITION BY trip_id ORDER BY point_index) AS prev_lat,
                LAG(tms) OVER (PARTITION BY trip_id ORDER BY point_index) AS prev_tms,
                LAG(point_is_valid) OVER (PARTITION BY trip_id ORDER BY point_index) AS prev_point_is_valid
            FROM gps_src
        ),
        step_metrics AS (
            SELECT
                trip_id,
                point_is_valid,
                prev_point_is_valid,
                tms - prev_tms AS delta_t_sec,
                CASE
                    WHEN prev_lon IS NULL OR prev_lat IS NULL THEN NULL
                    ELSE 2 * 6371.0 * ASIN(
                        SQRT(
                            POW(SIN(RADIANS(lat - prev_lat) / 2.0), 2) +
                            COS(RADIANS(prev_lat)) * COS(RADIANS(lat)) *
                            POW(SIN(RADIANS(lon - prev_lon) / 2.0), 2)
                        )
                    )
                END AS step_dist_km
            FROM ordered_points
        )
        SELECT
            trip_id,
            COALESCE(
                SUM(
                    CASE
                        WHEN point_is_valid
                             AND COALESCE(prev_point_is_valid, FALSE)
                             AND delta_t_sec > 0
                             AND delta_t_sec <= 180
                             AND (step_dist_km / (delta_t_sec / 3600.0)) <= 100
                        THEN step_dist_km
                        ELSE 0.0
                    END
                ),
                0.0
            ) AS trip_distance_km
        FROM step_metrics
        GROUP BY trip_id
        """,
        "Building trip_distance_base from GPS points",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE trip_road_base AS
        SELECT
            trip_id,
            COUNT(DISTINCT road_id) AS unique_road_cnt
        FROM matched_src
        WHERE segment_is_valid
          AND road_id IS NOT NULL
        GROUP BY trip_id
        """,
        "Building trip_road_base from valid matched segments",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE trip_edge_base AS
        SELECT
            trip_id,
            SUM(CASE WHEN route_heading = 'forward' THEN 1 ELSE 0 END) AS forward_edge_cnt,
            SUM(CASE WHEN route_heading = 'backward' THEN 1 ELSE 0 END) AS backward_edge_cnt
        FROM route_edges_src
        WHERE route_edge_is_valid
        GROUP BY trip_id
        """,
        "Building trip_edge_base from valid route edges",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE trip_od_base AS
        SELECT
            trip_id,
            arg_min(lon, point_index) AS pickup_lon,
            arg_min(lat, point_index) AS pickup_lat,
            arg_max(lon, point_index) AS dropoff_lon,
            arg_max(lat, point_index) AS dropoff_lat
        FROM gps_src
        GROUP BY trip_id
        """,
        "Building trip_od_base from trip endpoints",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE matched_valid_enriched AS
        SELECT
            m.trip_id,
            t.devid,
            t.stat_date,
            t.biz_start_hour,
            t.time_period_type,
            t.night_trip_flag,
            t.morning_peak_trip_flag,
            t.evening_peak_trip_flag,
            t.peak_trip_flag,
            m.road_id
        FROM matched_src AS m
        INNER JOIN trip_base AS t
            ON t.trip_id = m.trip_id
        WHERE m.segment_is_valid
          AND m.road_id IS NOT NULL
        """,
        "Building matched_valid_enriched helper table",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE route_edges_valid_enriched AS
        SELECT
            r.trip_id,
            t.stat_date,
            r.route_road_id AS road_id,
            r.route_heading
        FROM route_edges_src AS r
        INNER JOIN trip_base AS t
            ON t.trip_id = r.trip_id
        WHERE r.route_edge_is_valid
          AND r.route_road_id IS NOT NULL
        """,
        "Building route_edges_valid_enriched helper table",
    )


def build_trip_profile(conn: duckdb.DuckDBPyConnection) -> None:
    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE tdm_trip_profile AS
        SELECT
            t.trip_id,
            t.devid,
            t.source_file,
            t.stat_date,
            t.biz_start_time,
            t.biz_end_time,
            t.biz_start_hour,
            t.biz_end_hour,
            t.time_period_type,
            t.point_count,
            t.matched_segment_count,
            t.route_edge_count,
            t.has_matched_segments,
            t.trip_duration_min,
            COALESCE(d.trip_distance_km, 0.0) AS trip_distance_km,
            CASE
                WHEN t.trip_duration_min > 0 THEN COALESCE(d.trip_distance_km, 0.0) / (t.trip_duration_min / 60.0)
                ELSE NULL
            END AS avg_speed_kmh,
            COALESCE(r.unique_road_cnt, 0) AS unique_road_cnt,
            CASE
                WHEN t.matched_segment_count > 0 THEN 1.0 - (COALESCE(r.unique_road_cnt, 0)::DOUBLE / t.matched_segment_count)
                ELSE 0.0
            END AS road_repeat_ratio,
            COALESCE(e.forward_edge_cnt, 0) AS forward_edge_cnt,
            COALESCE(e.backward_edge_cnt, 0) AS backward_edge_cnt,
            CASE
                WHEN COALESCE(e.forward_edge_cnt, 0) + COALESCE(e.backward_edge_cnt, 0) > 0
                THEN COALESCE(e.forward_edge_cnt, 0)::DOUBLE /
                    (COALESCE(e.forward_edge_cnt, 0) + COALESCE(e.backward_edge_cnt, 0))
                ELSE NULL
            END AS forward_edge_ratio,
            t.night_trip_flag,
            t.morning_peak_trip_flag,
            t.evening_peak_trip_flag,
            t.peak_trip_flag,
            CASE
                WHEN COALESCE(d.trip_distance_km, 0.0) < 2.89 THEN 'short'
                WHEN COALESCE(d.trip_distance_km, 0.0) < 5.74 THEN 'medium'
                WHEN COALESCE(d.trip_distance_km, 0.0) < 11.46 THEN 'long'
                ELSE 'extra_long'
            END AS trip_distance_level,
            CASE
                WHEN t.trip_duration_min < 9.15 THEN 'short'
                WHEN t.trip_duration_min < 16.22 THEN 'medium'
                WHEN t.trip_duration_min < 31.30 THEN 'long'
                ELSE 'extra_long'
            END AS trip_duration_level,
            CASE
                WHEN CASE
                    WHEN t.trip_duration_min > 0 THEN COALESCE(d.trip_distance_km, 0.0) / (t.trip_duration_min / 60.0)
                    ELSE NULL
                END IS NULL THEN NULL
                WHEN COALESCE(d.trip_distance_km, 0.0) / (t.trip_duration_min / 60.0) < 16.04 THEN 'slow'
                WHEN COALESCE(d.trip_distance_km, 0.0) / (t.trip_duration_min / 60.0) < 20.41 THEN 'normal'
                WHEN COALESCE(d.trip_distance_km, 0.0) / (t.trip_duration_min / 60.0) < 25.35 THEN 'fast'
                ELSE 'very_fast'
            END AS trip_speed_level
        FROM trip_base AS t
        LEFT JOIN trip_distance_base AS d
            ON d.trip_id = t.trip_id
        LEFT JOIN trip_road_base AS r
            ON r.trip_id = t.trip_id
        LEFT JOIN trip_edge_base AS e
            ON e.trip_id = t.trip_id
        """,
        "Building tdm_trip_profile",
    )


def build_vehicle_profiles(conn: duckdb.DuckDBPyConnection) -> None:
    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE vehicle_day_road_coverage AS
        SELECT
            devid,
            stat_date,
            COUNT(DISTINCT road_id) AS road_coverage_cnt
        FROM matched_valid_enriched
        GROUP BY devid, stat_date
        """,
        "Building vehicle_day_road_coverage",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE vehicle_day_dominant_period AS
        WITH period_counts AS (
            SELECT
                devid,
                stat_date,
                time_period_type,
                COUNT(*) AS period_trip_cnt
            FROM tdm_trip_profile
            GROUP BY devid, stat_date, time_period_type
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY devid, stat_date
                    ORDER BY period_trip_cnt DESC, time_period_type ASC
                ) AS rn
            FROM period_counts
        )
        SELECT
            devid,
            stat_date,
            time_period_type AS dominant_time_period
        FROM ranked
        WHERE rn = 1
        """,
        "Building vehicle_day_dominant_period",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE tdm_vehicle_day_profile AS
        WITH agg AS (
            SELECT
                devid,
                stat_date,
                COUNT(*) AS trip_cnt,
                SUM(CASE WHEN has_matched_segments THEN 1 ELSE 0 END) AS matched_trip_cnt,
                SUM(trip_distance_km) AS total_distance_km,
                SUM(trip_duration_min) AS total_duration_min,
                COUNT(DISTINCT biz_start_hour) AS active_hour_cnt,
                SUM(CASE WHEN night_trip_flag THEN 1 ELSE 0 END) AS night_trip_cnt,
                SUM(CASE WHEN morning_peak_trip_flag THEN 1 ELSE 0 END) AS morning_peak_trip_cnt,
                SUM(CASE WHEN evening_peak_trip_flag THEN 1 ELSE 0 END) AS evening_peak_trip_cnt,
                SUM(CASE WHEN peak_trip_flag THEN 1 ELSE 0 END) AS peak_trip_cnt
            FROM tdm_trip_profile
            GROUP BY devid, stat_date
        )
        SELECT
            a.devid,
            a.stat_date,
            a.trip_cnt,
            a.matched_trip_cnt,
            a.matched_trip_cnt::DOUBLE / a.trip_cnt AS matched_trip_ratio,
            a.total_distance_km,
            a.total_duration_min,
            a.total_distance_km / a.trip_cnt AS avg_trip_distance_km,
            a.total_duration_min / a.trip_cnt AS avg_trip_duration_min,
            CASE
                WHEN a.total_duration_min > 0 THEN a.total_distance_km / (a.total_duration_min / 60.0)
                ELSE NULL
            END AS avg_speed_kmh,
            a.active_hour_cnt,
            COALESCE(r.road_coverage_cnt, 0) AS road_coverage_cnt,
            a.night_trip_cnt,
            a.night_trip_cnt::DOUBLE / a.trip_cnt AS night_trip_ratio,
            a.morning_peak_trip_cnt,
            a.evening_peak_trip_cnt,
            a.peak_trip_cnt,
            a.peak_trip_cnt::DOUBLE / a.trip_cnt AS peak_trip_ratio,
            d.dominant_time_period,
            CASE
                WHEN a.trip_cnt < 14 THEN 'low'
                WHEN a.trip_cnt < 20 THEN 'medium'
                WHEN a.trip_cnt < 28 THEN 'high'
                ELSE 'very_high'
            END AS trip_frequency_level,
            CAST((a.night_trip_cnt::DOUBLE / a.trip_cnt) >= 0.22 AS BOOLEAN) AS night_activity_flag,
            CAST((a.peak_trip_cnt::DOUBLE / a.trip_cnt) >= 0.39 AS BOOLEAN) AS peak_activity_flag
        FROM agg AS a
        LEFT JOIN vehicle_day_road_coverage AS r
            ON r.devid = a.devid
           AND r.stat_date = a.stat_date
        LEFT JOIN vehicle_day_dominant_period AS d
            ON d.devid = a.devid
           AND d.stat_date = a.stat_date
        """,
        "Building tdm_vehicle_day_profile",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE vehicle_5d_road_coverage AS
        SELECT
            devid,
            COUNT(DISTINCT road_id) AS road_coverage_cnt_5d
        FROM matched_valid_enriched
        GROUP BY devid
        """,
        "Building vehicle_5d_road_coverage",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE vehicle_5d_dominant_period AS
        WITH period_counts AS (
            SELECT
                devid,
                time_period_type,
                COUNT(*) AS period_trip_cnt
            FROM tdm_trip_profile
            GROUP BY devid, time_period_type
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY devid
                    ORDER BY period_trip_cnt DESC, time_period_type ASC
                ) AS rn
            FROM period_counts
        )
        SELECT
            devid,
            time_period_type AS dominant_time_period_5d
        FROM ranked
        WHERE rn = 1
        """,
        "Building vehicle_5d_dominant_period",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE tdm_vehicle_5d_profile AS
        WITH agg AS (
            SELECT
                devid,
                COUNT(DISTINCT stat_date) AS active_day_cnt,
                COUNT(*) AS total_trip_cnt,
                SUM(trip_distance_km) AS total_distance_km,
                SUM(trip_duration_min) AS total_duration_min,
                SUM(CASE WHEN night_trip_flag THEN 1 ELSE 0 END) AS night_trip_cnt,
                SUM(CASE WHEN peak_trip_flag THEN 1 ELSE 0 END) AS peak_trip_cnt
            FROM tdm_trip_profile
            GROUP BY devid
        )
        SELECT
            a.devid,
            a.active_day_cnt,
            a.total_trip_cnt,
            a.total_trip_cnt::DOUBLE / a.active_day_cnt AS avg_daily_trip_cnt,
            a.total_distance_km,
            a.total_duration_min,
            a.total_distance_km / a.total_trip_cnt AS avg_trip_distance_km,
            CASE
                WHEN a.total_duration_min > 0 THEN a.total_distance_km / (a.total_duration_min / 60.0)
                ELSE NULL
            END AS avg_speed_kmh,
            a.night_trip_cnt::DOUBLE / a.total_trip_cnt AS night_trip_ratio_5d,
            a.peak_trip_cnt::DOUBLE / a.total_trip_cnt AS peak_trip_ratio_5d,
            COALESCE(r.road_coverage_cnt_5d, 0) AS road_coverage_cnt_5d,
            d.dominant_time_period_5d,
            CASE
                WHEN a.total_trip_cnt < 65 THEN 'low'
                WHEN a.total_trip_cnt < 84 THEN 'medium'
                WHEN a.total_trip_cnt < 116 THEN 'high'
                ELSE 'core'
            END AS driver_activity_level,
            CAST(a.total_trip_cnt >= 116 AS BOOLEAN) AS core_driver_flag,
            CAST(a.active_day_cnt = 5 AS BOOLEAN) AS full_attendance_flag
        FROM agg AS a
        LEFT JOIN vehicle_5d_road_coverage AS r
            ON r.devid = a.devid
        LEFT JOIN vehicle_5d_dominant_period AS d
            ON d.devid = a.devid
        """,
        "Building tdm_vehicle_5d_profile",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE tdm_vehicle_road_preference_5d AS
        WITH road_counts AS (
            SELECT
                devid,
                road_id,
                COUNT(*) AS pass_cnt,
                COUNT(DISTINCT stat_date) AS active_day_cnt_on_road
            FROM matched_valid_enriched
            GROUP BY devid, road_id
        ),
        device_totals AS (
            SELECT
                devid,
                SUM(pass_cnt) AS total_valid_segment_cnt_of_device
            FROM road_counts
            GROUP BY devid
        ),
        ranked AS (
            SELECT
                rc.devid,
                rc.road_id,
                ROW_NUMBER() OVER (
                    PARTITION BY rc.devid
                    ORDER BY rc.pass_cnt DESC, rc.road_id ASC
                ) AS rank_in_device,
                rc.pass_cnt,
                rc.active_day_cnt_on_road,
                dt.total_valid_segment_cnt_of_device
            FROM road_counts AS rc
            INNER JOIN device_totals AS dt
                ON dt.devid = rc.devid
        )
        SELECT
            devid,
            road_id,
            rank_in_device,
            pass_cnt,
            pass_cnt::DOUBLE / total_valid_segment_cnt_of_device AS pass_ratio,
            active_day_cnt_on_road,
            CASE
                WHEN rank_in_device <= 3 THEN 'core_route'
                ELSE 'frequent_route'
            END AS preference_level
        FROM ranked
        WHERE rank_in_device <= 10
        """,
        "Building tdm_vehicle_road_preference_5d",
    )


def build_road_and_time_profiles(conn: duckdb.DuckDBPyConnection) -> None:
    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE road_day_matched_agg AS
        SELECT
            road_id,
            stat_date,
            COUNT(*) AS pass_cnt,
            COUNT(DISTINCT devid) AS vehicle_cnt,
            COUNT(DISTINCT trip_id) AS trip_cnt,
            SUM(CASE WHEN morning_peak_trip_flag THEN 1 ELSE 0 END) AS morning_peak_pass_cnt,
            SUM(CASE WHEN evening_peak_trip_flag THEN 1 ELSE 0 END) AS evening_peak_pass_cnt,
            SUM(CASE WHEN night_trip_flag THEN 1 ELSE 0 END) AS night_pass_cnt
        FROM matched_valid_enriched
        GROUP BY road_id, stat_date
        """,
        "Building road_day_matched_agg",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE road_day_edge_agg AS
        SELECT
            road_id,
            stat_date,
            SUM(CASE WHEN route_heading = 'forward' THEN 1 ELSE 0 END) AS forward_edge_cnt,
            SUM(CASE WHEN route_heading = 'backward' THEN 1 ELSE 0 END) AS backward_edge_cnt
        FROM route_edges_valid_enriched
        GROUP BY road_id, stat_date
        """,
        "Building road_day_edge_agg",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE tdm_road_day_profile AS
        WITH base AS (
            SELECT
                m.road_id,
                m.stat_date,
                m.pass_cnt,
                m.vehicle_cnt,
                m.trip_cnt,
                m.morning_peak_pass_cnt,
                m.evening_peak_pass_cnt,
                m.night_pass_cnt,
                COALESCE(e.forward_edge_cnt, 0) AS forward_edge_cnt,
                COALESCE(e.backward_edge_cnt, 0) AS backward_edge_cnt,
                m.pass_cnt - m.morning_peak_pass_cnt - m.evening_peak_pass_cnt - m.night_pass_cnt AS offpeak_pass_cnt
            FROM road_day_matched_agg AS m
            LEFT JOIN road_day_edge_agg AS e
                ON e.road_id = m.road_id
               AND e.stat_date = m.stat_date
        )
        SELECT
            road_id,
            stat_date,
            pass_cnt,
            vehicle_cnt,
            trip_cnt,
            morning_peak_pass_cnt,
            evening_peak_pass_cnt,
            night_pass_cnt,
            (morning_peak_pass_cnt + evening_peak_pass_cnt)::DOUBLE / pass_cnt AS peak_pass_ratio,
            forward_edge_cnt,
            backward_edge_cnt,
            CASE
                WHEN forward_edge_cnt + backward_edge_cnt > 0
                THEN forward_edge_cnt::DOUBLE / (forward_edge_cnt + backward_edge_cnt)
                ELSE NULL
            END AS forward_ratio,
            CASE
                WHEN forward_edge_cnt + backward_edge_cnt = 0 THEN 'balanced'
                WHEN forward_edge_cnt::DOUBLE / (forward_edge_cnt + backward_edge_cnt) >= 0.80 THEN 'mainly_forward'
                WHEN forward_edge_cnt::DOUBLE / (forward_edge_cnt + backward_edge_cnt) <= 0.20 THEN 'mainly_backward'
                ELSE 'balanced'
            END AS direction_bias,
            CASE
                WHEN pass_cnt < 13 THEN 'long_tail'
                WHEN pass_cnt < 91 THEN 'normal'
                WHEN pass_cnt < 454 THEN 'active'
                ELSE 'hot'
            END AS road_activity_level,
            CASE
                WHEN morning_peak_pass_cnt >= evening_peak_pass_cnt
                     AND morning_peak_pass_cnt >= night_pass_cnt
                     AND morning_peak_pass_cnt >= offpeak_pass_cnt THEN 'morning_peak'
                WHEN evening_peak_pass_cnt >= night_pass_cnt
                     AND evening_peak_pass_cnt >= offpeak_pass_cnt THEN 'evening_peak'
                WHEN night_pass_cnt >= offpeak_pass_cnt THEN 'night'
                ELSE 'offpeak'
            END AS peak_bias_type
        FROM base
        """,
        "Building tdm_road_day_profile",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE time_slot_road_coverage AS
        SELECT
            stat_date,
            biz_start_hour AS biz_hour,
            COUNT(DISTINCT road_id) AS road_coverage_cnt
        FROM matched_valid_enriched
        GROUP BY stat_date, biz_start_hour
        """,
        "Building time_slot_road_coverage",
    )

    execute(
        conn,
        f"""
        CREATE OR REPLACE TEMP TABLE tdm_time_slot_day_profile AS
        WITH date_dim AS (
            SELECT DISTINCT stat_date
            FROM trip_base
        ),
        hour_dim AS (
            SELECT generate_series AS biz_hour
            FROM generate_series(0, 23)
        ),
        slot_dim AS (
            SELECT
                d.stat_date,
                h.biz_hour
            FROM date_dim AS d
            CROSS JOIN hour_dim AS h
        ),
        slot_agg AS (
            SELECT
                stat_date,
                biz_start_hour AS biz_hour,
                COUNT(*) AS trip_cnt,
                SUM(CASE WHEN has_matched_segments THEN 1 ELSE 0 END) AS matched_trip_cnt,
                COUNT(DISTINCT devid) AS vehicle_cnt,
                SUM(trip_distance_km) AS total_distance_km,
                SUM(trip_duration_min) AS total_duration_min
            FROM tdm_trip_profile
            GROUP BY stat_date, biz_start_hour
        )
        SELECT
            strftime(s.stat_date, '%Y-%m-%d') || '_' || lpad(CAST(s.biz_hour AS VARCHAR), 2, '0') AS time_range_id,
            s.stat_date,
            s.biz_hour,
            {time_period_case("s.biz_hour")} AS time_period_type,
            COALESCE(a.trip_cnt, 0) AS trip_cnt,
            COALESCE(a.matched_trip_cnt, 0) AS matched_trip_cnt,
            COALESCE(a.vehicle_cnt, 0) AS vehicle_cnt,
            COALESCE(a.total_distance_km, 0.0) AS total_distance_km,
            COALESCE(a.total_duration_min, 0.0) AS total_duration_min,
            CASE
                WHEN COALESCE(a.trip_cnt, 0) > 0 THEN a.total_distance_km / a.trip_cnt
                ELSE 0.0
            END AS avg_trip_distance_km,
            CASE
                WHEN COALESCE(a.trip_cnt, 0) > 0 THEN a.total_duration_min / a.trip_cnt
                ELSE 0.0
            END AS avg_trip_duration_min,
            CASE
                WHEN COALESCE(a.total_duration_min, 0.0) > 0 THEN a.total_distance_km / (a.total_duration_min / 60.0)
                ELSE 0.0
            END AS avg_speed_kmh,
            COALESCE(r.road_coverage_cnt, 0) AS road_coverage_cnt,
            CASE
                WHEN COALESCE(a.trip_cnt, 0) < 5936 THEN 'low'
                WHEN COALESCE(a.trip_cnt, 0) < 9612 THEN 'medium'
                WHEN COALESCE(a.trip_cnt, 0) < 15022 THEN 'high'
                ELSE 'hot'
            END AS slot_activity_level
        FROM slot_dim AS s
        LEFT JOIN slot_agg AS a
            ON a.stat_date = s.stat_date
           AND a.biz_hour = s.biz_hour
        LEFT JOIN time_slot_road_coverage AS r
            ON r.stat_date = s.stat_date
           AND r.biz_hour = s.biz_hour
        """,
        "Building tdm_time_slot_day_profile",
    )


def build_region_grid_profile(conn: duckdb.DuckDBPyConnection) -> None:
    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE region_grid_events AS
        WITH pickup_events AS (
            SELECT
                t.trip_id,
                t.devid,
                t.stat_date,
                t.night_trip_flag,
                t.peak_trip_flag,
                CAST(FLOOR(o.pickup_lon / 0.01) AS BIGINT) AS grid_x,
                CAST(FLOOR(o.pickup_lat / 0.01) AS BIGINT) AS grid_y,
                'pickup' AS od_type
            FROM trip_base AS t
            INNER JOIN trip_od_base AS o
                ON o.trip_id = t.trip_id
            WHERE o.pickup_lon IS NOT NULL
              AND o.pickup_lat IS NOT NULL
        ),
        dropoff_events AS (
            SELECT
                t.trip_id,
                t.devid,
                t.stat_date,
                t.night_trip_flag,
                t.peak_trip_flag,
                CAST(FLOOR(o.dropoff_lon / 0.01) AS BIGINT) AS grid_x,
                CAST(FLOOR(o.dropoff_lat / 0.01) AS BIGINT) AS grid_y,
                'dropoff' AS od_type
            FROM trip_base AS t
            INNER JOIN trip_od_base AS o
                ON o.trip_id = t.trip_id
            WHERE o.dropoff_lon IS NOT NULL
              AND o.dropoff_lat IS NOT NULL
        )
        SELECT * FROM pickup_events
        UNION ALL
        SELECT * FROM dropoff_events
        """,
        "Building region_grid_events",
    )

    execute(
        conn,
        """
        CREATE OR REPLACE TEMP TABLE tdm_region_grid_day_profile AS
        WITH agg AS (
            SELECT
                stat_date,
                CAST(grid_x AS VARCHAR) || '_' || CAST(grid_y AS VARCHAR) AS grid_id,
                (grid_x + 0.5) * 0.01 AS grid_center_lon,
                (grid_y + 0.5) * 0.01 AS grid_center_lat,
                SUM(CASE WHEN od_type = 'pickup' THEN 1 ELSE 0 END) AS pickup_trip_cnt,
                SUM(CASE WHEN od_type = 'dropoff' THEN 1 ELSE 0 END) AS dropoff_trip_cnt,
                COUNT(*) AS total_od_trip_cnt,
                COUNT(DISTINCT devid) AS active_vehicle_cnt,
                SUM(CASE WHEN night_trip_flag THEN 1 ELSE 0 END) AS night_od_trip_cnt,
                SUM(CASE WHEN peak_trip_flag THEN 1 ELSE 0 END) AS peak_od_trip_cnt
            FROM region_grid_events
            GROUP BY stat_date, grid_id, grid_center_lon, grid_center_lat
        )
        SELECT
            grid_id,
            stat_date,
            grid_center_lon,
            grid_center_lat,
            pickup_trip_cnt,
            dropoff_trip_cnt,
            total_od_trip_cnt,
            active_vehicle_cnt,
            night_od_trip_cnt,
            peak_od_trip_cnt,
            pickup_trip_cnt::DOUBLE / total_od_trip_cnt AS pickup_ratio,
            CASE
                WHEN pickup_trip_cnt::DOUBLE / total_od_trip_cnt >= 0.60 THEN 'pickup_dominant'
                WHEN pickup_trip_cnt::DOUBLE / total_od_trip_cnt <= 0.40 THEN 'dropoff_dominant'
                ELSE 'balanced'
            END AS grid_role_bias,
            CASE
                WHEN total_od_trip_cnt < 26 THEN 'long_tail'
                WHEN total_od_trip_cnt < 171 THEN 'normal'
                WHEN total_od_trip_cnt < 1127 THEN 'active'
                ELSE 'hotspot'
            END AS grid_activity_level
        FROM agg
        """,
        "Building tdm_region_grid_day_profile",
    )


def write_outputs(conn: duckdb.DuckDBPyConnection) -> None:
    copy_table(conn, "tdm_trip_profile", OUTPUT_FILES["tdm_trip_profile"])
    copy_table(conn, "tdm_vehicle_day_profile", OUTPUT_FILES["tdm_vehicle_day_profile"])
    copy_table(conn, "tdm_vehicle_5d_profile", OUTPUT_FILES["tdm_vehicle_5d_profile"])
    copy_table(conn, "tdm_vehicle_road_preference_5d", OUTPUT_FILES["tdm_vehicle_road_preference_5d"])
    copy_table(conn, "tdm_road_day_profile", OUTPUT_FILES["tdm_road_day_profile"])
    copy_table(conn, "tdm_time_slot_day_profile", OUTPUT_FILES["tdm_time_slot_day_profile"])
    copy_table(conn, "tdm_region_grid_day_profile", OUTPUT_FILES["tdm_region_grid_day_profile"])


def collect_row_counts(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    counts = {}
    for table_name, output_path in OUTPUT_FILES.items():
        if output_path.suffix == ".parquet":
            counts[table_name] = conn.execute(
                f"SELECT COUNT(*) FROM read_parquet('{sql_literal(output_path)}')"
            ).fetchone()[0]
    return counts


def collect_file_sizes() -> dict[str, int]:
    sizes = {}
    for key, output_path in OUTPUT_FILES.items():
        if output_path.exists():
            sizes[key] = output_path.stat().st_size
    return sizes


def collect_validations(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    validations = {}
    validations["trip_stat_date_mismatch_cnt"] = conn.execute(
        """
        SELECT COUNT(*)
        FROM tdm_trip_profile
        WHERE stat_date <> CAST(
            strptime(
                regexp_extract(source_file, 'trips_(\\d{6})\\.jld2', 1),
                '%y%m%d'
            ) AS DATE
        )
        """
    ).fetchone()[0]
    validations["matched_time_priority_mismatch_cnt"] = conn.execute(
        """
        SELECT COUNT(*)
        FROM trip_base
        WHERE has_matched_segments
          AND biz_start_time IS DISTINCT FROM matched_start_time_utc
        """
    ).fetchone()[0]
    validations["gps_fallback_mismatch_cnt"] = conn.execute(
        """
        SELECT COUNT(*)
        FROM trip_base
        WHERE NOT has_matched_segments
          AND biz_start_time IS DISTINCT FROM gps_start_time_utc - INTERVAL 8 HOUR
        """
    ).fetchone()[0]
    validations["negative_trip_distance_cnt"] = conn.execute(
        """
        SELECT COUNT(*)
        FROM tdm_trip_profile
        WHERE trip_distance_km < 0
        """
    ).fetchone()[0]
    validations["negative_avg_speed_cnt"] = conn.execute(
        """
        SELECT COUNT(*)
        FROM tdm_trip_profile
        WHERE avg_speed_kmh < 0
        """
    ).fetchone()[0]
    validations["blank_trip_frequency_level_cnt"] = conn.execute(
        """
        SELECT COUNT(*)
        FROM tdm_vehicle_day_profile
        WHERE COALESCE(trip_frequency_level, '') = ''
        """
    ).fetchone()[0]
    validations["blank_driver_activity_level_cnt"] = conn.execute(
        """
        SELECT COUNT(*)
        FROM tdm_vehicle_5d_profile
        WHERE COALESCE(driver_activity_level, '') = ''
        """
    ).fetchone()[0]
    validations["blank_road_activity_level_cnt"] = conn.execute(
        """
        SELECT COUNT(*)
        FROM tdm_road_day_profile
        WHERE COALESCE(road_activity_level, '') = ''
        """
    ).fetchone()[0]
    validations["blank_grid_activity_level_cnt"] = conn.execute(
        """
        SELECT COUNT(*)
        FROM tdm_region_grid_day_profile
        WHERE COALESCE(grid_activity_level, '') = ''
        """
    ).fetchone()[0]
    return validations


def build_summary(
    row_counts: dict[str, int],
    tag_definition_count: int,
    validation_counts: dict[str, int],
    started_at_utc: str,
    finished_at_utc: str,
    duration_seconds: float,
) -> dict[str, object]:
    files_exist = {key: path.exists() for key, path in OUTPUT_FILES.items()}
    row_count_checks = {
        name: {
            "expected": expected,
            "actual": row_counts.get(name),
            "diff": None if row_counts.get(name) is None else row_counts[name] - expected,
        }
        for name, expected in EXPECTED_ROW_COUNTS.items()
    }
    return {
        "status": "success",
        "build_started_at_utc": started_at_utc,
        "build_finished_at_utc": finished_at_utc,
        "duration_seconds": round(duration_seconds, 2),
        "input_root": str(ROOT_DIR),
        "output_root": str(OUTPUT_DIR),
        "source_files": SOURCE_FILES,
        "files_exist": files_exist,
        "row_counts": row_counts,
        "expected_row_counts": EXPECTED_ROW_COUNTS,
        "row_count_checks": row_count_checks,
        "tag_definition_count": tag_definition_count,
        "validation_counts": validation_counts,
        "validation_passed": all(value == 0 for value in validation_counts.values()),
        "file_sizes_bytes": collect_file_sizes(),
    }


def write_summary(summary: dict[str, object], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(summary, json_file, ensure_ascii=False, indent=2)


def main() -> None:
    started_at_utc = now_utc_iso()
    build_started = time.time()
    conn = setup_connection()
    try:
        create_base_views(conn)
        build_trip_intermediates(conn)
        build_trip_profile(conn)
        build_vehicle_profiles(conn)
        build_road_and_time_profiles(conn)
        build_region_grid_profile(conn)
        write_outputs(conn)
        tag_definition_count = build_tag_definitions(OUTPUT_FILES["tdm_tag_definition"])
        row_counts = collect_row_counts(conn)
        validation_counts = collect_validations(conn)
        finished_at_utc = now_utc_iso()
        summary = build_summary(
            row_counts=row_counts,
            tag_definition_count=tag_definition_count,
            validation_counts=validation_counts,
            started_at_utc=started_at_utc,
            finished_at_utc=finished_at_utc,
            duration_seconds=time.time() - build_started,
        )
        write_summary(summary, OUTPUT_FILES["tdm_build_summary"])
        summary["files_exist"]["tdm_build_summary"] = True
        summary["file_sizes_bytes"] = collect_file_sizes()
        write_summary(summary, OUTPUT_FILES["tdm_build_summary"])
        log("TDM layer build completed")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

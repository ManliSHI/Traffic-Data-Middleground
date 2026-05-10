from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ADS_DIR = Path(__file__).resolve().parent
ROOT_DIR = ADS_DIR.parent
INPUT_DIR = ROOT_DIR / "tdm_output"
OUTPUT_DIR = ADS_DIR / "ads_output"

INPUT_FILES = {
    "trip_profile": INPUT_DIR / "tdm_trip_profile.parquet",
    "vehicle_day_profile": INPUT_DIR / "tdm_vehicle_day_profile.parquet",
    "vehicle_5d_profile": INPUT_DIR / "tdm_vehicle_5d_profile.parquet",
    "vehicle_road_preference_5d": INPUT_DIR / "tdm_vehicle_road_preference_5d.parquet",
    "road_day_profile": INPUT_DIR / "tdm_road_day_profile.parquet",
    "time_slot_day_profile": INPUT_DIR / "tdm_time_slot_day_profile.parquet",
    "region_grid_day_profile": INPUT_DIR / "tdm_region_grid_day_profile.parquet",
}

OUTPUT_FILES = {
    "ads_daily_overview": OUTPUT_DIR / "ads_daily_overview.parquet",
    "ads_daily_growth_compare": OUTPUT_DIR / "ads_daily_growth_compare.parquet",
    "ads_hourly_trend": OUTPUT_DIR / "ads_hourly_trend.parquet",
    "ads_peak_window_top3_daily": OUTPUT_DIR / "ads_peak_window_top3_daily.parquet",
    "ads_time_period_summary_daily": OUTPUT_DIR / "ads_time_period_summary_daily.parquet",
    "ads_trip_structure_daily": OUTPUT_DIR / "ads_trip_structure_daily.parquet",
    "ads_trip_efficiency_by_period_daily": OUTPUT_DIR / "ads_trip_efficiency_by_period_daily.parquet",
    "ads_trip_complexity_daily": OUTPUT_DIR / "ads_trip_complexity_daily.parquet",
    "ads_vehicle_profile_5d": OUTPUT_DIR / "ads_vehicle_profile_5d.parquet",
    "ads_vehicle_segment_summary_5d": OUTPUT_DIR / "ads_vehicle_segment_summary_5d.parquet",
    "ads_vehicle_daily_operating_style": OUTPUT_DIR / "ads_vehicle_daily_operating_style.parquet",
    "ads_vehicle_road_preference_topn": OUTPUT_DIR / "ads_vehicle_road_preference_topn.parquet",
    "ads_vehicle_route_stability_5d": OUTPUT_DIR / "ads_vehicle_route_stability_5d.parquet",
    "ads_road_hotspot_feature_daily": OUTPUT_DIR / "ads_road_hotspot_feature_daily.parquet",
    "ads_road_top20_daily": OUTPUT_DIR / "ads_road_top20_daily.parquet",
    "ads_road_watchlist_daily": OUTPUT_DIR / "ads_road_watchlist_daily.parquet",
    "ads_region_hotspot_role_daily": OUTPUT_DIR / "ads_region_hotspot_role_daily.parquet",
    "ads_region_top20_daily": OUTPUT_DIR / "ads_region_top20_daily.parquet",
    "ads_dispatch_focus_grid_daily": OUTPUT_DIR / "ads_dispatch_focus_grid_daily.parquet",
    "ads_region_bias_daily": OUTPUT_DIR / "ads_region_bias_daily.parquet",
    "ads_abnormal_vehicle_daily_detail": OUTPUT_DIR / "ads_abnormal_vehicle_daily_detail.parquet",
    "ads_abnormal_vehicle_daily_summary": OUTPUT_DIR / "ads_abnormal_vehicle_daily_summary.parquet",
    "ads_data_quality_daily": OUTPUT_DIR / "ads_data_quality_daily.parquet",
    "ads_metric_definition": OUTPUT_DIR / "ads_metric_definition.csv",
    "ads_build_summary": OUTPUT_DIR / "ads_build_summary.json",
}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype("float64") / denominator.astype("float64")
    return result.where(denominator.astype("float64") != 0)


def add_rank(
    df: pd.DataFrame,
    group_cols: list[str],
    sort_cols: list[str],
    ascending: list[bool],
    rank_col: str,
) -> pd.DataFrame:
    ranked = df.sort_values(group_cols + sort_cols, ascending=[True] * len(group_cols) + ascending).copy()
    ranked[rank_col] = ranked.groupby(group_cols).cumcount() + 1
    return ranked


def add_percentile_score(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    ascending: bool,
    score_col: str,
) -> pd.DataFrame:
    ranked = df.copy()
    ranked[score_col] = ranked.groupby(group_col)[value_col].rank(pct=True, ascending=ascending)
    return ranked


def build_daily_overview(vehicle_day: pd.DataFrame, time_slot: pd.DataFrame) -> pd.DataFrame:
    daily = (
        vehicle_day.groupby("stat_date", as_index=False)
        .agg(
            active_vehicle_cnt=("devid", "size"),
            total_trip_cnt=("trip_cnt", "sum"),
            total_distance_km=("total_distance_km", "sum"),
            total_duration_min=("total_duration_min", "sum"),
            avg_vehicle_speed_kmh=("avg_speed_kmh", "mean"),
            night_active_vehicle_cnt=("night_activity_flag", "sum"),
            peak_active_vehicle_cnt=("peak_activity_flag", "sum"),
        )
        .sort_values("stat_date")
    )
    daily["global_avg_speed_kmh"] = safe_divide(daily["total_distance_km"], daily["total_duration_min"] / 60.0)

    peak_trip = (
        time_slot.loc[time_slot["time_period_type"].isin(["morning_peak", "evening_peak"])]
        .groupby("stat_date", as_index=False)["trip_cnt"]
        .sum()
        .rename(columns={"trip_cnt": "peak_trip_cnt"})
    )

    peak_hour = (
        time_slot.sort_values(["stat_date", "trip_cnt", "biz_hour"], ascending=[True, False, True])
        .drop_duplicates("stat_date")
        .loc[:, ["stat_date", "biz_hour", "trip_cnt"]]
        .rename(columns={"biz_hour": "hourly_peak_hour", "trip_cnt": "hourly_peak_trip_cnt"})
    )

    daily = daily.merge(peak_trip, on="stat_date", how="left").merge(peak_hour, on="stat_date", how="left")
    daily["peak_trip_cnt"] = daily["peak_trip_cnt"].fillna(0).astype("int64")
    daily["hourly_peak_hour"] = daily["hourly_peak_hour"].astype("int64")
    daily["hourly_peak_trip_cnt"] = daily["hourly_peak_trip_cnt"].astype("int64")
    daily["active_vehicle_cnt"] = daily["active_vehicle_cnt"].astype("int64")
    daily["night_active_vehicle_cnt"] = daily["night_active_vehicle_cnt"].astype("int64")
    daily["peak_active_vehicle_cnt"] = daily["peak_active_vehicle_cnt"].astype("int64")
    return daily.sort_values("stat_date").reset_index(drop=True)


def build_daily_growth_compare(daily_overview: pd.DataFrame) -> pd.DataFrame:
    df = daily_overview.sort_values("stat_date").copy()
    for col in ["total_trip_cnt", "active_vehicle_cnt", "global_avg_speed_kmh"]:
        df[f"{col}_prev_day"] = df[col].shift(1)

    df["trip_cnt_dod_growth"] = safe_divide(
        df["total_trip_cnt"] - df["total_trip_cnt_prev_day"],
        df["total_trip_cnt_prev_day"],
    )
    df["active_vehicle_dod_growth"] = safe_divide(
        df["active_vehicle_cnt"] - df["active_vehicle_cnt_prev_day"],
        df["active_vehicle_cnt_prev_day"],
    )
    df["speed_dod_change"] = df["global_avg_speed_kmh"] - df["global_avg_speed_kmh_prev_day"]
    return df.reset_index(drop=True)


def build_hourly_trend(time_slot: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "time_range_id",
        "stat_date",
        "biz_hour",
        "time_period_type",
        "trip_cnt",
        "matched_trip_cnt",
        "vehicle_cnt",
        "total_distance_km",
        "total_duration_min",
        "avg_trip_distance_km",
        "avg_trip_duration_min",
        "avg_speed_kmh",
        "road_coverage_cnt",
        "slot_activity_level",
    ]
    df = time_slot.loc[:, cols].copy().sort_values(["stat_date", "biz_hour"]).reset_index(drop=True)
    daily_trip_total = df.groupby("stat_date")["trip_cnt"].transform("sum")
    df["trip_share_in_day"] = safe_divide(df["trip_cnt"], daily_trip_total).fillna(0.0)
    return df


def build_peak_window_top3_daily(hourly_trend: pd.DataFrame) -> pd.DataFrame:
    ranked = add_rank(hourly_trend, ["stat_date"], ["trip_cnt", "biz_hour"], [False, True], "rank_in_day")
    cols = [
        "stat_date",
        "rank_in_day",
        "biz_hour",
        "time_period_type",
        "trip_cnt",
        "vehicle_cnt",
        "avg_speed_kmh",
        "trip_share_in_day",
    ]
    return ranked.loc[ranked["rank_in_day"] <= 3, cols].reset_index(drop=True)


def build_time_period_summary_daily(trip_profile: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        trip_profile.groupby(["stat_date", "time_period_type"], as_index=False)
        .agg(
            trip_cnt=("trip_id", "size"),
            avg_trip_distance_km=("trip_distance_km", "mean"),
            avg_trip_duration_min=("trip_duration_min", "mean"),
            avg_speed_kmh=("avg_speed_kmh", "mean"),
            avg_unique_road_cnt=("unique_road_cnt", "mean"),
            avg_road_repeat_ratio=("road_repeat_ratio", "mean"),
            avg_forward_edge_ratio=("forward_edge_ratio", "mean"),
        )
        .sort_values(["stat_date", "trip_cnt", "time_period_type"], ascending=[True, False, True])
        .reset_index(drop=True)
    )
    total = grouped.groupby("stat_date")["trip_cnt"].transform("sum")
    grouped["trip_ratio_in_day"] = safe_divide(grouped["trip_cnt"], total).fillna(0.0)
    return grouped


def build_trip_structure_daily(trip_profile: pd.DataFrame) -> pd.DataFrame:
    df = trip_profile.copy()
    df["trip_speed_level"] = df["trip_speed_level"].fillna("unknown")
    grouped = (
        df.groupby(
            ["stat_date", "trip_distance_level", "trip_duration_level", "trip_speed_level"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "trip_cnt"})
    )
    total = grouped.groupby("stat_date")["trip_cnt"].transform("sum")
    grouped["trip_ratio"] = safe_divide(grouped["trip_cnt"], total).fillna(0.0)
    return grouped.sort_values(
        ["stat_date", "trip_cnt", "trip_distance_level", "trip_duration_level", "trip_speed_level"],
        ascending=[True, False, True, True, True],
    ).reset_index(drop=True)


def build_trip_efficiency_by_period_daily(time_period_summary: pd.DataFrame) -> pd.DataFrame:
    df = time_period_summary.copy()
    df = add_rank(df, ["stat_date"], ["avg_speed_kmh", "time_period_type"], [False, True], "speed_rank_in_day")
    df = add_rank(
        df,
        ["stat_date"],
        ["avg_trip_duration_min", "time_period_type"],
        [False, True],
        "duration_rank_in_day",
    )
    cols = [
        "stat_date",
        "time_period_type",
        "trip_cnt",
        "trip_ratio_in_day",
        "avg_trip_distance_km",
        "avg_trip_duration_min",
        "avg_speed_kmh",
        "avg_unique_road_cnt",
        "avg_road_repeat_ratio",
        "avg_forward_edge_ratio",
        "speed_rank_in_day",
        "duration_rank_in_day",
    ]
    return df.loc[:, cols].sort_values(["stat_date", "speed_rank_in_day", "time_period_type"]).reset_index(drop=True)


def build_trip_complexity_daily(trip_profile: pd.DataFrame) -> pd.DataFrame:
    df = trip_profile.copy()
    unique_threshold = float(df["unique_road_cnt"].quantile(0.75))
    repeat_threshold = float(df["road_repeat_ratio"].quantile(0.75))
    df["complex_trip_flag"] = (df["unique_road_cnt"] >= unique_threshold) | (df["road_repeat_ratio"] >= repeat_threshold)
    grouped = (
        df.groupby("stat_date", as_index=False)
        .agg(
            avg_unique_road_cnt=("unique_road_cnt", "mean"),
            avg_road_repeat_ratio=("road_repeat_ratio", "mean"),
            avg_forward_edge_ratio=("forward_edge_ratio", "mean"),
            complex_trip_ratio=("complex_trip_flag", "mean"),
            p75_unique_road_cnt=("unique_road_cnt", lambda s: s.quantile(0.75)),
            p75_road_repeat_ratio=("road_repeat_ratio", lambda s: s.quantile(0.75)),
        )
        .sort_values("stat_date")
        .reset_index(drop=True)
    )
    grouped["complexity_unique_threshold"] = unique_threshold
    grouped["complexity_repeat_threshold"] = repeat_threshold
    return grouped


def build_vehicle_profile_5d(vehicle_5d: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "devid",
        "active_day_cnt",
        "total_trip_cnt",
        "avg_daily_trip_cnt",
        "total_distance_km",
        "total_duration_min",
        "avg_trip_distance_km",
        "avg_speed_kmh",
        "night_trip_ratio_5d",
        "peak_trip_ratio_5d",
        "road_coverage_cnt_5d",
        "dominant_time_period_5d",
        "driver_activity_level",
        "core_driver_flag",
        "full_attendance_flag",
    ]
    df = vehicle_5d.loc[:, cols].copy()
    df = df.sort_values(["total_trip_cnt", "devid"], ascending=[False, True]).reset_index(drop=True)
    df["rank_by_total_trip_cnt"] = np.arange(1, len(df) + 1, dtype=np.int64)
    return df


def build_vehicle_segment_summary_5d(vehicle_profile_5d: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        vehicle_profile_5d.groupby(["driver_activity_level", "dominant_time_period_5d"], dropna=False, as_index=False)
        .agg(
            vehicle_cnt=("devid", "size"),
            avg_total_trip_cnt=("total_trip_cnt", "mean"),
            avg_total_distance_km=("total_distance_km", "mean"),
            avg_speed_kmh=("avg_speed_kmh", "mean"),
            avg_night_trip_ratio_5d=("night_trip_ratio_5d", "mean"),
            avg_peak_trip_ratio_5d=("peak_trip_ratio_5d", "mean"),
            core_driver_cnt=("core_driver_flag", "sum"),
            full_attendance_cnt=("full_attendance_flag", "sum"),
        )
    )
    grouped["core_driver_ratio"] = safe_divide(grouped["core_driver_cnt"], grouped["vehicle_cnt"]).fillna(0.0)
    grouped["full_attendance_ratio"] = safe_divide(grouped["full_attendance_cnt"], grouped["vehicle_cnt"]).fillna(0.0)
    return grouped.sort_values(["vehicle_cnt", "driver_activity_level"], ascending=[False, True]).reset_index(drop=True)


def build_vehicle_daily_operating_style(vehicle_day: pd.DataFrame) -> pd.DataFrame:
    df = vehicle_day.copy()
    df["operation_style_type"] = np.select(
        [
            df["night_activity_flag"] & ~df["peak_activity_flag"],
            df["peak_activity_flag"] & ~df["night_activity_flag"],
            df["trip_frequency_level"].isin(["high", "very_high"]) & (df["active_hour_cnt"] >= 8),
        ],
        [
            "night_shift",
            "peak_shift",
            "intensive_operation",
        ],
        default="balanced_operation",
    )
    df = add_rank(df, ["stat_date"], ["trip_cnt", "devid"], [False, True], "rank_by_trip_cnt_in_day")
    cols = [
        "stat_date",
        "devid",
        "trip_cnt",
        "matched_trip_cnt",
        "matched_trip_ratio",
        "total_distance_km",
        "total_duration_min",
        "avg_trip_distance_km",
        "avg_trip_duration_min",
        "avg_speed_kmh",
        "active_hour_cnt",
        "road_coverage_cnt",
        "night_trip_cnt",
        "night_trip_ratio",
        "morning_peak_trip_cnt",
        "evening_peak_trip_cnt",
        "peak_trip_cnt",
        "peak_trip_ratio",
        "dominant_time_period",
        "trip_frequency_level",
        "night_activity_flag",
        "peak_activity_flag",
        "operation_style_type",
        "rank_by_trip_cnt_in_day",
    ]
    return df.loc[:, cols].sort_values(["stat_date", "rank_by_trip_cnt_in_day"]).reset_index(drop=True)


def build_vehicle_road_preference_topn(vehicle_road_pref: pd.DataFrame) -> pd.DataFrame:
    df = vehicle_road_pref.copy()
    df["preference_score"] = df["pass_ratio"] * df["active_day_cnt_on_road"]
    return df.sort_values(["devid", "rank_in_device"]).reset_index(drop=True)


def build_vehicle_route_stability_5d(
    vehicle_road_pref: pd.DataFrame,
    vehicle_profile_5d: pd.DataFrame,
) -> pd.DataFrame:
    pref = vehicle_road_pref.copy()
    agg = (
        pref.groupby("devid", as_index=False)
        .agg(
            top1_pass_ratio=("pass_ratio", "max"),
            top3_pass_ratio_sum=("pass_ratio", lambda s: s.sort_values(ascending=False).head(3).sum()),
            core_route_cnt=("preference_level", lambda s: (s == "core_route").sum()),
            frequent_route_cnt=("preference_level", lambda s: (s == "frequent_route").sum()),
        )
    )
    df = vehicle_profile_5d.merge(agg, on="devid", how="left")
    df[["top1_pass_ratio", "top3_pass_ratio_sum"]] = df[["top1_pass_ratio", "top3_pass_ratio_sum"]].fillna(0.0)
    df[["core_route_cnt", "frequent_route_cnt"]] = df[["core_route_cnt", "frequent_route_cnt"]].fillna(0).astype("int64")
    df["route_stability_level"] = np.select(
        [
            df["top3_pass_ratio_sum"] >= 0.60,
            df["top3_pass_ratio_sum"] >= 0.40,
            df["top3_pass_ratio_sum"] >= 0.25,
        ],
        [
            "very_stable",
            "stable",
            "mixed",
        ],
        default="diversified",
    )
    cols = [
        "devid",
        "active_day_cnt",
        "total_trip_cnt",
        "driver_activity_level",
        "road_coverage_cnt_5d",
        "top1_pass_ratio",
        "top3_pass_ratio_sum",
        "core_route_cnt",
        "frequent_route_cnt",
        "route_stability_level",
    ]
    return df.loc[:, cols].sort_values(["top3_pass_ratio_sum", "devid"], ascending=[False, True]).reset_index(drop=True)


def build_road_hotspot_feature_daily(road_day: pd.DataFrame) -> pd.DataFrame:
    df = road_day.copy()
    df["peak_pass_cnt"] = df["morning_peak_pass_cnt"] + df["evening_peak_pass_cnt"]
    df = add_rank(df, ["stat_date"], ["pass_cnt", "road_id"], [False, True], "rank_by_pass_cnt")
    df = add_rank(df, ["stat_date"], ["vehicle_cnt", "road_id"], [False, True], "rank_by_vehicle_cnt")
    df = add_rank(df, ["stat_date"], ["trip_cnt", "road_id"], [False, True], "rank_by_trip_cnt")
    ordered_cols = [
        "stat_date",
        "road_id",
        "rank_by_pass_cnt",
        "rank_by_vehicle_cnt",
        "rank_by_trip_cnt",
        "pass_cnt",
        "vehicle_cnt",
        "trip_cnt",
        "morning_peak_pass_cnt",
        "evening_peak_pass_cnt",
        "peak_pass_cnt",
        "night_pass_cnt",
        "peak_pass_ratio",
        "forward_edge_cnt",
        "backward_edge_cnt",
        "forward_ratio",
        "direction_bias",
        "road_activity_level",
        "peak_bias_type",
    ]
    return df.loc[:, ordered_cols].sort_values(["stat_date", "rank_by_pass_cnt"]).reset_index(drop=True)


def build_road_top20_daily(road_hotspot: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "stat_date",
        "road_id",
        "rank_by_pass_cnt",
        "rank_by_vehicle_cnt",
        "rank_by_trip_cnt",
        "pass_cnt",
        "vehicle_cnt",
        "trip_cnt",
        "peak_pass_cnt",
        "night_pass_cnt",
        "peak_pass_ratio",
        "direction_bias",
        "road_activity_level",
        "peak_bias_type",
    ]
    return (
        road_hotspot.loc[road_hotspot["rank_by_pass_cnt"] <= 20, cols]
        .sort_values(["stat_date", "rank_by_pass_cnt"])
        .reset_index(drop=True)
    )


def build_road_watchlist_daily(road_hotspot: pd.DataFrame) -> pd.DataFrame:
    df = road_hotspot.copy()
    max_rank = df.groupby("stat_date")["rank_by_pass_cnt"].transform("max")
    df["flow_score"] = 1 - safe_divide(df["rank_by_pass_cnt"] - 1, (max_rank - 1).replace(0, np.nan)).fillna(1.0)
    df["peak_sensitivity_score"] = df["peak_pass_ratio"].fillna(0.0)
    df["direction_imbalance_score"] = (df["forward_ratio"].fillna(0.5) - 0.5).abs() * 2
    df["watch_score"] = (
        0.50 * df["flow_score"] +
        0.30 * df["peak_sensitivity_score"] +
        0.20 * df["direction_imbalance_score"]
    )
    df["watch_reason"] = np.select(
        [
            (df["peak_pass_ratio"] >= 0.50) & (df["direction_bias"] != "balanced"),
            df["peak_pass_ratio"] >= 0.50,
            df["direction_bias"] != "balanced",
            df["road_activity_level"] == "hot",
        ],
        [
            "peak_and_directional",
            "peak_sensitive",
            "directional_bias",
            "high_activity",
        ],
        default="normal_watch",
    )
    df["watch_level"] = np.select(
        [
            df["watch_score"] >= 0.75,
            df["watch_score"] >= 0.55,
            df["watch_score"] >= 0.35,
        ],
        [
            "critical",
            "high",
            "medium",
        ],
        default="normal",
    )
    cols = [
        "stat_date",
        "road_id",
        "pass_cnt",
        "vehicle_cnt",
        "trip_cnt",
        "peak_pass_ratio",
        "direction_bias",
        "road_activity_level",
        "peak_bias_type",
        "flow_score",
        "peak_sensitivity_score",
        "direction_imbalance_score",
        "watch_score",
        "watch_level",
        "watch_reason",
    ]
    return df.loc[:, cols].sort_values(["stat_date", "watch_score", "road_id"], ascending=[True, False, True]).reset_index(drop=True)


def build_region_hotspot_role_daily(region_grid: pd.DataFrame) -> pd.DataFrame:
    df = region_grid.copy()
    df = add_rank(df, ["stat_date"], ["total_od_trip_cnt", "grid_id"], [False, True], "rank_by_total_od")
    df = add_rank(df, ["stat_date"], ["pickup_trip_cnt", "grid_id"], [False, True], "rank_by_pickup")
    df = add_rank(df, ["stat_date"], ["dropoff_trip_cnt", "grid_id"], [False, True], "rank_by_dropoff")
    ordered_cols = [
        "stat_date",
        "grid_id",
        "rank_by_total_od",
        "rank_by_pickup",
        "rank_by_dropoff",
        "grid_center_lon",
        "grid_center_lat",
        "pickup_trip_cnt",
        "dropoff_trip_cnt",
        "total_od_trip_cnt",
        "active_vehicle_cnt",
        "night_od_trip_cnt",
        "peak_od_trip_cnt",
        "pickup_ratio",
        "grid_role_bias",
        "grid_activity_level",
    ]
    return df.loc[:, ordered_cols].sort_values(["stat_date", "rank_by_total_od"]).reset_index(drop=True)


def build_region_top20_daily(region_hotspot: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "stat_date",
        "grid_id",
        "rank_by_total_od",
        "rank_by_pickup",
        "rank_by_dropoff",
        "grid_center_lon",
        "grid_center_lat",
        "pickup_trip_cnt",
        "dropoff_trip_cnt",
        "total_od_trip_cnt",
        "active_vehicle_cnt",
        "peak_od_trip_cnt",
        "night_od_trip_cnt",
        "pickup_ratio",
        "grid_role_bias",
        "grid_activity_level",
    ]
    return (
        region_hotspot.loc[region_hotspot["rank_by_total_od"] <= 20, cols]
        .sort_values(["stat_date", "rank_by_total_od"])
        .reset_index(drop=True)
    )


def build_dispatch_focus_grid_daily(region_hotspot: pd.DataFrame) -> pd.DataFrame:
    df = region_hotspot.copy()
    df["od_per_vehicle"] = safe_divide(df["total_od_trip_cnt"], df["active_vehicle_cnt"]).fillna(0.0)
    for source_col, target_col in [
        ("total_od_trip_cnt", "activity_score"),
        ("peak_od_trip_cnt", "peak_score"),
        ("od_per_vehicle", "pressure_score"),
    ]:
        pct = df.groupby("stat_date")[source_col].rank(pct=True, ascending=True)
        df[target_col] = pct.fillna(0.0)
    df["departure_bias_score"] = np.maximum(df["pickup_ratio"] - 0.5, 0.0) * 2
    df["dispatch_score"] = (
        0.40 * df["activity_score"] +
        0.35 * df["pressure_score"] +
        0.15 * df["peak_score"] +
        0.10 * df["departure_bias_score"]
    )
    df["dispatch_level"] = np.select(
        [
            df["dispatch_score"] >= 0.75,
            df["dispatch_score"] >= 0.55,
            df["dispatch_score"] >= 0.35,
        ],
        [
            "very_high",
            "high",
            "medium",
        ],
        default="normal",
    )
    cols = [
        "stat_date",
        "grid_id",
        "grid_center_lon",
        "grid_center_lat",
        "total_od_trip_cnt",
        "peak_od_trip_cnt",
        "active_vehicle_cnt",
        "od_per_vehicle",
        "pickup_ratio",
        "dispatch_score",
        "dispatch_level",
    ]
    return df.loc[:, cols].sort_values(["stat_date", "dispatch_score", "grid_id"], ascending=[True, False, True]).reset_index(drop=True)


def build_region_bias_daily(region_grid: pd.DataFrame) -> pd.DataFrame:
    df = region_grid.copy()
    df["peak_share"] = safe_divide(df["peak_od_trip_cnt"], df["total_od_trip_cnt"]).fillna(0.0)
    df["night_share"] = safe_divide(df["night_od_trip_cnt"], df["total_od_trip_cnt"]).fillna(0.0)
    df["region_bias_type"] = np.select(
        [
            (df["night_share"] >= 0.25) & (df["peak_share"] < 0.35),
            (df["peak_share"] >= 0.45) & (df["grid_role_bias"] == "pickup_dominant"),
            (df["peak_share"] >= 0.45) & (df["grid_role_bias"] == "dropoff_dominant"),
            df["grid_role_bias"] == "pickup_dominant",
            df["grid_role_bias"] == "dropoff_dominant",
        ],
        [
            "night_active",
            "commute_source",
            "commute_destination",
            "pickup_source",
            "dropoff_sink",
        ],
        default="balanced_mixed",
    )
    cols = [
        "stat_date",
        "grid_id",
        "grid_center_lon",
        "grid_center_lat",
        "total_od_trip_cnt",
        "peak_od_trip_cnt",
        "night_od_trip_cnt",
        "pickup_ratio",
        "grid_role_bias",
        "grid_activity_level",
        "peak_share",
        "night_share",
        "region_bias_type",
    ]
    return df.loc[:, cols].sort_values(["stat_date", "total_od_trip_cnt", "grid_id"], ascending=[True, False, True]).reset_index(drop=True)


def build_abnormal_vehicle_daily_detail(vehicle_day: pd.DataFrame) -> pd.DataFrame:
    df = vehicle_day.copy()
    df["low_match_flag"] = df["matched_trip_ratio"] < 0.5
    df["high_speed_flag"] = df["avg_speed_kmh"] > 40
    df["night_overactive_flag"] = df["night_activity_flag"] & df["trip_frequency_level"].isin(["high", "very_high"])
    df["abnormal_flag"] = df["low_match_flag"] | df["high_speed_flag"] | df["night_overactive_flag"]

    def abnormal_reason(row: pd.Series) -> str:
        reasons: list[str] = []
        if bool(row["low_match_flag"]):
            reasons.append("low_match_ratio")
        if bool(row["high_speed_flag"]):
            reasons.append("high_avg_speed")
        if bool(row["night_overactive_flag"]):
            reasons.append("night_overactive")
        return "|".join(reasons)

    df = df.loc[df["abnormal_flag"]].copy()
    df["abnormal_reason"] = df.apply(abnormal_reason, axis=1)
    df["abnormal_type"] = np.select(
        [
            df["low_match_flag"] & ~df["high_speed_flag"] & ~df["night_overactive_flag"],
            df["high_speed_flag"] & ~df["low_match_flag"] & ~df["night_overactive_flag"],
            df["night_overactive_flag"] & ~df["low_match_flag"] & ~df["high_speed_flag"],
        ],
        [
            "match_quality",
            "speed_outlier",
            "night_operation",
        ],
        default="mixed",
    )
    ordered_cols = [
        "stat_date",
        "devid",
        "trip_cnt",
        "matched_trip_ratio",
        "avg_speed_kmh",
        "night_trip_ratio",
        "trip_frequency_level",
        "night_activity_flag",
        "peak_activity_flag",
        "low_match_flag",
        "high_speed_flag",
        "night_overactive_flag",
        "abnormal_type",
        "abnormal_reason",
    ]
    return df.loc[:, ordered_cols].sort_values(["stat_date", "devid"]).reset_index(drop=True)


def build_abnormal_vehicle_daily_summary(abnormal_detail: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        abnormal_detail.groupby("stat_date", as_index=False)
        .agg(
            abnormal_vehicle_cnt=("devid", "size"),
            low_match_vehicle_cnt=("low_match_flag", "sum"),
            high_speed_vehicle_cnt=("high_speed_flag", "sum"),
            night_overactive_vehicle_cnt=("night_overactive_flag", "sum"),
        )
        .sort_values("stat_date")
        .reset_index(drop=True)
    )
    return grouped


def build_data_quality_daily(trip_profile: pd.DataFrame, vehicle_day: pd.DataFrame) -> pd.DataFrame:
    trip_df = trip_profile.copy()
    trip_df["very_fast_flag"] = trip_df["trip_speed_level"].fillna("unknown").eq("very_fast")
    trip_daily = (
        trip_df.groupby("stat_date", as_index=False)
        .agg(
            total_trip_cnt=("trip_id", "size"),
            unmatched_trip_cnt=("has_matched_segments", lambda s: (~s).sum()),
            very_fast_trip_cnt=("very_fast_flag", "sum"),
        )
        .sort_values("stat_date")
    )
    trip_daily["unmatched_trip_ratio"] = safe_divide(trip_daily["unmatched_trip_cnt"], trip_daily["total_trip_cnt"]).fillna(0.0)
    trip_daily["very_fast_trip_ratio"] = safe_divide(trip_daily["very_fast_trip_cnt"], trip_daily["total_trip_cnt"]).fillna(0.0)

    low_match_vehicle = (
        vehicle_day.assign(low_match_flag=vehicle_day["matched_trip_ratio"] < 0.5)
        .groupby("stat_date", as_index=False)["low_match_flag"]
        .sum()
        .rename(columns={"low_match_flag": "low_match_vehicle_cnt"})
    )
    return trip_daily.merge(low_match_vehicle, on="stat_date", how="left").sort_values("stat_date").reset_index(drop=True)


def build_metric_definition() -> pd.DataFrame:
    rows = [
        {
            "table_name": "ads_daily_overview",
            "grain": "1 row = 1 stat_date",
            "primary_use": "daily dashboard and KPI cards",
            "source_tables": "tdm_vehicle_day_profile;tdm_time_slot_day_profile",
        },
        {
            "table_name": "ads_daily_growth_compare",
            "grain": "1 row = 1 stat_date",
            "primary_use": "day-over-day change analysis",
            "source_tables": "ads_daily_overview",
        },
        {
            "table_name": "ads_hourly_trend",
            "grain": "1 row = 1 stat_date + 1 biz_hour",
            "primary_use": "hourly trend charts",
            "source_tables": "tdm_time_slot_day_profile",
        },
        {
            "table_name": "ads_peak_window_top3_daily",
            "grain": "1 row = 1 stat_date + 1 rank",
            "primary_use": "peak window ranking",
            "source_tables": "ads_hourly_trend",
        },
        {
            "table_name": "ads_time_period_summary_daily",
            "grain": "1 row = 1 stat_date + 1 time_period_type",
            "primary_use": "time period behavior summary",
            "source_tables": "tdm_trip_profile",
        },
        {
            "table_name": "ads_trip_structure_daily",
            "grain": "1 row = 1 stat_date + trip structure combination",
            "primary_use": "trip structure distribution",
            "source_tables": "tdm_trip_profile",
        },
        {
            "table_name": "ads_trip_efficiency_by_period_daily",
            "grain": "1 row = 1 stat_date + 1 time_period_type",
            "primary_use": "trip efficiency comparison by time period",
            "source_tables": "ads_time_period_summary_daily",
        },
        {
            "table_name": "ads_trip_complexity_daily",
            "grain": "1 row = 1 stat_date",
            "primary_use": "trip complexity monitoring",
            "source_tables": "tdm_trip_profile",
        },
        {
            "table_name": "ads_vehicle_profile_5d",
            "grain": "1 row = 1 devid",
            "primary_use": "driver and vehicle profiling",
            "source_tables": "tdm_vehicle_5d_profile",
        },
        {
            "table_name": "ads_vehicle_segment_summary_5d",
            "grain": "1 row = 1 driver segment",
            "primary_use": "driver segmentation summary",
            "source_tables": "ads_vehicle_profile_5d",
        },
        {
            "table_name": "ads_vehicle_daily_operating_style",
            "grain": "1 row = 1 stat_date + 1 devid",
            "primary_use": "daily operating style for each vehicle",
            "source_tables": "tdm_vehicle_day_profile",
        },
        {
            "table_name": "ads_vehicle_road_preference_topn",
            "grain": "1 row = 1 devid + 1 road_id",
            "primary_use": "vehicle road preference topn",
            "source_tables": "tdm_vehicle_road_preference_5d",
        },
        {
            "table_name": "ads_vehicle_route_stability_5d",
            "grain": "1 row = 1 devid",
            "primary_use": "route stability profiling",
            "source_tables": "tdm_vehicle_road_preference_5d;tdm_vehicle_5d_profile",
        },
        {
            "table_name": "ads_road_hotspot_feature_daily",
            "grain": "1 row = 1 stat_date + 1 road_id",
            "primary_use": "road hotspot and road ranking",
            "source_tables": "tdm_road_day_profile",
        },
        {
            "table_name": "ads_road_top20_daily",
            "grain": "1 row = 1 stat_date + 1 rank",
            "primary_use": "top20 roads per day",
            "source_tables": "ads_road_hotspot_feature_daily",
        },
        {
            "table_name": "ads_road_watchlist_daily",
            "grain": "1 row = 1 stat_date + 1 road_id",
            "primary_use": "road watchlist and watch score",
            "source_tables": "ads_road_hotspot_feature_daily",
        },
        {
            "table_name": "ads_region_hotspot_role_daily",
            "grain": "1 row = 1 stat_date + 1 grid_id",
            "primary_use": "regional hotspot map and pickup/dropoff bias",
            "source_tables": "tdm_region_grid_day_profile",
        },
        {
            "table_name": "ads_region_top20_daily",
            "grain": "1 row = 1 stat_date + 1 rank",
            "primary_use": "top20 hotspot regions per day",
            "source_tables": "ads_region_hotspot_role_daily",
        },
        {
            "table_name": "ads_dispatch_focus_grid_daily",
            "grain": "1 row = 1 stat_date + 1 grid_id",
            "primary_use": "dispatch focus regions",
            "source_tables": "ads_region_hotspot_role_daily",
        },
        {
            "table_name": "ads_region_bias_daily",
            "grain": "1 row = 1 stat_date + 1 grid_id",
            "primary_use": "regional bias analysis",
            "source_tables": "tdm_region_grid_day_profile",
        },
        {
            "table_name": "ads_abnormal_vehicle_daily_detail",
            "grain": "1 row = 1 stat_date + 1 devid",
            "primary_use": "abnormal vehicle detail",
            "source_tables": "tdm_vehicle_day_profile",
        },
        {
            "table_name": "ads_abnormal_vehicle_daily_summary",
            "grain": "1 row = 1 stat_date",
            "primary_use": "abnormal vehicle trend",
            "source_tables": "ads_abnormal_vehicle_daily_detail",
        },
        {
            "table_name": "ads_data_quality_daily",
            "grain": "1 row = 1 stat_date",
            "primary_use": "data quality monitoring",
            "source_tables": "tdm_trip_profile;tdm_vehicle_day_profile",
        },
    ]
    return pd.DataFrame(rows)


def read_inputs() -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for name, path in INPUT_FILES.items():
        log(f"Loading {path.name}")
        frames[name] = pd.read_parquet(path)
    return frames


def write_parquet(outputs: dict[str, pd.DataFrame]) -> None:
    for key, frame in outputs.items():
        path = OUTPUT_FILES[key]
        log(f"Writing {path.name}")
        frame.to_parquet(path, index=False)


def build_summary(
    started_at: str,
    finished_at: str,
    outputs: dict[str, pd.DataFrame],
    metric_definition: pd.DataFrame,
) -> dict[str, object]:
    date_min = outputs["ads_daily_overview"]["stat_date"].min()
    date_max = outputs["ads_daily_overview"]["stat_date"].max()
    distinct_dates = int(outputs["ads_daily_overview"]["stat_date"].nunique())
    hourly_rows = int(len(outputs["ads_hourly_trend"]))
    expected_hourly_rows = distinct_dates * 24
    abnormal_detail = outputs["ads_abnormal_vehicle_daily_detail"]
    abnormal_summary = outputs["ads_abnormal_vehicle_daily_summary"]

    summary = {
        "status": "success",
        "build_started_at_utc": started_at,
        "build_finished_at_utc": finished_at,
        "input_root": str(INPUT_DIR),
        "output_root": str(OUTPUT_DIR),
        "source_files": {name: path.name for name, path in INPUT_FILES.items()},
        "row_counts": {name: int(len(df)) for name, df in outputs.items()},
        "metric_definition_count": int(len(metric_definition)),
        "validation": {
            "stat_date_min": str(date_min),
            "stat_date_max": str(date_max),
            "stat_date_distinct_cnt": distinct_dates,
            "hourly_row_cnt": hourly_rows,
            "expected_hourly_row_cnt": expected_hourly_rows,
            "hourly_coverage_ok": hourly_rows == expected_hourly_rows,
            "peak_top3_row_cnt": int(len(outputs["ads_peak_window_top3_daily"])),
            "road_top20_row_cnt": int(len(outputs["ads_road_top20_daily"])),
            "region_top20_row_cnt": int(len(outputs["ads_region_top20_daily"])),
            "abnormal_summary_matches_detail": int(abnormal_detail["stat_date"].size) == int(
                abnormal_summary["abnormal_vehicle_cnt"].sum()
            ),
            "negative_trip_cnt_in_overview": int((outputs["ads_daily_overview"]["total_trip_cnt"] < 0).sum()),
            "negative_speed_in_overview": int((outputs["ads_daily_overview"]["global_avg_speed_kmh"] < 0).sum()),
            "negative_trip_cnt_in_hourly": int((outputs["ads_hourly_trend"]["trip_cnt"] < 0).sum()),
        },
        "file_sizes_bytes": {
            key: OUTPUT_FILES[key].stat().st_size
            for key in outputs
            if OUTPUT_FILES[key].exists()
        },
    }
    return summary


def main() -> None:
    started_at = now_utc_iso()
    start_ts = time.time()
    OUTPUT_DIR.mkdir(exist_ok=True)

    inputs = read_inputs()
    outputs: dict[str, pd.DataFrame] = {}

    log("Building ads_daily_overview")
    outputs["ads_daily_overview"] = build_daily_overview(
        inputs["vehicle_day_profile"],
        inputs["time_slot_day_profile"],
    )

    log("Building ads_daily_growth_compare")
    outputs["ads_daily_growth_compare"] = build_daily_growth_compare(outputs["ads_daily_overview"])

    log("Building ads_hourly_trend")
    outputs["ads_hourly_trend"] = build_hourly_trend(inputs["time_slot_day_profile"])

    log("Building ads_peak_window_top3_daily")
    outputs["ads_peak_window_top3_daily"] = build_peak_window_top3_daily(outputs["ads_hourly_trend"])

    log("Building ads_time_period_summary_daily")
    outputs["ads_time_period_summary_daily"] = build_time_period_summary_daily(inputs["trip_profile"])

    log("Building ads_trip_structure_daily")
    outputs["ads_trip_structure_daily"] = build_trip_structure_daily(inputs["trip_profile"])

    log("Building ads_trip_efficiency_by_period_daily")
    outputs["ads_trip_efficiency_by_period_daily"] = build_trip_efficiency_by_period_daily(
        outputs["ads_time_period_summary_daily"]
    )

    log("Building ads_trip_complexity_daily")
    outputs["ads_trip_complexity_daily"] = build_trip_complexity_daily(inputs["trip_profile"])

    log("Building ads_vehicle_profile_5d")
    outputs["ads_vehicle_profile_5d"] = build_vehicle_profile_5d(inputs["vehicle_5d_profile"])

    log("Building ads_vehicle_segment_summary_5d")
    outputs["ads_vehicle_segment_summary_5d"] = build_vehicle_segment_summary_5d(outputs["ads_vehicle_profile_5d"])

    log("Building ads_vehicle_daily_operating_style")
    outputs["ads_vehicle_daily_operating_style"] = build_vehicle_daily_operating_style(inputs["vehicle_day_profile"])

    log("Building ads_vehicle_road_preference_topn")
    outputs["ads_vehicle_road_preference_topn"] = build_vehicle_road_preference_topn(
        inputs["vehicle_road_preference_5d"]
    )

    log("Building ads_vehicle_route_stability_5d")
    outputs["ads_vehicle_route_stability_5d"] = build_vehicle_route_stability_5d(
        outputs["ads_vehicle_road_preference_topn"],
        outputs["ads_vehicle_profile_5d"],
    )

    log("Building ads_road_hotspot_feature_daily")
    outputs["ads_road_hotspot_feature_daily"] = build_road_hotspot_feature_daily(inputs["road_day_profile"])

    log("Building ads_road_top20_daily")
    outputs["ads_road_top20_daily"] = build_road_top20_daily(outputs["ads_road_hotspot_feature_daily"])

    log("Building ads_road_watchlist_daily")
    outputs["ads_road_watchlist_daily"] = build_road_watchlist_daily(outputs["ads_road_hotspot_feature_daily"])

    log("Building ads_region_hotspot_role_daily")
    outputs["ads_region_hotspot_role_daily"] = build_region_hotspot_role_daily(inputs["region_grid_day_profile"])

    log("Building ads_region_top20_daily")
    outputs["ads_region_top20_daily"] = build_region_top20_daily(outputs["ads_region_hotspot_role_daily"])

    log("Building ads_dispatch_focus_grid_daily")
    outputs["ads_dispatch_focus_grid_daily"] = build_dispatch_focus_grid_daily(outputs["ads_region_hotspot_role_daily"])

    log("Building ads_region_bias_daily")
    outputs["ads_region_bias_daily"] = build_region_bias_daily(inputs["region_grid_day_profile"])

    log("Building ads_abnormal_vehicle_daily_detail")
    outputs["ads_abnormal_vehicle_daily_detail"] = build_abnormal_vehicle_daily_detail(inputs["vehicle_day_profile"])

    log("Building ads_abnormal_vehicle_daily_summary")
    outputs["ads_abnormal_vehicle_daily_summary"] = build_abnormal_vehicle_daily_summary(
        outputs["ads_abnormal_vehicle_daily_detail"]
    )

    log("Building ads_data_quality_daily")
    outputs["ads_data_quality_daily"] = build_data_quality_daily(
        inputs["trip_profile"],
        inputs["vehicle_day_profile"],
    )

    metric_definition = build_metric_definition()
    write_parquet(outputs)

    log(f"Writing {OUTPUT_FILES['ads_metric_definition'].name}")
    metric_definition.to_csv(OUTPUT_FILES["ads_metric_definition"], index=False, encoding="utf-8")

    finished_at = now_utc_iso()
    summary = build_summary(started_at, finished_at, outputs, metric_definition)
    summary["duration_seconds"] = round(time.time() - start_ts, 2)

    log(f"Writing {OUTPUT_FILES['ads_build_summary'].name}")
    OUTPUT_FILES["ads_build_summary"].write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log("ADS build completed")


if __name__ == "__main__":
    main()

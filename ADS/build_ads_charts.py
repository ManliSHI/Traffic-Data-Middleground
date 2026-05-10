from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ADS_DIR = Path(__file__).resolve().parent
INPUT_DIR = ADS_DIR / "ads_output"
OUTPUT_DIR = ADS_DIR / "charts_output"

INPUT_FILES = {
    "ads_daily_overview": INPUT_DIR / "ads_daily_overview.parquet",
    "ads_daily_growth_compare": INPUT_DIR / "ads_daily_growth_compare.parquet",
    "ads_hourly_trend": INPUT_DIR / "ads_hourly_trend.parquet",
    "ads_peak_window_top3_daily": INPUT_DIR / "ads_peak_window_top3_daily.parquet",
    "ads_trip_structure_daily": INPUT_DIR / "ads_trip_structure_daily.parquet",
    "ads_vehicle_profile_5d": INPUT_DIR / "ads_vehicle_profile_5d.parquet",
    "ads_road_hotspot_feature_daily": INPUT_DIR / "ads_road_hotspot_feature_daily.parquet",
    "ads_region_hotspot_role_daily": INPUT_DIR / "ads_region_hotspot_role_daily.parquet",
}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def save_fig(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def series_to_label(values: pd.Series) -> list[str]:
    return pd.to_datetime(values).dt.strftime("%Y-%m-%d").tolist()


def build_daily_trip_vehicle_combo(daily: pd.DataFrame, path: Path) -> None:
    fig, ax1 = plt.subplots(figsize=(10, 5))
    labels = series_to_label(daily["stat_date"])
    x = np.arange(len(labels))
    ax1.bar(x, daily["total_trip_cnt"], color="#3b82f6", label="Total Trips")
    ax1.set_ylabel("Total Trips")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=20)

    ax2 = ax1.twinx()
    ax2.plot(x, daily["active_vehicle_cnt"], color="#ef4444", marker="o", linewidth=2, label="Active Vehicles")
    ax2.set_ylabel("Active Vehicles")
    ax1.set_title("Daily Trips and Active Vehicles")
    save_fig(fig, path)


def build_daily_avg_speed(daily: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = series_to_label(daily["stat_date"])
    ax.plot(labels, daily["global_avg_speed_kmh"], marker="o", linewidth=2, label="Global Avg Speed")
    ax.plot(labels, daily["avg_vehicle_speed_kmh"], marker="s", linewidth=2, label="Avg Vehicle Speed")
    ax.set_ylabel("km/h")
    ax.set_title("Daily Average Speed")
    ax.legend()
    save_fig(fig, path)


def build_daily_night_peak_active(daily: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = series_to_label(daily["stat_date"])
    x = np.arange(len(labels))
    width = 0.38
    ax.bar(x - width / 2, daily["night_active_vehicle_cnt"], width=width, label="Night Active Vehicles", color="#8b5cf6")
    ax.bar(x + width / 2, daily["peak_active_vehicle_cnt"], width=width, label="Peak Active Vehicles", color="#f59e0b")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20)
    ax.set_ylabel("Vehicle Count")
    ax.set_title("Night vs Peak Active Vehicles")
    ax.legend()
    save_fig(fig, path)


def build_daily_dod_growth(growth: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = series_to_label(growth["stat_date"])
    x = np.arange(len(labels))
    width = 0.38
    ax.bar(x - width / 2, growth["trip_cnt_dod_growth"].fillna(0), width=width, label="Trip DoD Growth", color="#10b981")
    ax.bar(x + width / 2, growth["active_vehicle_dod_growth"].fillna(0), width=width, label="Vehicle DoD Growth", color="#0ea5e9")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20)
    ax.set_ylabel("Growth Rate")
    ax.set_title("Day-over-Day Growth")
    ax.legend()
    save_fig(fig, path)


def build_daily_speed_change(growth: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = series_to_label(growth["stat_date"])
    colors = ["#ef4444" if v < 0 else "#22c55e" for v in growth["speed_dod_change"].fillna(0)]
    ax.bar(labels, growth["speed_dod_change"].fillna(0), color=colors)
    ax.axhline(0, color="#111827", linewidth=1)
    ax.set_ylabel("km/h Change")
    ax.set_title("Daily Speed Change vs Previous Day")
    save_fig(fig, path)


def build_hourly_line_chart(hourly: pd.DataFrame, y_col: str, title: str, y_label: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    for stat_date, group in hourly.groupby("stat_date"):
        label = pd.to_datetime(stat_date).strftime("%Y-%m-%d")
        ax.plot(group["biz_hour"], group[y_col], marker="o", linewidth=1.8, label=label)
    ax.set_xticks(range(24))
    ax.set_xlabel("Hour")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.legend(ncol=3, fontsize=8)
    save_fig(fig, path)


def build_hourly_trip_heatmap(hourly: pd.DataFrame, path: Path) -> None:
    pivot = hourly.pivot(index="stat_date", columns="biz_hour", values="trip_cnt").sort_index()
    pivot.index = [pd.to_datetime(v).strftime("%Y-%m-%d") for v in pivot.index]
    fig, ax = plt.subplots(figsize=(12, 4.5))
    sns.heatmap(pivot, cmap="YlOrRd", ax=ax)
    ax.set_title("Hourly Trip Count Heatmap")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Date")
    save_fig(fig, path)


def build_peak_top3_chart(peak_top3: pd.DataFrame, path: Path) -> None:
    dates = sorted(peak_top3["stat_date"].unique())
    fig, axes = plt.subplots(len(dates), 1, figsize=(10, 3.2 * len(dates)))
    if len(dates) == 1:
        axes = [axes]
    for ax, stat_date in zip(axes, dates):
        group = peak_top3.loc[peak_top3["stat_date"] == stat_date].sort_values("rank_in_day")
        labels = [f"Rank {r}: {h}:00" for r, h in zip(group["rank_in_day"], group["biz_hour"])]
        ax.bar(labels, group["trip_cnt"], color=["#2563eb", "#60a5fa", "#93c5fd"])
        ax.set_title(f"Top 3 Peak Hours - {pd.to_datetime(stat_date).strftime('%Y-%m-%d')}")
        ax.set_ylabel("Trips")
        ax.tick_params(axis="x", rotation=15)
    save_fig(fig, path)


def build_peak_share_chart(peak_top3: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for stat_date, group in peak_top3.groupby("stat_date"):
        label = pd.to_datetime(stat_date).strftime("%Y-%m-%d")
        ax.plot(group["rank_in_day"], group["trip_share_in_day"], marker="o", linewidth=2, label=label)
    ax.set_xticks([1, 2, 3])
    ax.set_xlabel("Rank in Day")
    ax.set_ylabel("Trip Share in Day")
    ax.set_title("Peak Hour Share within Day")
    ax.legend(ncol=3, fontsize=8)
    save_fig(fig, path)


def build_trip_distance_structure(structure: pd.DataFrame, path: Path) -> None:
    order = ["short", "medium", "long", "extra_long"]
    pivot = (
        structure.groupby(["stat_date", "trip_distance_level"], as_index=False)["trip_cnt"]
        .sum()
        .pivot(index="stat_date", columns="trip_distance_level", values="trip_cnt")
        .fillna(0)
        .reindex(columns=order)
    )
    pivot.index = [pd.to_datetime(v).strftime("%Y-%m-%d") for v in pivot.index]
    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = np.zeros(len(pivot))
    colors = ["#60a5fa", "#34d399", "#f59e0b", "#ef4444"]
    for level, color in zip(order, colors):
        vals = pivot[level].values
        ax.bar(pivot.index, vals, bottom=bottom, label=level, color=color)
        bottom += vals
    ax.set_ylabel("Trip Count")
    ax.set_title("Trip Distance Level Structure")
    ax.legend()
    save_fig(fig, path)


def build_trip_speed_structure(structure: pd.DataFrame, path: Path) -> None:
    order = ["slow", "normal", "fast", "very_fast", "unknown"]
    pivot = (
        structure.groupby(["stat_date", "trip_speed_level"], as_index=False)["trip_cnt"]
        .sum()
        .pivot(index="stat_date", columns="trip_speed_level", values="trip_cnt")
        .fillna(0)
    )
    for col in order:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot[order]
    pivot.index = [pd.to_datetime(v).strftime("%Y-%m-%d") for v in pivot.index]
    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = np.zeros(len(pivot))
    colors = ["#f97316", "#10b981", "#3b82f6", "#8b5cf6", "#9ca3af"]
    for level, color in zip(order, colors):
        vals = pivot[level].values
        ax.bar(pivot.index, vals, bottom=bottom, label=level, color=color)
        bottom += vals
    ax.set_ylabel("Trip Count")
    ax.set_title("Trip Speed Level Structure")
    ax.legend()
    save_fig(fig, path)


def build_trip_distance_duration_matrix(structure: pd.DataFrame, path: Path) -> None:
    pivot = (
        structure.groupby(["trip_distance_level", "trip_duration_level"], as_index=False)["trip_cnt"]
        .sum()
        .pivot(index="trip_distance_level", columns="trip_duration_level", values="trip_cnt")
        .fillna(0)
    )
    row_order = ["short", "medium", "long", "extra_long"]
    col_order = ["short", "medium", "long", "extra_long"]
    pivot = pivot.reindex(index=row_order, columns=col_order)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="Blues", ax=ax)
    ax.set_title("Trip Distance vs Duration Matrix")
    ax.set_xlabel("Duration Level")
    ax.set_ylabel("Distance Level")
    save_fig(fig, path)


def build_driver_activity_structure(vehicle: pd.DataFrame, path: Path) -> None:
    order = ["low", "medium", "high", "core"]
    counts = vehicle["driver_activity_level"].value_counts().reindex(order).fillna(0)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(counts.index, counts.values, color=["#cbd5e1", "#93c5fd", "#60a5fa", "#1d4ed8"])
    ax.set_title("Driver Activity Level Distribution")
    ax.set_ylabel("Vehicle Count")
    save_fig(fig, path)


def build_core_full_attendance_counts(vehicle: pd.DataFrame, path: Path) -> None:
    values = [
        int(vehicle["core_driver_flag"].sum()),
        int(vehicle["full_attendance_flag"].sum()),
    ]
    labels = ["Core Drivers", "Full Attendance"]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(labels, values, color=["#2563eb", "#16a34a"])
    ax.set_ylabel("Vehicle Count")
    ax.set_title("Core and Full Attendance Drivers")
    save_fig(fig, path)


def build_driver_top20(vehicle: pd.DataFrame, path: Path) -> None:
    top = vehicle.nsmallest(20, "rank_by_total_trip_cnt").sort_values("total_trip_cnt")
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.barh(top["devid"].astype(str), top["total_trip_cnt"], color="#2563eb")
    ax.set_xlabel("Total Trips in 5 Days")
    ax.set_ylabel("Device ID")
    ax.set_title("Top 20 Drivers by Total Trips")
    save_fig(fig, path)


def build_road_top20_by_day(road: pd.DataFrame, value_col: str, title_prefix: str, path: Path) -> None:
    dates = sorted(road["stat_date"].unique())
    fig, axes = plt.subplots(len(dates), 1, figsize=(10, 4 * len(dates)))
    if len(dates) == 1:
        axes = [axes]
    for ax, stat_date in zip(axes, dates):
        group = road.loc[road["stat_date"] == stat_date].nsmallest(20, f"rank_by_{'pass_cnt' if value_col=='pass_cnt' else 'pass_cnt'}")
        if value_col == "peak_pass_cnt":
            group = road.loc[road["stat_date"] == stat_date].sort_values(["peak_pass_cnt", "road_id"], ascending=[False, True]).head(20)
        else:
            group = road.loc[road["stat_date"] == stat_date].sort_values([value_col, "road_id"], ascending=[False, True]).head(20)
        group = group.sort_values(value_col)
        ax.barh(group["road_id"].astype(str), group[value_col], color="#0ea5e9")
        ax.set_title(f"{title_prefix} - {pd.to_datetime(stat_date).strftime('%Y-%m-%d')}")
        ax.set_xlabel(value_col)
    save_fig(fig, path)


def build_road_direction_bias_distribution(road: pd.DataFrame, path: Path) -> None:
    counts = road.groupby("direction_bias", as_index=False)["road_id"].size().rename(columns={"size": "road_cnt"})
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=counts, x="direction_bias", y="road_cnt", ax=ax, palette="Blues_d")
    ax.set_title("Road Direction Bias Distribution")
    ax.set_xlabel("Direction Bias")
    ax.set_ylabel("Road Count")
    save_fig(fig, path)


def build_region_hotspot_top20_map(region: pd.DataFrame, path: Path) -> None:
    dates = sorted(region["stat_date"].unique())
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes = axes.flatten()
    for ax in axes:
        ax.set_visible(False)
    for ax, stat_date in zip(axes, dates):
        ax.set_visible(True)
        group = region.loc[region["stat_date"] == stat_date].sort_values(["rank_by_total_od"]).head(20)
        sizes = np.clip(group["total_od_trip_cnt"] / group["total_od_trip_cnt"].max() * 600, 50, None)
        scatter = ax.scatter(
            group["grid_center_lon"],
            group["grid_center_lat"],
            s=sizes,
            c=group["total_od_trip_cnt"],
            cmap="viridis",
            alpha=0.7,
            edgecolors="black",
            linewidths=0.4,
        )
        ax.set_title(pd.to_datetime(stat_date).strftime("%Y-%m-%d"))
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
    fig.suptitle("Top 20 Regional Hotspots by Day", y=1.02)
    fig.colorbar(scatter, ax=axes.tolist(), shrink=0.75, label="Total OD Trips")
    save_fig(fig, path)


def build_region_pickup_dropoff_top10(region: pd.DataFrame, path: Path) -> None:
    agg = (
        region.groupby("grid_id", as_index=False)
        .agg(
            pickup_trip_cnt=("pickup_trip_cnt", "sum"),
            dropoff_trip_cnt=("dropoff_trip_cnt", "sum"),
        )
    )
    top_pickup = agg.sort_values(["pickup_trip_cnt", "grid_id"], ascending=[False, True]).head(10).sort_values("pickup_trip_cnt")
    top_dropoff = agg.sort_values(["dropoff_trip_cnt", "grid_id"], ascending=[False, True]).head(10).sort_values("dropoff_trip_cnt")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].barh(top_pickup["grid_id"], top_pickup["pickup_trip_cnt"], color="#10b981")
    axes[0].set_title("Top 10 Pickup Hotspots")
    axes[0].set_xlabel("Pickup Trips")
    axes[1].barh(top_dropoff["grid_id"], top_dropoff["dropoff_trip_cnt"], color="#f59e0b")
    axes[1].set_title("Top 10 Dropoff Hotspots")
    axes[1].set_xlabel("Dropoff Trips")
    save_fig(fig, path)


def build_region_role_bias_distribution(region: pd.DataFrame, path: Path) -> None:
    counts = region.groupby("grid_role_bias", as_index=False)["grid_id"].size().rename(columns={"size": "grid_cnt"})
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=counts, x="grid_role_bias", y="grid_cnt", ax=ax, palette="Set2")
    ax.set_title("Regional Role Bias Distribution")
    ax.set_xlabel("Grid Role Bias")
    ax.set_ylabel("Grid Count")
    save_fig(fig, path)


def build_chart_manifest() -> list[dict[str, str]]:
    return [
        {"file_name": "01_daily_trip_vehicle_combo.png", "chart_name": "每日活跃车辆数与总trip数双轴图", "source_table": "ads_daily_overview", "category": "总览"},
        {"file_name": "02_daily_avg_speed.png", "chart_name": "每日平均速度趋势图", "source_table": "ads_daily_overview", "category": "总览"},
        {"file_name": "03_daily_night_peak_active_vehicles.png", "chart_name": "夜间与高峰活跃车辆对比图", "source_table": "ads_daily_overview", "category": "总览"},
        {"file_name": "04_daily_dod_growth.png", "chart_name": "日环比增长图", "source_table": "ads_daily_growth_compare", "category": "趋势"},
        {"file_name": "05_daily_speed_change.png", "chart_name": "日速度变化图", "source_table": "ads_daily_growth_compare", "category": "趋势"},
        {"file_name": "06_hourly_trip_trend.png", "chart_name": "每小时trip趋势图", "source_table": "ads_hourly_trend", "category": "小时趋势"},
        {"file_name": "07_hourly_vehicle_trend.png", "chart_name": "每小时活跃车辆趋势图", "source_table": "ads_hourly_trend", "category": "小时趋势"},
        {"file_name": "08_hourly_speed_trend.png", "chart_name": "每小时平均速度趋势图", "source_table": "ads_hourly_trend", "category": "小时趋势"},
        {"file_name": "09_hourly_trip_heatmap.png", "chart_name": "小时trip热力图", "source_table": "ads_hourly_trend", "category": "小时趋势"},
        {"file_name": "10_peak_window_top3_daily.png", "chart_name": "每日Top3高峰小时图", "source_table": "ads_peak_window_top3_daily", "category": "高峰"},
        {"file_name": "11_peak_window_share_daily.png", "chart_name": "高峰小时占比图", "source_table": "ads_peak_window_top3_daily", "category": "高峰"},
        {"file_name": "12_trip_distance_structure.png", "chart_name": "行程距离结构图", "source_table": "ads_trip_structure_daily", "category": "行程结构"},
        {"file_name": "13_trip_speed_structure.png", "chart_name": "行程速度结构图", "source_table": "ads_trip_structure_daily", "category": "行程结构"},
        {"file_name": "14_trip_distance_duration_matrix.png", "chart_name": "距离-时长结构矩阵图", "source_table": "ads_trip_structure_daily", "category": "行程结构"},
        {"file_name": "15_driver_activity_structure.png", "chart_name": "司机活跃度结构图", "source_table": "ads_vehicle_profile_5d", "category": "司机画像"},
        {"file_name": "16_core_full_attendance_counts.png", "chart_name": "核心司机与满勤司机数量图", "source_table": "ads_vehicle_profile_5d", "category": "司机画像"},
        {"file_name": "17_driver_top20_by_trip.png", "chart_name": "司机Top20排行榜", "source_table": "ads_vehicle_profile_5d", "category": "司机画像"},
        {"file_name": "18_road_top20_by_day.png", "chart_name": "每日热点道路Top20图", "source_table": "ads_road_hotspot_feature_daily", "category": "道路热点"},
        {"file_name": "19_road_peak_top20_by_day.png", "chart_name": "每日高峰道路Top20图", "source_table": "ads_road_hotspot_feature_daily", "category": "道路热点"},
        {"file_name": "20_road_direction_bias_distribution.png", "chart_name": "道路方向偏向分布图", "source_table": "ads_road_hotspot_feature_daily", "category": "道路热点"},
        {"file_name": "21_region_hotspot_top20_map.png", "chart_name": "热点区域Top20地图", "source_table": "ads_region_hotspot_role_daily", "category": "区域热点"},
        {"file_name": "22_region_pickup_dropoff_top10.png", "chart_name": "上车/下车热点Top10图", "source_table": "ads_region_hotspot_role_daily", "category": "区域热点"},
        {"file_name": "23_region_role_bias_distribution.png", "chart_name": "区域角色偏向分布图", "source_table": "ads_region_hotspot_role_daily", "category": "区域热点"},
    ]


def write_manifest(manifest: list[dict[str, str]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["file_name", "chart_name", "source_table", "category"])
        writer.writeheader()
        writer.writerows(manifest)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid")

    started_at = now_utc_iso()
    log("Loading ADS outputs")
    daily = pd.read_parquet(INPUT_FILES["ads_daily_overview"])
    growth = pd.read_parquet(INPUT_FILES["ads_daily_growth_compare"])
    hourly = pd.read_parquet(INPUT_FILES["ads_hourly_trend"])
    peak_top3 = pd.read_parquet(INPUT_FILES["ads_peak_window_top3_daily"])
    structure = pd.read_parquet(INPUT_FILES["ads_trip_structure_daily"])
    vehicle = pd.read_parquet(INPUT_FILES["ads_vehicle_profile_5d"])
    road = pd.read_parquet(INPUT_FILES["ads_road_hotspot_feature_daily"])
    region = pd.read_parquet(INPUT_FILES["ads_region_hotspot_role_daily"])

    log("Generating chart images")
    build_daily_trip_vehicle_combo(daily, OUTPUT_DIR / "01_daily_trip_vehicle_combo.png")
    build_daily_avg_speed(daily, OUTPUT_DIR / "02_daily_avg_speed.png")
    build_daily_night_peak_active(daily, OUTPUT_DIR / "03_daily_night_peak_active_vehicles.png")
    build_daily_dod_growth(growth, OUTPUT_DIR / "04_daily_dod_growth.png")
    build_daily_speed_change(growth, OUTPUT_DIR / "05_daily_speed_change.png")
    build_hourly_line_chart(hourly, "trip_cnt", "Hourly Trip Trend", "Trip Count", OUTPUT_DIR / "06_hourly_trip_trend.png")
    build_hourly_line_chart(hourly, "vehicle_cnt", "Hourly Active Vehicle Trend", "Vehicle Count", OUTPUT_DIR / "07_hourly_vehicle_trend.png")
    build_hourly_line_chart(hourly, "avg_speed_kmh", "Hourly Average Speed Trend", "km/h", OUTPUT_DIR / "08_hourly_speed_trend.png")
    build_hourly_trip_heatmap(hourly, OUTPUT_DIR / "09_hourly_trip_heatmap.png")
    build_peak_top3_chart(peak_top3, OUTPUT_DIR / "10_peak_window_top3_daily.png")
    build_peak_share_chart(peak_top3, OUTPUT_DIR / "11_peak_window_share_daily.png")
    build_trip_distance_structure(structure, OUTPUT_DIR / "12_trip_distance_structure.png")
    build_trip_speed_structure(structure, OUTPUT_DIR / "13_trip_speed_structure.png")
    build_trip_distance_duration_matrix(structure, OUTPUT_DIR / "14_trip_distance_duration_matrix.png")
    build_driver_activity_structure(vehicle, OUTPUT_DIR / "15_driver_activity_structure.png")
    build_core_full_attendance_counts(vehicle, OUTPUT_DIR / "16_core_full_attendance_counts.png")
    build_driver_top20(vehicle, OUTPUT_DIR / "17_driver_top20_by_trip.png")
    build_road_top20_by_day(road, "pass_cnt", "Road Top 20 by Pass Count", OUTPUT_DIR / "18_road_top20_by_day.png")
    build_road_top20_by_day(road, "peak_pass_cnt", "Road Top 20 by Peak Pass Count", OUTPUT_DIR / "19_road_peak_top20_by_day.png")
    build_road_direction_bias_distribution(road, OUTPUT_DIR / "20_road_direction_bias_distribution.png")
    build_region_hotspot_top20_map(region, OUTPUT_DIR / "21_region_hotspot_top20_map.png")
    build_region_pickup_dropoff_top10(region, OUTPUT_DIR / "22_region_pickup_dropoff_top10.png")
    build_region_role_bias_distribution(region, OUTPUT_DIR / "23_region_role_bias_distribution.png")

    manifest = build_chart_manifest()
    write_manifest(manifest, OUTPUT_DIR / "chart_manifest.csv")

    finished_at = now_utc_iso()
    png_files = sorted(OUTPUT_DIR.glob("*.png"))
    summary = {
        "status": "success",
        "build_started_at_utc": started_at,
        "build_finished_at_utc": finished_at,
        "chart_count": len(png_files),
        "chart_files": [p.name for p in png_files],
        "manifest_file": "chart_manifest.csv",
    }
    (OUTPUT_DIR / "charts_build_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log("Chart generation completed")


if __name__ == "__main__":
    main()

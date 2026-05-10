# ADS 候选 23 表清单

## 1. 文档目的

本文档将当前项目建议建设的 ADS 结果表统一整理为 23 张表，方便后续同学：

- 快速理解 ADS 层全貌
- 选择最终要落地的表
- 对接可视化、报告和 PPT

说明：

- 当前这 23 张表已经全部落地到 `ads_output/`
- 对应的 preview 也已经全部生成到 `preview/`
- 所有表都基于当前 TDM 能力边界设计，没有强依赖外部 POI、真实商圈边界或道路名称映射

---

## 2. 23 表总览

| 编号 | 表名 | 类别 | 状态 | 粒度 | 主要来源 | 主要用途 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `ads_daily_overview` | 总览 | 已落地 | `1 row = 1 stat_date` | `tdm_vehicle_day_profile` + `tdm_time_slot_day_profile` | 每日核心 KPI |
| 2 | `ads_daily_growth_compare` | 总览 | 已落地 | `1 row = 1 stat_date` | `ads_daily_overview` | 日环比分析 |
| 3 | `ads_hourly_trend` | 时序 | 已落地 | `1 row = 1 stat_date + 1 biz_hour` | `tdm_time_slot_day_profile` | 每小时趋势 |
| 4 | `ads_peak_window_top3_daily` | 时序 | 已落地 | `1 row = 1 stat_date + 1 rank` | `ads_hourly_trend` | 每日高峰窗口识别 |
| 5 | `ads_time_period_summary_daily` | 时段 | 已落地 | `1 row = 1 stat_date + 1 time_period_type` | `tdm_trip_profile` | 早晚高峰 / 夜间对比 |
| 6 | `ads_trip_structure_daily` | 行程结构 | 已落地 | `1 row = 1 stat_date + 结构组合` | `tdm_trip_profile` | 长短单 / 速度结构 |
| 7 | `ads_trip_efficiency_by_period_daily` | 行程结构 | 已落地 | `1 row = 1 stat_date + 1 time_period_type` | `tdm_trip_profile` | 不同时段效率分析 |
| 8 | `ads_trip_complexity_daily` | 行程结构 | 已落地 | `1 row = 1 stat_date` | `tdm_trip_profile` | 路径复杂度分析 |
| 9 | `ads_vehicle_profile_5d` | 司机画像 | 已落地 | `1 row = 1 devid` | `tdm_vehicle_5d_profile` | 五日司机画像 |
| 10 | `ads_vehicle_segment_summary_5d` | 司机画像 | 已落地 | `1 row = 1 分层组合` | `ads_vehicle_profile_5d` | 司机群体分层 |
| 11 | `ads_vehicle_daily_operating_style` | 司机画像 | 已落地 | `1 row = 1 stat_date + 1 devid` | `tdm_vehicle_day_profile` | 日级运营风格 |
| 12 | `ads_vehicle_road_preference_topn` | 司机画像 | 已落地 | `1 row = 1 devid + 1 road_id` | `tdm_vehicle_road_preference_5d` | 司机偏好道路 |
| 13 | `ads_vehicle_route_stability_5d` | 司机画像 | 已落地 | `1 row = 1 devid` | `tdm_vehicle_road_preference_5d` + `tdm_vehicle_5d_profile` | 路线稳定性 |
| 14 | `ads_road_hotspot_feature_daily` | 道路热点 | 已落地 | `1 row = 1 stat_date + 1 road_id` | `tdm_road_day_profile` | 道路热度主表 |
| 15 | `ads_road_top20_daily` | 道路热点 | 已落地 | `1 row = 1 stat_date + 1 rank` | `ads_road_hotspot_feature_daily` | 每日热点道路 Top20 |
| 16 | `ads_road_watchlist_daily` | 道路热点 | 已落地 | `1 row = 1 stat_date + 1 road_id` | `ads_road_hotspot_feature_daily` | 重点关注道路 |
| 17 | `ads_region_hotspot_role_daily` | 区域热点 | 已落地 | `1 row = 1 stat_date + 1 grid_id` | `tdm_region_grid_day_profile` | 区域热度与角色主表 |
| 18 | `ads_region_top20_daily` | 区域热点 | 已落地 | `1 row = 1 stat_date + 1 rank` | `ads_region_hotspot_role_daily` | 每日热点区域 Top20 |
| 19 | `ads_dispatch_focus_grid_daily` | 区域热点 | 已落地 | `1 row = 1 stat_date + 1 grid_id` | `ads_region_hotspot_role_daily` | 调度重点区域 |
| 20 | `ads_region_bias_daily` | 区域热点 | 已落地 | `1 row = 1 stat_date + 1 grid_id` | `tdm_region_grid_day_profile` | 区域上车/下车偏向 |
| 21 | `ads_abnormal_vehicle_daily_detail` | 异常识别 | 已落地 | `1 row = 1 stat_date + 1 devid` | `tdm_vehicle_day_profile` | 异常车辆明细 |
| 22 | `ads_abnormal_vehicle_daily_summary` | 异常识别 | 已落地 | `1 row = 1 stat_date` | `ads_abnormal_vehicle_daily_detail` | 每日异常车辆汇总 |
| 23 | `ads_data_quality_daily` | 质量监控 | 已落地 | `1 row = 1 stat_date` | `tdm_trip_profile` + `tdm_vehicle_day_profile` | 数据质量监控 |

---

## 3. 按类别整理

## 3.1 总览与时序类

### 1. `ads_daily_overview`

- 用途：做首页 KPI、每日活跃车辆数、总 trip 数、总里程、平均速度
- 关键字段：
  - `stat_date`
  - `active_vehicle_cnt`
  - `total_trip_cnt`
  - `total_distance_km`
  - `global_avg_speed_kmh`
  - `peak_trip_cnt`
- 意义：所有展示的总览入口

### 2. `ads_daily_growth_compare`

- 用途：做环比增长、速度变化、日报类分析
- 关键字段：
  - `trip_cnt_dod_growth`
  - `active_vehicle_dod_growth`
  - `speed_dod_change`
- 意义：把“变化”单独做成稳定结果

### 3. `ads_hourly_trend`

- 用途：做每小时车流量、活跃车辆数、速度趋势
- 关键字段：
  - `biz_hour`
  - `trip_cnt`
  - `vehicle_cnt`
  - `avg_speed_kmh`
  - `road_coverage_cnt`
- 意义：路况监测主表

### 4. `ads_peak_window_top3_daily`

- 用途：做每天最繁忙 3 个小时的排行榜
- 关键字段：
  - `rank_in_day`
  - `biz_hour`
  - `trip_cnt`
  - `trip_share_in_day`
- 意义：高峰窗口识别

### 5. `ads_time_period_summary_daily`

- 用途：对比夜间、白天、早高峰、晚高峰的出行差异
- 关键字段：
  - `time_period_type`
  - `trip_cnt`
  - `avg_trip_distance_km`
  - `avg_trip_duration_min`
  - `avg_speed_kmh`
- 意义：比单纯按小时更适合解释业务规律

---

## 3.2 行程结构类

### 6. `ads_trip_structure_daily`

- 用途：做长短单结构、速度结构、时长结构分析
- 关键字段：
  - `trip_distance_level`
  - `trip_duration_level`
  - `trip_speed_level`
  - `trip_cnt`
  - `trip_ratio`
- 意义：可替代部分“长短单推荐”的基础分析

### 7. `ads_trip_efficiency_by_period_daily`

- 用途：比较不同时段的效率差异
- 关键字段：
  - `time_period_type`
  - `avg_trip_distance_km`
  - `avg_trip_duration_min`
  - `avg_speed_kmh`
- 意义：解释高峰为什么更慢、夜间为什么更偏长单

### 8. `ads_trip_complexity_daily`

- 用途：分析行程路径是否复杂、是否存在绕行感
- 关键字段：
  - `avg_unique_road_cnt`
  - `avg_road_repeat_ratio`
  - `avg_forward_edge_ratio`
- 意义：这是当前 TDM 相对有特色的一类能力

---

## 3.3 司机画像类

### 9. `ads_vehicle_profile_5d`

- 用途：做五日累计司机画像
- 关键字段：
  - `active_day_cnt`
  - `total_trip_cnt`
  - `avg_daily_trip_cnt`
  - `avg_speed_kmh`
  - `driver_activity_level`
  - `core_driver_flag`
  - `full_attendance_flag`
- 意义：司机画像主表

### 10. `ads_vehicle_segment_summary_5d`

- 用途：做司机分层结构图
- 关键字段：
  - `driver_activity_level`
  - `dominant_time_period_5d`
  - `vehicle_cnt`
  - `core_driver_ratio`
  - `full_attendance_ratio`
- 意义：适合做群体画像而不是单车明细

### 11. `ads_vehicle_daily_operating_style`

- 用途：看每天每辆车的运营风格
- 关键字段：
  - `trip_cnt`
  - `active_hour_cnt`
  - `night_trip_ratio`
  - `peak_trip_ratio`
  - `trip_frequency_level`
- 意义：可做夜班司机、高峰司机分析

### 12. `ads_vehicle_road_preference_topn`

- 用途：看司机最常走的道路
- 关键字段：
  - `devid`
  - `road_id`
  - `rank_in_device`
  - `pass_cnt`
  - `pass_ratio`
- 意义：可做“熟路型司机”分析

### 13. `ads_vehicle_route_stability_5d`

- 用途：判断司机是固定路线型还是分散路线型
- 关键字段：
  - `top1_pass_ratio`
  - `top3_pass_ratio_sum`
  - `route_stability_level`
- 意义：属于有亮点的增强分析表

---

## 3.4 道路与区域类

### 14. `ads_road_hotspot_feature_daily`

- 用途：道路热度主表
- 关键字段：
  - `road_id`
  - `pass_cnt`
  - `vehicle_cnt`
  - `trip_cnt`
  - `peak_pass_cnt`
  - `direction_bias`
  - `road_activity_level`
- 意义：最接近往届 `road_counts`

### 15. `ads_road_top20_daily`

- 用途：把道路主表压缩成每天 Top20 榜单
- 关键字段：
  - `rank_by_pass_cnt`
  - `road_id`
  - `pass_cnt`
- 意义：方便可视化直接取榜单

### 16. `ads_road_watchlist_daily`

- 用途：识别重点关注道路
- 关键字段：
  - `pass_cnt`
  - `peak_pass_ratio`
  - `direction_bias`
  - `watch_score`
  - `watch_reason`
- 意义：把“道路热度”升级成“管理建议”

### 17. `ads_region_hotspot_role_daily`

- 用途：区域热度主表
- 关键字段：
  - `grid_center_lon`
  - `grid_center_lat`
  - `pickup_trip_cnt`
  - `dropoff_trip_cnt`
  - `total_od_trip_cnt`
  - `pickup_ratio`
  - `grid_role_bias`
- 意义：当前最稳妥的“商圈分析替代版”

### 18. `ads_region_top20_daily`

- 用途：每日热点区域 Top20
- 关键字段：
  - `rank_by_total_od`
  - `grid_id`
  - `total_od_trip_cnt`
- 意义：方便可视化直接取区域榜单

### 19. `ads_dispatch_focus_grid_daily`

- 用途：挑出最值得调度车辆的区域
- 关键字段：
  - `total_od_trip_cnt`
  - `peak_od_trip_cnt`
  - `active_vehicle_cnt`
  - `dispatch_score`
- 意义：更贴近应用价值

### 20. `ads_region_bias_daily`

- 用途：分析区域偏上车还是偏下车
- 关键字段：
  - `pickup_ratio`
  - `grid_role_bias`
  - `peak_od_trip_cnt`
  - `night_od_trip_cnt`
- 意义：可推断区域功能偏向

---

## 3.5 异常与质量类

### 21. `ads_abnormal_vehicle_daily_detail`

- 用途：输出异常车辆明细
- 关键字段：
  - `matched_trip_ratio`
  - `avg_speed_kmh`
  - `night_trip_ratio`
  - `low_match_flag`
  - `high_speed_flag`
  - `night_overactive_flag`
  - `abnormal_reason`
- 意义：异常识别底表

### 22. `ads_abnormal_vehicle_daily_summary`

- 用途：每天异常车辆数量汇总
- 关键字段：
  - `abnormal_vehicle_cnt`
  - `low_match_vehicle_cnt`
  - `high_speed_vehicle_cnt`
  - `night_overactive_vehicle_cnt`
- 意义：直接支撑图表和报告

### 23. `ads_data_quality_daily`

- 用途：做每日数据质量监控
- 关键字段：
  - `unmatched_trip_cnt`
  - `unmatched_trip_ratio`
  - `very_fast_trip_cnt`
  - `very_fast_trip_ratio`
  - `low_match_vehicle_cnt`
- 意义：适合答辩防守和质量说明

---

## 4. 当前最推荐的第一版落地范围

如果只做一版最稳妥、最有展示价值的 ADS，建议优先保留这 10 张：

1. `ads_daily_overview`
2. `ads_daily_growth_compare`
3. `ads_hourly_trend`
4. `ads_peak_window_top3_daily`
5. `ads_trip_structure_daily`
6. `ads_vehicle_profile_5d`
7. `ads_vehicle_segment_summary_5d`
8. `ads_road_hotspot_feature_daily`
9. `ads_region_hotspot_role_daily`
10. `ads_abnormal_vehicle_daily_summary`

这 10 张已经足够支撑：

- 总览页
- 路况趋势页
- 行程结构页
- 司机画像页
- 道路热点页
- 区域热点页
- 异常识别页

---

## 5. 当前已经落地的表

当前已经生成到 `ads/ads_output/` 的表为完整 23 张候选表，`ads/preview/` 中也已对应生成 23 个 preview CSV。

这些表已经可以直接供下一阶段同学选择使用，不需要再额外补表。

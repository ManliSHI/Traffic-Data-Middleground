# ADS 字段说明与 Quick BI 使用方案

## 1. 先说结论

- 你现在这套 ADS 结果表，完全可以接 Quick BI 做课程大作业展示。
- 但 Quick BI 更适合做趋势图、柱状图、排行榜、透视表、气泡地图、热力地图这类标准 BI 图表，不适合直接做“真实道路线网地图”。
- 原因不是 Quick BI 不行，而是你当前 ADS 里没有道路几何线数据，只有 `road_id`，所以道路类结果更适合做 TopN 排行、分布、对比，不适合画真实道路线段。
- 你当前输出是 `parquet`，而 Quick BI 官方文档说明本地文件数据源支持的是 `CSV` 和 `Excel`，所以如果你走“本地文件上传”路线，需要先把要用的 ADS 表导成 CSV。

## 2. Quick BI 怎么接这套 ADS

### 2.1 可以怎么接

- 方案 A：把 ADS 表导出成 `CSV`，上传到 Quick BI 的本地文件数据源或探索空间。
- 方案 B：把 ADS 表先导入 MySQL、ClickHouse、PostgreSQL 之类数据库，再让 Quick BI 连数据库。
- 对你们这种课程项目，最省事的是方案 A。

### 2.2 推荐你先上传哪些表

建议先传这 10 张，已经够做一版完整看板：

1. `ads_daily_overview`
2. `ads_daily_growth_compare`
3. `ads_hourly_trend`
4. `ads_peak_window_top3_daily`
5. `ads_trip_structure_daily`
6. `ads_vehicle_profile_5d`
7. `ads_vehicle_segment_summary_5d`
8. `ads_road_top20_daily`
9. `ads_region_top20_daily`
10. `ads_abnormal_vehicle_daily_summary`

如果你想做更完整的大屏，再补：

1. `ads_road_watchlist_daily`
2. `ads_region_hotspot_role_daily`
3. `ads_dispatch_focus_grid_daily`
4. `ads_region_bias_daily`
5. `ads_data_quality_daily`

### 2.3 上传到 Quick BI 时要注意的字段类型

- `stat_date`：设成日期维度，不要保留成纯文本。
- `biz_hour`：设成数值或离散维度都行。做折线图时一般作为维度。
- `devid`、`road_id`、`grid_id`：虽然看起来像数字，但在 BI 里通常应该当“维度 ID”而不是度量，建议设成文本或维度。
- `grid_center_lon`、`grid_center_lat`：做地图时必须设成数值，再在数据集里改成经度、纬度类型。
- `*_ratio`、`*_share`、`*_score`：都属于度量字段，适合做颜色、气泡大小、排序。
- `*_flag`：如果 Quick BI 把布尔值识别得不理想，可以转成 `0/1` 或 `yes/no` 再用。
- `*_level`、`*_type`、`*_bias`：都是分层/分类字段，适合作为图例、颜色、筛选器。

### 2.4 适合 Quick BI 做的图

- 折线图：每日趋势、每小时趋势、速度变化。
- 柱状图：TopN 排行、结构分布、异常数量。
- 堆积柱状图：距离结构、速度结构、时段结构。
- 双轴图：车辆数和 trip 数一起展示。
- 明细表 / 透视表：异常车辆、道路观察名单、区域调度名单。
- 气泡地图 / LBS 地图：区域热点、调度重点区域。

### 2.5 不建议直接在 Quick BI 里做的内容

- 真实道路线网图，因为当前只有 `road_id`，没有道路 geometry。
- 复杂定制地图动画，如果只是课程展示可以，但 Quick BI 不是为了 GIS 级交互设计的。
- 重新做一层复杂口径计算。ADS 已经把主要口径固定好了，Quick BI 更适合消费，不适合再改业务定义。

## 3. 通用字段字典

这些字段在很多表里都会反复出现，先统一解释：

| 字段 | 含义 | 你在图里怎么用 |
| --- | --- | --- |
| `stat_date` | 统计日期 | X 轴、筛选器 |
| `biz_hour` | 小时，`0` 到 `23` | X 轴、热力图列 |
| `time_range_id` | `YYYY-MM-DD_HH` 形式的小时主键 | 明细主键，一般不直接画图 |
| `time_period_type` | 时段分类，`night`、`morning_peak`、`evening_peak`、`daytime`、`shoulder` | 图例、分组、筛选 |
| `devid` | 车辆/设备 ID | 明细主键、排行标签 |
| `road_id` | 道路 ID | 排行标签、筛选 |
| `grid_id` | 网格 ID | 地图点主键、筛选 |
| `grid_center_lon` | 网格中心经度 | 地图经度 |
| `grid_center_lat` | 网格中心纬度 | 地图纬度 |
| `trip_cnt` | trip 数，行程次数 | 核心度量 |
| `vehicle_cnt` | 车辆数 | 核心度量 |
| `pass_cnt` | 路段通行事件数 | 道路热度度量 |
| `total_distance_km` | 总里程，单位 km | 规模、强度、效率 |
| `total_duration_min` | 总时长，单位分钟 | 规模、强度、效率 |
| `avg_speed_kmh` | 平均速度，单位 km/h | 效率、拥堵/通畅侧面反映 |
| `*_ratio` | 占比字段 | 结构图、排序、颜色 |
| `*_share` | 占当天或占总量的份额 | 结构图、排序、颜色 |
| `*_rank_*` | 排名字段 | TopN 筛选 |
| `*_level` | 分层等级字段 | 图例、筛选、结构分布 |
| `*_type` | 类型字段 | 图例、筛选 |
| `*_flag` | 布尔标记 | 筛选、计数 |
| `*_score` | 综合得分 | 排序、颜色、重点名单 |

## 4. 23 张 ADS 表逐表说明

## 4.1 `ads_daily_overview`

- 粒度：`1 row = 1 stat_date`
- 作用：每日总览 KPI 主表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 统计日期 | 横轴 |
| `active_vehicle_cnt` | 当日活跃车辆数 | KPI、折线、柱状 |
| `total_trip_cnt` | 当日总 trip 数 | KPI、柱状、双轴 |
| `total_distance_km` | 当日总里程 | KPI、折线 |
| `total_duration_min` | 当日总时长 | KPI、折线 |
| `avg_vehicle_speed_kmh` | 先按车算再按天聚合的平均速度 | 车均速度趋势 |
| `night_active_vehicle_cnt` | 夜间活跃车辆数 | 夜间 vs 高峰对比 |
| `peak_active_vehicle_cnt` | 高峰活跃车辆数 | 夜间 vs 高峰对比 |
| `global_avg_speed_kmh` | 整体口径平均速度 | 总体效率趋势 |
| `peak_trip_cnt` | 高峰时段总 trip 数 | 高峰活跃度趋势 |
| `hourly_peak_hour` | 当天 trip 最高的小时 | 标签、注释 |
| `hourly_peak_trip_cnt` | 当天最高峰小时的 trip 数 | 高峰强度对比 |

- 最适合的图：
- 每日活跃车辆数与 trip 数双轴图
- 每日平均速度折线图
- 每日夜间/高峰活跃车辆对比图

## 4.2 `ads_daily_growth_compare`

- 粒度：`1 row = 1 stat_date`
- 作用：看环比变化

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 统计日期 | 横轴 |
| `active_vehicle_cnt` | 当日活跃车辆数 | 对照值 |
| `total_trip_cnt` | 当日总 trip 数 | 对照值 |
| `total_distance_km` | 当日总里程 | 对照值 |
| `total_duration_min` | 当日总时长 | 对照值 |
| `avg_vehicle_speed_kmh` | 车均速度 | 对照值 |
| `night_active_vehicle_cnt` | 夜间活跃车辆数 | 对照值 |
| `peak_active_vehicle_cnt` | 高峰活跃车辆数 | 对照值 |
| `global_avg_speed_kmh` | 整体平均速度 | 对照值 |
| `peak_trip_cnt` | 高峰 trip 数 | 对照值 |
| `hourly_peak_hour` | 当天峰值小时 | 说明字段 |
| `hourly_peak_trip_cnt` | 峰值小时 trip 数 | 说明字段 |
| `total_trip_cnt_prev_day` | 前一日总 trip 数 | 环比基准 |
| `active_vehicle_cnt_prev_day` | 前一日活跃车辆数 | 环比基准 |
| `global_avg_speed_kmh_prev_day` | 前一日整体平均速度 | 环比基准 |
| `trip_cnt_dod_growth` | trip 数环比增长率 | 核心图表字段 |
| `active_vehicle_dod_growth` | 活跃车辆环比增长率 | 核心图表字段 |
| `speed_dod_change` | 速度较前一日变化值 | 核心图表字段 |

- 最适合的图：
- 环比增长柱状图
- 速度变化图

## 4.3 `ads_hourly_trend`

- 粒度：`1 row = 1 stat_date + 1 biz_hour`
- 作用：小时趋势主表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `time_range_id` | 小时主键，如 `2015-01-03_08` | 明细主键 |
| `stat_date` | 日期 | 分面、图例、筛选 |
| `biz_hour` | 小时 | 横轴 |
| `time_period_type` | 小时所属时段 | 图例、筛选 |
| `trip_cnt` | 该小时 trip 数 | 折线、热力图颜色 |
| `matched_trip_cnt` | 该小时有匹配结果的 trip 数 | 质量监控 |
| `vehicle_cnt` | 该小时活跃车辆数 | 折线 |
| `total_distance_km` | 该小时总里程 | 强度趋势 |
| `total_duration_min` | 该小时总时长 | 强度趋势 |
| `avg_trip_distance_km` | 该小时平均单次里程 | 结构分析 |
| `avg_trip_duration_min` | 该小时平均单次时长 | 结构分析 |
| `avg_speed_kmh` | 该小时平均速度 | 效率趋势 |
| `road_coverage_cnt` | 该小时覆盖道路数 | 活跃范围 |
| `slot_activity_level` | 小时活跃度等级，`low/medium/high/hot` | 热门小时分类 |
| `trip_share_in_day` | 该小时 trip 占当天比例 | 高峰占比图 |

- 最适合的图：
- 每小时 trip 趋势图
- 每小时活跃车辆趋势图
- 每小时平均速度图
- 按日期 x 小时的热力图

## 4.4 `ads_peak_window_top3_daily`

- 粒度：`1 row = 1 stat_date + 1 rank_in_day`
- 作用：每天最忙的 3 个小时

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 横轴 |
| `rank_in_day` | 当天高峰排名 1/2/3 | 分组、图例 |
| `biz_hour` | 高峰对应小时 | 标签 |
| `time_period_type` | 所属时段 | 分类解释 |
| `trip_cnt` | 该高峰小时 trip 数 | 柱长 |
| `vehicle_cnt` | 该高峰小时车辆数 | 对照值 |
| `avg_speed_kmh` | 该高峰小时平均速度 | 补充解释 |
| `trip_share_in_day` | 该小时 trip 占全天比例 | 占比图 |

- 最适合的图：
- 每日 Top3 高峰小时图
- 每日峰值小时占比图

## 4.5 `ads_time_period_summary_daily`

- 粒度：`1 row = 1 stat_date + 1 time_period_type`
- 作用：按时段汇总的行为总表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 分面、筛选 |
| `time_period_type` | 时段类型 | 横轴、图例 |
| `trip_cnt` | 该时段 trip 数 | 柱状、堆积柱 |
| `avg_trip_distance_km` | 该时段平均里程 | 时段效率对比 |
| `avg_trip_duration_min` | 该时段平均时长 | 时段效率对比 |
| `avg_speed_kmh` | 该时段平均速度 | 时段效率对比 |
| `avg_unique_road_cnt` | 该时段平均唯一路段数 | 路径复杂度 |
| `avg_road_repeat_ratio` | 该时段平均路段重复率 | 路径重复程度 |
| `avg_forward_edge_ratio` | 该时段平均正向边占比 | 方向性侧面特征 |
| `trip_ratio_in_day` | 该时段 trip 占当日比例 | 结构图 |

- 最适合的图：
- 时段 trip 结构图
- 时段平均速度/时长对比图

## 4.6 `ads_trip_structure_daily`

- 粒度：`1 row = 1 stat_date + 距离层级 + 时长层级 + 速度层级`
- 作用：行程结构分布表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 筛选、分面 |
| `trip_distance_level` | 距离等级，`short/medium/long/extra_long` | 结构分类 |
| `trip_duration_level` | 时长等级，`short/medium/long/extra_long` | 结构分类 |
| `trip_speed_level` | 速度等级，`slow/normal/fast/very_fast` | 结构分类 |
| `trip_cnt` | 该结构组合下的 trip 数 | 柱状、热力图 |
| `trip_ratio` | 该结构组合占比 | 堆积柱、环图 |

- 最适合的图：
- 距离结构分布图
- 速度结构分布图
- 距离 x 时长矩阵热力图

## 4.7 `ads_trip_efficiency_by_period_daily`

- 粒度：`1 row = 1 stat_date + 1 time_period_type`
- 作用：按时段对比出行效率

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 筛选 |
| `time_period_type` | 时段 | 横轴 |
| `trip_cnt` | 该时段 trip 数 | 规模对比 |
| `trip_ratio_in_day` | 该时段 trip 占比 | 结构对比 |
| `avg_trip_distance_km` | 平均里程 | 效率对比 |
| `avg_trip_duration_min` | 平均时长 | 效率对比 |
| `avg_speed_kmh` | 平均速度 | 效率对比 |
| `avg_unique_road_cnt` | 平均唯一路段数 | 路径复杂度 |
| `avg_road_repeat_ratio` | 平均路段重复率 | 路径复杂度 |
| `avg_forward_edge_ratio` | 平均正向占比 | 方向性说明 |
| `speed_rank_in_day` | 当天各时段速度排名 | 排名图、标签 |
| `duration_rank_in_day` | 当天各时段时长排名 | 排名图、标签 |

- 最适合的图：
- 时段效率雷达图
- 时段速度/时长对比柱状图

## 4.8 `ads_trip_complexity_daily`

- 粒度：`1 row = 1 stat_date`
- 作用：监控每天行程路径复杂度

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 横轴 |
| `avg_unique_road_cnt` | 平均唯一路段数 | 复杂度趋势 |
| `avg_road_repeat_ratio` | 平均路段重复率 | 复杂度趋势 |
| `avg_forward_edge_ratio` | 平均正向边占比 | 方向性趋势 |
| `complex_trip_ratio` | 复杂 trip 占比 | 核心复杂度指标 |
| `p75_unique_road_cnt` | 唯一路段数 75 分位 | 边界值趋势 |
| `p75_road_repeat_ratio` | 路段重复率 75 分位 | 边界值趋势 |
| `complexity_unique_threshold` | 复杂 trip 判定阈值之一 | 说明字段 |
| `complexity_repeat_threshold` | 复杂 trip 判定阈值之一 | 说明字段 |

- 最适合的图：
- 每日复杂度趋势图

## 4.9 `ads_vehicle_profile_5d`

- 粒度：`1 row = 1 devid`
- 作用：五天车辆/司机画像主表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `devid` | 车辆 ID | 主键、排行标签 |
| `active_day_cnt` | 五天内活跃天数 | 出勤分析 |
| `total_trip_cnt` | 五天总 trip 数 | 活跃度排行 |
| `avg_daily_trip_cnt` | 日均 trip 数 | 活跃度对比 |
| `total_distance_km` | 五天总里程 | 运营强度 |
| `total_duration_min` | 五天总时长 | 运营强度 |
| `avg_trip_distance_km` | 平均单次里程 | 行程特征 |
| `avg_speed_kmh` | 五天平均速度 | 效率画像 |
| `night_trip_ratio_5d` | 五天夜间 trip 占比 | 夜班偏向 |
| `peak_trip_ratio_5d` | 五天高峰 trip 占比 | 高峰偏向 |
| `road_coverage_cnt_5d` | 五天覆盖道路数 | 覆盖范围 |
| `dominant_time_period_5d` | 五天主导时段 | 行为偏好 |
| `driver_activity_level` | 活跃度等级，`low/medium/high/core` | 结构图、筛选 |
| `core_driver_flag` | 是否核心司机 | 指标卡、筛选 |
| `full_attendance_flag` | 是否满勤 | 指标卡、筛选 |
| `rank_by_total_trip_cnt` | 按总 trip 数排名 | TopN 司机图 |

- 最适合的图：
- 司机活跃度结构图
- 核心司机/满勤司机数量图
- 司机 Top20 排行

## 4.10 `ads_vehicle_segment_summary_5d`

- 粒度：`1 row = 1 driver_activity_level + 1 dominant_time_period_5d`
- 作用：司机分层群体汇总表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `driver_activity_level` | 活跃度等级 | 横轴/分层 |
| `dominant_time_period_5d` | 主导时段 | 图例/分组 |
| `vehicle_cnt` | 该分层下车辆数 | 结构图 |
| `avg_total_trip_cnt` | 该分层平均总 trip 数 | 分层画像 |
| `avg_total_distance_km` | 该分层平均总里程 | 分层画像 |
| `avg_speed_kmh` | 该分层平均速度 | 分层画像 |
| `avg_night_trip_ratio_5d` | 该分层平均夜间占比 | 分层画像 |
| `avg_peak_trip_ratio_5d` | 该分层平均高峰占比 | 分层画像 |
| `core_driver_cnt` | 该分层核心司机数 | 分层画像 |
| `full_attendance_cnt` | 该分层满勤司机数 | 分层画像 |
| `core_driver_ratio` | 该分层核心司机占比 | 颜色、排序 |
| `full_attendance_ratio` | 该分层满勤占比 | 颜色、排序 |

- 最适合的图：
- 分层司机结构图
- 主导时段 x 活跃度分组柱状图

## 4.11 `ads_vehicle_daily_operating_style`

- 粒度：`1 row = 1 stat_date + 1 devid`
- 作用：每天每辆车的运营风格

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 筛选 |
| `devid` | 车辆 ID | 明细主键 |
| `trip_cnt` | 当日 trip 数 | 排行、分布 |
| `matched_trip_cnt` | 当日匹配成功 trip 数 | 质量判断 |
| `matched_trip_ratio` | 匹配成功占比 | 质量判断 |
| `total_distance_km` | 当日总里程 | 运营强度 |
| `total_duration_min` | 当日总时长 | 运营强度 |
| `avg_trip_distance_km` | 平均单次里程 | 行程结构 |
| `avg_trip_duration_min` | 平均单次时长 | 行程结构 |
| `avg_speed_kmh` | 平均速度 | 效率 |
| `active_hour_cnt` | 活跃小时数 | 运营时长 |
| `road_coverage_cnt` | 覆盖道路数 | 覆盖范围 |
| `night_trip_cnt` | 夜间 trip 数 | 夜间运营 |
| `night_trip_ratio` | 夜间占比 | 夜间运营 |
| `morning_peak_trip_cnt` | 早高峰 trip 数 | 早高峰运营 |
| `evening_peak_trip_cnt` | 晚高峰 trip 数 | 晚高峰运营 |
| `peak_trip_cnt` | 高峰 trip 数 | 高峰运营 |
| `peak_trip_ratio` | 高峰占比 | 高峰运营 |
| `dominant_time_period` | 当日主导时段 | 分类 |
| `trip_frequency_level` | 当日频次等级，`low/medium/high/very_high` | 分类 |
| `night_activity_flag` | 夜间活跃标记 | 筛选 |
| `peak_activity_flag` | 高峰活跃标记 | 筛选 |
| `operation_style_type` | 运营风格，`night_shift/peak_shift/intensive_operation/balanced_operation` | 核心分类图 |
| `rank_by_trip_cnt_in_day` | 当天 trip 数排名 | TopN 排行 |

- 最适合的图：
- 每日运营风格分布图
- 当日高强度车辆排行榜

## 4.12 `ads_vehicle_road_preference_topn`

- 粒度：`1 row = 1 devid + 1 road_id`
- 作用：车辆偏好道路 TopN

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `devid` | 车辆 ID | 筛选 |
| `road_id` | 道路 ID | 标签 |
| `rank_in_device` | 该车辆内部道路偏好排名 | TopN 过滤 |
| `pass_cnt` | 五天内通行次数 | 排行 |
| `pass_ratio` | 占该车辆所有有效通行的比例 | 偏好强度 |
| `active_day_cnt_on_road` | 在这条路上活跃的天数 | 偏好稳定性 |
| `preference_level` | 偏好等级，`core_route/frequent_route` | 分类 |
| `preference_score` | 综合偏好得分 | 排序、颜色 |

- 最适合的图：
- 单车偏好道路 Top10 表
- 道路偏好强度分布图

## 4.13 `ads_vehicle_route_stability_5d`

- 粒度：`1 row = 1 devid`
- 作用：车辆路线稳定性画像

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `devid` | 车辆 ID | 主键 |
| `active_day_cnt` | 活跃天数 | 补充信息 |
| `total_trip_cnt` | 五天总 trip 数 | 活跃度 |
| `driver_activity_level` | 活跃度等级 | 分层 |
| `road_coverage_cnt_5d` | 覆盖道路数 | 范围 |
| `top1_pass_ratio` | 最常走道路占比 | 稳定性强弱 |
| `top3_pass_ratio_sum` | Top3 道路通行占比之和 | 核心稳定性指标 |
| `core_route_cnt` | 核心路线条数 | 稳定性结构 |
| `frequent_route_cnt` | 高频路线条数 | 稳定性结构 |
| `route_stability_level` | 路线稳定等级，`very_stable/stable/mixed/diversified` | 结构图、筛选 |

- 最适合的图：
- 路线稳定性结构图
- 稳定司机 vs 分散司机对比

## 4.14 `ads_road_hotspot_feature_daily`

- 粒度：`1 row = 1 stat_date + 1 road_id`
- 作用：道路热点主表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 分面、筛选 |
| `road_id` | 道路 ID | 排行标签 |
| `rank_by_pass_cnt` | 按通行事件数排名 | TopN 过滤 |
| `rank_by_vehicle_cnt` | 按车辆数排名 | TopN 过滤 |
| `rank_by_trip_cnt` | 按 trip 数排名 | TopN 过滤 |
| `pass_cnt` | 路段通行事件数 | 核心道路热度指标 |
| `vehicle_cnt` | 经过该路段的车辆数 | 覆盖强度 |
| `trip_cnt` | 涉及该路段的 trip 数 | 覆盖强度 |
| `morning_peak_pass_cnt` | 早高峰通行数 | 时段热度 |
| `evening_peak_pass_cnt` | 晚高峰通行数 | 时段热度 |
| `peak_pass_cnt` | 高峰总通行数 | 高峰敏感度 |
| `night_pass_cnt` | 夜间通行数 | 夜间热度 |
| `peak_pass_ratio` | 高峰通行占比 | 高峰敏感度 |
| `forward_edge_cnt` | 正向边数 | 方向结构 |
| `backward_edge_cnt` | 反向边数 | 方向结构 |
| `forward_ratio` | 正向占比 | 方向偏向基础值 |
| `direction_bias` | 方向偏向，`mainly_forward/mainly_backward/balanced` | 图例、分类 |
| `road_activity_level` | 路段活跃等级，`long_tail/normal/active/hot` | 图例、筛选 |
| `peak_bias_type` | 时段偏向，`morning_peak/evening_peak/night/offpeak` | 图例、分类 |

- 最适合的图：
- 道路 Top20 排行
- 高峰道路 Top20
- 方向偏向分布图

## 4.15 `ads_road_top20_daily`

- 粒度：`1 row = 1 stat_date + 1 rank`
- 作用：每天道路 Top20 榜单，适合可视化直接取数

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 分面 |
| `road_id` | 道路 ID | 标签 |
| `rank_by_pass_cnt` | 按通行事件数排名 | 横向排序 |
| `rank_by_vehicle_cnt` | 按车辆数排名 | 补充排序 |
| `rank_by_trip_cnt` | 按 trip 数排名 | 补充排序 |
| `pass_cnt` | 通行事件数 | 柱长 |
| `vehicle_cnt` | 车辆数 | 对照值 |
| `trip_cnt` | trip 数 | 对照值 |
| `peak_pass_cnt` | 高峰通行数 | 高峰图 |
| `night_pass_cnt` | 夜间通行数 | 夜间图 |
| `peak_pass_ratio` | 高峰占比 | 颜色 |
| `direction_bias` | 方向偏向 | 图例 |
| `road_activity_level` | 路段活跃等级 | 图例 |
| `peak_bias_type` | 时段偏向类型 | 图例 |

- 最适合的图：
- 每日热点道路 Top20 条形图

## 4.16 `ads_road_watchlist_daily`

- 粒度：`1 row = 1 stat_date + 1 road_id`
- 作用：道路重点关注名单

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 筛选 |
| `road_id` | 道路 ID | 主键、标签 |
| `pass_cnt` | 通行事件数 | 基础热度 |
| `vehicle_cnt` | 车辆数 | 覆盖强度 |
| `trip_cnt` | trip 数 | 覆盖强度 |
| `peak_pass_ratio` | 高峰占比 | 峰值敏感度 |
| `direction_bias` | 方向偏向 | 图例 |
| `road_activity_level` | 活跃等级 | 图例 |
| `peak_bias_type` | 时段偏向类型 | 图例 |
| `flow_score` | 由排名换算的流量得分 | 排序 |
| `peak_sensitivity_score` | 高峰敏感得分 | 排序 |
| `direction_imbalance_score` | 方向失衡得分 | 排序 |
| `watch_score` | 综合关注得分 | 核心排序字段 |
| `watch_level` | 关注等级，`normal/medium/high/critical` | 分类、筛选 |
| `watch_reason` | 关注原因，`high_activity/peak_sensitive/directional_bias/peak_and_directional/normal_watch` | 解释字段 |

- 最适合的图：
- 道路观察名单表
- 关注等级分布图
- 重点道路 TopN 排行

## 4.17 `ads_region_hotspot_role_daily`

- 粒度：`1 row = 1 stat_date + 1 grid_id`
- 作用：区域热点与角色主表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 筛选 |
| `grid_id` | 网格 ID | 主键 |
| `rank_by_total_od` | 按总 OD 量排名 | TopN 过滤 |
| `rank_by_pickup` | 按上车量排名 | TopN 过滤 |
| `rank_by_dropoff` | 按下车量排名 | TopN 过滤 |
| `grid_center_lon` | 网格中心经度 | 地图经度 |
| `grid_center_lat` | 网格中心纬度 | 地图纬度 |
| `pickup_trip_cnt` | 上车次数 | 上车热点图 |
| `dropoff_trip_cnt` | 下车次数 | 下车热点图 |
| `total_od_trip_cnt` | OD 总次数 | 气泡大小 |
| `active_vehicle_cnt` | 活跃车辆数 | 对照值 |
| `night_od_trip_cnt` | 夜间 OD 次数 | 夜间热点 |
| `peak_od_trip_cnt` | 高峰 OD 次数 | 高峰热点 |
| `pickup_ratio` | 上车占比 | 角色偏向 |
| `grid_role_bias` | 网格角色，`pickup_dominant/dropoff_dominant/balanced` | 图例 |
| `grid_activity_level` | 网格活跃等级，`long_tail/normal/active/hotspot` | 颜色、筛选 |

- 最适合的图：
- 热点区域 Top20 气泡地图
- 上车/下车热点 Top10
- 区域角色偏向分布图

## 4.18 `ads_region_top20_daily`

- 粒度：`1 row = 1 stat_date + 1 rank`
- 作用：每天区域 Top20 榜单

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 分面 |
| `grid_id` | 网格 ID | 标签 |
| `rank_by_total_od` | 按总 OD 排名 | TopN 过滤 |
| `rank_by_pickup` | 按上车排名 | 补充排序 |
| `rank_by_dropoff` | 按下车排名 | 补充排序 |
| `grid_center_lon` | 中心经度 | 地图经度 |
| `grid_center_lat` | 中心纬度 | 地图纬度 |
| `pickup_trip_cnt` | 上车次数 | 柱状、对照 |
| `dropoff_trip_cnt` | 下车次数 | 柱状、对照 |
| `total_od_trip_cnt` | OD 总次数 | 柱长或气泡大小 |
| `active_vehicle_cnt` | 活跃车辆数 | 补充指标 |
| `peak_od_trip_cnt` | 高峰 OD 次数 | 补充指标 |
| `night_od_trip_cnt` | 夜间 OD 次数 | 补充指标 |
| `pickup_ratio` | 上车占比 | 颜色 |
| `grid_role_bias` | 区域角色偏向 | 图例 |
| `grid_activity_level` | 活跃等级 | 图例 |

- 最适合的图：
- 每日区域 Top20 排行
- Top20 区域地图

## 4.19 `ads_dispatch_focus_grid_daily`

- 粒度：`1 row = 1 stat_date + 1 grid_id`
- 作用：调度重点区域表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 筛选 |
| `grid_id` | 网格 ID | 标签 |
| `grid_center_lon` | 中心经度 | 地图经度 |
| `grid_center_lat` | 中心纬度 | 地图纬度 |
| `total_od_trip_cnt` | 总 OD 次数 | 活跃度 |
| `peak_od_trip_cnt` | 高峰 OD 次数 | 高峰压力 |
| `active_vehicle_cnt` | 活跃车辆数 | 运力规模 |
| `od_per_vehicle` | 单车承载的 OD 压力 | 压力强度 |
| `pickup_ratio` | 上车占比 | 出发型区域偏向 |
| `dispatch_score` | 综合调度得分 | 核心排序字段 |
| `dispatch_level` | 调度优先级，`normal/medium/high/very_high` | 分类、筛选 |

- 最适合的图：
- 调度重点区域地图
- 调度优先级 TopN 排行

## 4.20 `ads_region_bias_daily`

- 粒度：`1 row = 1 stat_date + 1 grid_id`
- 作用：区域功能偏向分析

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 筛选 |
| `grid_id` | 网格 ID | 标签 |
| `grid_center_lon` | 中心经度 | 地图经度 |
| `grid_center_lat` | 中心纬度 | 地图纬度 |
| `total_od_trip_cnt` | 总 OD 次数 | 活跃度 |
| `peak_od_trip_cnt` | 高峰 OD 次数 | 高峰特征 |
| `night_od_trip_cnt` | 夜间 OD 次数 | 夜间特征 |
| `pickup_ratio` | 上车占比 | 偏向核心字段 |
| `grid_role_bias` | pickup / dropoff 偏向 | 分类 |
| `grid_activity_level` | 活跃等级 | 分类 |
| `peak_share` | 高峰 OD 占比 | 高峰敏感度 |
| `night_share` | 夜间 OD 占比 | 夜间敏感度 |
| `region_bias_type` | 区域类型，`pickup_source/dropoff_sink/commute_source/commute_destination/night_active/balanced_mixed` | 核心分类图 |

- 最适合的图：
- 区域功能类型分布图
- 通勤来源区 / 到达区对比

## 4.21 `ads_abnormal_vehicle_daily_detail`

- 粒度：`1 row = 1 stat_date + 1 devid`
- 作用：异常车辆明细表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 筛选 |
| `devid` | 车辆 ID | 明细主键 |
| `trip_cnt` | 当日 trip 数 | 强度参考 |
| `matched_trip_ratio` | 匹配成功占比 | 异常判定 |
| `avg_speed_kmh` | 平均速度 | 异常判定 |
| `night_trip_ratio` | 夜间占比 | 异常判定 |
| `trip_frequency_level` | 频次等级 | 异常判定 |
| `night_activity_flag` | 是否夜间活跃 | 异常判定 |
| `peak_activity_flag` | 是否高峰活跃 | 异常参考 |
| `low_match_flag` | 是否低匹配率异常 | 过滤、计数 |
| `high_speed_flag` | 是否高速度异常 | 过滤、计数 |
| `night_overactive_flag` | 是否夜间过度活跃异常 | 过滤、计数 |
| `abnormal_type` | 异常类型，`match_quality/speed_outlier/night_operation/mixed` | 分类统计 |
| `abnormal_reason` | 异常原因组合 | 说明字段 |

- 最适合的图：
- 异常车辆明细表
- 异常类型分布图

## 4.22 `ads_abnormal_vehicle_daily_summary`

- 粒度：`1 row = 1 stat_date`
- 作用：每天异常车辆汇总

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 横轴 |
| `abnormal_vehicle_cnt` | 当日异常车辆总数 | 核心异常趋势 |
| `low_match_vehicle_cnt` | 低匹配率异常车辆数 | 结构图 |
| `high_speed_vehicle_cnt` | 高速度异常车辆数 | 结构图 |
| `night_overactive_vehicle_cnt` | 夜间过度活跃车辆数 | 结构图 |

- 最适合的图：
- 异常车辆趋势图
- 异常类型堆积柱图

## 4.23 `ads_data_quality_daily`

- 粒度：`1 row = 1 stat_date`
- 作用：数据质量监控表

| 字段 | 含义 | 图表怎么用 |
| --- | --- | --- |
| `stat_date` | 日期 | 横轴 |
| `total_trip_cnt` | 当日总 trip 数 | 基准值 |
| `unmatched_trip_cnt` | 无匹配 trip 数 | 质量风险量 |
| `very_fast_trip_cnt` | 超高速 trip 数 | 质量风险量 |
| `unmatched_trip_ratio` | 无匹配 trip 占比 | 核心质量图 |
| `very_fast_trip_ratio` | 超高速 trip 占比 | 核心质量图 |
| `low_match_vehicle_cnt` | 低匹配率车辆数 | 质量风险量 |

- 最适合的图：
- 每日数据质量趋势图
- 风险项对比图

## 5. 如果你要在 Quick BI 里画图，推荐这样配

## 5.1 总览页

- 表：`ads_daily_overview`
- 图 1：双轴图
- 维度：`stat_date`
- 左轴度量：`total_trip_cnt`
- 右轴度量：`active_vehicle_cnt`

- 图 2：折线图
- 维度：`stat_date`
- 度量：`global_avg_speed_kmh`

- 图 3：分组柱状图
- 维度：`stat_date`
- 度量：`night_active_vehicle_cnt`、`peak_active_vehicle_cnt`

## 5.2 趋势页

- 表：`ads_hourly_trend`
- 图 1：折线图
- 维度：`biz_hour`
- 度量：`trip_cnt`
- 图例：`stat_date`

- 图 2：折线图
- 维度：`biz_hour`
- 度量：`avg_speed_kmh`
- 图例：`stat_date`

- 图 3：热力图
- 行：`stat_date`
- 列：`biz_hour`
- 颜色：`trip_cnt`

## 5.3 结构页

- 表：`ads_trip_structure_daily`
- 图 1：堆积柱状图
- 维度：`stat_date`
- 图例：`trip_distance_level`
- 度量：`trip_cnt` 或 `trip_ratio`

- 图 2：堆积柱状图
- 维度：`stat_date`
- 图例：`trip_speed_level`
- 度量：`trip_cnt` 或 `trip_ratio`

- 图 3：热力图
- 行：`trip_distance_level`
- 列：`trip_duration_level`
- 度量：`trip_cnt`
- 筛选：`stat_date`

## 5.4 司机页

- 表：`ads_vehicle_profile_5d`
- 图 1：柱状图
- 维度：`driver_activity_level`
- 度量：`devid` 计数

- 图 2：指标卡
- 度量：`core_driver_flag = true` 的计数
- 度量：`full_attendance_flag = true` 的计数

- 图 3：TopN 横向条形图
- 维度：`devid`
- 度量：`total_trip_cnt`
- 排序：`rank_by_total_trip_cnt`

## 5.5 道路页

- 表：`ads_road_top20_daily`
- 图 1：横向条形图
- 维度：`road_id`
- 度量：`pass_cnt`
- 分面或筛选：`stat_date`

- 图 2：横向条形图
- 维度：`road_id`
- 度量：`peak_pass_cnt`
- 分面或筛选：`stat_date`

- 表：`ads_road_watchlist_daily`
- 图 3：明细表
- 维度：`road_id`、`watch_level`、`watch_reason`
- 度量：`watch_score`、`pass_cnt`

## 5.6 区域页

- 表：`ads_region_top20_daily`
- 图 1：气泡地图
- 经度：`grid_center_lon`
- 纬度：`grid_center_lat`
- 气泡大小：`total_od_trip_cnt`
- 气泡颜色：`pickup_ratio` 或 `grid_role_bias`
- 筛选：`stat_date`

- 表：`ads_region_hotspot_role_daily`
- 图 2：分组柱状图
- 维度：`grid_id`
- 度量：`pickup_trip_cnt`、`dropoff_trip_cnt`
- 过滤：`rank_by_total_od <= 10`

- 表：`ads_dispatch_focus_grid_daily`
- 图 3：气泡地图
- 经度：`grid_center_lon`
- 纬度：`grid_center_lat`
- 气泡大小：`dispatch_score`
- 颜色：`dispatch_level`

## 5.7 异常与质量页

- 表：`ads_abnormal_vehicle_daily_summary`
- 图 1：堆积柱状图
- 维度：`stat_date`
- 度量：`low_match_vehicle_cnt`、`high_speed_vehicle_cnt`、`night_overactive_vehicle_cnt`

- 表：`ads_data_quality_daily`
- 图 2：折线图
- 维度：`stat_date`
- 度量：`unmatched_trip_ratio`、`very_fast_trip_ratio`

## 6. Quick BI 对这套数据最现实的使用建议

- 先不要把 23 张表全传上去。先传 8 到 10 张核心表，做出一版看板最重要。
- 把 `road_id`、`devid`、`grid_id` 明确设成维度，不然 Quick BI 容易把它们当数值。
- 把 `grid_center_lon`、`grid_center_lat` 改成数值并转经纬度类型，否则地图出不来。
- 布尔字段如果不好用，就在 Quick BI 数据集里新建计算字段，把 `true/false` 转成 `1/0` 或中文标签。
- 如果想做“区域热点地图”，优先用 `ads_region_top20_daily` 或 `ads_region_hotspot_role_daily`。
- 如果想做“道路热点地图”，当前不建议。因为没有真实道路几何，只做道路 TopN 就够了。

## 7. 你现在最应该怎么做

1. 先确定最终展示图 6 到 8 张，不要一开始贪多。
2. 优先选总览、小时趋势、结构、司机、道路、区域这 6 类。
3. 从对应 ADS 表导出 CSV。
4. 上传到 Quick BI。
5. 在数据集中把 `stat_date`、经纬度、ID 字段类型改对。
6. 先把图做出来，再回头优化样式和文案。

## 8. 官方文档结论

根据阿里云 Quick BI 官方文档：

- 本地文件数据源支持上传 `Excel` 和 `CSV` 文件，不支持直接上传 `Parquet`。
- 文件大小建议不超过 `50 MB`，列数不超过 `100`。
- 探索空间也支持上传本地 `CSV/Excel` 文件后直接建数据集和仪表板。
- 地图图表支持经纬度方式建图，你可以把 `grid_center_lon`、`grid_center_lat` 配成经纬度字段，再用气泡地图或 LBS 地图。

你这套 ADS 很适合做 Quick BI，尤其适合：

- 课程汇报
- 业务看板
- 简版数据大屏

不太适合的只是“真实路网 GIS 风格展示”，这个是数据边界问题，不是 BI 平台问题。

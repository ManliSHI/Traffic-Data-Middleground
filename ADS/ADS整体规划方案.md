# ADS 整体规划方案

## 1. 角色定位

本项目中，ADS（应用数据层）的职责不是重新处理原始 GPS 轨迹，也不是重新设计 TDM 标签，而是：

- 承接已经完成的 TDM 画像结果
- 面向业务问题整理可直接消费的统计指标
- 输出可直接支撑可视化模块、报告模块和 PPT 的应用层结果表

当前项目的真实进度决定了 ADS 的工作重点应是：

- 把 TDM 中已经稳定的画像数据组织成更适合展示的小结果表
- 明确每个业务指标的对象粒度和统计口径
- 为后续可视化和报告提供统一、可解释的数字来源

补充说明：

- 本文最初用于 ADS 规划
- 截至当前，ADS 候选 23 表已经全部落地到 `ads/ads_output/`
- 对应 preview 也已经生成到 `ads/preview/`

## 2. 当前基础与可用输入

当前 ADS 已有的上游基础已经足够开工。

### 2.1 上游原始与清洗结果

项目根目录下已有以下清洗结果：

- `trips_clean.parquet`
- `gps_points_clean.parquet`
- `matched_segments_clean.parquet`
- `route_edges_clean.parquet`
- `route_geometries_clean.parquet`
- `cleaning_report.json`

### 2.2 TDM 已完成产物

`tdm_output` 目录中已有以下可直接消费的标签层结果：

- `tdm_trip_profile.parquet`
- `tdm_vehicle_day_profile.parquet`
- `tdm_vehicle_5d_profile.parquet`
- `tdm_vehicle_road_preference_5d.parquet`
- `tdm_road_day_profile.parquet`
- `tdm_time_slot_day_profile.parquet`
- `tdm_region_grid_day_profile.parquet`
- `tdm_tag_definition.csv`
- `tdm_build_summary.json`

### 2.3 关键参考文档

ADS 开发需要优先参考以下文档：

- `DATA_HANDOFF_ADS.md`
- `tdm_output/tdm_tag_definition.csv`
- `tdm_output/tdm_build_summary.json`
- `DATA_HANDOFF_TDM.md`

其中：

- `DATA_HANDOFF_ADS.md` 是 ADS 开发主文档
- `tdm_tag_definition.csv` 用于查字段业务含义
- `tdm_build_summary.json` 用于确认 TDM 结果是否完整且校验通过
- `DATA_HANDOFF_TDM.md` 主要用于理解上游数据来源和口径背景

## 3. ADS 的核心目标

ADS 这一层建议围绕“可展示、可解释、可复用”三个目标设计。

### 3.1 可展示

产出的结果应能直接被可视化模块使用，例如：

- 每日车辆数量趋势图
- 每日平均速度趋势图
- 每小时车流量折线图
- 热点道路排行榜
- 热点区域地图
- 异常车辆数量统计图

### 3.2 可解释

每个指标必须明确：

- 统计对象是谁
- 粒度是什么
- 时间口径是什么
- 使用的字段来源于哪张 TDM 表

### 3.3 可复用

ADS 不应为某一张图临时拼接一次性查询，而应输出稳定结果表，供：

- 可视化模块复用
- 报告与 PPT 直接引用
- 后续补充接口或图表时继续复用

## 4. ADS 设计原则

### 4.1 优先使用 TDM 产物

大多数 ADS 指标都应直接从 TDM 的 7 张结果表中取得，不重新回扫原始大表。

原因：

- TDM 已统一业务时间口径
- TDM 已统一统计日期口径
- TDM 已统一时段划分逻辑
- TDM 已统一距离和速度的计算方法

因此 ADS 不建议重新扫描：

- `gps_points_clean.parquet`
- `matched_segments_clean.parquet`
- `route_edges_clean.parquet`

除非出现 TDM 无法覆盖的新需求。

### 4.2 指标先确定对象粒度

同一个名字的指标，可能存在不同统计口径。

例如“平均速度”至少可能有：

- 全局整体平均速度
- 车均平均速度
- 单 trip 平均速度
- 小时级平均速度

ADS 在出表前必须先固定口径，避免图表与报告数字不一致。

### 4.3 不改写 TDM 已定义的核心口径

ADS 层开发必须继承 TDM 已有定义，不自行更改：

- `stat_date`
- `biz_hour`
- `time_period_type`
- `trip_distance_km`
- `avg_speed_kmh`

### 4.4 对外命名要谨慎

当前数据边界决定了某些词不能随意对外宣传：

- 当前没有真实 `district_id`
- 当前没有真实商圈边界
- 当前没有道路名称映射表
- 当前没有稳定拥堵指数

因此 ADS 对外展示建议使用：

- “热点区域” 而不是 “商圈”
- “道路热度/通行事件数” 而不是 “真实物理车流绝对值”

## 5. 推荐的 ADS 交付物

建议在后续 ADS 目录下形成如下产物结构：

```text
ads/
  ADS整体规划方案.md
  build_ads_layer.py
  ads_metric_definition.csv
  ads_output/
    ads_daily_overview.parquet
    ads_hourly_trend.parquet
    ads_road_hotspot_top20_daily.parquet
    ads_region_hotspot_top20_daily.parquet
    ads_abnormal_vehicle_detail_daily.parquet
    ads_abnormal_vehicle_summary_daily.parquet
    ads_build_summary.json
```

其中：

- `build_ads_layer.py`：ADS 构建脚本
- `ads_metric_definition.csv`：指标定义说明文件
- `ads_output/*.parquet`：ADS 结果表
- `ads_build_summary.json`：构建摘要与校验结果

## 6. 推荐优先建设的 ADS 表

建议优先做以下 6 张表，已经足够支撑本次大作业的第一版展示。

### 6.1 `ads_daily_overview`

用途：

- 每日总览看板
- 每日趋势图
- 报告中的总体统计结果

建议字段：

- `stat_date`
- `active_vehicle_cnt`
- `total_trip_cnt`
- `total_distance_km`
- `global_avg_speed_kmh`
- `avg_vehicle_speed_kmh`
- `peak_trip_cnt`
- `night_active_vehicle_cnt`
- `peak_active_vehicle_cnt`

推荐来源：

- `tdm_vehicle_day_profile.parquet`
- `tdm_time_slot_day_profile.parquet`

### 6.2 `ads_hourly_trend`

用途：

- 每小时车流量趋势图
- 每小时活跃车辆数折线图
- 每小时平均速度图

建议字段：

- `stat_date`
- `biz_hour`
- `time_range_id`
- `time_period_type`
- `trip_cnt`
- `vehicle_cnt`
- `avg_speed_kmh`
- `total_distance_km`
- `total_duration_min`
- `road_coverage_cnt`

推荐来源：

- `tdm_time_slot_day_profile.parquet`

### 6.3 `ads_road_hotspot_top20_daily`

用途：

- 每日热点道路 Top20
- 高峰热点道路榜单
- 夜间活跃道路榜单

建议字段：

- `stat_date`
- `road_id`
- `rank_by_pass_cnt`
- `pass_cnt`
- `vehicle_cnt`
- `trip_cnt`
- `peak_pass_cnt`
- `night_pass_cnt`
- `peak_pass_ratio`
- `direction_bias`
- `road_activity_level`
- `peak_bias_type`

说明：

- `peak_pass_cnt` 可由 `morning_peak_pass_cnt + evening_peak_pass_cnt` 得到

推荐来源：

- `tdm_road_day_profile.parquet`

### 6.4 `ads_region_hotspot_top20_daily`

用途：

- 区域热点 Top20
- 上车热点 / 下车热点
- 地图散点图

建议字段：

- `stat_date`
- `grid_id`
- `grid_center_lon`
- `grid_center_lat`
- `rank_by_total_od`
- `pickup_trip_cnt`
- `dropoff_trip_cnt`
- `total_od_trip_cnt`
- `active_vehicle_cnt`
- `night_od_trip_cnt`
- `peak_od_trip_cnt`
- `pickup_ratio`
- `grid_role_bias`
- `grid_activity_level`

推荐来源：

- `tdm_region_grid_day_profile.parquet`

注意：

- 当前应称为“热点区域”或“热点网格”
- 不建议直接命名为“商圈”

### 6.5 `ads_abnormal_vehicle_detail_daily`

用途：

- 异常车辆识别明细
- 支撑异常车辆数量统计
- 方便报告中解释“为什么被判定为异常”

建议字段：

- `stat_date`
- `devid`
- `trip_cnt`
- `matched_trip_ratio`
- `avg_speed_kmh`
- `night_trip_ratio`
- `trip_frequency_level`
- `night_activity_flag`
- `peak_activity_flag`
- `low_match_flag`
- `high_speed_flag`
- `night_overactive_flag`
- `abnormal_type`
- `abnormal_reason`

推荐来源：

- `tdm_vehicle_day_profile.parquet`

### 6.6 `ads_abnormal_vehicle_summary_daily`

用途：

- 每日异常车辆数量图
- 报告中的异常车辆统计结果

建议字段：

- `stat_date`
- `abnormal_vehicle_cnt`
- `low_match_vehicle_cnt`
- `high_speed_vehicle_cnt`
- `night_overactive_vehicle_cnt`

推荐来源：

- 基于 `ads_abnormal_vehicle_detail_daily` 再聚合

## 7. 核心指标与建议口径

以下指标是 ADS 第一版最值得优先交付的内容。

### 7.1 每日活跃车辆数

定义：

- 每个 `stat_date` 下 `tdm_vehicle_day_profile` 的记录数

建议口径：

- `count(*) by stat_date`

### 7.2 每日总 trip 数

定义：

- 每日总出行次数

建议口径：

- 使用 `tdm_vehicle_day_profile` 中 `sum(trip_cnt)`
- 或使用 `tdm_trip_profile` 中 `count(*)`

建议：

- 优先用 `tdm_vehicle_day_profile`

### 7.3 每日平均速度

需要明确分成两个版本：

1. 全局整体平均速度
2. 车均平均速度

建议口径：

- `global_avg_speed_kmh = sum(total_distance_km) / sum(total_duration_min / 60.0)`
- `avg_vehicle_speed_kmh = avg(avg_speed_kmh)`

### 7.4 每日高峰时段车流量

定义：

- 每天在 `morning_peak` 和 `evening_peak` 中的出行量总和

建议口径：

- `sum(trip_cnt)` where `time_period_type in ('morning_peak', 'evening_peak')`

推荐来源：

- `tdm_time_slot_day_profile.parquet`

### 7.5 每小时车流量趋势

定义：

- 按天、按小时展示：
  - `trip_cnt`
  - `vehicle_cnt`
  - `avg_speed_kmh`

推荐来源：

- `tdm_time_slot_day_profile.parquet`

### 7.6 热点道路 Top20

定义前必须澄清“热度”的含义。

可选口径：

1. 路段通行事件数：`pass_cnt`
2. 路段独立车辆数：`vehicle_cnt`
3. 路段涉及 trip 数：`trip_cnt`

建议：

- 第一版默认按 `pass_cnt` 做 Top20
- 同时在报告中说明这是“匹配路段通行事件次数”

### 7.7 热点区域 Top20

建议口径：

- `total_od_trip_cnt` 作为区域综合热度
- `pickup_trip_cnt` 作为上车热点
- `dropoff_trip_cnt` 作为下车热点

推荐来源：

- `tdm_region_grid_day_profile.parquet`

### 7.8 异常车辆数量

当前 TDM 层没有固化唯一的异常车辆标签，ADS 需做业务定义。

第一版建议采用规则法，便于解释。

建议规则：

- `matched_trip_ratio < 0.5`
- 或 `avg_speed_kmh > 40`
- 或 `night_activity_flag = true` 且 `trip_frequency_level in ('high', 'very_high')`

说明：

- 这只是当前作业场景下的候选实现
- 后续可根据老师或组内要求再调整

## 8. ADS 开发流程建议

ADS 开发建议按以下顺序推进。

### 8.1 先和可视化模块对齐图表需求

建议优先确认最终要展示的图表：

- 每日活跃车辆数趋势图
- 每日平均速度趋势图
- 每小时车流量趋势图
- 热点道路 Top20 柱状图
- 热点区域 Top20 地图
- 异常车辆数量图

只有先定图表，ADS 才能反向确定结果表结构。

### 8.2 再固定指标口径

每个指标需要写清楚：

- 统计对象
- 时间粒度
- 来源表
- 聚合方法
- 是否需要排序或 TopN

### 8.3 编写 ADS 构建脚本

建议新增：

- `build_ads_layer.py`

技术路线建议延续 TDM：

- 使用 DuckDB
- 输入为 `tdm_output/*.parquet`
- 输出为 `ads_output/*.parquet`

### 8.4 输出指标定义文件

建议新增：

- `ads_metric_definition.csv`

至少包含：

- 指标英文名
- 指标中文名
- 指标口径
- 来源表
- 粒度
- 备注

### 8.5 产出构建摘要

建议新增：

- `ads_build_summary.json`

内容包括：

- 生成文件列表
- 各表行数
- 构建时间
- 关键校验结果

## 9. 校验方案

ADS 层开发不能只看“能不能出结果”，还需要做基础校验。

### 9.1 数据范围校验

- `stat_date` 是否仅覆盖 `2015-01-03` 到 `2015-01-07`
- `biz_hour` 是否覆盖 `0` 到 `23`

### 9.2 数值合法性校验

- 数量类字段不得为负
- 速度类字段不得为负
- 比例字段应在合理范围内

### 9.3 TopN 结果校验

- 每日 Top20 结果是否排序正确
- 是否存在重复主键

### 9.4 异常车辆结果校验

- 汇总数量是否能回溯到异常明细
- 异常原因是否可解释

## 10. 与其他模块的协作方式

### 10.1 与 TDM 同学协作

需要确认：

- TDM 表字段是否稳定
- 是否还有补充字段计划
- 异常车辆候选特征是否需要调整

### 10.2 与可视化模块协作

ADS 需要向可视化模块提供：

- 每张图对应的 ADS 表名
- 图表字段说明
- 推荐过滤字段
- 示例图所需的口径说明

### 10.3 与报告/PPT 模块协作

ADS 需要向报告模块提供：

- ADS 层设计说明
- 关键结果表清单
- 指标定义和口径
- 数据发现结论

## 11. 可直接用于报告/PPT 的表达方式

ADS 部分在报告中可写成：

### 11.1 ADS 层目标

围绕业务需求，将 TDM 画像结果进一步聚合为可直接展示和分析的应用层指标，形成面向趋势分析、热点识别和异常识别的结果表。

### 11.2 ADS 层核心产物

围绕每日总览、小时趋势、热点道路、热点区域和异常车辆五类业务场景，设计并生成多张 ADS 结果表，供可视化模块和报告模块直接消费。

### 11.3 ADS 层价值

- 为可视化模块提供直接取数的数据接口
- 为报告与 PPT 提供统一数字来源
- 为后续扩展更多业务页面保留稳定接口

## 12. 风险与限制

当前 ADS 开发需要注意以下限制：

- 当前没有真实商圈边界，因此空间分析以规则网格为主
- 当前没有道路名称映射，因此热点道路可能只能展示 `road_id`
- 当前没有稳定拥堵指数，因此不建议强行输出“拥堵指数”
- 当前异常车辆定义是规则法，不是最终唯一标准

## 13. 推荐排期

如果按一周节奏推进，建议如下：

### 第 1 阶段：需求对齐

- 确认可视化要展示的图表
- 确认指标名称和口径

### 第 2 阶段：结果表建设

- 完成 `ads_daily_overview`
- 完成 `ads_hourly_trend`
- 完成 `ads_road_hotspot_top20_daily`
- 完成 `ads_region_hotspot_top20_daily`

### 第 3 阶段：异常识别与整理

- 完成 `ads_abnormal_vehicle_detail_daily`
- 完成 `ads_abnormal_vehicle_summary_daily`

### 第 4 阶段：交付与联调

- 生成 `ads_metric_definition.csv`
- 生成 `ads_build_summary.json`
- 与可视化模块联调
- 提供报告所需口径说明

## 14. 下一步建议

ADS 同学的下一步最合理动作是：

1. 先在组内确认最终要展示的图表范围
2. 再固定 6 张 ADS 表结构
3. 然后编写 `build_ads_layer.py`
4. 最后输出 `ads_output` 并交付给可视化与报告同学

如果时间紧张，优先级建议为：

1. `ads_daily_overview`
2. `ads_hourly_trend`
3. `ads_road_hotspot_top20_daily`
4. `ads_region_hotspot_top20_daily`
5. `ads_abnormal_vehicle_summary_daily`

这 5 类结果已经足够支撑一个规范的 ADS 第一版。

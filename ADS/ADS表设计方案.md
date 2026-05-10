# ADS 表设计方案

## 1. 文档目的

本文档基于当前项目已经完成的 TDM 产物，结合往届 ADS 的实现思路，整理出本项目当前最适合建设的 ADS 表清单。

目标不是机械复刻往届表名，而是：

- 充分利用当前 TDM 的真实能力边界
- 优先设计能直接落地、能支撑图表和报告的 ADS 表
- 兼顾规范性、可解释性和展示效果

本文档重点回答以下问题：

1. 当前 TDM 能支撑哪些 ADS 场景
2. 每张 ADS 表应该怎么设计
3. 每张表用到哪些字段
4. 这些表分别能做什么分析
5. 为什么这些表值得做、有什么意义

---

## 1.1 当前实现状态

截至当前，本文档中规划的 23 张候选 ADS 表已经全部生成到：

- `ads/ads_output/`

对应的 preview 也已经全部生成到：

- `ads/preview/`

因此本文档现在既是设计文档，也是当前已实现 ADS 表的结构参考文档。

---

## 2. 当前 TDM 的能力边界

当前项目已经完成的 TDM 结果位于 `tdm_output/`，包括：

- `tdm_trip_profile.parquet`
- `tdm_vehicle_day_profile.parquet`
- `tdm_vehicle_5d_profile.parquet`
- `tdm_vehicle_road_preference_5d.parquet`
- `tdm_road_day_profile.parquet`
- `tdm_time_slot_day_profile.parquet`
- `tdm_region_grid_day_profile.parquet`

结合 `DATA_HANDOFF_ADS.md` 可以判断，当前 TDM 的优势主要在以下几个方向：

- 按日统计
- 按小时趋势
- 车辆画像
- 道路热度
- 区域热点
- 异常车辆识别
- 高峰/夜间等时段分类

但当前也存在明确边界：

- 没有真实商圈边界，只有规则网格
- 没有稳定道路名称映射表
- 没有可靠的道路拥堵指数口径
- 没有可直接回放的轨迹点序列 ADS 结果
- 没有外部 POI、景点、餐厅、收入等补充数据

因此，本轮 ADS 最适合做的是：

- 路况监测
- 司机/车辆画像
- 区域热点分析
- 异常识别
- 行程结构分析

不适合强行直接做的是：

- 真实商圈分析
- 道路名称排行榜
- 拥堵指数大屏
- 轨迹回放接口
- 景点推荐/商圈消费推荐

---

## 3. 往届 ADS 思路如何映射到当前项目

往届 ADS 的核心思路不是“表名必须一样”，而是“围绕具体业务场景出结果”。

### 3.1 23 级 ADS 思路

23 级更偏向“基础结果表”模式，典型表包括：

- `hotmap`
- `road_counts`
- `taxi_counts`
- `point`
- `trip_track`

其特点是：

- 一张图或一类页面对应一张表
- 结果比较贴前端
- 适合直接做图

### 3.2 2025 级 ADS 思路

2025 级更偏向“场景化结果集”模式，核心场景包括：

- 路况监测
- 商圈分析
- 轨迹可视化
- 长短单推荐
- 商圈劳模代表

其特点是：

- 不是强调物理表名
- 更强调每个场景的指标组合
- 适合写报告和做数据大屏故事线

### 3.3 当前项目的合理改造方式

结合当前 TDM 能力边界，最合理的方式是：

- 继承 23 级“做清晰结果表”的思路
- 继承 2025 级“按业务场景组织结果”的思路
- 不强行复刻往届依赖外部数据的模块

因此当前 ADS 应优先围绕以下场景建设：

- 每日总览
- 小时趋势
- 行程结构
- 车辆画像
- 热点道路
- 热点区域
- 异常车辆

---

## 4. ADS 表设计总览

建议本轮 ADS 分成四类表：

1. 总览与时序类
2. 行程结构类
3. 车辆画像类
4. 道路与区域类
5. 质量与异常类

建议优先落地的核心表如下：

1. `ads_daily_overview`
2. `ads_daily_growth_compare`
3. `ads_hourly_trend`
4. `ads_peak_window_top3_daily`
5. `ads_time_period_summary_daily`
6. `ads_trip_structure_daily`
7. `ads_trip_efficiency_by_period_daily`
8. `ads_vehicle_profile_5d`
9. `ads_vehicle_segment_summary_5d`
10. `ads_vehicle_daily_operating_style`
11. `ads_vehicle_road_preference_topn`
12. `ads_vehicle_route_stability_5d`
13. `ads_road_hotspot_feature_daily`
14. `ads_road_watchlist_daily`
15. `ads_region_hotspot_role_daily`
16. `ads_dispatch_focus_grid_daily`
17. `ads_region_bias_daily`
18. `ads_abnormal_vehicle_daily_detail`
19. `ads_abnormal_vehicle_daily_summary`
20. `ads_data_quality_daily`

其中，前 8 到 10 张已经足够支撑本次作业的第一版。

---

## 4.1 优先级分档建议

为了便于实际落地，建议把 ADS 表分成三档：

### A 档：本轮必须完成

这部分最能直接支撑可视化和报告，是 ADS 第一版的主干。

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

### B 档：有时间就做

这部分能显著增强分析深度，但不是第一版必需品。

1. `ads_time_period_summary_daily`
2. `ads_trip_efficiency_by_period_daily`
3. `ads_trip_complexity_daily`
4. `ads_vehicle_daily_operating_style`
5. `ads_vehicle_road_preference_topn`
6. `ads_vehicle_route_stability_5d`
7. `ads_road_watchlist_daily`
8. `ads_dispatch_focus_grid_daily`
9. `ads_region_bias_daily`
10. `ads_abnormal_vehicle_daily_detail`
11. `ads_data_quality_daily`

### C 档：当前建议暂缓

这部分通常需要额外数据或不适合当前 TDM 直接支撑。

1. 轨迹回放类 ADS 表
2. 真实商圈类 ADS 表
3. 拥堵指数类 ADS 表
4. POI / 景点 / 餐饮推荐类 ADS 表
5. 长短单聚类中心类 ADS 表

### 分档原则

- A 档优先服务于“必须出图、必须写报告”的核心任务
- B 档服务于“提升亮点和深度”
- C 档避免超出当前数据边界，防止做出难以解释的结果

---

## 5. 总览与时序类表

## 5.1 `ads_daily_overview`

### 表定位

每日总览表，面向数据看板首页和报告摘要。

### 粒度

- `1 row = 1 stat_date`

### 主要来源

- `tdm_vehicle_day_profile.parquet`
- `tdm_time_slot_day_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `stat_date` | vehicle_day / time_slot_day | 统计日期 |
| `active_vehicle_cnt` | vehicle_day | 当日活跃车辆数 |
| `total_trip_cnt` | vehicle_day | 当日总出行次数 |
| `total_distance_km` | vehicle_day | 当日总里程 |
| `global_avg_speed_kmh` | vehicle_day | 全局整体平均速度 |
| `avg_vehicle_speed_kmh` | vehicle_day | 车均平均速度 |
| `night_active_vehicle_cnt` | vehicle_day | 夜间活跃车辆数 |
| `peak_active_vehicle_cnt` | vehicle_day | 高峰活跃车辆数 |
| `peak_trip_cnt` | time_slot_day | 高峰时段 trip 总数 |
| `hourly_peak_trip_cnt` | time_slot_day | 单小时最高 trip 数 |
| `hourly_peak_hour` | time_slot_day | 当天最繁忙小时 |

### 能做的分析

- 哪一天最忙
- 哪一天活跃车辆最多
- 哪一天总里程最高
- 哪一天平均速度最低
- 高峰是否集中在固定日期

### 价值与意义

- 是全项目最核心的总览表
- 能直接支撑首页 KPI、报告摘要和 PPT 总结页
- 能把复杂 TDM 结果压缩成业务方最容易理解的指标

---

## 5.2 `ads_daily_growth_compare`

### 表定位

每日环比/相邻日比较表，用于趋势分析。

### 粒度

- `1 row = 1 stat_date`

### 主要来源

- `ads_daily_overview`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `stat_date` | 当前日期 |
| `total_trip_cnt` | 当前日 trip 数 |
| `active_vehicle_cnt` | 当前日活跃车辆数 |
| `global_avg_speed_kmh` | 当前日整体平均速度 |
| `trip_cnt_prev_day` | 前一日 trip 数 |
| `active_vehicle_prev_day` | 前一日活跃车辆数 |
| `trip_cnt_dod_growth` | trip 数环比增速 |
| `active_vehicle_dod_growth` | 活跃车辆数环比增速 |
| `speed_dod_change` | 平均速度变化值 |

### 能做的分析

- 哪一天相对前一天增长最快
- 活跃车辆增加时速度是否下降
- 车流和速度是否存在反向关系

### 价值与意义

- 往届的“增长率/周期对比”功能可以由这张表自然实现
- 图表表现力强，适合报告中讲趋势变化

---

## 5.3 `ads_hourly_trend`

### 表定位

小时级趋势表，是路况监测的主力表。

### 粒度

- `1 row = 1 stat_date + 1 biz_hour`

### 主要来源

- `tdm_time_slot_day_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `stat_date` | time_slot_day | 统计日期 |
| `biz_hour` | time_slot_day | 小时 |
| `time_range_id` | time_slot_day | 日期小时主键 |
| `time_period_type` | time_slot_day | 时段类型 |
| `trip_cnt` | time_slot_day | 小时 trip 数 |
| `vehicle_cnt` | time_slot_day | 小时活跃车辆数 |
| `avg_speed_kmh` | time_slot_day | 小时综合平均速度 |
| `total_distance_km` | time_slot_day | 小时总里程 |
| `total_duration_min` | time_slot_day | 小时总时长 |
| `road_coverage_cnt` | time_slot_day | 小时覆盖道路数 |
| `slot_activity_level` | time_slot_day | 小时活跃度等级 |

### 能做的分析

- 每小时车流量趋势
- 每小时活跃车辆数趋势
- 每小时平均速度变化
- 每小时活跃范围变化
- 高峰时段是否稳定

### 价值与意义

- 这是最适合做折线图和高峰识别的基础表
- 可以直接替代往届的部分“路况监测”查询
- 与总览表配合后，能形成完整的时间维度分析链

---

## 5.4 `ads_peak_window_top3_daily`

### 表定位

每天最繁忙小时 Top3 结果表。

### 粒度

- `1 row = 1 stat_date + 1 rank_in_day`

### 主要来源

- `ads_hourly_trend`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `stat_date` | 日期 |
| `rank_in_day` | 当天排名 |
| `biz_hour` | 小时 |
| `trip_cnt` | 小时 trip 数 |
| `vehicle_cnt` | 活跃车辆数 |
| `avg_speed_kmh` | 平均速度 |
| `time_period_type` | 时段类型 |

### 能做的分析

- 每天最繁忙的三个小时分别是什么
- 高峰时段是不是总出现在同一时间窗口
- 最忙时段的速度是否显著下降

### 价值与意义

- 特别适合报告写“高峰窗口识别”
- 适合做排行榜或结论卡片
- 讲故事能力强，图表成本低

---

## 5.5 `ads_time_period_summary_daily`

### 表定位

按时段类型聚合的日统计表。

### 粒度

- `1 row = 1 stat_date + 1 time_period_type`

### 主要来源

- `tdm_trip_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `stat_date` | trip_profile | 日期 |
| `time_period_type` | trip_profile | 时段类型 |
| `trip_cnt` | trip_profile | trip 数 |
| `avg_trip_distance_km` | trip_profile | 平均单次里程 |
| `avg_trip_duration_min` | trip_profile | 平均单次时长 |
| `avg_speed_kmh` | trip_profile | 平均速度 |
| `avg_unique_road_cnt` | trip_profile | 平均唯一路段数 |
| `avg_road_repeat_ratio` | trip_profile | 平均道路重复率 |

### 能做的分析

- 早高峰、晚高峰、夜间、白天的出行差异
- 夜间是否更偏长单
- 高峰是否更偏低速
- 不同时段行程复杂度是否不同

### 价值与意义

- 可以把简单的“时间趋势”升级为“时段行为分析”
- 更适合在报告里写解释，而不是只展示折线图

---

## 6. 行程结构类表

## 6.1 `ads_trip_structure_daily`

### 表定位

行程结构分布表，用来替代往届“长短单推荐”中的基础部分。

### 粒度

- `1 row = 1 stat_date + 结构维度组合`

### 主要来源

- `tdm_trip_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `stat_date` | trip_profile | 日期 |
| `trip_distance_level` | trip_profile | 距离分层 |
| `trip_duration_level` | trip_profile | 时长分层 |
| `trip_speed_level` | trip_profile | 速度分层 |
| `trip_cnt` | trip_profile | 数量 |
| `trip_ratio` | trip_profile 派生 | 占当日比例 |

### 能做的分析

- 长短单比例
- 慢速/正常/快速 trip 的分布
- 哪一天更偏短途、哪一天更偏长途

### 价值与意义

- 当前没有必要直接做聚类推荐，但完全可以先做好“长短单结构画像”
- 能支撑柱状图、堆积图、环形图
- 可解释性强，便于报告书写

---

## 6.2 `ads_trip_efficiency_by_period_daily`

### 表定位

按时段聚合的行程效率表。

### 粒度

- `1 row = 1 stat_date + 1 time_period_type`

### 主要来源

- `tdm_trip_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `stat_date` | trip_profile | 日期 |
| `time_period_type` | trip_profile | 时段类型 |
| `avg_trip_distance_km` | trip_profile | 平均距离 |
| `avg_trip_duration_min` | trip_profile | 平均时长 |
| `avg_speed_kmh` | trip_profile | 平均速度 |
| `avg_unique_road_cnt` | trip_profile | 平均唯一路段数 |
| `avg_road_repeat_ratio` | trip_profile | 平均重复率 |

### 能做的分析

- 高峰期是不是更慢
- 夜间 trip 是否更长
- 高峰期路径是否更绕

### 价值与意义

- 可以自然回答“效率”问题
- 比只给均值更接近业务场景

---

## 6.3 `ads_trip_complexity_daily`

### 表定位

关注路径复杂度的日统计表。

### 粒度

- `1 row = 1 stat_date`

### 主要来源

- `tdm_trip_profile.parquet`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `stat_date` | 日期 |
| `avg_unique_road_cnt` | 平均唯一路段数 |
| `avg_road_repeat_ratio` | 平均路径重复率 |
| `avg_forward_edge_ratio` | 平均正向边占比 |
| `complex_trip_ratio` | 高复杂度 trip 占比 |

### 能做的分析

- 哪一天行程路径更复杂
- 路径重复率是否高
- 车辆是否更倾向走熟悉路线

### 价值与意义

- 这是当前 TDM 的特色能力
- 往届很少做到这么细，这部分反而能体现你们的技术含量

---

## 7. 车辆画像类表

## 7.1 `ads_vehicle_profile_5d`

### 表定位

五天累计车辆画像表，是“司机画像中心”的基础表。

### 粒度

- `1 row = 1 devid`

### 主要来源

- `tdm_vehicle_5d_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `devid` | vehicle_5d | 设备编号 |
| `active_day_cnt` | vehicle_5d | 活跃天数 |
| `total_trip_cnt` | vehicle_5d | 五天总 trip 数 |
| `avg_daily_trip_cnt` | vehicle_5d | 日均 trip 数 |
| `total_distance_km` | vehicle_5d | 五天总里程 |
| `total_duration_min` | vehicle_5d | 五天总时长 |
| `avg_trip_distance_km` | vehicle_5d | 平均单次里程 |
| `avg_speed_kmh` | vehicle_5d | 五天平均速度 |
| `night_trip_ratio_5d` | vehicle_5d | 夜间偏向 |
| `peak_trip_ratio_5d` | vehicle_5d | 高峰偏向 |
| `road_coverage_cnt_5d` | vehicle_5d | 五天覆盖道路数 |
| `dominant_time_period_5d` | vehicle_5d | 主导时段 |
| `driver_activity_level` | vehicle_5d | 活跃度等级 |
| `core_driver_flag` | vehicle_5d | 核心司机标记 |
| `full_attendance_flag` | vehicle_5d | 满勤标记 |

### 能做的分析

- 核心司机数量
- 满勤司机数量
- 不同活跃度司机结构
- 夜班偏向司机数量
- 高峰偏向司机数量

### 价值与意义

- 是最完整、最稳定的司机画像底表
- 特别适合做分层经营分析和报告中的“司机群体画像”

---

## 7.2 `ads_vehicle_segment_summary_5d`

### 表定位

司机分层结构表，用于群体对比分析。

### 粒度

- `1 row = 1 分层组合`

### 主要来源

- `tdm_vehicle_5d_profile.parquet`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `driver_activity_level` | 活跃度等级 |
| `dominant_time_period_5d` | 主导时段 |
| `vehicle_cnt` | 车辆数 |
| `avg_total_trip_cnt` | 平均总 trip 数 |
| `avg_total_distance_km` | 平均总里程 |
| `avg_speed_kmh` | 平均速度 |
| `core_driver_ratio` | 核心司机占比 |
| `full_attendance_ratio` | 满勤占比 |

### 能做的分析

- 司机群体如何分层
- 高活跃司机是否更集中在某些时段
- 满勤司机和非满勤司机有什么差异

### 价值与意义

- 特别适合做饼图、堆积图和群体画像图
- 比直接展示单车明细更适合课程汇报

---

## 7.3 `ads_vehicle_daily_operating_style`

### 表定位

车辆日级运营风格表。

### 粒度

- `1 row = 1 stat_date + 1 devid`

### 主要来源

- `tdm_vehicle_day_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `stat_date` | vehicle_day | 日期 |
| `devid` | vehicle_day | 车辆 |
| `trip_cnt` | vehicle_day | 当日出行次数 |
| `active_hour_cnt` | vehicle_day | 活跃小时数 |
| `road_coverage_cnt` | vehicle_day | 覆盖道路数 |
| `night_trip_ratio` | vehicle_day | 夜间占比 |
| `peak_trip_ratio` | vehicle_day | 高峰占比 |
| `dominant_time_period` | vehicle_day | 主导时段 |
| `trip_frequency_level` | vehicle_day | 频次等级 |
| `night_activity_flag` | vehicle_day | 夜间活跃标记 |
| `peak_activity_flag` | vehicle_day | 高峰活跃标记 |

### 能做的分析

- 当天最活跃车辆是谁
- 哪些车辆是夜班型
- 哪些车辆是高峰型
- 哪些车辆作业范围广

### 价值与意义

- 适合做日级榜单和画像页
- 也是异常识别的重要底表

---

## 7.4 `ads_vehicle_road_preference_topn`

### 表定位

车辆偏好道路结果表。

### 粒度

- `1 row = 1 devid + 1 road_id`

### 主要来源

- `tdm_vehicle_road_preference_5d.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `devid` | vehicle_road_pref | 车辆 |
| `road_id` | vehicle_road_pref | 道路 |
| `rank_in_device` | vehicle_road_pref | 设备内排名 |
| `pass_cnt` | vehicle_road_pref | 通行次数 |
| `pass_ratio` | vehicle_road_pref | 占比 |
| `active_day_cnt_on_road` | vehicle_road_pref | 活跃天数 |
| `preference_level` | vehicle_road_pref | 核心/常走道路 |

### 能做的分析

- 某辆车最常走哪些道路
- 哪些车的路线偏好非常集中
- 哪些车更像“熟路型司机”

### 价值与意义

- 可替代往届的司机排行榜/劳模榜部分思路
- 体现“个体轨迹偏好”这一更细的中台价值

---

## 7.5 `ads_vehicle_route_stability_5d`

### 表定位

路线稳定性画像表。

### 粒度

- `1 row = 1 devid`

### 主要来源

- `tdm_vehicle_road_preference_5d.parquet`
- `tdm_vehicle_5d_profile.parquet`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `devid` | 设备编号 |
| `top1_pass_ratio` | 最偏好道路占比 |
| `top3_pass_ratio_sum` | Top3 道路累计占比 |
| `active_day_cnt` | 活跃天数 |
| `total_trip_cnt` | 五天总 trip 数 |
| `driver_activity_level` | 司机活跃度等级 |
| `route_stability_level` | 路线稳定性分层 |

### 能做的分析

- 固定路线型司机和分散路线型司机的区分
- 是否存在“高度依赖某几条道路”的车辆

### 价值与意义

- 很有“想象力”，但仍完全基于现有 TDM
- 有助于形成特色分析点，提升作业亮点

---

## 8. 道路与区域类表

## 8.1 `ads_road_hotspot_feature_daily`

### 表定位

道路热点和道路画像主表。

### 粒度

- `1 row = 1 stat_date + 1 road_id`

### 主要来源

- `tdm_road_day_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `stat_date` | road_day | 日期 |
| `road_id` | road_day | 道路编号 |
| `pass_cnt` | road_day | 通行事件次数 |
| `vehicle_cnt` | road_day | 通行车辆数 |
| `trip_cnt` | road_day | 涉及 trip 数 |
| `morning_peak_pass_cnt` | road_day | 早高峰通行次数 |
| `evening_peak_pass_cnt` | road_day | 晚高峰通行次数 |
| `night_pass_cnt` | road_day | 夜间通行次数 |
| `peak_pass_ratio` | road_day | 高峰占比 |
| `forward_edge_cnt` | road_day | 正向边数量 |
| `backward_edge_cnt` | road_day | 反向边数量 |
| `forward_ratio` | road_day | 正向占比 |
| `direction_bias` | road_day | 方向偏向 |
| `road_activity_level` | road_day | 活跃度等级 |
| `peak_bias_type` | road_day | 时段偏向类型 |

### 能做的分析

- 每日热点道路 TopN
- 高峰热点道路
- 夜间活跃道路
- 道路方向偏向分析
- 热门道路结构分析

### 价值与意义

- 这是最接近往届 `road_counts` 的核心表
- 也是最适合做“路况监测”模块的结果表

---

## 8.2 `ads_road_watchlist_daily`

### 表定位

重点道路观察表。

### 粒度

- `1 row = 1 stat_date + 1 road_id`

### 主要来源

- `ads_road_hotspot_feature_daily`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `stat_date` | 日期 |
| `road_id` | 道路 |
| `pass_cnt` | 通行事件数 |
| `peak_pass_ratio` | 高峰占比 |
| `direction_bias` | 方向偏向 |
| `road_activity_level` | 活跃度 |
| `peak_bias_type` | 时段偏向 |
| `watch_reason` | 重点关注原因 |
| `watch_score` | 关注分值 |

### 能做的分析

- 哪些道路值得重点关注
- 哪些道路特别偏高峰
- 哪些道路方向明显失衡

### 价值与意义

- 能把“热点道路”升级成“管理建议”
- 非常适合答辩时讲“应用价值”

---

## 8.3 `ads_region_hotspot_role_daily`

### 表定位

热点区域与区域角色分析主表。

### 粒度

- `1 row = 1 stat_date + 1 grid_id`

### 主要来源

- `tdm_region_grid_day_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `stat_date` | region_grid_day | 日期 |
| `grid_id` | region_grid_day | 网格编号 |
| `grid_center_lon` | region_grid_day | 中心经度 |
| `grid_center_lat` | region_grid_day | 中心纬度 |
| `pickup_trip_cnt` | region_grid_day | 上车次数 |
| `dropoff_trip_cnt` | region_grid_day | 下车次数 |
| `total_od_trip_cnt` | region_grid_day | 总 OD 次数 |
| `active_vehicle_cnt` | region_grid_day | 活跃车辆数 |
| `night_od_trip_cnt` | region_grid_day | 夜间 OD 次数 |
| `peak_od_trip_cnt` | region_grid_day | 高峰 OD 次数 |
| `pickup_ratio` | region_grid_day | 上车占比 |
| `grid_role_bias` | region_grid_day | 区域角色偏向 |
| `grid_activity_level` | region_grid_day | 活跃度等级 |

### 能做的分析

- 热点区域 TopN
- 上车热点区域
- 下车热点区域
- 高峰热点区域
- 区域角色识别

### 价值与意义

- 是当前最合理的“商圈分析替代版”
- 可以直接做地图散点图、热区图、TopN 榜单
- 不依赖额外商圈边界数据

---

## 8.4 `ads_dispatch_focus_grid_daily`

### 表定位

调度重点区域表。

### 粒度

- `1 row = 1 stat_date + 1 grid_id`

### 主要来源

- `ads_region_hotspot_role_daily`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `stat_date` | 日期 |
| `grid_id` | 网格 |
| `grid_center_lon` | 中心经度 |
| `grid_center_lat` | 中心纬度 |
| `total_od_trip_cnt` | 总活跃度 |
| `peak_od_trip_cnt` | 高峰活跃度 |
| `active_vehicle_cnt` | 运力覆盖 |
| `pickup_ratio` | 上车偏向 |
| `dispatch_score` | 调度优先级评分 |
| `dispatch_level` | 调度等级 |

### 能做的分析

- 哪些区域最值得优先调度车辆
- 哪些区域高峰期最需要补充运力
- 哪些区域更像“出发区”

### 价值与意义

- 属于在当前 TDM 基础上的创意增强版
- 特别适合报告写“面向平台调度的应用价值”

---

## 8.5 `ads_region_bias_daily`

### 表定位

区域偏向特征分析表。

### 粒度

- `1 row = 1 stat_date + 1 grid_id`

### 主要来源

- `tdm_region_grid_day_profile.parquet`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `stat_date` | 日期 |
| `grid_id` | 网格 |
| `total_od_trip_cnt` | 总 OD 数 |
| `peak_od_trip_cnt` | 高峰 OD 数 |
| `night_od_trip_cnt` | 夜间 OD 数 |
| `pickup_ratio` | 上车占比 |
| `grid_role_bias` | 上下车角色偏向 |
| `grid_activity_level` | 热度等级 |
| `region_bias_type` | 区域偏向类型 |

### 能做的分析

- 哪些区域偏上车
- 哪些区域偏下车
- 哪些区域高峰更明显
- 哪些区域夜间更活跃

### 价值与意义

- 可以在没有真实商圈的情况下，做出一定程度的“区域功能感知”
- 很适合写出“通勤区/目的地区”的推断分析

---

## 9. 质量与异常类表

## 9.1 `ads_abnormal_vehicle_daily_detail`

### 表定位

异常车辆识别明细表。

### 粒度

- `1 row = 1 stat_date + 1 devid`

### 主要来源

- `tdm_vehicle_day_profile.parquet`

### 建议字段

| 字段名 | 来源 | 含义 |
| --- | --- | --- |
| `stat_date` | vehicle_day | 日期 |
| `devid` | vehicle_day | 车辆 |
| `trip_cnt` | vehicle_day | 当日出行数 |
| `matched_trip_ratio` | vehicle_day | 匹配成功率 |
| `avg_speed_kmh` | vehicle_day | 平均速度 |
| `night_trip_ratio` | vehicle_day | 夜间占比 |
| `trip_frequency_level` | vehicle_day | 频次等级 |
| `night_activity_flag` | vehicle_day | 夜间活跃标记 |
| `peak_activity_flag` | vehicle_day | 高峰活跃标记 |
| `low_match_flag` | 派生 | 低匹配标记 |
| `high_speed_flag` | 派生 | 高速异常标记 |
| `night_overactive_flag` | 派生 | 夜间高活跃标记 |
| `abnormal_type` | 派生 | 异常类型 |
| `abnormal_reason` | 派生 | 异常原因 |

### 建议规则

第一版可采用：

- `matched_trip_ratio < 0.5`
- 或 `avg_speed_kmh > 40`
- 或 `night_activity_flag = true` 且 `trip_frequency_level in ('high', 'very_high')`

### 能做的分析

- 当天有哪些异常车辆
- 异常原因主要是什么
- 哪类异常更多

### 价值与意义

- 异常规则最适合在 ADS 层定义
- 明细表有助于答辩和报告解释

---

## 9.2 `ads_abnormal_vehicle_daily_summary`

### 表定位

异常车辆统计汇总表。

### 粒度

- `1 row = 1 stat_date`

### 主要来源

- `ads_abnormal_vehicle_daily_detail`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `stat_date` | 日期 |
| `abnormal_vehicle_cnt` | 异常车辆总数 |
| `low_match_vehicle_cnt` | 低匹配车辆数 |
| `high_speed_vehicle_cnt` | 高速异常车辆数 |
| `night_overactive_vehicle_cnt` | 夜间异常活跃车辆数 |

### 能做的分析

- 每日异常车辆数量趋势
- 异常类型结构占比

### 价值与意义

- 可直接用于图表和报告
- 能快速体现 ADS 的“识别价值”

---

## 9.3 `ads_data_quality_daily`

### 表定位

每日数据质量观察表。

### 粒度

- `1 row = 1 stat_date`

### 主要来源

- `tdm_trip_profile.parquet`
- `tdm_vehicle_day_profile.parquet`

### 建议字段

| 字段名 | 含义 |
| --- | --- |
| `stat_date` | 日期 |
| `total_trip_cnt` | 总 trip 数 |
| `unmatched_trip_cnt` | 无匹配 trip 数 |
| `unmatched_trip_ratio` | 无匹配占比 |
| `very_fast_trip_cnt` | 超高速 trip 数 |
| `very_fast_trip_ratio` | 超高速占比 |
| `low_match_vehicle_cnt` | 低匹配车辆数 |

### 能做的分析

- 每日数据质量稳定性
- 是否有明显异常日期
- 是否存在大量匹配失败或异常速度

### 价值与意义

- 适合答辩时证明结果可靠
- 体现数据中台不只是做图，也在做质量治理

---

## 10. 当前最值得优先落地的 8 张 ADS 表

如果时间有限，建议优先做以下 8 张：

1. `ads_daily_overview`
2. `ads_daily_growth_compare`
3. `ads_hourly_trend`
4. `ads_peak_window_top3_daily`
5. `ads_trip_structure_daily`
6. `ads_vehicle_profile_5d`
7. `ads_road_hotspot_feature_daily`
8. `ads_region_hotspot_role_daily`

如果还能再补两张，优先加：

9. `ads_abnormal_vehicle_daily_summary`
10. `ads_vehicle_segment_summary_5d`

这 10 张已经足够支撑：

- 一页总览
- 一页小时趋势
- 一页行程结构
- 一页司机画像
- 一页道路热点
- 一页区域热点
- 一页异常分析

---

## 11. 当前不建议硬做的 ADS 表

为了避免走偏，当前不建议强行做以下表：

### 11.1 轨迹回放表

例如：

- `ads_trip_track`
- `ads_point_detail`

原因：

- 当前 TDM 不是轨迹点序列层
- 若确实要做，应回到 `gps_points_clean.parquet`

### 11.2 真实商圈表

例如：

- `ads_business_district_daily`
- `ads_shopping_mall_activity`

原因：

- 当前没有真实商圈边界或命名结果

### 11.3 拥堵指数表

例如：

- `ads_road_congestion_index_daily`

原因：

- 当前缺少稳定的道路长度、路段速度和真实拥堵口径

### 11.4 POI 推荐类表

例如：

- `ads_poi_recommendation`
- `ads_attraction_hotspot`

原因：

- 当前没有景点、餐厅、POI 数据

---

## 12. 结论

当前这套 TDM 虽然不适合机械复刻往届所有 ADS 模块，但已经足够支撑一套更加规范、更加贴近数仓分层思路的 ADS 第一版。

与其强行复刻：

- 商圈命名
- 拥堵指数
- 轨迹回放
- 长短单聚类推荐

不如把当前真正能做扎实的部分做到位：

- 日总览
- 小时趋势
- 行程结构
- 司机画像
- 道路热点
- 区域热点
- 异常识别

这样做的好处是：

- 数据口径更稳
- 指标更好解释
- 更容易和可视化模块联动
- 更适合作业汇报和答辩
- 能体现你们是基于真实数据边界在做设计，而不是照搬模板

下一步建议：

1. 先从本文件的“优先 8 张表”中确定最终落地范围
2. 再写 `build_ads_layer.py`
3. 然后输出 `ads_output/`
4. 最后交给可视化和报告模块联调

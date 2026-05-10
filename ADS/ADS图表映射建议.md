# ADS 图表映射建议

## 1. 文档目的

本文档用于把当前已经生成的 8 张核心 ADS 表，直接映射成：

- 适合做什么图
- 横轴、纵轴、颜色、筛选项该怎么选
- 每张图能讲什么结论
- 哪些图适合放报告，哪些图适合放 PPT 或大屏

当前可直接预览的 CSV 文件位于：

- `ads/preview/`

对应文件如下：

- `ads_daily_overview_preview.csv`
- `ads_daily_growth_compare_preview.csv`
- `ads_hourly_trend_preview.csv`
- `ads_peak_window_top3_daily_preview.csv`
- `ads_trip_structure_daily_preview.csv`
- `ads_vehicle_profile_5d_preview.csv`
- `ads_road_hotspot_feature_daily_preview.csv`
- `ads_region_hotspot_role_daily_preview.csv`

---

## 1.1 当前已实现的图表产物

本轮已经将本文档中建议的图表全部落地为静态图片文件。

相关脚本与产物如下：

- 图表生成脚本：`ads/build_ads_charts.py`
- 图表输出目录：`ads/charts_output/`
- 图表清单：`ads/charts_output/chart_manifest.csv`
- 图表构建摘要：`ads/charts_output/charts_build_summary.json`

当前已生成图表数量：

- `23` 张 PNG 图

因此，下一阶段同学不需要重新从零想图，只需要：

1. 直接查看 `ads/charts_output/`
2. 结合本文件选择适合最终展示的图
3. 如需调整样式，再基于 `build_ads_charts.py` 微调

---

## 2. 推荐图表总览

建议优先做以下图：

1. 每日活跃车辆数 / trip 数趋势图
2. 每日平均速度趋势图
3. 每小时车流量趋势图
4. 每日 Top3 高峰小时图
5. 行程结构分布图
6. 司机活跃度结构图
7. 热点道路 Top20 图
8. 热点区域 Top20 地图

如果版面够，还可以补：

9. 环比增长图
10. 核心司机榜单

---

## 3. 各表对应图表建议

## 3.1 `ads_daily_overview`

对应文件：

- `ads_output/ads_daily_overview.parquet`
- `preview/ads_daily_overview_preview.csv`

### 推荐图 1：每日活跃车辆数与总 trip 数双轴图

图形类型：

- 柱线组合图

字段使用：

- 横轴：`stat_date`
- 左轴柱状：`total_trip_cnt`
- 右轴折线：`active_vehicle_cnt`

筛选建议：

- 全部 5 天直接展示

适合表达的结论：

- 哪一天总出行次数最多
- 活跃车辆数与总 trip 数是否同步变化

意义：

- 是最直观的“总体业务规模”展示
- 适合放在总览页或报告摘要页

### 推荐图 2：每日平均速度图

图形类型：

- 折线图

字段使用：

- 横轴：`stat_date`
- 纵轴：`global_avg_speed_kmh`
- 可选第二条线：`avg_vehicle_speed_kmh`

适合表达的结论：

- 每天整体运行速度变化
- “整体平均速度”和“车均平均速度”差异是否明显

意义：

- 有助于解释整体运行效率

### 推荐图 3：夜间 / 高峰活跃车辆数对比图

图形类型：

- 分组柱状图

字段使用：

- 横轴：`stat_date`
- 值：`night_active_vehicle_cnt`、`peak_active_vehicle_cnt`

适合表达的结论：

- 哪一天夜间活跃车多
- 哪一天高峰参与车辆更多

---

## 3.2 `ads_daily_growth_compare`

对应文件：

- `ads_output/ads_daily_growth_compare.parquet`
- `preview/ads_daily_growth_compare_preview.csv`

### 推荐图 4：环比变化图

图形类型：

- 柱状图或折线图

字段使用：

- 横轴：`stat_date`
- 值：`trip_cnt_dod_growth`
- 可选第二条线：`active_vehicle_dod_growth`

适合表达的结论：

- 哪一天相对前一天增长最快
- 活跃车辆和 trip 数增长是否同步

意义：

- 非常适合写报告中的“趋势变化”
- 对 PPT 来说也很容易讲清楚

### 推荐图 5：速度变化图

图形类型：

- 柱状图

字段使用：

- 横轴：`stat_date`
- 值：`speed_dod_change`

适合表达的结论：

- 哪一天速度提升
- 哪一天速度下降

---

## 3.3 `ads_hourly_trend`

对应文件：

- `ads_output/ads_hourly_trend.parquet`
- `preview/ads_hourly_trend_preview.csv`

### 推荐图 6：每小时 trip 趋势图

图形类型：

- 多折线图

字段使用：

- 横轴：`biz_hour`
- 纵轴：`trip_cnt`
- 图例：`stat_date`

适合表达的结论：

- 每天车流高峰集中在哪些小时
- 工作日和周末模式是否不同

意义：

- 是“高峰识别”的核心图

### 推荐图 7：每小时活跃车辆数趋势图

图形类型：

- 多折线图

字段使用：

- 横轴：`biz_hour`
- 纵轴：`vehicle_cnt`
- 图例：`stat_date`

适合表达的结论：

- 运力在不同小时的分布
- 车流和运力是否匹配

### 推荐图 8：每小时平均速度图

图形类型：

- 折线图

字段使用：

- 横轴：`biz_hour`
- 纵轴：`avg_speed_kmh`
- 图例：`stat_date`

适合表达的结论：

- 哪些小时速度最低
- 高峰小时是否对应低速区间

### 推荐图 9：小时活跃度热力图

图形类型：

- 热力图

字段使用：

- 横轴：`biz_hour`
- 纵轴：`stat_date`
- 色深：`trip_cnt`

适合表达的结论：

- 哪些日期、哪些小时最忙
- 全部样本中是否存在稳定高峰

---

## 3.4 `ads_peak_window_top3_daily`

对应文件：

- `ads_output/ads_peak_window_top3_daily.parquet`
- `preview/ads_peak_window_top3_daily_preview.csv`

### 推荐图 10：每日 Top3 高峰小时排行榜

图形类型：

- 分组柱状图

字段使用：

- 横轴：`stat_date`
- 分类：`rank_in_day`
- 标签：`biz_hour`
- 值：`trip_cnt`

适合表达的结论：

- 每天最忙的 3 个小时分别是什么
- 高峰小时更偏早高峰还是晚高峰

意义：

- 报告里很好写
- 适合 PPT 结论页

### 推荐图 11：高峰小时占比图

图形类型：

- 柱状图

字段使用：

- 横轴：`stat_date`
- 值：`trip_share_in_day`

适合表达的结论：

- 每天最忙小时占当日总 trip 的比例有多高

---

## 3.5 `ads_trip_structure_daily`

对应文件：

- `ads_output/ads_trip_structure_daily.parquet`
- `preview/ads_trip_structure_daily_preview.csv`

### 推荐图 12：距离分层结构图

图形类型：

- 堆积柱状图

字段使用：

- 横轴：`stat_date`
- 堆积分类：`trip_distance_level`
- 值：`trip_cnt` 或 `trip_ratio`

适合表达的结论：

- 哪一天短途更多
- 哪一天长途更多

### 推荐图 13：速度结构图

图形类型：

- 堆积柱状图或环形图

字段使用：

- 分类：`trip_speed_level`
- 值：`trip_cnt` 或 `trip_ratio`

适合表达的结论：

- 慢速 / 正常 / 快速 trip 的占比结构

### 推荐图 14：距离-时长-速度结构矩阵

图形类型：

- 透视热力图

字段使用：

- 行：`trip_distance_level`
- 列：`trip_duration_level`
- 分面或筛选：`stat_date`
- 值：`trip_cnt`

适合表达的结论：

- 长单是否通常也伴随长时长
- 哪类 trip 组合最常见

意义：

- 这张图比较“数据分析型”，很适合展示你们不是只会做基础统计

---

## 3.6 `ads_vehicle_profile_5d`

对应文件：

- `ads_output/ads_vehicle_profile_5d.parquet`
- `preview/ads_vehicle_profile_5d_preview.csv`

### 推荐图 15：司机活跃度等级结构图

图形类型：

- 柱状图或饼图

字段使用：

- 分类：`driver_activity_level`
- 值：`devid` 计数

适合表达的结论：

- 核心司机、高活跃司机、中低活跃司机的结构

### 推荐图 16：核心司机 / 满勤司机数量图

图形类型：

- 指标卡片或柱状图

字段使用：

- `core_driver_flag`
- `full_attendance_flag`

适合表达的结论：

- 核心运力规模
- 满勤司机规模

### 推荐图 17：司机排行榜

图形类型：

- 横向条形图

字段使用：

- 标签：`devid`
- 值：`total_trip_cnt` 或 `total_distance_km`
- 排序：`rank_by_total_trip_cnt`

适合表达的结论：

- Top 司机的活跃程度
- 是否存在头部集中

---

## 3.7 `ads_road_hotspot_feature_daily`

对应文件：

- `ads_output/ads_road_hotspot_feature_daily.parquet`
- `preview/ads_road_hotspot_feature_daily_preview.csv`

### 推荐图 18：每日热点道路 Top20

图形类型：

- 横向条形图

字段使用：

- 筛选：`rank_by_pass_cnt <= 20`
- 标签：`road_id`
- 值：`pass_cnt`
- 分面：`stat_date`

适合表达的结论：

- 每天最热的道路有哪些
- 热点道路是否稳定

### 推荐图 19：高峰道路图

图形类型：

- 横向条形图

字段使用：

- 标签：`road_id`
- 值：`peak_pass_cnt`

适合表达的结论：

- 哪些道路最受高峰影响

### 推荐图 20：道路方向偏向图

图形类型：

- 分组柱状图或饼图

字段使用：

- 分类：`direction_bias`
- 值：道路数量或 `pass_cnt` 汇总

适合表达的结论：

- 热点道路是否明显单方向偏向

意义：

- 是最接近往届“道路流量统计”和“路况监测”的一张主表

---

## 3.8 `ads_region_hotspot_role_daily`

对应文件：

- `ads_output/ads_region_hotspot_role_daily.parquet`
- `preview/ads_region_hotspot_role_daily_preview.csv`

### 推荐图 21：热点区域 Top20 地图

图形类型：

- 地图散点图

字段使用：

- 经度：`grid_center_lon`
- 纬度：`grid_center_lat`
- 点大小：`total_od_trip_cnt`
- 点颜色：`grid_activity_level`
- 筛选：`rank_by_total_od <= 20`

适合表达的结论：

- 城市热点区域分布
- 热点是否集中在少数核心网格

### 推荐图 22：上车 / 下车热点图

图形类型：

- 双榜单或分组柱状图

字段使用：

- `rank_by_pickup`
- `rank_by_dropoff`
- `pickup_trip_cnt`
- `dropoff_trip_cnt`

适合表达的结论：

- 哪些区域更偏上车
- 哪些区域更偏下车

### 推荐图 23：区域角色分布图

图形类型：

- 饼图或柱状图

字段使用：

- 分类：`grid_role_bias`
- 值：区域数量或 `total_od_trip_cnt`

适合表达的结论：

- 热区更偏“出发区”还是“到达区”

意义：

- 是当前最稳妥的“商圈分析替代版”
- 没有真实商圈边界也能做出空间分析结果

---

## 4. 报告中最值得写的结论点

基于当前结果，报告部分最适合写的结论有：

1. 样本期覆盖 2015-01-03 到 2015-01-07，共 5 天，小时覆盖完整。
2. 每日活跃车辆数在 1.2 万左右波动，单日总 trip 数最高超过 28 万。
3. 高峰小时在不同日期存在差异，部分日期更偏下午 15-17 点，部分日期出现明显早高峰。
4. 道路热度存在明显头部集中，少数道路承担了大量通行事件。
5. 热点区域在空间上具有明显集中性，且部分区域呈现较平衡的 pickup / dropoff 结构。
6. 司机群体存在明显分层，可识别核心司机、满勤司机和不同活跃度群体。

---

## 5. 最推荐先做的图

如果时间有限，优先做这 6 张：

1. 每日活跃车辆数 / trip 数双轴图
2. 每小时 trip 趋势图
3. 每日 Top3 高峰小时图
4. 行程距离分层结构图
5. 热点道路 Top20 图
6. 热点区域 Top20 地图

这 6 张已经足够支撑一版完整的 ADS 展示页和报告主图。

---

## 6. 下一步建议

建议接下来的顺序是：

1. 先从 `preview/` 中看数据样例，确认图表字段是否符合预期
2. 确定最终展示的 6 到 8 张图
3. 与可视化同学对齐字段
4. 把最终图表清单写进报告提纲

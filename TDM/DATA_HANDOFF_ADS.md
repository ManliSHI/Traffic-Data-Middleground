# TDM 到 ADS 交付文档

## 1. 文档目的

本文档面向负责“4、应用数据层 ADS”的同学，说明当前已经完成的 **TDM 标签层** 产物可以如何被直接消费，支撑业务统计指标开发。

ADS 层的职责是：

- 围绕业务问题产出可直接展示、接口返回或报表使用的统计指标
- 例如：车辆数量、平均速度、高峰时段车流量、热点路段、活跃区域、异常车辆数量等

本文件重点回答以下问题：

1. TDM 层已经产出了什么
2. 每张表的粒度、主键、字段口径分别是什么
3. 做 ADS 指标时，应该优先从哪张表取数
4. 哪些指标已经可以直接算，哪些指标需要 ADS 再做二次定义
5. 哪些口径不能改，哪些地方容易踩坑

---

## 2. 交付范围

### 2.1 上游输入

TDM 脚本读取的数据来源于清洗完成的 5 张 Parquet：

- `E:\cleaned_output_full_final\trips_clean.parquet`
- `E:\cleaned_output_full_final\gps_points_clean.parquet`
- `E:\cleaned_output_full_final\matched_segments_clean.parquet`
- `E:\cleaned_output_full_final\route_edges_clean.parquet`
- `E:\cleaned_output_full_final\route_geometries_clean.parquet`

说明：

- `route_geometries_clean.parquet` 本轮没有作为主实现依赖
- 原因是上游交接文档已明确提示 geometry 与 road 存在对齐风险
- 所以 ADS 层也不要把 geometry 作为当前版本的强依赖前提

### 2.2 TDM 交付物

TDM 层交付目录：

- `E:\cleaned_output_full_final\tdm_output`

已生成文件：

- `tdm_trip_profile.parquet`
- `tdm_vehicle_day_profile.parquet`
- `tdm_vehicle_5d_profile.parquet`
- `tdm_vehicle_road_preference_5d.parquet`
- `tdm_road_day_profile.parquet`
- `tdm_time_slot_day_profile.parquet`
- `tdm_region_grid_day_profile.parquet`
- `tdm_tag_definition.csv`
- `tdm_build_summary.json`

### 2.3 构建脚本

TDM 构建脚本：

- `E:\cleaned_output_full_final\build_tdm_layer.py`

执行方式：

```powershell
cd E:\cleaned_output_full_final
python build_tdm_layer.py
```

---

## 3. 当前版本数据边界

### 3.1 时间范围

当前数据仅覆盖 5 天：

- `2015-01-03`
- `2015-01-04`
- `2015-01-05`
- `2015-01-06`
- `2015-01-07`

校验结果：

- `stat_date` 最小值：`2015-01-03`
- `stat_date` 最大值：`2015-01-07`
- `stat_date` distinct 数：`5`

### 3.2 时间小时覆盖

小时覆盖完整：

- `biz_hour` 最小值：`0`
- `biz_hour` 最大值：`23`
- `biz_hour` distinct 数：`24`

### 3.3 设备与对象规模

关键对象规模如下：

| 对象 | 行数 |
| --- | ---: |
| trip | 1,199,531 |
| vehicle_day | 55,265 |
| vehicle_5d | 12,472 |
| vehicle_road_preference_5d | 124,573 |
| road_day | 83,478 |
| time_slot_day | 120 |
| region_grid_day | 2,241 |

### 3.4 一些全局统计概览

这些值不是业务口径承诺，只是帮助 ADS 同学快速建立对数据分布的直觉：

| 指标 | 当前值 |
| --- | ---: |
| trip 总数 | 1,199,531 |
| 车辆数（5 天口径） | 12,472 |
| 平均单 trip 距离 | 9.1183 km |
| 平均单 trip 时长 | 25.6101 min |
| 平均单 trip 速度 | 20.7904 km/h |
| 高峰 trip 数 | 381,463 |
| 夜间 trip 数 | 178,933 |
| 每个 vehicle_day 平均 trip 数 | 21.7051 |
| 每个 vehicle_day 平均总里程 | 197.9124 km |
| 每个 vehicle_5d 平均总 trip 数 | 96.1779 |
| 每个 vehicle_5d 平均总里程 | 876.9748 km |
| road_day 平均通行次数 | 493.9819 |
| time_slot_day 平均 trip 数 | 9,996.0917 |
| time_slot_day 最大 trip 数 | 17,645 |
| region_grid_day 平均 OD 次数 | 1,070.5319 |

---

## 4. TDM 层统一业务口径

ADS 开发请严格继承以下口径，不要自行改写。

### 4.1 业务时间口径

不要直接把 GPS 时间当业务时间。

统一规则：

```text
有 matched 路段：
  业务时间 = matched_* 时间

无 matched 路段：
  业务时间 = gps_*_time_utc - 8 小时
```

即：

- `biz_start_time`
- `biz_end_time`
- `biz_start_hour`
- `biz_end_hour`

都已经在 TDM 层按统一规则算好。

### 4.2 统计日期口径

`stat_date` 不是从 GPS 时间截出来的，而是从 `source_file` 解析出来的业务日期。

例如：

- `trips_150103.jld2 -> 2015-01-03`
- `trips_150104.jld2 -> 2015-01-04`

这意味着：

- ADS 层做按天统计时，优先使用 `stat_date`
- 不要再自己从 `biz_start_time` 或 GPS 原始时间重新切天

### 4.3 时段分类口径

统一按 `biz_start_hour` 分类：

| time_period_type | 小时范围 |
| --- | --- |
| `night` | 22, 23, 0, 1, 2, 3, 4, 5 |
| `morning_peak` | 7, 8, 9 |
| `evening_peak` | 17, 18, 19 |
| `daytime` | 10, 11, 12, 13, 14, 15, 16 |
| `shoulder` | 6, 20, 21 |

对应布尔字段：

- `night_trip_flag`
- `morning_peak_trip_flag`
- `evening_peak_trip_flag`
- `peak_trip_flag`

### 4.4 距离和速度口径

距离基于相邻 GPS 点 haversine 计算，不依赖 geometry。

有效 step 条件：

- `point_is_valid = true`
- `delta_t_sec > 0`
- `delta_t_sec <= 180`
- `step_speed_kmh <= 100`

指标公式：

```text
trip_distance_km = sum(valid step_dist_km)
trip_duration_min = (gps_end_ts - gps_start_ts) / 60.0
avg_speed_kmh = trip_distance_km / (trip_duration_min / 60.0)
```

ADS 层如果展示“平均速度”，请优先沿用 TDM 已算好的：

- trip 级：`tdm_trip_profile.avg_speed_kmh`
- 车辆日级：`tdm_vehicle_day_profile.avg_speed_kmh`
- 车辆 5 日级：`tdm_vehicle_5d_profile.avg_speed_kmh`
- 小时级：`tdm_time_slot_day_profile.avg_speed_kmh`

不要重新从 GPS 原始点再扫一遍。

### 4.5 空间口径

当前没有真实 `district_id`。

因此本轮空间对象统一使用：

- `region_grid_day`

网格定义：

- `grid_size = 0.01` 度
- `grid_id = floor(lon / 0.01) || '_' || floor(lat / 0.01)`

OD 规则：

- `pickup = trip 第 1 个点`
- `dropoff = trip 最后 1 个点`

---

## 5. TDM 产物之间的关系

### 5.1 主对象链路

TDM 的主对象关系如下：

```text
trip
  -> vehicle_day
  -> vehicle_5d
  -> road_day
  -> time_slot_day
  -> region_grid_day
  -> vehicle_road_preference_5d
```

### 5.2 推荐理解方式

- `tdm_trip_profile`：最基础、最完整的单次出行画像表
- `tdm_vehicle_day_profile`：设备每天的聚合结果
- `tdm_vehicle_5d_profile`：设备 5 天累计聚合结果
- `tdm_vehicle_road_preference_5d`：设备偏好道路 Top10
- `tdm_road_day_profile`：道路每天被通行的统计结果
- `tdm_time_slot_day_profile`：每天每小时的时段统计结果
- `tdm_region_grid_day_profile`：每天每个空间网格的 OD 统计结果

### 5.3 ADS 取数优先级建议

对于大多数 ADS 统计，请遵循这个原则：

1. 优先用已经聚合好的 TDM 表
2. 只有在 TDM 表没有你要的最细粒度时，才回到 `tdm_trip_profile`
3. 不要为了简单指标再去扫 `gps_points_clean`、`matched_segments_clean` 这些大表

---

## 6. 各表详细说明

## 6.1 `tdm_trip_profile.parquet`

### 6.1.1 粒度与用途

粒度：

- `1 row = 1 trip`

主键：

- `trip_id`

主要用途：

- 做一切 trip 级分析
- 做车辆日聚合和车辆总聚合的基础来源
- 做按时段、按道路、按空间的二次映射来源

### 6.1.2 核心字段

| 字段名 | 类型 | 含义 | ADS 使用建议 |
| --- | --- | --- | --- |
| `trip_id` | varchar | trip 唯一标识 | 明细级主键 |
| `devid` | bigint | 设备编号 | 统计车辆数、设备聚合 |
| `source_file` | varchar | 来源原始文件 | 一般仅排查问题时使用 |
| `stat_date` | date | 业务统计日期 | 所有按天统计统一用它 |
| `biz_start_time` | timestamptz | 业务开始时间 | 需要展示精确开始时刻时使用 |
| `biz_end_time` | timestamptz | 业务结束时间 | 需要展示精确结束时刻时使用 |
| `biz_start_hour` | int | 业务开始小时 | 做小时维度统计时使用 |
| `biz_end_hour` | int | 业务结束小时 | 当前多用于补充说明 |
| `time_period_type` | varchar | 时段类型 | 用于高峰/夜间分类 |
| `point_count` | int | GPS 点数 | 质量观察字段 |
| `matched_segment_count` | int | 匹配路段数 | 质量观察字段 |
| `route_edge_count` | int | route edge 数 | 路线复杂度辅助字段 |
| `has_matched_segments` | bool | 是否有匹配路段 | 统计匹配率时使用 |
| `trip_duration_min` | double | trip 时长 | 做均值/总量/分段 |
| `trip_distance_km` | double | trip 距离 | 做均值/总量/分段 |
| `avg_speed_kmh` | double | trip 平均速度 | 做平均速度或异常速度识别 |
| `unique_road_cnt` | bigint | 唯一路段数 | 反映线路覆盖范围 |
| `road_repeat_ratio` | double | 路段重复率 | 反映路径是否重复绕行 |
| `forward_edge_cnt` | double | 正向边数 | 路线方向分析 |
| `backward_edge_cnt` | double | 反向边数 | 路线方向分析 |
| `forward_edge_ratio` | double | 正向占比 | 方向偏向判断 |
| `night_trip_flag` | bool | 夜间 trip 标记 | 夜间统计 |
| `morning_peak_trip_flag` | bool | 早高峰标记 | 高峰统计 |
| `evening_peak_trip_flag` | bool | 晚高峰标记 | 高峰统计 |
| `peak_trip_flag` | bool | 高峰标记 | 高峰统计 |
| `trip_distance_level` | varchar | 距离分层 | 分布分析、筛选 |
| `trip_duration_level` | varchar | 时长分层 | 分布分析、筛选 |
| `trip_speed_level` | varchar | 速度分层 | 快速分类分析 |

### 6.1.3 什么时候应该用这张表

适合：

- 统计某天总出行次数
- 统计某天高峰 trip 数
- 统计某设备日均出行速度
- 统计夜间出行占比
- 给 ADS 再做异常规则打标

不适合：

- 直接统计某道路被多少辆车经过
- 直接统计每小时的全局流量
- 直接统计某区域 pickup / dropoff 热度

这些场景优先用已经聚合好的：

- `tdm_road_day_profile`
- `tdm_time_slot_day_profile`
- `tdm_region_grid_day_profile`

---

## 6.2 `tdm_vehicle_day_profile.parquet`

### 6.2.1 粒度与用途

粒度：

- `1 row = 1 devid + 1 stat_date`

主键：

- `devid`
- `stat_date`

主要用途：

- 按天看每辆车的行为
- 做车辆数量、平均速度、活跃车辆数、夜间活跃车辆数
- 做 ADS 的日统计看板、日报表

### 6.2.2 核心字段

| 字段名 | 含义 | ADS 常见用途 |
| --- | --- | --- |
| `trip_cnt` | 当天 trip 数 | 日车辆活跃度、车均单量 |
| `matched_trip_cnt` | 当天有匹配 trip 数 | 地图匹配成功量 |
| `matched_trip_ratio` | 当天匹配 trip 占比 | 质量指标、异常匹配设备识别 |
| `total_distance_km` | 当天总里程 | 车均里程、总运力 |
| `total_duration_min` | 当天总时长 | 在线时长、运转时长 |
| `avg_trip_distance_km` | 平均单次里程 | 订单结构分析 |
| `avg_trip_duration_min` | 平均单次时长 | 行程效率分析 |
| `avg_speed_kmh` | 当天综合平均速度 | 车辆速度指标 |
| `active_hour_cnt` | 活跃小时数 | 在线活跃时长分布 |
| `road_coverage_cnt` | 当天覆盖道路数 | 作业范围/覆盖面 |
| `night_trip_cnt` | 夜间 trip 数 | 夜间运营分析 |
| `night_trip_ratio` | 夜间占比 | 夜间活跃车辆数 |
| `morning_peak_trip_cnt` | 早高峰 trip 数 | 早高峰参与车辆统计 |
| `evening_peak_trip_cnt` | 晚高峰 trip 数 | 晚高峰参与车辆统计 |
| `peak_trip_cnt` | 高峰 trip 数 | 高峰运营强度 |
| `peak_trip_ratio` | 高峰占比 | 高峰偏向分析 |
| `dominant_time_period` | 当天主导时段 | 车辆运营类型粗分类 |
| `trip_frequency_level` | 当天出行频次分层 | 高活跃车辆数 |
| `night_activity_flag` | 夜间活跃标记 | 直接统计夜间活跃车数 |
| `peak_activity_flag` | 高峰活跃标记 | 直接统计高峰活跃车数 |

### 6.2.3 这张表最适合做什么 ADS 指标

直接适合：

- 每日活跃车辆数
- 每日总 trip 数
- 每日车均 trip 数
- 每日总里程
- 每日平均速度
- 每日夜间活跃车辆数
- 每日高峰活跃车辆数
- 每日高频车辆数

### 6.2.4 示例

如果业务要“每天有多少活跃车辆”，直接对这张表按天 `count(*)` 即可。

如果业务要“每天夜间活跃车辆数”，直接按天统计：

- `night_activity_flag = true`

如果业务要“每天平均车均速度”，可以有两种口径：

1. 先按车日算好，再按天平均 `avg_speed_kmh`
2. 按天汇总 `sum(total_distance_km) / sum(total_duration_min/60)`

建议：

- 业务看板展示“车均平均速度”时用第 1 种
- 业务看板展示“全局整体平均速度”时用第 2 种

---

## 6.3 `tdm_vehicle_5d_profile.parquet`

### 6.3.1 粒度与用途

粒度：

- `1 row = 1 devid`

主键：

- `devid`

主要用途：

- 做 5 天累计车辆画像
- 做司机/车辆分类
- 做核心车辆识别、满勤车辆识别

### 6.3.2 核心字段

| 字段名 | 含义 | ADS 常见用途 |
| --- | --- | --- |
| `active_day_cnt` | 活跃天数 | 出勤情况 |
| `total_trip_cnt` | 五天总 trip 数 | 总活跃度 |
| `avg_daily_trip_cnt` | 日均 trip 数 | 运营强度 |
| `total_distance_km` | 五天总里程 | 总运力 |
| `total_duration_min` | 五天总时长 | 总作业时长 |
| `avg_trip_distance_km` | 平均单次里程 | 行程结构 |
| `avg_speed_kmh` | 五天综合平均速度 | 速度画像 |
| `night_trip_ratio_5d` | 五天夜间占比 | 夜班偏向 |
| `peak_trip_ratio_5d` | 五天高峰占比 | 高峰偏向 |
| `road_coverage_cnt_5d` | 五天覆盖道路数 | 覆盖范围 |
| `dominant_time_period_5d` | 五天主导时段 | 行为偏好 |
| `driver_activity_level` | 活跃度等级 | 司机分层 |
| `core_driver_flag` | 核心司机标记 | 核心运力数量 |
| `full_attendance_flag` | 满勤标记 | 满勤数量 |

### 6.3.3 这张表最适合做什么 ADS 指标

- 核心车辆数
- 满勤车辆数
- 司机活跃度结构分布
- 五天累计总里程分布
- 高峰偏向车辆数
- 夜间偏向车辆数

### 6.3.4 对 ADS 的价值

ADS 层如果要做“车辆分层经营画像”，优先从这张表出，不要自己再从 trip 明细重新聚合 5 天口径。

---

## 6.4 `tdm_vehicle_road_preference_5d.parquet`

### 6.4.1 粒度与用途

粒度：

- `1 row = 1 devid + 1 road_id`

限制：

- 仅保留每个设备 Top10 高频道路

主键：

- `devid`
- `road_id`

主要用途：

- 看车辆偏好道路
- 做车辆常走路线 TopN
- 做个体运营轨迹偏好分析

### 6.4.2 核心字段

| 字段名 | 含义 |
| --- | --- |
| `devid` | 设备编号 |
| `road_id` | 道路编号 |
| `rank_in_device` | 设备内排名 |
| `pass_cnt` | 五天通行次数 |
| `pass_ratio` | 占设备全部有效路段通行的比例 |
| `active_day_cnt_on_road` | 在该道路上活跃的天数 |
| `preference_level` | `core_route` / `frequent_route` |

### 6.4.3 注意事项

这张表不是全量“设备-道路关系表”，而是 **Top10 偏好道路表**。

所以：

- 可以做“设备最常走道路”
- 可以做“Top 道路偏好画像”
- 不适合做“某道路真实全量覆盖了多少设备”

后者应使用：

- `tdm_road_day_profile`

---

## 6.5 `tdm_road_day_profile.parquet`

### 6.5.1 粒度与用途

粒度：

- `1 row = 1 road_id + 1 stat_date`

主键：

- `road_id`
- `stat_date`

主要用途：

- 做道路通行统计
- 做热点道路、活跃道路、高峰道路
- 做方向偏向分析

### 6.5.2 核心字段

| 字段名 | 含义 | ADS 常见用途 |
| --- | --- | --- |
| `pass_cnt` | 路段通行次数 | 路段流量 |
| `vehicle_cnt` | 通行车辆数 | 路段车辆覆盖 |
| `trip_cnt` | 涉及 trip 数 | 路段订单/行程数 |
| `morning_peak_pass_cnt` | 早高峰通行次数 | 早高峰道路榜单 |
| `evening_peak_pass_cnt` | 晚高峰通行次数 | 晚高峰道路榜单 |
| `night_pass_cnt` | 夜间通行次数 | 夜间道路活跃度 |
| `peak_pass_ratio` | 高峰占比 | 高峰敏感路段 |
| `forward_edge_cnt` | 正向边数 | 正向通行结构 |
| `backward_edge_cnt` | 反向边数 | 反向通行结构 |
| `forward_ratio` | 正向占比 | 方向偏向判断 |
| `direction_bias` | 方向偏向类型 | 展示 mainly_forward / mainly_backward / balanced |
| `road_activity_level` | 道路活跃度分层 | 热门道路数量 |
| `peak_bias_type` | 时段偏向类型 | 早高峰型 / 晚高峰型 / 夜间型 / 平峰型 |

### 6.5.3 这张表最适合做什么 ADS 指标

- 每天道路通行次数 TopN
- 每天道路通行车辆数 TopN
- 高峰热点道路 TopN
- 夜间活跃道路 TopN
- 道路方向偏向分布
- 热门道路数量

### 6.5.4 重要提醒

`pass_cnt` 的含义是 **valid matched segments 的计数**，不是“物理车流绝对值”，更接近“匹配路段通行事件次数”。

因此如果业务说“车流量”，你需要先和产品/业务确认它是指：

1. 路段通行事件数
2. 路段独立车辆数
3. 路段独立 trip 数

这三种口径分别对应：

- `pass_cnt`
- `vehicle_cnt`
- `trip_cnt`

---

## 6.6 `tdm_time_slot_day_profile.parquet`

### 6.6.1 粒度与用途

粒度：

- `1 row = 1 stat_date + 1 biz_hour`

主键：

- `stat_date`
- `biz_hour`

辅助键：

- `time_range_id = YYYY-MM-DD_HH`

主要用途：

- 做每小时全局流量趋势
- 做高峰时段统计
- 做小时级速度、里程、车辆数统计

### 6.6.2 核心字段

| 字段名 | 含义 | ADS 常见用途 |
| --- | --- | --- |
| `time_range_id` | 小时粒度主键 | 对接前端图表 |
| `stat_date` | 日期 | 日维度过滤 |
| `biz_hour` | 小时 | 小时趋势 |
| `time_period_type` | 小时所属时段类型 | 高峰/夜间分组 |
| `trip_cnt` | 小时 trip 数 | 小时车流量 |
| `matched_trip_cnt` | 小时匹配 trip 数 | 小时匹配量 |
| `vehicle_cnt` | 小时活跃车辆数 | 小时在线车辆数 |
| `total_distance_km` | 小时总里程 | 运力强度 |
| `total_duration_min` | 小时总时长 | 运转强度 |
| `avg_trip_distance_km` | 小时平均单次里程 | 小时结构分析 |
| `avg_trip_duration_min` | 小时平均单次时长 | 小时结构分析 |
| `avg_speed_kmh` | 小时综合平均速度 | 小时速度趋势 |
| `road_coverage_cnt` | 小时覆盖道路数 | 活跃范围 |
| `slot_activity_level` | 小时活跃度等级 | 热点小时数量 |

### 6.6.3 这张表最适合做什么 ADS 指标

- 每天每小时 trip 趋势图
- 每天每小时活跃车辆数
- 高峰时段车流量
- 每小时平均速度趋势
- 热门小时数量

### 6.6.4 当前数据里的一些直观现象

按当前样本数据：

- 全部 `time_slot_day` 共 `120` 行，正好是 `5 天 * 24 小时`
- 单小时最大 `trip_cnt = 17,645`

每个日期 trip 数 Top3 小时如下：

| stat_date | Top 小时 1 | Top 小时 2 | Top 小时 3 |
| --- | --- | --- | --- |
| 2015-01-03 | 15 点: 9658 | 13 点: 9524 | 10 点: 9470 |
| 2015-01-04 | 15 点: 17645 | 16 点: 17578 | 17 点: 17404 |
| 2015-01-05 | 17 点: 17095 | 16 点: 17051 | 15 点: 16955 |
| 2015-01-06 | 8 点: 16706 | 10 点: 16518 | 9 点: 16444 |
| 2015-01-07 | 17 点: 15482 | 16 点: 15446 | 15 点: 15170 |

这类信息已经很适合 ADS 做“高峰窗口识别”和“小时趋势图”。

---

## 6.7 `tdm_region_grid_day_profile.parquet`

### 6.7.1 粒度与用途

粒度：

- `1 row = 1 stat_date + 1 grid_id`

主键：

- `stat_date`
- `grid_id`

主要用途：

- 做空间热点区域分析
- 做 pickup / dropoff 偏向区域统计
- 做热点网格 TopN

### 6.7.2 核心字段

| 字段名 | 含义 | ADS 常见用途 |
| --- | --- | --- |
| `grid_id` | 网格编号 | 区域主键 |
| `stat_date` | 日期 | 日期过滤 |
| `grid_center_lon` | 中心经度 | 地图打点 |
| `grid_center_lat` | 中心纬度 | 地图打点 |
| `pickup_trip_cnt` | 上车次数 | 上车热点 |
| `dropoff_trip_cnt` | 下车次数 | 下车热点 |
| `total_od_trip_cnt` | 总 OD 次数 | 综合活跃度 |
| `active_vehicle_cnt` | 活跃车辆数 | 区域运力覆盖 |
| `night_od_trip_cnt` | 夜间 OD 次数 | 夜间热点区域 |
| `peak_od_trip_cnt` | 高峰 OD 次数 | 高峰热点区域 |
| `pickup_ratio` | 上车占比 | 网格角色判断 |
| `grid_role_bias` | pickup/dropoff 偏向 | 区域功能判别 |
| `grid_activity_level` | 网格活跃度等级 | 热点区域数 |

### 6.7.3 当前版本说明

当前有效 grid 总数：

- `469`

当前是规则网格，不是真实商圈或行政区。

所以：

- 可以做“热点区域”
- 可以做“上车热点/下车热点”
- 不建议直接对外宣传为“商圈”或“行政区”

### 6.7.4 当前数据中 grid 分层分布

| grid_activity_level | 行数 |
| --- | ---: |
| `active` | 562 |
| `hotspot` | 561 |
| `normal` | 561 |
| `long_tail` | 557 |

---

## 7. 标签定义文件说明

文件：

- `tdm_tag_definition.csv`

作用：

- 记录每个画像表中每个衍生标签的中文名、英文 code、口径、来源表、刷新周期

当前记录数：

- `96`

如果 ADS 同学不确定某个字段的业务含义，建议先查这个文件，再看本 handoff 文档。

---

## 8. ADS 指标推荐映射

下面按常见业务需求，给出“优先用哪张 TDM 表”的建议。

| 业务指标 | 推荐来源表 | 推荐字段/口径 |
| --- | --- | --- |
| 每日活跃车辆数 | `tdm_vehicle_day_profile` | `count(*) by stat_date` |
| 每日总 trip 数 | `tdm_vehicle_day_profile` 或 `tdm_trip_profile` | `sum(trip_cnt)` 或 `count(*)` |
| 每日平均速度 | `tdm_vehicle_day_profile` | 车均口径用 `avg(avg_speed_kmh)`；整体口径用 `sum(total_distance_km)/sum(total_duration_min/60)` |
| 每日总里程 | `tdm_vehicle_day_profile` | `sum(total_distance_km)` |
| 高峰时段车流量 | `tdm_time_slot_day_profile` | `trip_cnt` 或按 `time_period_type in (...)` 汇总 |
| 每小时活跃车辆数 | `tdm_time_slot_day_profile` | `vehicle_cnt` |
| 道路 TopN 热点 | `tdm_road_day_profile` | `pass_cnt` / `vehicle_cnt` / `trip_cnt` |
| 夜间热点道路 | `tdm_road_day_profile` | `night_pass_cnt` |
| 高峰热点道路 | `tdm_road_day_profile` | `morning_peak_pass_cnt + evening_peak_pass_cnt` |
| 热点区域 TopN | `tdm_region_grid_day_profile` | `total_od_trip_cnt` |
| 上车热点区域 | `tdm_region_grid_day_profile` | `pickup_trip_cnt` |
| 下车热点区域 | `tdm_region_grid_day_profile` | `dropoff_trip_cnt` |
| 夜间活跃车辆数 | `tdm_vehicle_day_profile` | `count(*) where night_activity_flag = true` |
| 高峰活跃车辆数 | `tdm_vehicle_day_profile` | `count(*) where peak_activity_flag = true` |
| 核心车辆数 | `tdm_vehicle_5d_profile` | `count(*) where core_driver_flag = true` |
| 满勤车辆数 | `tdm_vehicle_5d_profile` | `count(*) where full_attendance_flag = true` |
| 车辆偏好道路 TopN | `tdm_vehicle_road_preference_5d` | `rank_in_device <= N` |

---

## 9. “异常车辆数量”如何做

### 9.1 先说明一件事

当前 TDM 层 **没有固化输出一个叫“abnormal_vehicle_flag”** 的最终标签。

这是有意为之。

原因是：

- “异常车辆”属于强业务定义
- 不同业务场景对异常的理解完全不同
- 如果在 TDM 直接固定，会让后续 ADS 很难改

因此 TDM 当前提供的是：

- 可复用的稳定基础特征
- 由 ADS 或更上层根据业务规则组合成异常定义

### 9.2 ADS 可以直接用的异常候选特征

最适合做异常判断的来源表：

- `tdm_vehicle_day_profile`
- `tdm_vehicle_5d_profile`
- `tdm_trip_profile`

可用字段包括：

- `matched_trip_ratio`
- `avg_speed_kmh`
- `trip_cnt`
- `night_trip_ratio`
- `peak_trip_ratio`
- `road_coverage_cnt`
- `driver_activity_level`
- `trip_speed_level`
- `road_repeat_ratio`

### 9.3 推荐的异常定义方式

下面给出几个可落地的 ADS 规则例子。

#### 方案 A：匹配异常车辆

定义思路：

- 当天 `matched_trip_ratio` 很低，说明轨迹或匹配质量异常

示例：

```text
matched_trip_ratio < 0.50
```

来源表：

- `tdm_vehicle_day_profile`

#### 方案 B：高速异常车辆

定义思路：

- 车日级平均速度过高，可能存在数据噪声或极端行为

示例：

```text
avg_speed_kmh > 40
```

来源表：

- `tdm_vehicle_day_profile`

或者更细粒度：

- `tdm_trip_profile` 中统计 `trip_speed_level = 'very_fast'` 的 trip 数

#### 方案 C：夜间高活跃异常车辆

定义思路：

- 夜间占比高且出行频次高

示例：

```text
night_activity_flag = true
AND trip_frequency_level IN ('high', 'very_high')
```

来源表：

- `tdm_vehicle_day_profile`

#### 方案 D：覆盖范围异常大车辆

定义思路：

- 短时间覆盖过多道路，可能是异常设备或特殊运营车辆

示例：

```text
road_coverage_cnt > 某业务阈值
AND trip_cnt > 某业务阈值
```

来源表：

- `tdm_vehicle_day_profile`

#### 方案 E：5 日核心高强度车辆

定义思路：

- 用于识别持续高强度运营车辆，不一定是负向异常，但通常是业务关注对象

示例：

```text
core_driver_flag = true
AND full_attendance_flag = true
```

来源表：

- `tdm_vehicle_5d_profile`

### 9.4 建议

如果 ADS 要对外输出“异常车辆数量”，请务必在需求文档中补充：

1. 异常的业务定义
2. 使用的时间窗口
3. 是否允许多规则并列
4. 是否区分质量异常 / 行为异常 / 强运营异常

否则最终数字虽然能算出来，但业务上会很难解释。

---

## 10. 推荐 SQL 模板

以下 SQL 均可直接在 DuckDB 上跑，主要用于帮助 ADS 同学快速起步。

## 10.1 每日活跃车辆数

```sql
SELECT
    stat_date,
    COUNT(*) AS active_vehicle_cnt
FROM read_parquet('E:/cleaned_output_full_final/tdm_output/tdm_vehicle_day_profile.parquet')
GROUP BY stat_date
ORDER BY stat_date;
```

## 10.2 每日整体平均速度

```sql
SELECT
    stat_date,
    SUM(total_distance_km) / SUM(total_duration_min / 60.0) AS global_avg_speed_kmh
FROM read_parquet('E:/cleaned_output_full_final/tdm_output/tdm_vehicle_day_profile.parquet')
WHERE total_duration_min > 0
GROUP BY stat_date
ORDER BY stat_date;
```

## 10.3 每日车均平均速度

```sql
SELECT
    stat_date,
    AVG(avg_speed_kmh) AS avg_vehicle_speed_kmh
FROM read_parquet('E:/cleaned_output_full_final/tdm_output/tdm_vehicle_day_profile.parquet')
GROUP BY stat_date
ORDER BY stat_date;
```

## 10.4 每日高峰时段车流量

```sql
SELECT
    stat_date,
    SUM(trip_cnt) AS peak_trip_cnt
FROM read_parquet('E:/cleaned_output_full_final/tdm_output/tdm_time_slot_day_profile.parquet')
WHERE time_period_type IN ('morning_peak', 'evening_peak')
GROUP BY stat_date
ORDER BY stat_date;
```

## 10.5 每小时车流量趋势

```sql
SELECT
    stat_date,
    biz_hour,
    trip_cnt,
    vehicle_cnt,
    avg_speed_kmh
FROM read_parquet('E:/cleaned_output_full_final/tdm_output/tdm_time_slot_day_profile.parquet')
ORDER BY stat_date, biz_hour;
```

## 10.6 每日热点道路 Top20

```sql
SELECT
    stat_date,
    road_id,
    pass_cnt,
    vehicle_cnt,
    trip_cnt
FROM read_parquet('E:/cleaned_output_full_final/tdm_output/tdm_road_day_profile.parquet')
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY stat_date
    ORDER BY pass_cnt DESC, road_id ASC
) <= 20
ORDER BY stat_date, pass_cnt DESC, road_id ASC;
```

## 10.7 每日热点区域 Top20

```sql
SELECT
    stat_date,
    grid_id,
    grid_center_lon,
    grid_center_lat,
    total_od_trip_cnt
FROM read_parquet('E:/cleaned_output_full_final/tdm_output/tdm_region_grid_day_profile.parquet')
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY stat_date
    ORDER BY total_od_trip_cnt DESC, grid_id ASC
) <= 20
ORDER BY stat_date, total_od_trip_cnt DESC, grid_id ASC;
```

## 10.8 每日异常车辆数量示例

以下示例仅是 ADS 的一个候选实现，不是 TDM 固定标准。

```sql
SELECT
    stat_date,
    COUNT(*) AS abnormal_vehicle_cnt
FROM read_parquet('E:/cleaned_output_full_final/tdm_output/tdm_vehicle_day_profile.parquet')
WHERE matched_trip_ratio < 0.5
   OR avg_speed_kmh > 40
   OR (
       night_activity_flag = TRUE
       AND trip_frequency_level IN ('high', 'very_high')
   )
GROUP BY stat_date
ORDER BY stat_date;
```

---

## 11. 开发建议

### 11.1 大多数 ADS 不需要回扫原始大表

请优先使用 TDM 产出的 7 张表。

原因：

- 它们已经统一了时间口径
- 已经统一了时段口径
- 已经统一了距离和速度口径
- 已经把原来 5000 万 GPS 点和 4700 万 matched segment 压缩成更适合消费的对象表

### 11.2 指标定义要先确认“对象粒度”

同样叫“平均速度”，可能有至少 4 种含义：

1. trip 平均速度
2. 车日平均速度
3. 小时全局平均速度
4. 路段平均通行速度

当前 TDM 已直接支持前 3 种。

第 4 种“路段平均通行速度”当前没有单独构造，因为本轮没有构建可靠的 segment 级速度口径。

### 11.3 指标解释要尽量贴近实际口径

例如“高峰车流量”：

- 如果用 `tdm_time_slot_day_profile.trip_cnt`，本质是“高峰小时 trip 数”
- 如果用 `tdm_road_day_profile.pass_cnt`，本质是“高峰路段通行事件数”

这两者不能混说。

### 11.4 对外展示要注意词汇

当前 `region_grid_day` 是规则网格，不是商圈。

建议文案：

- “热点区域”
- “热点网格”
- “活跃区域”

不建议文案：

- “商圈”
- “行政区”
- “片区聚类”

---

## 12. 已完成校验

本轮 TDM 已完成以下规则校验，ADS 可直接复用结果：

- `stat_date` 与 `source_file` 一致
- `biz_start_time` 优先使用 `matched_*`
- 无匹配 trip 回退到 `gps - 8h`
- `trip_distance_km >= 0`
- `avg_speed_kmh >= 0`
- 活跃度等级字段不为空

构建摘要详见：

- `E:\cleaned_output_full_final\tdm_output\tdm_build_summary.json`

---

## 13. 已知限制与后续扩展

### 13.1 当前版本未做的内容

- 未引入道路静态属性，如道路名称、等级、是否高架
- 未引入真实行政区或商圈边界
- 未构造稳定可解释的道路拥堵指数
- 未基于 geometry 做复杂空间分析
- 未固化“异常车辆”的唯一业务定义

### 13.2 后续若有新增输入，可扩展方向

- 有道路静态属性后，可做“主干道/支路/高架”维度 ADS
- 有真实区域边界后，可把 `grid_id` 升级到 `district_id`
- 有 POI / 商圈后，可做“区域功能类型”指标
- 有更稳定的 segment 级时间/长度口径后，可做道路速度与拥堵分析

---

## 14. 交付建议结论

如果 ADS 同学现在就要开工，最推荐的使用策略是：

1. 日统计指标从 `tdm_vehicle_day_profile` 出
2. 5 日车辆画像从 `tdm_vehicle_5d_profile` 出
3. 高峰/小时趋势从 `tdm_time_slot_day_profile` 出
4. 热点道路从 `tdm_road_day_profile` 出
5. 热点区域从 `tdm_region_grid_day_profile` 出
6. 异常车辆数量由 ADS 基于 `vehicle_day` 或 `vehicle_5d` 再定义
7. 不要重新回扫 GPS 大表，除非确实有 TDM 没覆盖的新需求

这套 TDM 已经足够支撑一个规范的 ADS 第一版。

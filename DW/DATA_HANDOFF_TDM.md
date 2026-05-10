# JLD2 清洗结果交接文档

## 1. 文档目的

本文档用于说明 `E:\jld2_files\cleaned_output_full_final` 目录下清洗结果的来源、处理过程、清洗规则、输出文件结构、字段含义，以及面向下一位同学进行标签数据层 TDM 开发时的对接建议。

下一位同学负责：

- 基于数仓层数据设计标签体系
- 计算交通行为相关标签，例如平均速度、出行频率、夜间活跃度、高峰出行次数等

## 2. 数据来源

原始输入文件位于 `E:\jld2_files`：

- `trips_150103.jld2`
- `trips_150104.jld2`
- `trips_150105.jld2`
- `trips_150106.jld2`
- `trips_150107.jld2`

原始文件总大小约 `19.55 GB`。

原始 `JLD2` 文件不是普通二维表，而是 Julia/JLD2 序列化后的对象结构。主数据集为 `trips`，每个 trip 内部再引用多个字段对象，核心字段包括：

- `lon`, `lat`, `tms`：原始 GPS 点
- `devid`：设备编号
- `roads`, `time`, `frac`：地图匹配后的路段级结果
- `route`, `route_heading`, `route_geom`：路线级结果

## 3. 结果文件怎么来的

清洗脚本：

- `clean_jld2_trips.py`

最终结果目录：

- `E:\cleaned_output_full_final`

执行逻辑概述：

1. 使用 `h5py` 直接读取 `JLD2` 文件中的 `trips` 数据集
2. 对每个 trip 解引用内部字段对象
3. 将原始嵌套结构展开为标准化明细表
4. 对时间、数值、缺失值、异常值进行统一处理
5. 使用 `Parquet + snappy` 压缩分块写出
6. 生成一份全量清洗报告 `cleaning_report.json`

本次不是“原始二进制拷贝”，而是“语义完整保留 + 结构重建”。

## 4. 本次做了什么

### 4.1 数据读取与结构展开

将原始 JLD2 的对象嵌套结构拆解为 5 张标准化表：

- trip 级主表
- GPS 点级表
- matched segment 级表
- route edge 级表
- route geometry 级表

### 4.2 异常值处理

已检查并统一标记以下问题：

- 经纬度越界
- 非有限数值
- 点级数组长度不一致
- 匹配级数组长度不一致
- 时间非单调
- `frac` 超出 `[0, 1]`
- `route_geom` 与 `roads` 长度关系不一致

### 4.3 缺失值处理

- 空匹配 trip 保留在主表中
- 无法可靠映射的 geometry 不强行补齐，而是置空并标记
- 缺失时间、缺失比例值统一按空值处理

### 4.4 时间字段规范

时间统一保留两套表示：

- 原始秒值字段
- UTC 时间字段

例如：

- `gps_start_ts` + `gps_start_time_utc`
- `match_ts` + `match_time_utc`

### 4.5 数据结构统一

- 所有表统一使用 `snake_case`
- 所有主键关联统一使用 `trip_id`
- 所有文件统一为 `Parquet`
- 文本字段统一转成字符串
- 数值字段统一为整数/浮点型

## 5. 清洗结果摘要

来源：

- `E:\cleaned_output_full_final\cleaning_report.json`

全量结果如下：

- 总 trip 数：`1,199,531`
- 有效 trip 数：`1,199,531`
- 无效 trip 数：`0`
- 空匹配 trip 数：`4,087`
- GPS 点总数：`50,781,857`
- matched segment 总数：`47,168,898`
- route edge 总数：`94,413,556`
- route geometry 总数：`45,901,643`

异常统计：

- `frac_missing = 0`
- `frac_out_of_range = 0`
- `point_length_mismatch = 0`
- `matched_length_mismatch = 0`
- `coord_out_of_range = 0`
- `non_finite_coord = 0`
- `non_finite_time = 0`
- `non_monotonic_time = 0`
- `route_geom_length_mismatch = 61,878`

分布统计：

- 每个 trip 的点数中位数：`23`
- 每个 trip 的点数 P95：`145`
- 每个 trip 的 matched segment 数中位数：`22`
- 每个 trip 的 matched segment 数 P95：`135`

## 6. 为什么拆成 5 张表，而不是 1 张表

原始数据天然存在多种粒度：

- 1 个 trip 对应多个 GPS 点
- 1 个 trip 对应多个 matched segment
- 1 个 trip 对应多个 route edge
- 1 个 trip 对应多个 route geometry

如果强行存成 1 张平面表，会有两个问题：

- 要么把点、路段、几何都塞成数组列，不利于分析和数仓开发
- 要么把不同层级互相展开，形成大量重复和数据爆炸

因此这里采用标准化拆表，使用 `trip_id` 做关联。这更适合数仓层和标签层建设。

## 7. 输出文件清单

### 7.1 trips_clean.parquet

路径：

- `E:\cleaned_output_full_final\trips_clean.parquet`

规模：

- 行数：`1,199,531`
- 列数：`21`
- 文件大小：约 `72 MB`

粒度：

- 一行表示一个 trip

字段说明：

| 字段名 | 类型 | 含义 |
| --- | --- | --- |
| `source_file` | string | 来源原始文件名 |
| `trip_id` | string | trip 唯一标识，格式为 `source_file:trip_index` |
| `devid` | int64 | 设备编号 |
| `point_count` | int32 | 原始 GPS 点数 |
| `matched_segment_count` | int32 | 地图匹配后的路段数 |
| `route_edge_count` | int32 | 路线边数 |
| `gps_start_ts` | int64 | 原始 GPS 起始时间戳，秒 |
| `gps_end_ts` | int64 | 原始 GPS 结束时间戳，秒 |
| `gps_start_time_utc` | timestamp | 原始 GPS 起始 UTC 时间 |
| `gps_end_time_utc` | timestamp | 原始 GPS 结束 UTC 时间 |
| `matched_start_ts` | int64 | 匹配结果起始时间戳，秒 |
| `matched_end_ts` | int64 | 匹配结果结束时间戳，秒 |
| `matched_start_time_utc` | timestamp | 匹配结果起始 UTC 时间 |
| `matched_end_time_utc` | timestamp | 匹配结果结束 UTC 时间 |
| `has_matched_segments` | bool | 是否存在匹配路段 |
| `is_valid_trip` | bool | trip 是否通过本轮规则校验 |
| `invalid_reason` | string | trip 异常原因，多值时以 `;` 连接 |
| `lon_min` | float64 | 轨迹最小经度 |
| `lon_max` | float64 | 轨迹最大经度 |
| `lat_min` | float64 | 轨迹最小纬度 |
| `lat_max` | float64 | 轨迹最大纬度 |

主要用途：

- trip 级质量控制
- 出行次数统计
- 出行时段统计
- 设备级聚合

### 7.2 gps_points_clean.parquet

路径：

- `E:\cleaned_output_full_final\gps_points_clean.parquet`

规模：

- 行数：`50,781,857`
- 列数：`10`
- 文件大小：约 `512 MB`

粒度：

- 一行表示一个原始 GPS 点

字段说明：

| 字段名 | 类型 | 含义 |
| --- | --- | --- |
| `source_file` | string | 来源原始文件名 |
| `trip_id` | string | 所属 trip 唯一标识 |
| `devid` | int64 | 设备编号 |
| `point_index` | int32 | 在该 trip 内的点序号，从 0 开始 |
| `lon` | float64 | 经度 |
| `lat` | float64 | 纬度 |
| `tms` | int64 | 原始点时间戳，秒 |
| `gps_time_utc` | timestamp | 原始点 UTC 时间 |
| `point_is_valid` | bool | 点是否通过本轮规则校验 |
| `point_invalid_reason` | string | 点异常原因 |

主要用途：

- 轨迹级速度、间隔、停留计算
- 时间窗口标签
- 空间轨迹分析

### 7.3 matched_segments_clean.parquet

路径：

- `E:\cleaned_output_full_final\matched_segments_clean.parquet`

规模：

- 行数：`47,168,898`
- 列数：`13`
- 文件大小：约 `3.93 GB`

粒度：

- 一行表示一个地图匹配后的 segment

字段说明：

| 字段名 | 类型 | 含义 |
| --- | --- | --- |
| `source_file` | string | 来源原始文件名 |
| `trip_id` | string | 所属 trip 唯一标识 |
| `devid` | int64 | 设备编号 |
| `segment_index` | int32 | 在该 trip 内的路段序号，从 0 开始 |
| `road_id` | int64 | 匹配到的道路 ID |
| `match_ts` | int64 | 匹配时间戳，秒 |
| `match_time_utc` | timestamp | 匹配 UTC 时间 |
| `frac` | float64 | 在该道路上的相对位置比例 |
| `frac_clipped` | float64 | 裁剪到 `[0, 1]` 后的比例值 |
| `is_frac_imputed` | bool | 是否为插补比例值，本批均为 `False` |
| `route_geom_wkt` | string | 若可可靠对齐，则写入对应 geometry，格式为 WKT |
| `segment_is_valid` | bool | 路段记录是否通过校验 |
| `segment_invalid_reason` | string | 路段异常原因 |

主要用途：

- 按道路统计通行次数
- 高峰期道路活跃度
- 设备道路访问特征
- 道路序列特征

### 7.4 route_edges_clean.parquet

路径：

- `E:\cleaned_output_full_final\route_edges_clean.parquet`

规模：

- 行数：`94,413,556`
- 列数：`8`
- 文件大小：约 `225 MB`

粒度：

- 一行表示一个 route edge

字段说明：

| 字段名 | 类型 | 含义 |
| --- | --- | --- |
| `source_file` | string | 来源原始文件名 |
| `trip_id` | string | 所属 trip 唯一标识 |
| `devid` | int64 | 设备编号 |
| `route_index` | int32 | 在该 trip 内的路线边序号 |
| `route_road_id` | int64 | 路线边道路 ID |
| `route_heading` | string | 行驶方向，例如 `forward` / `backward` |
| `route_edge_is_valid` | bool | 路线边记录是否有效 |
| `route_edge_invalid_reason` | string | 路线边异常原因 |

主要用途：

- 路线结构标签
- 方向性分析
- 路径复杂度特征

### 7.5 route_geometries_clean.parquet

路径：

- `E:\cleaned_output_full_final\route_geometries_clean.parquet`

规模：

- 行数：`45,901,643`
- 列数：`7`
- 文件大小：约 `3.19 GB`

粒度：

- 一行表示一个 route geometry

字段说明：

| 字段名 | 类型 | 含义 |
| --- | --- | --- |
| `source_file` | string | 来源原始文件名 |
| `trip_id` | string | 所属 trip 唯一标识 |
| `devid` | int64 | 设备编号 |
| `route_geom_index` | int32 | 几何片段序号 |
| `route_geom_wkt` | string | 路线几何，WKT 格式 |
| `route_geom_is_valid` | bool | geometry 是否有效 |
| `route_geom_invalid_reason` | string | geometry 异常原因 |

主要用途：

- 空间可视化
- 路径重建
- 基于 geometry 的空间分析

## 8. 表间关系

主关联键：

- `trip_id`

辅助键：

- `devid`
- `source_file`

关系如下：

- `trips_clean` 1 对多 `gps_points_clean`
- `trips_clean` 1 对多 `matched_segments_clean`
- `trips_clean` 1 对多 `route_edges_clean`
- `trips_clean` 1 对多 `route_geometries_clean`

各明细表内部序号字段：

- GPS 点表使用 `point_index`
- matched segment 表使用 `segment_index`
- route edge 表使用 `route_index`
- route geometry 表使用 `route_geom_index`

## 9. 关键质量说明

### 9.1 route_geom 与 roads 长度不一致

这是本批数据里最主要的质量问题。

现象：

- `route_geom_length_mismatch = 61,878`

处理原则：

- 保留原始 `route_geom`
- 保留原始 `roads`
- 在 `matched_segments_clean.parquet` 中，仅当几何与 segment 关系可安全对齐时才写入 `route_geom_wkt`
- 如果无法可靠对齐，则 `route_geom_wkt` 置空，并在 `segment_invalid_reason` 中标记

影响：

- 对普通统计影响较小
- 对空间分析、路径重建影响较大

### 9.2 时间字段说明

本次统一将原始秒值直接转换为 UTC 时间字段。

注意：

- 抽样观察时，`gps_time_utc` 与 `match_time_utc` 可能存在 8 小时偏差迹象
- 这说明原始字段可能存在“本地时间语义”和“UTC 语义”混用的可能
- 在做“夜间活跃度”“早晚高峰次数”等标签前，建议先确认业务时区定义

建议：

- 若项目统一按中国本地业务时间计算标签，先将时间转为 `Asia/Shanghai`
- 但原始秒值字段不要删除

## 10. 对下一位同学的建议

### 10.1 做标签层优先使用哪些表

建议主用：

- `trips_clean.parquet`
- `gps_points_clean.parquet`
- `matched_segments_clean.parquet`

按需补充：

- `route_edges_clean.parquet`
- `route_geometries_clean.parquet`

### 10.2 常见标签可从哪些表算

#### 平均速度

推荐来源：

- `gps_points_clean.parquet`

思路：

- 以同一 `trip_id` 内相邻点计算时间差
- 用经纬度距离或投影距离估计位移
- 汇总得到 trip 平均速度、设备平均速度

注意：

- 需要剔除异常点间隔过大或时间差为 0 的情况
- 若要求“道路级平均速度”，建议结合路网长度或 geometry 长度进一步计算

#### 出行频率

推荐来源：

- `trips_clean.parquet`

思路：

- 以 `devid` 为主键
- 按天、周、月统计 trip 数量

#### 夜间活跃度

推荐来源：

- `trips_clean.parquet` 或 `gps_points_clean.parquet`

思路：

- 先确认业务时区
- 按本地时间取夜间时间窗，例如 `22:00-06:00`
- 统计夜间 trip 数或夜间点占比

#### 高峰出行次数

推荐来源：

- `trips_clean.parquet`

思路：

- 按业务定义高峰时间窗，例如 `07:00-09:00`、`17:00-19:00`
- 依据 trip 起始或主要活动时间统计高峰出行次数

#### 道路偏好/常走路段

推荐来源：

- `matched_segments_clean.parquet`

思路：

- 以 `devid + road_id` 聚合通行次数
- 取 Top N 路段

## 11. 标签层开发时建议加的过滤条件

如果下一位同学直接做标签，建议默认增加以下过滤：

- `is_valid_trip = true`
- `point_is_valid = true`
- `segment_is_valid = true`

若标签依赖空间几何，再额外增加：

- `route_geom_wkt is not null`

若标签依赖本地业务时间，再先进行：

- UTC 转业务时区

## 12. 建议的标签层主键

建议标签层主键设计：

- 用户/设备级标签：`devid`
- 设备-日标签：`devid + stat_date`
- trip 级标签：`trip_id`
- 设备-道路偏好标签：`devid + road_id`

## 13. 快速使用示例

### 13.1 读取 trip 表

```python
import pandas as pd

trips = pd.read_parquet(r"E:\cleaned_output_full_final\trips_clean.parquet")
print(trips.head())
```

### 13.2 统计设备出行频率

```python
import pandas as pd

trips = pd.read_parquet(r"E:\cleaned_output_full_final\trips_clean.parquet")
daily_trip_cnt = (
    trips.assign(stat_date=pd.to_datetime(trips["gps_start_time_utc"]).dt.date)
         .groupby(["devid", "stat_date"])
         .size()
         .reset_index(name="trip_cnt")
)
```

### 13.3 统计设备道路偏好

```python
import pandas as pd

segments = pd.read_parquet(r"E:\cleaned_output_full_final\matched_segments_clean.parquet")
road_pref = (
    segments.groupby(["devid", "road_id"])
            .size()
            .reset_index(name="pass_cnt")
            .sort_values(["devid", "pass_cnt"], ascending=[True, False])
)
```

## 14. 本次交接结论

本次已经完成：

- 原始 JLD2 数据读取
- 异常值处理
- 缺失值处理
- 时间字段规范
- 数据结构统一
- 标准化数仓层表构建

当前这 5 张表可以作为下一位同学进行标签层 TDM 建设的直接输入。

需要重点提醒下一位同学的只有两点：

- 做夜间活跃度、高峰出行次数前，先确认时间字段使用的业务时区
- 做强依赖 geometry 的标签时，要过滤 `route_geom` 未可靠对齐的数据

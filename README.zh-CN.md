<p align="center">
  <img src="docs/assets/dataset-cover-image.png" alt="韩国电力系统运行数据集封面" width="560">
</p>

# 韩国电力系统 — KPX 5分钟运行数据集

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **简体中文**

本仓库是 Kaggle 数据集 **South Korea Power Grid 5-Minute Data** 背后的可复现**采集、标准化、质量验证与发布流水线**。

项目采集 **Korea Power Exchange（KPX，韩国电力交易所）**按月公开的数据，并将三类运行信号标准化为一个适合分析的 long-format 表：**5分钟电力需求预测**、**发电机经济调度 BASEPOINT／目标值**以及**发电机状态估计出力**。

**数据集：** https://www.kaggle.com/datasets/taeyangg4/south-korea-power-grid-5-minute

## 数据概览

| 项目 | V2 版本 |
|---|---|
| KPX 公告历史观测范围 | **2015-08 → 2026-07** |
| 时间分辨率 | **5分钟** |
| 标准化行数 | **1,008,249,180** |
| 信号类型 | `demand`, `dispatch`, `state_estimation` |
| 推荐文件 | `south_korea_power_grid_5min.parquet` — **1.99 GB** |
| 兼容文件 | `south_korea_power_grid_5min.csv` — **50.14 GB** |
| 原始提供方 | Korea Power Exchange (KPX) |

V2 将数百个月度分析文件整合为**一个完整历史 Parquet 文件和一个包含相同行的 CSV 文件**。日常分析建议使用 Parquet。

## 三类信号的含义

| `source` | `value_mw` 的含义 | `generator_id` |
|---|---|---|
| `demand` | 5分钟系统**电力需求预测**（MW） | 空 / null |
| `dispatch` | 发电机**经济调度 BASEPOINT／目标值**（MW） | KPX 原始发电机 CODE |
| `state_estimation` | **状态估计的发电机出力**（MW） | KPX 原始发电机 CODE |

这三类数据彼此相关，但**不是可互换的同一种测量值**。项目也不会猜测 dispatch 与 state estimation 之间的发电机 ID 映射关系。

## 统一字段

| 字段 | 说明 |
|---|---|
| `timestamp` | KPX 原始5分钟时间戳。由于源文件没有可验证的时区元数据，因此不擅自指定时区。 |
| `source` | `demand`、`dispatch` 或 `state_estimation` |
| `generator_id` | 发电机级数据中的 KPX 原始发电机 CODE；`demand` 行为空 |
| `value_mw` | MW 数值，其语义由 `source` 决定 |

## 快速开始

完整数据超过10亿行。建议先在 Parquet 层过滤时间范围与字段，**不要直接把整表加载到 pandas**。

```python
from datetime import datetime
import pyarrow.dataset as ds

grid = ds.dataset("south_korea_power_grid_5min.parquet", format="parquet")

week = grid.to_table(
    columns=["timestamp", "value_mw"],
    filter=(
        (ds.field("source") == "demand")
        & (ds.field("timestamp") >= datetime(2026, 7, 1))
        & (ds.field("timestamp") < datetime(2026, 7, 8))
    ),
)

df = week.to_pandas()
print(df.head())
```

Kaggle 数据集还关联了公开 notebook，演示内存友好的区间读取、5分钟爬坡分析、运行信号聚合、发电机集中度和覆盖率检查。

## 数据质量原则

- **8个官方 source-month 附件无法获取**，项目明确记录缺失，不制造替代文件。
- 缺失的5分钟时间点不会被静默插值。
- 仅按文档化的 canonical key 规则删除完全重复记录。
- `2016-06-03 17:20` 的状态估计数据出现两组相互冲突的全发电机快照；项目不任意选择其中一组，而是排除该时间点并记录为标准化例外。
- 源文件没有可验证的时区元数据，因此时间戳保持 timezone-naive。

可在 Kaggle 包中的 `missing_source_months.csv`、`missingness_summary.csv`、`normalization_exceptions.json` 和 `release_manifest.json` 查看机器可读证据。

## GitHub 与 Kaggle 的分工

| GitHub 仓库 | Kaggle 数据集 |
|---|---|
| 原始公告发现与下载 | 发布分析就绪数据 |
| 历史文件格式兼容 | 统一 Parquet + CSV |
| 标准化代码 | 数据字典和来源说明 |
| QA、manifest、checksum、发布门禁 | 公开 notebook 与 Data Card |

大型 raw/working/processed/release 数据不会提交到 Git；仓库保留用于复现的小型 manifest 与 audit 结果。

## 从 KPX 采集

```powershell
python scripts/collect.py --start 2023-08 --end 2026-07 --dry-run
python scripts/collect.py --start 2023-08 --end 2026-07
```

采集器会发现 KPX 的月度公告并解析每篇公告的附件，而不是硬编码整个历史时期的附件 URL。

## 文档

- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) — 官方来源与历史文件格式变化
- [`docs/LICENSE_REVIEW.md`](docs/LICENSE_REVIEW.md) — 来源及再分发权限审查
- [`docs/KAGGLE_PUBLISHING.md`](docs/KAGGLE_PUBLISHING.md) — 封面裁剪、Data Card 刷新与 Usability 元数据说明
- [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md) — Phase 0–3 与 V1 构建历史
- [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) — V2 统一字段与各 source 的语义

原有按 Phase 编写的材料仍保留用于复现，但项目首页优先说明当前数据集是什么以及如何使用。

## 来源与使用

原始数据提供方为 **Korea Power Exchange（KPX，韩国电力交易所）**。本项目发布的是清洗、标准化后的衍生数据，并非 KPX 官方分发渠道，也不代表 KPX 背书。发布前重新核对的 data.go.kr 官方记录显示 `이용허락범위 제한 없음`（使用许可范围无限制），因此 Kaggle 使用 `other` 许可证类别，而不是擅自附加原始来源未声明的 Creative Commons 许可证。

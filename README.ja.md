<p align="center">
  <img src="docs/assets/dataset-cover-image.png" alt="韓国電力系統運用データセットのカバー" width="560">
</p>

# 韓国電力系統 — KPX 5分間隔の運用データセット

[English](README.md) · [한국어](README.ko.md) · **日本語** · [简体中文](README.zh-CN.md)

このリポジトリは、Kaggle で公開している **South Korea Power Grid 5-Minute Data** を作成するための、再現可能な**収集・正規化・品質検証・公開パイプライン**です。

**Korea Power Exchange（KPX／韓国電力取引所）** が月次で公開する資料を収集し、**5分間隔の電力需要予測**、**発電機別の経済給電（Economic Dispatch）BASEPOINT／目標値**、**発電機別の状態推定出力**を、解析しやすい1つの long-format テーブルに正規化します。

**データセット:** https://www.kaggle.com/datasets/taeyangg4/south-korea-power-grid-5-minute

## データ概要

| 項目 | 現在の Kaggle リリース |
|---|---|
| KPX 掲示板で確認した期間 | **2015-08 → 2026-07** |
| 時間分解能 | **5分** |
| 正規化済み行数 | **1,008,249,180** |
| 信号 | `demand`, `dispatch`, `state_estimation` |
| 推奨ファイル | `south_korea_power_grid_5min.parquet` — **1.99 GB** |
| CSV 互換スライス | `south_korea_power_grid_5min_2026_07.csv` — **2026-07、10,060,444 行** |
| 原データ提供者 | Korea Power Exchange (KPX) |

現在の Kaggle リリースでは、**2015-2026 の全履歴を Parquet 1ファイル**にまとめ、CSV が必要なツール向けに **2026年7月の全3信号・10,060,444行の CSV 互換スライス**を追加しています。50GB超の全履歴 CSV は重複公開せず、通常の解析には Parquet を推奨します。

## 3種類の信号

| `source` | `value_mw` の意味 | `generator_id` |
|---|---|---|
| `demand` | 5分間隔の系統**需要予測**（MW） | なし |
| `dispatch` | 発電機の**経済給電 BASEPOINT／目標値**（MW） | KPX 原資料の発電機 CODE |
| `state_estimation` | **状態推定された発電機出力**（MW） | KPX 原資料の発電機 CODE |

これらは関連する運用信号ですが、**同じ測定量ではありません**。また、dispatch と state estimation の発電機 CODE を同一名前空間と仮定せず、推測による対応表も作成していません。

## 統一スキーマ

| 列 | 説明 |
|---|---|
| `timestamp` | KPX 原資料の5分時刻。原ファイルに検証可能なタイムゾーン情報がないため、タイムゾーンは付与していません。 |
| `source` | `demand`、`dispatch`、`state_estimation` のいずれか |
| `generator_id` | 発電機別データの KPX 原資料 CODE。`demand` では null／空欄 |
| `value_mw` | MW 値。意味は `source` によって決まる |

## クイックスタート

全体で10億行を超えるため、Parquet から必要な期間・列を**先に絞り込んでから** pandas に変換してください。

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

Kaggle には、メモリ効率のよい期間抽出、5分ランプ分析、運用信号の集計、発電機集中度、カバレッジ確認を示す公開ノートブックも紐づけています。

## データ品質方針

- 取得できなかった**8件の公式 source-month 添付ファイル**は捏造せず、欠損として明示しています。
- 欠けている5分時刻は自動補間しません。
- 重複除去は、文書化された canonical key で完全一致する場合に限ります。
- `2016-06-03 17:20` の状態推定には相互に矛盾する全発電機スナップショットが2つあり、任意に片方を選ばず、その時刻全体を除外して例外として記録しています。
- 原資料に検証可能なタイムゾーン情報がないため、timestamp は timezone-naive のままです。

根拠は Kaggle パッケージの `missing_source_months.csv`、`missingness_summary.csv`、`normalization_exceptions.json`、`release_manifest.json` にあります。

## GitHub と Kaggle の役割

| GitHub リポジトリ | Kaggle データセット |
|---|---|
| 原資料の探索・収集 | 解析用データの配布 |
| 歴史的なファイル形式差への対応 | 統一 Parquet 1個 + CSV 1個 |
| 正規化コード | データ辞書・出典文書 |
| QA、manifest、checksum、リリースゲート | 公開ノートブック・Data Card |

大容量の raw/working/processed/release データは Git から除外し、再現性に必要な小さな manifest と audit 結果を保存します。

## KPX データの収集

```powershell
python scripts/collect.py --start 2023-08 --end 2026-07 --dry-run
python scripts/collect.py --start 2023-08 --end 2026-07
```

収集処理は KPX の月次掲示を探索して各記事の添付ファイルを解決し、全履歴の URL をハードコードしません。

## ドキュメント

- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) — 公式出典と歴史的なファイル形式の変化
- [`docs/LICENSE_REVIEW.md`](docs/LICENSE_REVIEW.md) — 出典・再配布条件の確認
- [`docs/KAGGLE_PUBLISHING.md`](docs/KAGGLE_PUBLISHING.md) — カバー画像のクロップ、Data Card 更新、Usability メタデータ
- [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md) — Phase 0–3 と V1 の構築履歴
- [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) — V2 統一スキーマと source ごとの意味

従来の Phase ごとの記録は再現性のため残しますが、プロジェクトのトップページでは現在のデータセットと利用方法を優先します。

## 出典と利用条件

原データ提供者は **Korea Power Exchange（KPX／韓国電力取引所）**です。本プロジェクトは KPX の公式配布チャネルではなく、正規化した派生データセットであり、KPX の承認を意味しません。公開前に確認した data.go.kr の公式記録は `이용허락범위 제한 없음`（利用許諾範囲の制限なし）と表示しているため、Kaggle では原出典にない Creative Commons ライセンスを付与せず `other` を使用しています。

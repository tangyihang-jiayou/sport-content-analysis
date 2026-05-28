# content-gap — 运动内容缺口分析 (20260527-28)

基于 hermit 爬取数据，分析各运动 L2 维度的内容供给缺口，并批量生成 & 投放搜索种子。

## 目录结构

```
content-gap/
├── data/          # 各轮 query 清单 (.json)
├── scripts/       # hermit seed 投放脚本
└── docs/          # 分析报告 (.html) & 原始探针数据
```

## 各轮投放汇总

| 轮次 | 文件 | Queries | Seeds |
|------|------|---------|-------|
| R1 · weekly top | queries_weekly_20260527.json | 525 | 1,050 |
| R2 · zero supply | queries_zerosupply_20260528.json | 640 | 1,280 |
| R3 · top-gap extra | queries_topgap_extra_20260528.json | 300 | 600 |
| R4 · gap #21-30 | queries_gap21to30_20260528.json | 190 | 380 |
| R5 · full batch | queries_full_batch_20260528.json | — | — |
| R6 · high-ROI 10k | queries_highroi_10k_20260528.json | — | — |
| **合计** | | **1,655+** | **3,310+** |

## 核心公式

```
gap_score = combined_roi × (1000 / sqrt(supply + 1))
```

- `combined_roi` = 各平台 ROI 加权平均（权重=内容数量）
- 平台中位数基准：YT=1,210 / TK=4,679 / IG=5,476 likes

## 投放阈值

| ROI | Query数/维度 |
|-----|------------|
| ≥ 1.0× | 20条 |
| 0.5–1.0× | 15条 |
| < 0.5× | 跳过 |
| supply=0 | 20条（无论ROI） |

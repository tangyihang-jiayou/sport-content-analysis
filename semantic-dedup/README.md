# semantic-dedup — 语义去重 + 缺口补充 (2026-05-30)

把交付内容池从「topic_id 去重」升级到「**语义去重**」(表达不同但问同一件事的 topic 只保留一条),并按缺口补充 32 个长尾运动,最终池 **102,822** 条。

## 成果

| 阶段 | 数量 |
|------|------|
| 全量清洗池 (5 批次按 topic_id 去重) | 104,407 |
| 语义去重后 (τ=0.85) | **81,273** (删 23,134 = 22.2%) |
| + gap 合成补充 (净) | +21,549 |
| **最终池** | **102,822** (0 重复, 56 运动全覆盖) |

产物: `sport_pool_dedup.json` (81,273) / `sport_pool_final_100k.json` (102,822) — 数据文件在交付目录,未入 git (88MB).

## 一、语义去重 — 阈值如何定的 (关键: 避免拍脑袋)

最初用 cosine τ=0.92 只删了 3.2%，过于保守。改用**独立方法交叉验证**:

1. **Gemini 裁判校准** (`04_judge_bands.py`): 从各相似度 band 采样 240 对 pair，让 Gemini 判「是否问同一件事」:

   | 相似度 band | 同问题率 |
   |---|---|
   | 0.78-0.82 | 40-50% (真不同) |
   | 0.82-0.84 | 70% (混合) |
   | **0.84-0.86** | **100%** |
   | 0.86-0.94 | 86-100% |

   → 拐点在 **0.84**。同问题内容一直延伸到 0.84，肉眼校准会严重低估。

2. **方法用贪心代表法** (`05_greedy_dedup.py`，不用 union-find): 按播放量留代表，删掉与某个**保留代表** ≥τ 的项。每个被删项都直接 ≥τ 于一个保留项，避免单链 A~B~C 传递导致的链式误并 (union-find 在 0.85 会把不同动作并成巨簇)。

3. 最终 **τ=0.85** (拐点上方，精度 ~90%+)，按 L1 分块块内去重。

## 二、缺口补充 — gap 运动 topic 生成

**约束**: 主池=优质池=68,197 视频全部已生成过 topic，无未使用源视频 (新爬虫未落地)。
**方案**: Gemini taxonomy-driven 合成生成 — 不依赖源视频，基于 `L1 + L2维度 × 6技能层 × 8热门角度`，按 v0.5.1 风格 (锋利切入角度 + 价值锚点，导演 brief)。

- `gen_gap_sport.py` — 生成器 (gemini-2.5-flash, 温度1.0, thinking关)
- `qc_gap.py` — v3 规则质检
- `build_cfg.py` + `sport_cfg.json` — 32运动的 terms/L2维度/现有样例(避重)
- `merge_dedup.py` — 跨池语义去重 (合成 vs 现有池 + 合成互相，τ=0.85) + 合并
- 两轮 dynamic workflow (`workflow_gap_supplement.js` / `workflow_topup_r2.js`): pipeline 按运动并行 生成→QC

生成 36,807 → 跨池删 2,336 + 组内删 12,922 → 净入 21,549。组内删除率高(35%)说明窄运动内容空间有限，0.85 正确收掉了重复。

## 三、最终池效果

各运动从「严重失衡」变均衡:
- 力量训练 16,354 → 9,357 (去重)
- gap 运动全部补起来: 椭圆机 12→156, 乒乓 27→280, 攀岩 927→~2200, 户外徒步→+1075 ...

详见 `reports/semantic-dedup-final-report.html`.

## 运行顺序

```bash
# 去重
python3 scripts/01_assemble_pool.py      # 组装 104k 池 + L1/L2 分类
python3 scripts/02_embed.py              # Gemini embedding (768d)
python3 scripts/04_judge_bands.py        # (可选) 裁判校准阈值
python3 scripts/05_greedy_dedup.py 0.85 --save   # 贪心去重

# gap 补充
python3 scripts/build_cfg.py             # 构建 sport_cfg.json
# (跑 workflow 或直接 gen_gap_sport.py + qc_gap.py 每运动)
python3 scripts/merge_dedup.py           # 跨池去重 + 合并
python3 scripts/gen_final_report.py      # 报告
```

API: Gemini 官方 (gemini-2.5-flash + gemini-embedding-001), 本地直连.

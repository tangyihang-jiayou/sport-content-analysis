# Sport Content Analysis Pipeline

**运动内容质量筛选 + Topic 生成系统**

从海量社交媒体视频中自动识别高质量运动教学内容，并为每条视频生成结构化的创意 topic 标题。

---

## 系统架构

```
原始视频池 (110,302 条)
    │
    ▼
[Step 1] 基础过滤                 → 语言/内容质量 (CJK、特殊字符、空内容、极短视频)
    │
    ▼
[Step 2] 信号词过滤               → 形态词/娱乐词规则过滤
    │
    ▼
[Step 3] LLM 判别                 → gemini-3.1-flash-lite batch 模式 (10条/call)
    │                               判断 form + is_sport
    ▼
优质教学视频池 (68,197 条, 66% pass rate)
    │
    ▼
[Topic 生成]                      → gemini-3.1-pro-preview 逐条生成创意 topic
    │
    ▼
最终 topics_output.json
```

---

## 模块说明

### `content-filtering/` — 内容质量筛选

| 文件 | 说明 |
|------|------|
| `pipeline.py` | 主流水线，串联 Step 1-5，入口脚本 |
| `config.py` | 所有超参（阈值、关键词列表、LLM keep 判定） |
| `vocab.py` | 42 个 L1 运动词表 (L1_VOCAB) + 形态反向词表 (FORM_NEG) |
| `llm_judge.py` | LLM 批量判别引擎（CometAPI / OpenAI-compatible，batch 模式） |

**运行方式：**
```bash
export COMET_API_KEY=sk-...
python3 pipeline.py input.csv
```

输出到 `outputs/` 目录：
- `优质池_YYYY-MM-DD.json` — 所有通过的视频（含 LLM 判别结果）
- `主池.csv` / `silent_ok.csv` — 分池结果
- `pipeline_log.txt` — 完整运行日志

---

### Step 1：基础过滤

去除语言不符或内容太稀的视频：

| 规则 | 参数 |
|------|------|
| CJK 占比过高 | title+desc 前 200 字中 CJK ≥ 25% |
| 非英文欧洲字符 | title+desc 中特殊字符 ≥ 2 个 |
| 内容为空 | clean title < 5 字 且 clean desc < 10 字 |
| 极短且文本稀 | duration ≤ 12s 且 title+desc 总字符 < 25 |

---

### Step 2：信号词过滤

基于关键词判断视频形态，三条 hard filter：

| 规则 | 触发条件 | 说明 |
|------|----------|------|
| form_neg | ≥ 1 个形态反向词命中 | 集锦/MV/游戏/音乐等形态词 |
| multi_ent_kw | ≥ 2 个娱乐词命中 | compilation/recap/vlog/funny 等 |
| neg_instructional | instructional 得分 < -1.0 | 教学词×0.5 - 娱乐词×0.7 - 弱负词×0.25 |

**关键设计决策（v9 迭代）：**
- 从 FORM_NEG 移除 `top 10/top 5/must watch`：误伤大量「TOP 10 Youth Pitching Drills」类教学视频
- 从 ENTERTAINMENT_KW 移除 `fyp/foryou`：TikTok 平台发现标签，不代表内容质量，移除后 multi_ent_kw 拒绝从 3,002 条降至 101 条（找回 2,901 条）

---

### Step 3：LLM 判别

使用 `gemini-3.1-flash-lite` via CometAPI（OpenAI-compatible 接口）批量判别：

```python
# 每次 API call 发 10 条视频，system prompt 只计算一次
BATCH_SIZE = 10
# 300 并发 workers
max_workers = 300
```

LLM 输出两个字段：
- **`form`**：`instructional` / `competition` / `trick` / `vlog` / `other`
- **`is_sport`**：`true` / `false`

**保留条件：** `form == "instructional"` AND `is_sport == true`

**吞吐量：** ~373 条/秒（batch 模式），全量 68,197 条约 3 分钟。

**LLM 判别 form 类别定义：**
- `instructional`：教学/讲解/示范技术，包括有声教学和静音+文字叠加的演示
- `competition`：现场比赛、完整赛事、比赛集锦、锦标赛
- `trick`：技巧镜头、技能蒙太奇、"最佳"集锦、没有教学意图的病毒式技能片段
- `vlog`：日常生活记录、问答、播客/访谈、个人体验分享
- `other`：MV、电影片段、游戏视频、不相关内容、广告

---

### `gen-topics/` — Topic 生成

| 文件 | 说明 |
|------|------|
| `gen_topics_sport_v0.5.1.py` | 主脚本，并发调用 LLM 为每条视频生成 topic |
| `gen_topic_prompt_运动_v0.5.1.md` | System prompt，包含完整规则和 few-shot 示例 |

**运行方式（脚本支持双 provider，按环境变量自动切换）：**

```bash
# 方式 A — CometAPI（OpenAI-compatible），支持多 key 逗号轮询
export COMET_API_KEYS=sk-key1,sk-key2,sk-key3
export LLM_MODEL=gemini-3.1-pro-preview

# 方式 B — Gemini 官方 API（设了 GEMINI_API_KEY 即优先走官方）
export GEMINI_API_KEY=AQ.xxx
export LLM_MODEL=gemini-3.5-flash
# devbox 直连 google 被墙时需挂代理：
export http_proxy=http://192.168.1.222:1081 https_proxy=http://192.168.1.222:1081

python3 gen_topics_sport_v0.5.1.py \
    --metadata metadata.json \
    --input input.json \
    --output topics_output.json \
    --workers 300        # ⚠️ 见下方「运维经验」，不要盲目调到 1000
```

> **切换逻辑**：脚本里 `GEMINI_API_KEY` 非空 → 走 Gemini 官方 endpoint；否则 fallback 到 `COMET_API_KEYS` 轮询。CometAPI 配额耗尽时切官方即可无缝续跑。

**断点续跑（重要）**：输出按 `topic_id` 去重，重启自动跳过已完成条目。全量 68k 跑了 5+ 个小时、中途换过 provider / 改过并发 / 配额爆过，全靠它续上——长任务务必依赖这个机制，别从头重跑。

---

### Topic 生成规则（v0.5.1 核心）

每条视频生成一个英文 topic 字符串，规则：

| 规则 | 内容 |
|------|------|
| **B1** | 不曲解原视频主体动作/主语，必须忠实于 input |
| **B2** | 不使用大众媒体知名人物真实姓名（除顶流白名单）|
| **B3** | 不包含系列后缀（Day N of / Episode N / Part N）|
| **F1** | 必须有"立意"（具体角度/观点），不能是空洞描述 |
| **F2** | 不能直接照抄标题，必须重新提炼核心教学点 |
| **F3** | 项目数 ≤ 5，禁止虚构数字/比例/数据 |
| **W1** | 长度 10-20 词，不含引号/括号 |
| **W2** | 临床医疗内容 → null |
| **C1** | Few-shot 复制检测，与样例相似度过高自动重写 |

**输出字段（枚举值取自 68k 全量实跑结果）：**
- `topic`：生成的 topic 字符串（或 null）
- `video_type`：`single_skill` / `knowledge` / `multi_skill` / `follow_along` / `highlight` / `teach_method` / `other`
- `narrative_intent`：`teach_method` / `build_cognition` / `explore_principle` / `take_stance` / `answer_question` / `other`
- `names_used`：使用到的人名列表（用于后处理校验）
- `_rewrite_triggered`：是否触发了重写

---

## 运行结果

| 阶段 | 数量 | 说明 |
|------|------|------|
| 原始输入 | 110,302 | 来自 asset center |
| Step 1 通过 | ~96,000 | 基础语言/质量过滤 |
| Step 2 通过 | ~89,000 | 信号词过滤 |
| Step 3 LLM 通过 | **68,197** | 最终高质量教学视频 (66% pass rate) |
| Topic 生成 | **68,193** | 成功 68,193 / 失败 4 |

**Topic 生成实跑统计（68,193 条）：**

| 维度 | 分布 |
|------|------|
| `video_type` | single_skill 36.8% · knowledge 31.5% · multi_skill 18.5% · follow_along 8.8% · other 3.3% · highlight 0.4% |
| `narrative_intent` | teach_method 58.1% · build_cognition 32.0% · explore_principle 5.0% · take_stance 2.4% · answer_question 1.7% |
| `topic = null` | 2,818 / 68,193（4.1%，多为临床医疗内容主动判 null）|
| 人名重写触发 | 113（0.2%）|
| 审计硬规则违规 | 1,419（2.1%，主要 W1 空升华动词 815 / B1 人名残留 151）|

---

## LLM 配置

两路 provider，脚本按环境变量自动选：

| Provider | Endpoint | 鉴权 | 何时用 |
|----------|----------|------|--------|
| **CometAPI**（OpenAI-compatible）| `https://api.cometapi.com/v1` | `COMET_API_KEYS`（逗号多 key 轮询）| 默认，国内直连可用 |
| **Gemini 官方** | `generativelanguage.googleapis.com/v1beta` | `GEMINI_API_KEY` | CometAPI 配额爆掉时 fallback，devbox 需挂代理 |

| 阶段 | 模型 | 实测吞吐 | 原因 |
|------|------|----------|------|
| 内容筛选（Step 3）| `gemini-3.1-flash-lite` | **~373 条/s**（batch 10/call）| 速度优先 |
| Topic 生成 | `gemini-3.1-pro-preview` | ~11 条/s | 质量优先 |
| Topic 生成（fallback）| `gemini-3.5-flash` | ~17 条/s | 配额/速度兼顾 |

---

## ⚠️ 运维经验与踩坑（全量跑 68k 的实战教训）

> 这一节是 Topic 生成阶段真实跑出来的坑，比配置本身更重要。

### 1. 并发不是越大越好 —— 1000 workers 把 API 打死
试过 `--workers 1000`：进程起了 1001 个线程、内存 2GB+，但**连接全部卡在 in-flight，6 分钟 0 条完成**（API 端扛不住瞬时千级并发）。退回 **300 workers（每 key ~100 并发）稳定无错**。经验值：

| workers | 结果 |
|---------|------|
| 1000 | ❌ 全卡死，0 完成 |
| 300 | ✅ 稳定，~11–17 条/s，0 error |
| 50 | ✅ 稳但偏慢（~3.4 条/s）|

### 2. CometAPI 配额会突然耗尽 → 403
跑到 **86%（59,034/68,197）时三个 key 同时返回 `403 insufficient_user_quota`**（`remaining quota: $-9.41`）。教训：**长任务必须预备 fallback provider**，且**断点续跑**让切换零成本——切到 Gemini 官方后从 59k 直接续到 100%。

### 3. devbox 直连 Google 被墙 → 必须走代理
`generativelanguage.googleapis.com` 在 devbox 上直连 `HTTP=000`。解决：挂内网代理
```bash
export http_proxy=http://192.168.1.222:1081 https_proxy=http://192.168.1.222:1081
```
**注意**：devbox 默认 shell 是 fish，`~/.bashrc` 里的 `proxy_on` 函数不生效（fish 不读 bashrc + bashrc 有 non-interactive early-return）。最稳的做法是**非交互场景直接 `env http_proxy=... python3 ...` 把变量喂给进程**，不依赖任何 shell rc。

### 4. 断点续跑是长任务的生命线
全量 68k 历经「换 provider × 调并发 × 配额爆 × 进程被 kill」多次中断，全靠按 `topic_id` 去重的 resume 续上，没有一次从头重跑。

---

## 目录结构

```
sport-content-analysis/
├── README.md
├── content-filtering/
│   ├── pipeline.py          # 主流水线
│   ├── config.py            # 超参配置
│   ├── vocab.py             # 运动词表 + 形态词表
│   └── llm_judge.py         # LLM 批量判别
├── gen-topics/
│   ├── gen_topics_sport_v0.5.1.py      # Topic 生成脚本
│   └── gen_topic_prompt_运动_v0.5.1.md # System prompt
└── *.html                   # 分析报告（历史版本）
```

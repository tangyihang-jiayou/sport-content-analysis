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

**运行方式：**
```bash
# 支持多 key 轮询（逗号分隔）
export COMET_API_KEYS=sk-key1,sk-key2,sk-key3
export LLM_MODEL=gemini-3.1-pro-preview

python3 gen_topics_sport_v0.5.1.py \
    --metadata metadata.json \
    --input input.json \
    --output topics_output.json \
    --workers 300
```

支持断点续跑：中途中断后重启会自动跳过已完成的条目。

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

**输出字段：**
- `topic`：生成的 topic 字符串（或 null）
- `video_type`：`instructional_demo` / `science_explainer` / `coaching_breakdown` / ...
- `narrative_intent`：`challenge_assumption` / `framework` / `insider_knowledge` / ...
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
| Topic 生成 | 68,197 | 每条视频生成创意 topic |

---

## LLM 配置

使用 [CometAPI](https://api.cometapi.com)（OpenAI-compatible 代理）：

```bash
BASE_URL = "https://api.cometapi.com/v1"
```

| 阶段 | 模型 | 原因 |
|------|------|------|
| 内容筛选（Step 3）| `gemini-3.1-flash-lite` | 速度优先，~373条/s |
| Topic 生成 | `gemini-3.1-pro-preview` | 质量优先，创意输出 |

多 key 轮询（线程安全）：
```python
export COMET_API_KEYS=sk-key1,sk-key2,sk-key3
```

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

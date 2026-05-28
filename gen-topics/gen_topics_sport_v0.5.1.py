"""gen_topics_sport_v0.5.1.py — 运动 Topic 生成 v0.5.1 (英文专项 · 精修版)

v0.5.1 关键变化（vs v0.5）:
- 使用 gen_topic_prompt_运动_v0.5.1.md
- 默认剥离人名 + 内嵌顶流白名单 + post-process Gemini 校验 + 不达标自动重写
- 项目数硬上限 ≤5
- 视频执行时长剥离、教学方案周期保留
- 系列后缀全杜绝（day N of / episode N / part N）
- 临床医疗 null + TikTok 空 desc fallback
- B1 加严：不曲解原视频主体动作/主语
- 输出新增 names_used 字段（供后处理校验）
- 审计新增 F3-a/F3-b/F3-d/F1-name-fail
"""
import argparse, json, os, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import Counter
import requests

MODEL    = os.environ.get("LLM_MODEL", "gemini-3.1-pro-preview")
BASE_URL = "https://api.cometapi.com/v1"

# 支持多 key 轮询，环境变量逗号分隔：COMET_API_KEYS=key1,key2,...
_raw_keys = os.environ.get("COMET_API_KEYS", os.environ.get("COMET_API_KEY", "")).strip()
_API_KEYS = [k.strip() for k in _raw_keys.split(",") if k.strip()]
if not _API_KEYS:
    raise RuntimeError("请设置 COMET_API_KEYS 环境变量")

import itertools, threading
_key_cycle = itertools.cycle(_API_KEYS)
_key_lock  = threading.Lock()

def _next_key() -> str:
    with _key_lock:
        return next(_key_cycle)

PROMPT_VERSION = "gen_v0.5.1"
PROMPT_FILE = Path(__file__).parent / "gen_topic_prompt_运动_v0.5.1.md"
SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8")


# ============================================================
# few-shot 复制检测（防止模型直接抄 prompt §2 样例）
# ============================================================

_FEWSHOT_PHRASES = [
    "tennis singles strategies to stop getting broken",
    "consistently hold serve",
    "Why most people overreact when dodging",
    "micro head movements",
    "kettlebell coach's 3 technique adjustments",
    "Turkish Get-up",
    "Pool technique won't work in choppy water",
    "open water swimming",
    "ankle and hip mobility aren't the only blockers",
    "pistol squat",
    "From snowplough to parallel",
    "natural drift once you commit",
    "10 backcountry safety essentials for trail runners",
    "unpredictable conditions",
    "100 Years of Pre-Workout History",
    "1930s Stimulants",
    "physical therapist's protocol for lateral ankle sprains",
    "when to load and when to wait",
    "Pamela Reif's 10-minute morning routine",
    "no-equipment warm-up sequence",
]

def detect_fewshot_copy(topic: str, source_text: str) -> str | None:
    """检测 topic 是否复制了 prompt §2 的样例。
    命中且不在源材料里 → 返回命中短语；否则 None。"""
    if not topic: return None
    src_l = (source_text or "").lower()
    t_l = topic.lower()
    for ph in _FEWSHOT_PHRASES:
        if ph.lower() in t_l and ph.lower() not in src_l:
            return ph
    return None


# ============================================================
# 工具：API 调用 + JSON 解析
# ============================================================

def _call_gemini(user_text: str, system_prompt: str = SYSTEM_PROMPT, temperature: float = 0.7) -> dict:
    # body built inside retry loop below
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_next_key()}",
    }
    openai_body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_text.strip()},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    last_exc = None
    for attempt in range(1, 4):
        try:
            # 每次重试换一个 key（轮询）
            openai_body["messages"][0]["role"]  # warmup access
            cur_headers = dict(headers)
            cur_headers["Authorization"] = f"Bearer {_next_key()}"
            resp = requests.post(f"{BASE_URL}/chat/completions",
                                 headers=cur_headers, json=openai_body, timeout=180)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            obj = _parse_json_loose(text)
            if obj is None:
                raise ValueError(f"json parse fail: {text[:300]}")
            if isinstance(obj, list):
                if not obj: raise ValueError("empty list")
                obj = obj[0]
            if not isinstance(obj, dict):
                raise ValueError(f"not a dict: {type(obj).__name__}")
            return obj
        except Exception as e:
            last_exc = e
            if attempt < 3: time.sleep(3 * attempt)
    raise last_exc


def _parse_json_loose(text: str):
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try: return json.loads(m.group(0))
            except json.JSONDecodeError: return None
    return None


# ============================================================
# 人名顶流校验（Gemini-as-judge）
# ============================================================

_PERSON_JUDGE_PROMPT = """你是体育/健身圈名人认知度评估专家。对每个人名判定 is_top（是否乔丹/罗纳尔多/帕梅拉/费德勒/Andrew Huberman 级别的跨圈层顶流——圈外普通人也熟悉这个名字）。

判定门槛（极严）：
✓ is_top=true：
  - 历史/当代体育超级巨星（任意圈外普通人会主动搜索他/她）
    例：Michael Jordan / LeBron James / Cristiano Ronaldo / Lionel Messi / Mike Tyson /
        Tiger Woods / Roger Federer / Serena Williams / Usain Bolt / Michael Phelps /
        Arnold Schwarzenegger / Floyd Mayweather / Conor McGregor / Tom Brady / Kobe Bryant
  - 大众健身/健康跨圈 KOL（订阅 5M+ 且大众媒体常见）
    例：Pamela Reif / Chloe Ting / Joe Wicks / Andrew Huberman / Peter Attia /
        Chris Bumstead / Jeff Cavaliere (Athlean-X) / Yoga With Adriene / Joe Rogan

✗ is_top=false（默认归这里）：
  - 圈内有名但跨圈无主动搜索意愿：mid-tier 教练、小博主、专项教练、普通运动员
  - 不确定的、没听过的、奇怪名字 → false

【输出 JSON】
{
  "results": [
    {"name": "<原样人名>", "is_top": <true|false>, "reason": "<10-20字>"},
    ...
  ]
}
"""

_PERSON_CACHE: dict[str, dict] = {}

def judge_persons(names: list[str]) -> dict[str, dict]:
    """批量判定 names 顶流，带 cache。返回 {name: {'is_top': bool, 'reason': str}}"""
    names = list(dict.fromkeys(n for n in names if n))
    if not names: return {}
    out = {}
    todo = []
    for n in names:
        if n in _PERSON_CACHE:
            out[n] = _PERSON_CACHE[n]
        else:
            todo.append(n)
    if not todo:
        return out

    # 分批 ≤30 个/次
    BATCH = 30
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i+BATCH]
        user = "判定以下人名：\n" + "\n".join(f"- {n}" for n in chunk)
        try:
            obj = _call_gemini(user, system_prompt=_PERSON_JUDGE_PROMPT, temperature=0.0)
            results = obj.get("results", [])
            for r in results:
                nm = r.get("name")
                if nm:
                    rec = {"is_top": bool(r.get("is_top")), "reason": r.get("reason", "")}
                    _PERSON_CACHE[nm] = rec
                    out[nm] = rec
        except Exception as e:
            for n in chunk:
                rec = {"is_top": False, "reason": f"judge_err: {e}"}
                _PERSON_CACHE[n] = rec
                out[n] = rec
        # 兜底
        for n in chunk:
            if n not in out:
                rec = {"is_top": False, "reason": "未返回，默认 false"}
                _PERSON_CACHE[n] = rec
                out[n] = rec
    return out


_REWRITE_INSTRUCTION = """以下 topic 包含未通过白名单的人名（非"乔丹/帕梅拉级"跨圈顶流），必须重写为头衔。

【未通过的人名】
{bad_names}

【原 topic】
{topic}

【原视频信息】
title: {title}
description: {desc}
author: {author}

按 v0.5.1 prompt §3 F1 Step 2 规则改写：
- 把上述人名替换为身份头衔（如 "An Olympic boxing medalist's..." / "A pro volleyball coach's..."）
- 头衔资质必须能从源信息找到背书
- 如源里无背书 → 退到 "A coach's..." / "A pro player's..." 等中性表达
- **关键：剥离人名时立意必须保住**——原 topic 的反差/痛点/对比/反常识 角度不能丢
- 句式仍要"引用形态"（X's method / from X / inspired by X），不要讲述形态

直接输出 JSON（topic / names_used / self_check_note 更新；其余字段透传）。
"""


# ============================================================
# 单条生成（含人名后处理）
# ============================================================

def gen_topic(meta: dict, input_rec: dict):
    tid     = input_rec.get("topic_id") or meta.get("topic_id")
    title   = meta.get("title") or input_rec.get("original_title") or ""
    desc    = (meta.get("description") or "")[:600]
    tags    = meta.get("tags") or []
    if not isinstance(tags, list): tags = []
    author  = meta.get("author") or ""
    pubtime = meta.get("publish_time") or ""
    cats    = meta.get("categories") or []
    if not isinstance(cats, list): cats = []
    duration = meta.get("duration") or input_rec.get("duration") or 0
    views    = meta.get("views") if meta.get("views") is not None else input_rec.get("view_count", 0)
    biz      = meta.get("biz_domain") or ""
    sub_biz  = meta.get("sub_biz_domain") or ""
    url      = meta.get("canonical_url") or input_rec.get("url") or ""
    source   = (input_rec.get("source") or "").strip()

    user_msg = f"""topic_id: {tid}
url: {url}
source: {source}
biz_domain: {biz} / {sub_biz}
publish_time: {pubtime}
duration: {duration}s
views: {views}
title: {title}
author: {author}
tags: {", ".join(str(t) for t in tags[:30])}
categories: {", ".join(str(c) for c in cats[:10]) if cats else "(none)"}
description: {desc}

按 v0.5.1 prompt 规则生成 topic（English），按 §4 流程走（创作 → 4 问自查 → 输出）。
特别注意：
- C1 立意是首要判断；中性描述（"X for Y" / "X's protocol for Z"）合规但不及格
- 人名默认剥离为头衔（仅乔丹/帕梅拉级跨圈顶流保留）
- 剥离人名时立意必须保住——反差/痛点/对比角度不能丢
- 项目数硬上限 ≤5
- 视频执行时长（X-minute / X-hour 跟练时长）剥离；教学方案周期（N-day 教学计划）保留
- 系列后缀（day N of / episode N / part N）全杜绝
- names_used 列出 topic 中保留的人名（保守原则，不确定就空数组）

直接输出 JSON, 不加 markdown 代码块、不加任何解释文字。
"""

    try:
        # 第一轮生成
        obj = _call_gemini(user_msg)
        topic = obj.get("topic")
        if isinstance(topic, str): topic = topic.strip() or None
        names_used = obj.get("names_used") or []
        if not isinstance(names_used, list): names_used = []

        # few-shot 复制检测（防抄样例）
        source_text = " ".join([title, desc, " ".join(str(t) for t in tags)])
        copied = detect_fewshot_copy(topic, source_text)
        fewshot_retry = False
        if copied:
            fewshot_retry = True
            retry_user = user_msg + f"\n\n⚠️ 上次你生成的 topic 直接抄了 §2 样例中的短语「{copied}」。这个短语跟当前 input 完全无关。\n你必须基于当前 input 的源材料生成全新的 topic——不要复用任何样例的关键词或句式骨架。\n现在重新生成（温度更低，更聚焦源材料）。"
            try:
                obj_retry = _call_gemini(retry_user, temperature=0.3)
                new_topic = obj_retry.get("topic")
                if isinstance(new_topic, str):
                    nt = new_topic.strip()
                    # 再检测一次
                    if nt and not detect_fewshot_copy(nt, source_text):
                        topic = nt
                        names_used = obj_retry.get("names_used") or names_used
                        if isinstance(names_used, list) is False:
                            names_used = []
                        obj["video_type"]       = obj_retry.get("video_type", obj.get("video_type"))
                        obj["narrative_intent"] = obj_retry.get("narrative_intent", obj.get("narrative_intent"))
                        obj["self_check_note"]  = obj_retry.get("self_check_note", obj.get("self_check_note"))
            except Exception:
                pass  # 重试失败保留原

        # 后处理：人名校验
        rewrite_triggered = False
        bad_names = []
        if topic and names_used:
            judged = judge_persons(names_used)
            bad_names = [n for n in names_used if not judged.get(n, {}).get("is_top")]
            if bad_names:
                rewrite_triggered = True
                rewrite_user = _REWRITE_INSTRUCTION.format(
                    bad_names="\n".join(f"- {n}" for n in bad_names),
                    topic=topic,
                    title=title, desc=desc, author=author,
                ) + f"\n\n原 JSON:\n{json.dumps(obj, ensure_ascii=False)}"
                try:
                    obj2 = _call_gemini(rewrite_user, temperature=0.4)
                    new_topic = obj2.get("topic")
                    if isinstance(new_topic, str):
                        topic = new_topic.strip() or topic
                    new_names = obj2.get("names_used")
                    if isinstance(new_names, list):
                        names_used = new_names
                    new_sc = obj2.get("self_check_note")
                    if isinstance(new_sc, str) and new_sc.strip():
                        obj["self_check_note"] = new_sc
                except Exception as e:
                    # 重写失败 → 退回到原 topic + 标记 bad_names 以供 audit
                    pass

        return tid, {
            "topic_id":         tid,
            "source":           source,
            "url":              url,
            "original_title":   title,
            "topic":            topic,
            "description":      desc[:300],
            "video_type":       obj.get("video_type", ""),
            "narrative_intent": obj.get("narrative_intent", ""),
            "names_used":       names_used,
            "self_check_note":  obj.get("self_check_note", ""),
            "prompt_version":   PROMPT_VERSION,
            "_rewrite_triggered": rewrite_triggered,
            "_bad_names_initial": bad_names,
            "_fewshot_retry":     fewshot_retry,
        }, None
    except Exception as e:
        return tid, None, str(e)


# ============================================================
# 审计（v0.5 沿用 + v0.5.1 新增）
# ============================================================

NUM_RE = re.compile(r"\d+(?:\.\d+)?")

# ---------- v0.5 沿用 ----------

_CURRENT_YEAR = "2026"  # 与 prompt §时效条款保持一致

def b1_number_audit(topic, source_text, duration=0, views=0):
    if not topic: return []
    src_nums = set(NUM_RE.findall(source_text or ""))
    if duration:
        src_nums.add(str(duration))
        for v in (duration // 60, round(duration / 60), duration // 3600):
            if v: src_nums.add(str(v))
    if views:
        src_nums.add(str(views))
        for v in (views // 1000, views // 1000000, views // 10000):
            if v: src_nums.add(str(v))
    out = []
    for n in NUM_RE.findall(topic):
        if n in src_nums: continue
        if n in {"1","2","3","4","5","6","7","8","9","10"}: continue
        if n == _CURRENT_YEAR: continue  # 当前年份是 prompt 允许的时效表达
        out.append(n)
    return out

_PROTOCOL_TERMS = [
    "ISSN","NSCA","WHO","ACSM","AHA","Mifflin-St Jeor","Mifflin","Harris-Benedict",
    "Cooper test","Cooper","Karvonen","Borg","RPE","1RM","VO2max","VO2 max",
    "FITT","DEXA","BMR","TDEE","EPOC","Zone 2","FTP","HRmax","HRR",
    "posterior chain","kinetic chain","mitochondrial biogenesis",
]
_PROTOCOL_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in _PROTOCOL_TERMS) + r")\b", re.IGNORECASE)

def b1_protocol_audit(topic, source_text):
    if not topic: return []
    src_l = (source_text or "").lower()
    out, seen = [], set()
    for m in _PROTOCOL_RE.finditer(topic):
        term = m.group(1); key = term.lower()
        if key in seen: continue
        seen.add(key)
        if key in src_l: continue
        head = key.split("-")[0].split()[0]
        if head and head in src_l: continue
        out.append(term)
    return out

_NAME_TITLE_EN_RE = re.compile(r"\b(Dr|Doctor|Coach|Trainer|Olympian|Champion|Champ|Professor|Pro)\.?\s+([A-Z][a-z]+)(?:\s+([A-Z][a-z]+))?")
_NAME_POSS_EN_RE  = re.compile(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)['']s\b")
_NAME_BY_EN_RE    = re.compile(r"\b(?:by|from|with|featuring)\s+([A-Z][a-z]+)\s+([A-Z][a-z]+)\b")

def b1_name_audit(topic, source_title):
    """检测 topic 中是否残留未在源里出现的两词大写人名。
    v0.5.1 下：经过后处理重写后，topic 应该极少残留小众人名。
    这里仍保留兜底检测——任何残留人名都需要 review。"""
    if not topic: return []
    out, seen = [], set()
    src_l = (source_title or "").lower()
    def _check(nm):
        if not nm or nm in seen: return
        seen.add(nm)
        if nm.lower() in src_l: return
        parts = nm.split()
        if len(parts) > 1 and any(len(p)>2 and p.lower() in src_l for p in parts): return
        out.append(nm)
    for m in _NAME_TITLE_EN_RE.finditer(topic):
        nm = m.group(2) + (' '+m.group(3) if m.group(3) else '')
        _check(nm)
    for m in _NAME_POSS_EN_RE.finditer(topic):
        _check(f"{m.group(1)} {m.group(2)}")
    for m in _NAME_BY_EN_RE.finditer(topic):
        _check(f"{m.group(1)} {m.group(2)}")
    return out

_METHOD_DETAIL_PATTERNS = [
    (re.compile(r"\b\d+\s*(?:g/kg|kcal|calorie)\s*(?:deficit|surplus)", re.IGNORECASE), "热量缺口"),
    (re.compile(r"(?:every|daily|weekly|per\s+\w+)\s*\d+\s*(?:sets?|reps?|min(?:utes?)?)", re.IGNORECASE), "组数频次"),
    (re.compile(r"\b\d+\s*(?:spm|rpm|bpm)\b", re.IGNORECASE), "频率单位"),
    (re.compile(r"\b\d+\s*%\s*(?:HRmax|HRR|MHR|max heart rate)", re.IGNORECASE), "心率区间"),
    (re.compile(r"\b\d+\s*deg(?:rees?)?\b", re.IGNORECASE), "角度"),
]

def b2_method_audit(topic):
    if not topic: return []
    out = []
    for pat, label in _METHOD_DETAIL_PATTERNS:
        m = pat.search(topic)
        if m: out.append(f"{label}={m.group(0).strip()}")
    return out

_AUTHORING_PATTERNS = [
    (re.compile(r"\b\w+\s+teaches?\s+you\b", re.IGNORECASE), "X teaches you"),
    (re.compile(r"\b\w+\s+explains?\s+(?:why|how|what)\b", re.IGNORECASE), "X explains why/how"),
    (re.compile(r"\b\w+\s+breaks?\s+(?:down|it down)\b", re.IGNORECASE), "X breaks down"),
    (re.compile(r"\b\w+\s+shows?\s+(?:you\s+)?how\b", re.IGNORECASE), "X shows how"),
    (re.compile(r"\blearn\s+(?:\w+\s+){0,3}from\s+[A-Z][a-z]+", re.IGNORECASE), "learn from X"),
    (re.compile(r"\btrain\s+with\s+[A-Z][a-z]+", re.IGNORECASE), "train with X"),
]

def f1_authoring_audit(topic):
    if not topic: return []
    out = []
    for pat, label in _AUTHORING_PATTERNS:
        m = pat.search(topic)
        if m: out.append(f"{label}={m.group(0).strip()}")
    return out

def f2_colon_trap_audit(topic):
    if not topic or (":" not in topic and "：" not in topic): return []
    parts = re.split(r"[:：]", topic, maxsplit=1)
    if len(parts) != 2: return []
    head, tail = parts[0].strip(), parts[1].strip()
    head_l = head.lower()
    suspense = ["why your", "the real ", "the true ", "the exact ", "stop ", "decoded"]
    head_is_suspense = any(s in head_l for s in suspense)
    payoff_patterns = [
        re.compile(r"^\d+\s+(?:ways?|tips?|steps?|drills?|methods?|techniques?|exercises?|essentials?|reasons?|rules?|principles?|secrets?|cues?)\b", re.IGNORECASE),
        re.compile(r"^(?:the\s+)?(?:exact|specific|essential|key|real)\s+(?:technique|method|drill|exercise|fix|reason)", re.IGNORECASE),
        re.compile(r"\bhere['']s\s+(?:how|the|why)\b", re.IGNORECASE),
    ]
    tail_is_payoff = any(p.search(tail) for p in payoff_patterns)
    out = []
    if head_is_suspense and tail_is_payoff:
        out.append("悬念+承诺")
    return out

_EMPTY_ELEVATION_RE = [
    re.compile(r"\bcompletely\s+(?:change|transform)s?\b", re.IGNORECASE),
    re.compile(r"\b(?:shifts?|transforms?|unlocks?)\s+(?:the|your)\s+\w+(?:\s+(?:stimulus|tension|response|profile|signal))?", re.IGNORECASE),
]
def w1_empty_elevation_audit(topic):
    if not topic: return []
    return [m.group(0).strip() for pat in _EMPTY_ELEVATION_RE for m in [pat.search(topic)] if m]

_PAST_YEAR_RE = re.compile(r"\b(2020|2021|2022|2023|2024|2025)\b")
def year_audit(topic):
    if not topic: return []
    return list(set(_PAST_YEAR_RE.findall(topic)))


# ---------- v0.5.1 新增 ----------

_NUM_LIST_RE = re.compile(r"\b(\d+)\s+(?:ways?|tips?|steps?|drills?|methods?|techniques?|exercises?|essentials?|reasons?|rules?|principles?|secrets?|moves?|tricks?|habits?|adjustments?|fixes?|cues?|mistakes?|drills?|signals?|approaches?|protocols?|workouts?|stretches?|positions?|skills?|tools?)\b", re.IGNORECASE)

def f3a_too_many_items(topic):
    """F3-a: 项目数 ≤5"""
    if not topic: return []
    out = []
    for m in _NUM_LIST_RE.finditer(topic):
        n = int(m.group(1))
        if n > 5:
            out.append(f"{m.group(0)} (n={n}>5)")
    return out

_EXEC_DURATION_RE = re.compile(
    r"\b(\d+)\s*-?\s*(?:minute|min|hour|hr)\s+"
    r"(?:workout|training|session|routine|class|sequence|flow|ride|run|stretch|practice|yoga|hiit|tutorial|guide|warm-?up|cool-?down)",
    re.IGNORECASE,
)

def f3b_exec_duration(topic, source_text):
    """F3-b: 视频执行时长后缀（X-minute workout/routine/...）应被剥离"""
    if not topic: return []
    out = []
    for m in _EXEC_DURATION_RE.finditer(topic):
        hit = m.group(0).strip()
        # 检查是否源里明确说"教学方案周期 N-day"——这种保留
        n = int(m.group(1))
        # 一般视频执行时长在 3-90 分钟。这里直接 flag。
        out.append(f"{hit} (n={n})")
    return out

_SERIES_SUFFIX_RES = [
    re.compile(r"\bday\s+\d+\s+of\s+(?:the\s+)?\d+-?day\b", re.IGNORECASE),
    re.compile(r"\bday\s+\d+\s+of\b", re.IGNORECASE),
    re.compile(r"\bepisode\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bep\.?\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bpart\s+\d+\s+of\b", re.IGNORECASE),
    re.compile(r"\bweek\s+\d+\s+of\b", re.IGNORECASE),
    re.compile(r"\bs0\d+e0\d+\b", re.IGNORECASE),
]

def f3d_series_suffix(topic):
    """F3-d: 系列后缀（day N of / episode N / part N）"""
    if not topic: return []
    out = []
    for pat in _SERIES_SUFFIX_RES:
        m = pat.search(topic)
        if m: out.append(m.group(0).strip())
    return out

def f1_name_unverified(record):
    """F1: 经过后处理后，仍有未通过校验的 bad_names 残留在 topic 里"""
    bad = record.get("_bad_names_initial") or []
    topic = record.get("topic") or ""
    out = []
    for nm in bad:
        if nm.lower() in topic.lower():
            out.append(nm)
    return out


# ---------- 信息 flag (INFO, 不计违规) ----------

_FLAG_PATTERNS = [
    (re.compile(r"\bwhy\s+(your|most|elite|the|a)\b", re.IGNORECASE), "Why X 起手"),
    (re.compile(r"\bhow\s+to\s+actually\s+\w+", re.IGNORECASE), "How to actually X"),
    (re.compile(r"\bthe\s+(?:real|true|exact)\s+\w+", re.IGNORECASE), "the real/true/exact X"),
    (re.compile(r"\bbreaking\s+down\b|\bbreakdown\s+of\b", re.IGNORECASE), "breaking down"),
    (re.compile(r"\bbeyond\s+\w+", re.IGNORECASE), "Beyond X"),
    (re.compile(r"\b\w+\s+isn['']t\s+just\b", re.IGNORECASE), "X isn't just"),
    (re.compile(r"\bmastering\s+\w+|\bunlocking\s+\w+", re.IGNORECASE), "mastering/unlocking"),
    (re.compile(r"\bthe\s+(?:science|physics|art|logic|mechanics)\s+of\s+\w+", re.IGNORECASE), "the science of X"),
]

def info_flag_audit(topic):
    if not topic: return []
    out = []
    for pat, label in _FLAG_PATTERNS:
        m = pat.search(topic)
        if m: out.append(f"{label}={m.group(0).strip()}")
    return out


# ============================================================
# 审计聚合
# ============================================================

HARD_RULES = [
    ("b1_numbers",         "B1 数字保真"),
    ("b1_protocols",       "B1 协议名保真"),
    ("b1_names",           "B1 人名残留"),
    ("b2_method",          "B2 方法剧透"),
    ("f1_authoring",       "F1 讲述视角"),
    ("f1_name_unverified", "F1 人名未通过白名单"),
    ("f2_colon_trap",      "F2 冒号陷阱"),
    ("f3a_too_many_items", "F3-a 项目数>5"),
    ("f3b_exec_duration",  "F3-b 视频执行时长"),
    ("f3d_series_suffix",  "F3-d 系列后缀"),
    ("w1_elevation",       "W1 空升华动词"),
    ("stale_years",        "时效·过期年份"),
]

def audit_results_v051(results, by_url):
    out = []
    for r in results:
        topic = r.get("topic")
        if not topic: continue
        m = by_url.get(r.get("url"))
        if not m: continue
        title_only = m.get("title") or ""
        src_text = " ".join([title_only, m.get("description") or "",
                              " ".join(str(t) for t in (m.get("tags") or []))])
        hard = {
            "b1_numbers":         b1_number_audit(topic, src_text,
                                                   duration=int(m.get("duration") or 0),
                                                   views=int(m.get("views") or 0)),
            "b1_protocols":       b1_protocol_audit(topic, src_text),
            "b1_names":           b1_name_audit(topic, title_only),
            "b2_method":          b2_method_audit(topic),
            "f1_authoring":       f1_authoring_audit(topic),
            "f1_name_unverified": f1_name_unverified(r),
            "f2_colon_trap":      f2_colon_trap_audit(topic),
            "f3a_too_many_items": f3a_too_many_items(topic),
            "f3b_exec_duration":  f3b_exec_duration(topic, src_text),
            "f3d_series_suffix":  f3d_series_suffix(topic),
            "w1_elevation":       w1_empty_elevation_audit(topic),
            "stale_years":        year_audit(topic),
        }
        info = info_flag_audit(topic)
        has_hard = any(hard.values())
        if has_hard or info:
            out.append({
                "topic_id":         r["topic_id"],
                "source":           r.get("source", ""),
                "topic":            topic,
                "names_used":       r.get("names_used", []),
                "rewrite_triggered": r.get("_rewrite_triggered", False),
                "self_check_note":  r.get("self_check_note", ""),
                "hard_violations":  {k: v for k, v in hard.items() if v},
                "info_flags":       info,
            })
    return out


def print_audit_v051(audits):
    if not audits:
        print("✓ 审计：无发现"); return
    hard_count = sum(1 for a in audits if a['hard_violations'])
    info_count = sum(1 for a in audits if a['info_flags'])
    print(f"硬规则违规: {hard_count} 条 / 信息 flag: {info_count} 条 / 总命中: {len(audits)} 条\n")
    print("硬规则违规明细:")
    for k, label in HARD_RULES:
        cnt = sum(1 for a in audits if k in a['hard_violations'])
        if cnt > 0:
            print(f"  {label:24s}: {cnt:4d} 条")
    if info_count:
        print("\n信息 flag (不计违规，仅供参考):")
        flag_counter = Counter()
        for a in audits:
            for f in a['info_flags']:
                flag_counter[f.split('=')[0]] += 1
        for label, n in flag_counter.most_common():
            print(f"  {label:24s}: {n:4d} 处")


# ============================================================
# 主流程
# ============================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", "-m", required=True, help="元数据文件（含 title/desc/tags 等）")
    ap.add_argument("--input", "-b", required=True, help="输入 list（含 topic_id / source / url）")
    ap.add_argument("--output", "-o", required=True)
    ap.add_argument("--workers", type=int, default=1000)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--source-filter", type=str, default="", help="按 source 过滤，空字符串=不过滤")
    args = ap.parse_args()

    meta_list = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    inputs    = json.loads(Path(args.input).read_text(encoding="utf-8"))

    by_tid       = {m.get("topic_id"): m for m in meta_list if m.get("topic_id")}
    by_canonical = {m.get("canonical_url"): m for m in meta_list if m.get("canonical_url")}
    # 兼容 metadata 用 url 字段
    for m in meta_list:
        if m.get("url") and not m.get("canonical_url"):
            by_canonical[m["url"]] = m

    if args.source_filter:
        inputs = [b for b in inputs if (b.get("source") or "").lower() == args.source_filter.lower()]
        print(f"source 过滤 '{args.source_filter}': {len(inputs)} 条")

    if args.limit > 0:
        inputs = inputs[:args.limit]

    jobs, missing = [], []
    for b in inputs:
        tid = b.get("topic_id")
        meta = by_tid.get(tid)
        if not meta and b.get("url"):
            meta = by_canonical.get(b["url"])
        if not meta:
            # 没有元数据时，用 input 自身字段拼凑
            meta = {
                "title": b.get("original_title", ""),
                "description": b.get("description", ""),
                "duration": b.get("duration", 0),
                "views": b.get("view_count", 0),
                "canonical_url": b.get("url", ""),
            }
            missing.append(tid)
        jobs.append((meta, b))
    print(f"输入 {len(inputs)} 条 → 匹配元数据 {len(jobs)-len(missing)}/{len(jobs)} 条")

    out_path = Path(args.output)
    existing, done_ids = [], set()
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            done_ids = {r.get("topic_id") for r in existing if r.get("topic_id")}
            print(f"resumed: 已有 {len(done_ids)} 条")
        except Exception as e:
            print(f"[warn] 读旧产出失败：{e}")

    pending = [(m, b) for m, b in jobs if b.get("topic_id") not in done_ids]
    print(f"待生成: {len(pending)} 条 / 并发 {args.workers}")
    if not pending and not existing:
        return

    results = list(existing); errors = {}; ckpt_every = 50
    if pending:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(gen_topic, m, b): b.get("topic_id") for m, b in pending}
            done = 0
            for f in as_completed(futs):
                tid, data, err = f.result()
                done += 1
                if data:
                    results.append(data)
                    t = data.get("topic") or "(null)"
                    rw = "↻" if data.get("_rewrite_triggered") else " "
                    print(f"[{done}/{len(pending)}] ✓{rw} {tid} | {t[:60]}", flush=True)
                else:
                    errors[tid] = err
                    print(f"[{done}/{len(pending)}] ✗ {tid}: {(err or '')[:80]}", flush=True)
                if done % ckpt_every == 0:
                    _atomic_write(out_path, results)
        _atomic_write(out_path, results)
        print(f"\n完成: {len(results)} 成功 / {len(errors)} 失败 → {args.output}")

    # 统计
    print("\n类型分布:")
    for t, n in Counter(r.get("video_type", "") for r in results).most_common():
        print(f"  {t}: {n}")
    print("\nnarrative_intent 分布:")
    for t, n in Counter(r.get("narrative_intent", "") for r in results).most_common():
        print(f"  {t}: {n}")
    null_cnt = sum(1 for r in results if r.get("topic") is None)
    rewrite_cnt = sum(1 for r in results if r.get("_rewrite_triggered"))
    print(f"\nNull 比例: {null_cnt} / {len(results)} ({null_cnt/max(len(results),1)*100:.1f}%)")
    print(f"人名重写触发: {rewrite_cnt} / {len(results)} ({rewrite_cnt/max(len(results),1)*100:.1f}%)")

    print("\n========== v0.5.1 审计 ==========")
    audits = audit_results_v051(results, by_canonical)
    print_audit_v051(audits)
    if audits:
        audit_path = out_path.with_suffix(".audit.json")
        audit_path.write_text(json.dumps(audits, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  审计明细 → {audit_path}")


def _atomic_write(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


if __name__ == "__main__":
    main()

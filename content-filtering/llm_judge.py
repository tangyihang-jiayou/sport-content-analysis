"""
LLM judge — CometAPI batch 模式 (gemini-3.1-flash-lite)

核心优化：
- 每次 API call 发 BATCH_SIZE 条视频，system prompt 只算一次
- 指数退避重试（最多 5 次），batch 失败自动降级为逐条重试
- ThreadPoolExecutor 并发 batch 调用

用法:
    export COMET_API_KEY=sk-...
    python3 llm_judge.py sanity
"""
import json, os, re, sys, time, random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

COMET_API_KEY = os.environ.get("COMET_API_KEY", "").strip()
MODEL_NAME    = os.environ.get("LLM_MODEL", "gemini-3.1-flash-lite")
BASE_URL      = "https://api.cometapi.com/v1"
TEMPERATURE   = 0.0
MAX_RETRIES   = 5
BATCH_SIZE    = int(os.environ.get("BATCH_SIZE", "10"))

SYSTEM_PROMPT = """You are a video content classifier for a sports content curation pipeline.
You will receive multiple videos. For each video output two judgments:

1. "form" — what FORMAT the video is. Pick ONE:
   - "instructional": teaching/explaining/demonstrating technique, drills, tutorials, fundamentals, breakdowns, analysis, guides, tips, science explainers. Includes voiced-over teaching AND silent-with-text-overlay demos. Includes equipment reviews with explanation.
   - "competition": live matches, full games, game highlights, tournaments, match recaps, race coverage.
   - "trick": trick shots, skill montages, "best of" plays, freestyle combos, impressive moments compilations, dance challenges, viral skill clips with no teaching intent.
   - "vlog": day-in-life, Q&A, podcast/interview chat, story-time, reaction videos, personal experience sharing, raw lifestyle recording.
   - "other": none of the above (music videos, movie clips, video game footage, unrelated content, ads).

2. "is_sport" — whether the video is genuinely about sports/fitness/exercise.
   - true: any sport, fitness, exercise, or physical training
   - false: completely unrelated (cooking, gaming, finance, music)

Key rules:
- "instructional" means teaching intent. Highlight reels are NOT instructional.
- Short-form videos often have hashtag-heavy captions with teaching words but show only flashy clips — judge by content intent, not promotional language.
- "competition" requires actual match/race/game footage.
- If description is empty, lean on title + duration.
- 90+ second videos are more likely real teaching than 15-second clips.

Output a JSON ARRAY with one object per video in the SAME ORDER as input. STRICT JSON only, no markdown, no commentary:
[{"form": "...", "is_sport": true_or_false}, ...]"""


def _build_user_text_for_batch(samples: list) -> str:
    parts = []
    for i, s in enumerate(samples, 1):
        title    = (s.get("title") or "").strip()[:200]
        desc     = (s.get("desc") or s.get("description") or "").strip()[:400]
        L1       = s.get("L1") or ""
        platform = s.get("platform") or ""
        duration = s.get("duration") or 0
        parts.append(
            f"[Video {i}]\n"
            f"L1: {L1 or '(sports/fitness)'}  Platform: {platform}  Duration: {duration}s\n"
            f"Title: {title or '(empty)'}\n"
            f"Description: {desc or '(empty)'}"
        )
    return "\n\n".join(parts)


def _call_api(user_text: str) -> list:
    """调一次 API，返回结果列表；失败抛异常。"""
    if not COMET_API_KEY:
        raise RuntimeError("COMET_API_KEY 未设置")
    endpoint = f"{BASE_URL}/chat/completions"
    headers  = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {COMET_API_KEY}",
    }
    body = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_text},
        ],
        "temperature": TEMPERATURE,
        "response_format": {"type": "json_object"},
    }
    r = requests.post(endpoint, headers=headers, json=body, timeout=(30, 90))
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    parsed = json.loads(text)
    # 模型可能返回 {"results": [...]} 或直接 [...]
    if isinstance(parsed, list):
        return parsed
    for key in ("results", "videos", "classifications", "items"):
        if key in parsed and isinstance(parsed[key], list):
            return parsed[key]
    raise ValueError(f"无法解析响应结构: {list(parsed.keys())}")


def _judge_batch_with_retry(samples: list) -> list:
    """
    发一批 samples，返回等长结果列表。
    重试策略：指数退避，最多 MAX_RETRIES 次。
    batch 失败后降级为逐条重试。
    """
    user_text = _build_user_text_for_batch(samples)
    last_exc  = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            results = _call_api(user_text)
            if len(results) != len(samples):
                raise ValueError(f"返回条数 {len(results)} ≠ 请求条数 {len(samples)}")
            return results
        except Exception as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                wait = min(2 ** attempt + random.random(), 30)
                time.sleep(wait)

    # batch 全失败 → 逐条降级
    fallback = []
    for s in samples:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                res = _call_api(_build_user_text_for_batch([s]))
                fallback.append(res[0])
                break
            except Exception as e:
                if attempt < MAX_RETRIES:
                    time.sleep(min(2 ** attempt, 15))
                else:
                    fallback.append({"error": str(e)})
    return fallback


def run_batch(samples: list, max_workers: int = 200,
              out_path: str = None, resume: bool = True):
    """并发批量判别，结果实时写 out_path（jsonl），支持断点续跑。"""
    # 加载已有 cache
    done = {}
    if resume and out_path and os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    done[d["url"]] = d
                except:
                    pass
        print(f"  resume: 已有 {len(done):,} 条")

    pending = [s for s in samples if s["url"] not in done]
    print(f"  待跑: {len(pending):,} / 总 {len(samples):,}  batch_size={BATCH_SIZE}  workers={max_workers}")
    if not pending:
        return list(done.values())

    # 切 batch
    batches = [pending[i:i+BATCH_SIZE] for i in range(0, len(pending), BATCH_SIZE)]
    print(f"  共 {len(batches):,} 个 batch")

    out_f   = open(out_path, "a", encoding="utf-8") if out_path else None
    results = list(done.values())
    n_done  = n_err = 0
    t0      = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_judge_batch_with_retry, b): b for b in batches}
        for fut in as_completed(futures):
            batch   = futures[fut]
            try:
                batch_results = fut.result()
            except Exception as e:
                batch_results = [{"error": str(e)}] * len(batch)

            for s, res in zip(batch, batch_results):
                n_done += 1
                if "error" in res:
                    n_err += 1
                    rec = {"url": s["url"], "error": res["error"]}
                else:
                    rec = {"url": s["url"], **res}
                results.append(rec)
                if out_f:
                    out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            if out_f:
                out_f.flush()

            if n_done % 2000 == 0 or n_done == len(pending):
                elapsed = time.time() - t0
                rate    = n_done / elapsed
                eta     = (len(pending) - n_done) / rate if rate > 0 else 0
                print(f"  [{n_done:,}/{len(pending):,}] err={n_err} "
                      f"rate={rate:.1f}/s eta={eta:.0f}s", flush=True)

    if out_f:
        out_f.close()
    print(f"  完成: {n_done:,} 条 (err={n_err}), 用时 {time.time()-t0:.0f}s")
    return results


# ---- sanity test ----
if __name__ == "__main__":
    if not COMET_API_KEY:
        print("ERROR: export COMET_API_KEY=sk-..."); sys.exit(1)
    if len(sys.argv) > 1 and sys.argv[1] == "sanity":
        print(f"[Sanity] model={MODEL_NAME}  batch_size={BATCH_SIZE}")
        samples = [
            {"url": "t1", "title": "How to do a proper squat", "desc": "Step by step squat tutorial for beginners.",
             "L1": "", "platform": "YouTube", "duration": 300},
            {"url": "t2", "title": "Top 10 NBA dunks 2024", "desc": "Insane compilation of the best dunks this season.",
             "L1": "", "platform": "YouTube", "duration": 180},
            {"url": "t3", "title": "My marathon vlog", "desc": "Day in the life running my first marathon.",
             "L1": "", "platform": "TikTok", "duration": 45},
        ]
        res = _judge_batch_with_retry(samples)
        for s, r in zip(samples, res):
            print(f"  {s['title'][:50]} → {r}")

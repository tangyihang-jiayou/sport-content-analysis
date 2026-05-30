"""
Gap-sport topic generator (taxonomy + viral-angle driven, Gemini official API, local).
Generates diverse English teaching-topic briefs in the established v0.5.1 style for a sport
that lacks source videos. Grounds on L2 dims × skill levels × viral angles; dedups within run.

Usage: python3 gen_gap_sport.py --sport 乒乓球 --quota 300 --out /tmp/supp/out_乒乓球.json
"""
import argparse, os, json, asyncio, re, time, os, hashlib, random
import httpx

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL   = "gemini-2.5-flash"
URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
PER_CALL = 20
CONC     = 12

# Sport → English seed terms + L2 dimensions + typical skill levels
SPORT_CFG = json.load(open(os.path.join(os.path.dirname(__file__), 'sport_cfg.json'), encoding='utf-8'))

ANGLES = [
    "痛点切入 (a real frustration learners hit at a specific level)",
    "反常识 (challenge a widespread misconception in this sport)",
    "受众限定 (target a specific level/age/context: beginner, intermediate plateau, over-40, returning)",
    "对比抉择 (A vs B choice learners face: technique/gear/approach)",
    "隐藏机制 (the underlying reason a common problem happens)",
    "快速见效 (a single adjustment / drill with outsized impact)",
    "进阶卡点 (the specific thing blocking progress to the next level)",
    "器材/场地认知 (gear or setup knowledge that changes outcomes)",
]

SYSTEM = """You generate English teaching-topic briefs for a sports short-video content pool.

A topic is a CREATIVE SEED for a downstream AI director — the single sharpest angle that makes a video "worth making". NOT a summary, NOT an SEO title, NOT a rating template.

CORE VALUE (every topic must have):
1. A sharp angle (痛点 / 反常识 / 受众限定 / 对比 / 隐藏机制) — this is the #1 requirement.
2. A specific value anchor (a concrete skill, drill, adjustment, or insight — not vague).
3. Executable by an AI director: give the angle/scene/audience/painpoint, do NOT spoil step-by-step methods.

HARD RULES:
- English only. Natural sports-audience phrasing.
- NO real person names as presenters. A coach/pro can be a credibility source ("a climbing coach's...") but never a named on-camera narrator.
- ≤5 items if listing (prefer 2-4). NEVER 10/15/40-item roundups.
- No video-duration/series suffixes (no "day 3 of", "episode 2", "part 4", "20-minute video").
- Do NOT fabricate specific stats/records. Keep claims realistic for the sport.
- Each topic must be DISTINCT — different L2 dimension, angle, or skill level. No two topics should ask the same thing reworded.

FAILURE MODES TO AVOID:
- Neutral description: "X for Y" / "Fundamentals of X" (no angle).
- Empty packaging: "X decoded: mastering Y" / "The science of X" (decoration, no substance).
- Anxiety click-bait: "Why your X fails: 3 ways to..." used as a hollow hook.

OUTPUT: a JSON array of objects, each: {"topic": "...", "l2": "<which sub-dimension>", "angle": "<which angle>"}
Output ONLY the JSON array."""

def build_user(sport, terms, l2_dims, levels, angles_subset, avoid_samples):
    avoid = "\n".join(f"- {s}" for s in avoid_samples[:12])
    l2s = ", ".join(l2_dims) if l2_dims else "(use natural sub-skills of this sport)"
    return f"""Sport: {sport} (English terms: {', '.join(terms)})

Generate {PER_CALL} DISTINCT teaching-topic briefs for this sport.

Spread them across these sub-dimensions (L2): {l2s}
Use a VARIETY of these angles: {'; '.join(angles_subset)}
Span skill levels: {', '.join(levels)}

Each topic must:
- Pick a DIFFERENT (sub-dimension × angle × level) combination than the others.
- Have a sharp angle + specific value anchor (see system rules).
- Be realistic and specific to {sport}.

Avoid duplicating the meaning of these EXISTING topics (write about other aspects):
{avoid}

Output the JSON array of {PER_CALL} objects now."""

async def gen_call(client, sport, terms, l2_dims, levels, avoid, sem, salt, attempt=0):
    # rotate angles per call for diversity
    asub = random.sample(ANGLES, k=min(4, len(ANGLES)))
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": build_user(sport, terms, l2_dims, levels, asub, avoid) + f"\n\n(batch {salt})"}]}],
        "generationConfig": {"temperature": 1.0, "topP": 0.95, "maxOutputTokens": 4000,
                             "thinkingConfig": {"thinkingBudget": 0}}
    }
    try:
        async with sem:
            r = await client.post(URL, json=body, timeout=90)
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"]["parts"]
        raw = "".join(p.get("text","") for p in parts).strip()
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if not m: raise ValueError("no json")
        return json.loads(m.group())
    except Exception as e:
        if attempt < 3:
            await asyncio.sleep(2**attempt)
            return await gen_call(client, sport, terms, l2_dims, levels, avoid, sem, salt, attempt+1)
        return []

async def main(sport, quota, out_path):
    cfg = SPORT_CFG.get(sport, {})
    terms = cfg.get('terms', [sport])
    l2_dims = cfg.get('l2', [])
    levels = cfg.get('levels', ['beginner', 'intermediate', 'advanced'])
    avoid = cfg.get('existing_samples', [])

    n_calls = int(quota / PER_CALL * 1.3) + 2   # overshoot for dedup attrition
    sem = asyncio.Semaphore(CONC)
    seen_norm = set()
    results = []
    t0 = time.time()
    async with httpx.AsyncClient() as client:
        tasks = [gen_call(client, sport, terms, l2_dims, levels, avoid, sem, i) for i in range(n_calls)]
        for fut in asyncio.as_completed(tasks):
            batch = await fut
            for item in batch:
                topic = (item.get('topic') or '').strip()
                if not topic or len(topic) < 15: continue
                norm = re.sub(r'[^a-z0-9 ]','', topic.lower())
                norm = ' '.join(sorted(set(norm.split())))
                if norm in seen_norm: continue   # exact/near-exact intra-run dedup
                seen_norm.add(norm)
                tid = "sport_synth_" + hashlib.md5((sport+topic).encode()).hexdigest()[:12]
                results.append({
                    "topic_id": tid, "topic": topic,
                    "domain": "运动教学", "tier": "synth_gap", "source": "synthetic",
                    "original_title": "", "view_count": 0, "duration": 0, "url": "",
                    "asset_id": tid, "l1_gen": sport,
                    "l2_gen": item.get('l2',''), "angle_gen": item.get('angle',''),
                })
    results = results[:int(quota*1.25)]
    json.dump(results, open(out_path,'w'), ensure_ascii=False, indent=2)
    print(f"{sport}: generated {len(results)} unique (target {quota}) in {time.time()-t0:.0f}s -> {out_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", required=True)
    ap.add_argument("--quota", type=int, default=300)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    asyncio.run(main(a.sport, a.quota, a.out))

#!/usr/bin/env python3
"""
R8 投放：基于今天优质池 68k 数据分析后的 viral pattern + gap fill 混合批
4,148 unique queries × 3 platforms (YT/TK/IG) = 12,444 seeds

Strategy by priority:
- P0 (2,761): 极度稀缺 L1，全 viral pattern (challenge/shorts/no equipment/transformation/...)
- P1 (1,037): 不足 L1，主流 viral pattern
- P2 (200): 够用 L1，viral 增量
- P3 (150): 饱和 L1，仅保 challenge/dance/celebrity 维持新鲜度
"""
import json, subprocess, hashlib, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

HERMIT = "/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit"
QUERY_FILE = "/tmp/queries_r8_viral_gap_20260529.json"
DATE = "20260529"
VERSION = "v10_r8"

def seed_name(q, platform):
    l1 = (q.get("l1") or "misc").replace("/", "").replace(" ", "")[:8]
    pri = q.get("priority", "P0")
    h = hashlib.md5(q["query"].encode()).hexdigest()[:6]
    return f"r8_{pri}_{l1}_{h}_{platform}"[:60]

def make_origin(platform):
    return f"sports_gap_{VERSION}_{platform}_{DATE}"

def create_seed(q, platform):
    if platform == "yt":   label = "youtube_search"
    elif platform == "tk": label = "tiktok_search"
    elif platform == "ig": label = "instagram_search"
    else: return (q["query"], platform, False, f"Unknown: {platform}")
    origin = make_origin(platform)
    name = seed_name(q, platform)
    config = json.dumps({"keyword": q["query"], "limit": 50})
    cmd = [HERMIT, "seed", "create", "--name", name, "--platform", platform,
           "--label", label, "--origin", origin, "--config", config,
           "--execute-type", "one_shot"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (q["query"], platform, r.returncode==0, (r.stdout+r.stderr)[:200])
    except Exception as e:
        return (q["query"], platform, False, str(e)[:200])

def main():
    with open(QUERY_FILE) as f:
        queries = json.load(f)

    tasks = []
    for q in queries:
        for plat in ("yt", "tk", "ig"):
            tasks.append((q, plat))

    print(f"R8 投放: {len(tasks)} seeds ({len(queries)} queries × 3 platforms)")
    print(f"Start: {datetime.now().isoformat()}\n")

    ok = 0; fail = 0; errors = []
    with ThreadPoolExecutor(max_workers=14) as ex:
        futures = {ex.submit(create_seed, q, p): (q, p) for q, p in tasks}
        for i, fut in enumerate(as_completed(futures), 1):
            query, platform, success, output = fut.result()
            if success: ok += 1
            else:
                fail += 1
                if len(errors) < 10: errors.append((query, platform, output))
            if i % 200 == 0 or i == len(tasks):
                print(f"  [{i}/{len(tasks)}] OK={ok}, FAIL={fail}", flush=True)

    print(f"\n=== R8 DONE ===")
    print(f"End: {datetime.now().isoformat()}")
    print(f"OK={ok}, FAIL={fail}")
    if errors:
        for q, p, o in errors[:5]:
            print(f"  [{p}] {q[:60]}: {o[:80]}")

if __name__ == "__main__":
    main()

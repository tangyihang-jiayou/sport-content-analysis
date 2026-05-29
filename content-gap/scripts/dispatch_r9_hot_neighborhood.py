#!/usr/bin/env python3
"""
R9 投放：基于热门内容的 specific 衍生 query
556 unique queries × 3 platforms = 1,668 seeds
重点：抓 R7/R8 通用 pattern 没覆盖到的、具体到动作/技术名/明星名的 long-tail
"""
import json, subprocess, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

HERMIT = "/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit"
QUERY_FILE = "/tmp/queries_r9_hot_neighborhood_20260529.json"
DATE = "20260529"
VERSION = "v11_r9"

def make_seed(q, platform):
    l1 = (q.get("l1") or "misc").replace("/", "").replace(" ", "")[:8]
    h = hashlib.md5(q["query"].encode()).hexdigest()[:6]
    name = f"r9_hot_{l1}_{h}_{platform}"[:60]
    origin = f"sports_gap_{VERSION}_{platform}_{DATE}"
    label_map = {'yt':'youtube_search','tk':'tiktok_search','ig':'instagram_search'}
    config = json.dumps({"keyword": q["query"], "limit": 50})
    return [HERMIT, "seed", "create", "--name", name, "--platform", platform,
            "--label", label_map[platform], "--origin", origin,
            "--config", config, "--execute-type", "one_shot"]

def create(q, platform):
    try:
        r = subprocess.run(make_seed(q, platform), capture_output=True, text=True, timeout=20)
        return (q["query"], platform, r.returncode==0, (r.stdout+r.stderr)[:200])
    except Exception as e:
        return (q["query"], platform, False, str(e)[:200])

def main():
    with open(QUERY_FILE) as f: queries = json.load(f)
    tasks = [(q, p) for q in queries for p in ("yt","tk","ig")]
    print(f"R9: {len(tasks)} seeds ({len(queries)} q × 3) | Start: {datetime.now().isoformat()}")
    ok=0; fail=0
    with ThreadPoolExecutor(max_workers=12) as ex:
        for i, fut in enumerate(as_completed({ex.submit(create,q,p):(q,p) for q,p in tasks}), 1):
            _, _, success, _ = fut.result()
            if success: ok+=1
            else: fail+=1
            if i%100==0 or i==len(tasks):
                print(f"  [{i}/{len(tasks)}] OK={ok} FAIL={fail}", flush=True)
    print(f"\n=== R9 DONE === OK={ok} FAIL={fail} | End: {datetime.now().isoformat()}")

if __name__ == "__main__": main()

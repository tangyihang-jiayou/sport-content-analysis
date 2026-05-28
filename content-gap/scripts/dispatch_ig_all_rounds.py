"""Create IG seeds for all 6 rounds of queries (R1-R6).

Previously only YT + TK seeds were created. This script adds the missing
Instagram platform coverage.
"""
import json, subprocess, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

HERMIT = "/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit"
DATE = "20260528"

ROUND_FILES = [
    ("R1", "/tmp/queries_weekly_20260527.json", "sports_gap_v5_ig_20260528"),
    ("R2", "/tmp/queries_zerosupply_20260528.json", "sports_gap_v5_ig_20260528"),
    ("R3", "/tmp/queries_topgap_extra_20260528.json", "sports_gap_v5_ig_20260528"),
    ("R4", "/tmp/queries_gap21to30_20260528.json", "sports_gap_v5_ig_20260528"),
    ("R5", "/tmp/queries_full_batch_20260528.json", "sports_gap_v7_ig_20260528"),
    ("R6", "/tmp/queries_highroi_10k_20260528.json", "sports_gap_v8_ig_20260528"),
]

all_tasks = []
for rname, fp, origin in ROUND_FILES:
    try:
        with open(fp) as f:
            qs = json.load(f)
        print(f"  {rname}: {len(qs)} queries -> origin={origin}")
        for q in qs:
            all_tasks.append((q, origin, rname))
    except FileNotFoundError:
        print(f"  {rname}: file not found: {fp}")

print(f"\nTotal IG seeds to create: {len(all_tasks)}")

# Dedup by query text (since some rounds may overlap)
seen = set()
unique_tasks = []
for q, origin, rname in all_tasks:
    key = q["query"].lower().strip()
    if key in seen:
        continue
    seen.add(key)
    unique_tasks.append((q, origin, rname))

print(f"After dedup: {len(unique_tasks)} unique IG seeds")

def create_ig_seed(q, origin):
    l2 = (q.get("l2") or "misc").replace("/","").replace(" ","")[:10]
    h = hashlib.md5(q["query"].encode()).hexdigest()[:6]
    name = f"ig_{l2}_{h}"[:60]
    config = json.dumps({"keyword": q["query"], "limit": 50})
    cmd = [HERMIT, "seed", "create", "--name", name, "--platform", "ig",
           "--label", "instagram_search", "--origin", origin, "--config", config,
           "--execute-type", "one_shot"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0, q["query"] if r.returncode != 0 else None

ok = fail = 0
failed_queries = []

with ThreadPoolExecutor(max_workers=20) as ex:
    futures = {ex.submit(create_ig_seed, q, origin): (q, origin, rname)
               for q, origin, rname in unique_tasks}
    for i, fut in enumerate(as_completed(futures), 1):
        success, failed_q = fut.result()
        if success:
            ok += 1
        else:
            fail += 1
            if failed_q:
                failed_queries.append(failed_q)
        if i % 500 == 0 or i == len(unique_tasks):
            print(f"  [{i}/{len(unique_tasks)}] ok={ok} fail={fail}")

print(f"\nDone: {ok} IG seeds created, {fail} failed")
if failed_queries:
    print(f"Failed sample (first 5): {failed_queries[:5]}")

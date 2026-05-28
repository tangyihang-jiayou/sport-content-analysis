import json, subprocess, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

HERMIT = "/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit"
DATE = "20260528"

with open("/tmp/queries_zerosupply_20260528.json") as f:
    queries = json.load(f)

def create_seed(q, platform):
    label = "youtube_search" if platform == "yt" else "tiktok_search"
    origin = f"sports_gap_v5_{platform}_{DATE}"
    l2 = (q.get("l2") or "misc").replace("/","").replace(" ","")[:10]
    h = hashlib.md5(q["query"].encode()).hexdigest()[:6]
    name = f"gap_{l2}_{h}_{platform}"[:60]
    config = json.dumps({"keyword": q["query"], "limit": 50})
    cmd = [HERMIT, "seed", "create", "--name", name, "--platform", platform,
           "--label", label, "--origin", origin, "--config", config, "--execute-type", "one_shot"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0

tasks = [(q, p) for q in queries for p in ["yt", "tk"]]
print(f"Total seeds: {len(tasks)}")
ok = fail = 0
with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(create_seed, q, p): i for i, (q, p) in enumerate(tasks)}
    for i, f in enumerate(as_completed(futures), 1):
        if f.result(): ok += 1
        else: fail += 1
        if i % 100 == 0 or i == len(tasks):
            print(f"  [{i}/{len(tasks)}] ok={ok} fail={fail}")

print(f"Done: {ok} ok, {fail} fail")

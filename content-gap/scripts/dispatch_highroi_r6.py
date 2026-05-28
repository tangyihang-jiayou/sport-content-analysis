import json, subprocess, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

HERMIT = "/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit"
DATE = "20260528"

with open("/tmp/queries_highroi_10k_20260528.json") as f:
    queries = json.load(f)

print(f"Loaded {len(queries)} high-ROI queries")

def create_seed(q, platform):
    label = "youtube_search" if platform == "yt" else "tiktok_search"
    origin = f"sports_gap_v8_{platform}_{DATE}"
    l2 = (q.get("l2") or "misc").replace("/","").replace(" ","")[:10]
    h = hashlib.md5(q["query"].encode()).hexdigest()[:6]
    name = f"hr_{l2}_{h}_{platform}"[:60]
    config = json.dumps({"keyword": q["query"], "limit": 50})
    cmd = [HERMIT, "seed", "create", "--name", name, "--platform", platform,
           "--label", label, "--origin", origin, "--config", config, "--execute-type", "one_shot"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0, q["query"] if r.returncode != 0 else None

tasks = [(q, p) for q in queries for p in ["yt", "tk"]]
print(f"Total seeds to create: {len(tasks)}")
ok = fail = 0
failed_queries = []

with ThreadPoolExecutor(max_workers=20) as ex:
    futures = {ex.submit(create_seed, q, p): (q, p) for q, p in tasks}
    for i, f in enumerate(as_completed(futures), 1):
        success, failed_q = f.result()
        if success:
            ok += 1
        else:
            fail += 1
            if failed_q:
                failed_queries.append(failed_q)
        if i % 500 == 0 or i == len(tasks):
            print(f"  [{i}/{len(tasks)}] ok={ok} fail={fail}")

print(f"\nDone: {ok} ok, {fail} fail")
if failed_queries:
    print(f"Failed sample (first 5): {failed_queries[:5]}")

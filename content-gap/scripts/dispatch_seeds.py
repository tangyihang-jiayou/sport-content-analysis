#!/usr/bin/env python3
"""
批量创建 hermit 爬虫种子
- Track A (gap) → YT + TK，每个query各一条
- Track B (viral) → YT + TK，每个query各一条
"""
import json, subprocess, hashlib, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

HERMIT = "/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit"
QUERY_FILE = "/tmp/queries_weekly_20260527.json"
DATE = "20260527"
VERSION = "v5"

def seed_name(q, platform):
    l2 = q.get("l2") or "viral"
    l2_abbrev = l2.replace("/", "").replace(" ", "")[:10]
    h = hashlib.md5(q["query"].encode()).hexdigest()[:6]
    src = "gap" if q["source"] == "gap" else "vrl"
    return f"{src}_{l2_abbrev}_{h}_{platform}"[:60]

def make_origin(source, platform):
    if source == "gap":
        return f"sports_gap_{VERSION}_{platform}_{DATE}"
    else:
        return f"sports_viral_{platform}_{DATE}"

def create_seed(q, platform):
    label = "youtube_search" if platform == "yt" else "tiktok_search"
    origin = make_origin(q["source"], platform)
    name = seed_name(q, platform)
    config = json.dumps({"keyword": q["query"], "limit": 50})
    cmd = [
        HERMIT, "seed", "create",
        "--name", name,
        "--platform", platform,
        "--label", label,
        "--origin", origin,
        "--config", config,
        "--execute-type", "one_shot"
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = r.stdout.strip() + r.stderr.strip()
        success = r.returncode == 0
        return (q["query"], platform, success, output)
    except Exception as e:
        return (q["query"], platform, False, str(e))

def main():
    with open(QUERY_FILE) as f:
        queries = json.load(f)

    # 每条query → YT + TK 各一条种子
    tasks = []
    for q in queries:
        tasks.append((q, "yt"))
        tasks.append((q, "tk"))

    print(f"总种子数: {len(tasks)} (YT: {len(queries)}, TK: {len(queries)})")
    print(f"开始批量创建...\n")

    ok = 0
    fail = 0
    errors = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(create_seed, q, p): (q, p) for q, p in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            query, platform, success, output = future.result()
            if success:
                ok += 1
            else:
                fail += 1
                errors.append((query, platform, output))
            if i % 50 == 0 or i == len(tasks):
                print(f"  [{i}/{len(tasks)}] 成功: {ok}, 失败: {fail}")

    print(f"\n✅ 完成！成功: {ok}, 失败: {fail}")
    if errors:
        print(f"\n失败详情 (前10条):")
        for q, p, msg in errors[:10]:
            print(f"  [{p.upper()}] {q[:60]}")
            print(f"    错误: {msg[:100]}")

if __name__ == "__main__":
    main()

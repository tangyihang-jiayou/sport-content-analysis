#!/usr/bin/env python3
"""
R7 投放：P0/P1/P2 缺口补强 (after 65k 入池)
基于 V4 深度分析报告诊断的内容缺口，三平台投放（YT+TK+IG）。

Total queries: 1,581
- P0 (1,133): 21 极度稀缺运动 (椭圆机/乒乓球/壁球/踏步机/赛艇/飞盘/曲棍球/长曲棍球/跑酷/冰球/跳绳/田径/潜水/橄榄球/板球/综合拉伸/户外徒步/运动营养/台球/皮克球/气功太极)
- P1 (346): 7 户外/极限/小众球类不足运动 (攀岩/滑板/冲浪水上/壶铃/举重竞技/羽毛球/滑冰滑雪)
- P2 (102): 12 L2 细分缺口 (篮球传球/武术太极/游泳开放水域 等)
"""
import json, subprocess, hashlib, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

HERMIT = "/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit"
QUERY_FILE = "/tmp/queries_r7_p0p1p2_20260528.json"
DATE = "20260528"
VERSION = "v9_r7"

def seed_name(q, platform):
    l1 = (q.get("l1") or "misc").replace("/", "").replace(" ", "")[:8]
    pri = q.get("priority", "P0")
    h = hashlib.md5(q["query"].encode()).hexdigest()[:6]
    return f"r7_{pri}_{l1}_{h}_{platform}"[:60]

def make_origin(platform):
    return f"sports_gap_{VERSION}_{platform}_{DATE}"

def create_seed(q, platform):
    if platform == "yt":   label = "youtube_search"
    elif platform == "tk": label = "tiktok_search"
    elif platform == "ig": label = "instagram_search"
    else: return (q["query"], platform, False, f"Unknown platform: {platform}")

    origin = make_origin(platform)
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
        return (q["query"], platform, success, output[:200])
    except Exception as e:
        return (q["query"], platform, False, str(e)[:200])

def main():
    with open(QUERY_FILE) as f:
        queries = json.load(f)

    # 每条 query × {yt, tk, ig}
    tasks = []
    for q in queries:
        for plat in ("yt", "tk", "ig"):
            tasks.append((q, plat))

    print(f"R7 投放总种子: {len(tasks)} (YT={len(queries)} + TK={len(queries)} + IG={len(queries)})")
    print(f"开始批量创建...\n")

    ok = 0
    fail = 0
    errors = []

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(create_seed, q, p): (q, p) for q, p in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            query, platform, success, output = future.result()
            if success:
                ok += 1
            else:
                fail += 1
                if len(errors) < 10:
                    errors.append((query, platform, output))
            if i % 100 == 0 or i == len(tasks):
                print(f"  [{i}/{len(tasks)}] OK: {ok}, FAIL: {fail}")

    print(f"\n=== R7 完成 ===")
    print(f"成功: {ok}, 失败: {fail}")
    if errors:
        print(f"\n前 10 个失败案例:")
        for q, p, o in errors[:10]:
            print(f"  [{p}] {q[:60]}: {o[:80]}")

if __name__ == "__main__":
    main()

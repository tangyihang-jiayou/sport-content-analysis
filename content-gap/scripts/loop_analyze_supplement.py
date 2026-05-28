#!/usr/bin/env python3
"""
Loop analysis + supplement generator
Runs each loop iteration:
1. Pull latest ingested data (from upstream pipeline output)
2. Reclassify using V6 vocab
3. Compare against baseline (V4 105k pool)
4. Identify NEW gaps + hot content
5. Generate next-round queries (R8, R9, ...)
6. Dispatch to hermit (YT+TK+IG)

Designed to run autonomously every 30-60 min for 14h.
"""
import json, re, os, sys, time, subprocess, hashlib
from collections import Counter, defaultdict
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR    = '/tmp/loop_supplement'
RULES_PATH  = '/tmp/rules_v6.json'  # synced from GitHub
HERMIT      = '/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit'

# Latest ingested data folder (upstream output)
INGEST_DIRS = [
    '/root/workspace/sport-content/data/topics/',  # adjust to actual path
    '/tmp/topics_supplement/',
]

# Baseline (V4): 105k pool with L1 distribution
BASELINE_PATH = '/tmp/baseline_v4.json'

os.makedirs(DATA_DIR, exist_ok=True)

# ── Load rules ────────────────────────────────────────────────────────────────
with open(RULES_PATH) as f:
    rules = json.load(f)
l1_rules = [(name, re.compile(pat, re.I)) for name, pat in rules['l1']]
l2_rules = defaultdict(list)
for l1, l2, pat in rules['l2']:
    try:
        l2_rules[l1].append((l2, re.compile(pat, re.I)))
    except: pass

def classify(text):
    if not text: return '其他/未分类', None
    for name, pat in l1_rules:
        if pat.search(text):
            for l2, lp in l2_rules.get(name, []):
                if lp.search(text):
                    return name, l2
            return name, None
    return '其他/未分类', None

# ── Step 1: Find latest ingested data ─────────────────────────────────────────
def find_latest_ingest():
    candidates = []
    for d in INGEST_DIRS:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith('.json'):
                    fp = os.path.join(d, f)
                    candidates.append((fp, os.path.getmtime(fp)))
    if not candidates: return None
    candidates.sort(key=lambda x: -x[1])
    return candidates[0][0]

# ── Step 2: Classify and diff against baseline ───────────────────────────────
def analyze():
    latest = find_latest_ingest()
    if not latest:
        print("No new ingest data found")
        return None

    with open(latest) as f:
        new_data = json.load(f)
    print(f"Latest ingest: {latest} ({len(new_data)} rows)")

    classified = Counter()
    for r in new_data:
        text = ' '.join(str(r.get(f) or '') for f in ['topic','original_title','description'])
        l1, l2 = classify(text)
        classified[l1] += 1

    # Load baseline
    if os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH) as f:
            baseline = json.load(f)
    else:
        baseline = {'l1_total': {}}

    return {
        'timestamp': datetime.now().isoformat(),
        'latest_file': latest,
        'new_total': sum(classified.values()),
        'new_l1': dict(classified),
        'baseline_l1': baseline.get('l1_total', {}),
    }

# ── Step 3: Identify gaps and generate next-round queries ────────────────────
def identify_gaps(analysis):
    if not analysis: return []
    baseline = analysis['baseline_l1']
    new_l1 = analysis['new_l1']

    combined = {**baseline}
    for k, v in new_l1.items():
        combined[k] = combined.get(k, 0) + v

    # Find gaps: total < 1500 or recent ingestion not meeting demand
    gaps = []
    for l1, total in combined.items():
        if l1 == '其他/未分类': continue
        if total < 500:
            gaps.append({'l1': l1, 'total': total, 'priority': 'P0', 'need': 1500-total})
        elif total < 1500:
            gaps.append({'l1': l1, 'total': total, 'priority': 'P1', 'need': 2000-total})
        elif total < 3000 and new_l1.get(l1, 0) < 100:
            gaps.append({'l1': l1, 'total': total, 'priority': 'P2', 'need': 1500})
    gaps.sort(key=lambda g: g['total'])
    return gaps

# ── Step 4: Generate queries ─────────────────────────────────────────────────
QUERY_TEMPLATES = [
    '{} for beginners', '{} basic technique', '{} training routine',
    '{} drills', '{} common mistakes', '{} proper form',
    'how to start {}', 'advanced {} tips', '{} tutorial',
    'master {}', 'pro {} techniques', '{} workout plan',
    'best {} drills', '{} home workout', '{} progression',
]

# L1 to English term mapping (extend as needed)
L1_EN = {
    '椭圆机': 'elliptical machine', '乒乓球': 'table tennis', '壁球/手球': 'squash',
    '踏步机': 'stair climber', '赛艇/皮划艇': 'rowing kayaking', '飞盘': 'frisbee ultimate',
    '曲棍球': 'field hockey', '长曲棍球': 'lacrosse', '跑酷': 'parkour', '冰球': 'ice hockey',
    '跳绳': 'jump rope', '田径': 'track and field', '潜水': 'scuba diving',
    '橄榄球': 'rugby football', '板球': 'cricket sport', '综合拉伸': 'stretching mobility',
    '户外/徒步': 'hiking backpacking', '运动营养': 'sports nutrition',
    '台球/斯诺克': 'billiards pool snooker', '皮克球': 'pickleball',
    '气功/太极': 'tai chi qigong', '攀岩': 'rock climbing', '滑板': 'skateboarding',
    '冲浪/水上': 'surfing paddleboard', '壶铃': 'kettlebell', '举重竞技': 'olympic weightlifting',
    '羽毛球': 'badminton', '滑冰/滑雪': 'skiing snowboarding ice skating',
    '柔韧/活动度': 'mobility flexibility', '体姿矫正/PT': 'posture correction physical therapy',
    '睡眠/恢复': 'sleep recovery athlete', '心肺/HIIT': 'HIIT cardio interval',
}

def generate_queries(gaps, max_per_l1=20):
    qs = []
    for g in gaps:
        en = L1_EN.get(g['l1'], g['l1'])
        for tmpl in QUERY_TEMPLATES[:max_per_l1]:
            qs.append({
                'query': tmpl.format(en),
                'source': 'gap',
                'l1': g['l1'],
                'l2': '',
                'priority': g['priority'],
            })
    return qs

# ── Step 5: Dispatch queries ──────────────────────────────────────────────────
def dispatch_seeds(queries, round_tag):
    """Dispatch to YT + TK + IG via hermit"""
    ok = 0; fail = 0
    DATE = datetime.now().strftime('%Y%m%d')
    for q in queries:
        for platform in ('yt', 'tk', 'ig'):
            label_map = {'yt':'youtube_search','tk':'tiktok_search','ig':'instagram_search'}
            l1_short = (q['l1'] or 'misc').replace('/','').replace(' ','')[:8]
            h = hashlib.md5(q['query'].encode()).hexdigest()[:6]
            name = f"{round_tag}_{l1_short}_{h}_{platform}"[:60]
            origin = f"sports_gap_{round_tag}_{platform}_{DATE}"
            config = json.dumps({"keyword": q['query'], "limit": 50})
            cmd = [HERMIT, "seed", "create", "--name", name, "--platform", platform,
                   "--label", label_map[platform], "--origin", origin,
                   "--config", config, "--execute-type", "one_shot"]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                if r.returncode == 0: ok += 1
                else: fail += 1
            except: fail += 1
    return ok, fail

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    round_tag = f"loop_{datetime.now().strftime('%Y%m%d_%H%M')}"
    print(f"\n=== LOOP iteration: {round_tag} ===")

    analysis = analyze()
    if analysis:
        gap_path = f"{DATA_DIR}/analysis_{round_tag}.json"
        with open(gap_path, 'w') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"Analysis saved: {gap_path}")

        gaps = identify_gaps(analysis)
        print(f"Identified gaps: {len(gaps)}")
        for g in gaps[:10]:
            print(f"  {g['l1']:<14} total={g['total']:>6} priority={g['priority']}")

        queries = generate_queries(gaps)
        q_path = f"{DATA_DIR}/queries_{round_tag}.json"
        with open(q_path, 'w') as f:
            json.dump(queries, f, ensure_ascii=False, indent=2)
        print(f"Generated {len(queries)} queries: {q_path}")

        # Optional: dispatch
        if '--dispatch' in sys.argv:
            ok, fail = dispatch_seeds(queries, round_tag)
            print(f"Dispatched: OK={ok}, FAIL={fail}")

if __name__ == '__main__':
    main()

"""
Step 1: Assemble unified clean pool from all delivered batches.
Classify each with V6 rules (L1/L2) for blocking. Keep view_count for tiebreak.
"""
import json, re, os
from collections import Counter, defaultdict

os.makedirs('/tmp/dedup', exist_ok=True)

SOURCES = [
    ('/Users/ricktang/Desktop/sport_v054_65k_final.json', 'v054_65k'),
    ('/Users/ricktang/Downloads/sport_v051_19072_clean.json', 'v051_19k'),
    ('/Users/ricktang/Desktop/sport_v053_12k_final.json', 'v053_12k'),
    ('/Users/ricktang/Downloads/sport_v051_indb.json', 'indb1'),
    ('/Users/ricktang/Downloads/sport_v051_indb_batch2.json', 'indb2'),
]

with open('/tmp/qc_59k/rules_v6.json') as f:
    rules = json.load(f)
l1_rules = [(n, re.compile(p, re.I)) for n, p in rules['l1']]
l2_rules = defaultdict(list)
for l1, l2, pat in rules['l2']:
    try: l2_rules[l1].append((l2, re.compile(pat, re.I)))
    except: pass

def classify(text):
    if not text: return '其他', None
    for n, p in l1_rules:
        if p.search(text):
            for l2, lp in l2_rules.get(n, []):
                if lp.search(text):
                    return n, l2
            return n, None
    return '其他', None

pool = []
seen_tid = set()
dup_tid = 0
for path, batch in SOURCES:
    with open(path) as f:
        data = json.load(f)
    for r in data:
        tid = r.get('topic_id')
        if not tid or tid in seen_tid:
            dup_tid += 1
            continue
        seen_tid.add(tid)
        topic = r.get('topic') or ''
        if not topic:
            continue
        clf_text = ' '.join(str(r.get(f) or '') for f in ['topic','original_title','description'])
        l1, l2 = classify(clf_text)
        pool.append({
            'topic_id': tid,
            'topic': topic,
            'batch': batch,
            'view_count': int(r.get('view_count') or r.get('views') or 0),
            'l1': l1, 'l2': l2,
            # keep all original fields for final output
            '_orig': r,
        })

print(f"Assembled pool: {len(pool)} (dropped {dup_tid} topic_id dups)")
print(f"\nBatch breakdown:")
for b, c in Counter(p['batch'] for p in pool).most_common():
    print(f"  {b}: {c}")
print(f"\nL1 blocks (top 15):")
for l1, c in Counter(p['l1'] for p in pool).most_common(15):
    print(f"  {l1}: {c}")

with open('/tmp/dedup/pool.json', 'w') as f:
    json.dump(pool, f, ensure_ascii=False)
print(f"\nSaved /tmp/dedup/pool.json")

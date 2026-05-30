"""
Corrected dedup: GREEDY representative method (no chaining) at calibrated TAU=0.85.
Calibration (Gemini judge): same-question rate is 100% at 0.84-0.86, knee at 0.84,
drops to 70% at 0.82-0.84 and ~50% below 0.82. So 0.85 = high precision (~90%+).
Greedy: keep highest-view item as representative, remove items >=TAU to a KEPT rep.
"""
import json, sys, numpy as np
from collections import defaultdict, Counter
np.seterr(all='ignore')

TAU = float(sys.argv[1]) if len(sys.argv) > 1 else 0.85
pool = json.load(open('/tmp/dedup/pool.json'))
embs = np.load('/tmp/dedup/embeddings.npy').astype(np.float32)
N = len(pool)

blocks = defaultdict(list)
for i,p in enumerate(pool): blocks[p['l1']].append(i)

removed = np.zeros(N, dtype=bool)
removed_pairs = []   # (kept_idx, removed_idx) samples
rep_of = {}          # removed -> its representative

for l1, idxs in blocks.items():
    m = len(idxs)
    if m < 2: continue
    idxs = np.array(idxs)
    sub = embs[idxs]                                  # (m, d)
    # order by view_count desc (keep popular as reps), tiebreak longer topic
    order = sorted(range(m), key=lambda k: (pool[idxs[k]]['view_count'], len(pool[idxs[k]]['topic'])), reverse=True)
    local_removed = np.zeros(m, dtype=bool)
    for k in order:
        if local_removed[k]:
            continue
        # k is a representative; find all not-yet-removed within TAU
        sims = sub @ sub[k]                            # (m,)
        hit = (sims >= TAU) & (~local_removed)
        hit[k] = False
        idx_hits = np.where(hit)[0]
        for h in idx_hits:
            local_removed[h] = True
            gi_rep, gi_rem = int(idxs[k]), int(idxs[h])
            rep_of[gi_rem] = gi_rep
            if len(removed_pairs) < 60:
                removed_pairs.append((gi_rep, gi_rem, float(sims[h])))
    for k in range(m):
        if local_removed[k]:
            removed[idxs[k]] = True

n_rem = int(removed.sum())
keep_idx = [i for i in range(N) if not removed[i]]
print(f"TAU={TAU} (GREEDY representative method)")
print(f"Original={N}  Kept={len(keep_idx)}  Removed={n_rem} ({n_rem/N*100:.1f}%)")

rem_by_l1 = Counter(pool[i]['l1'] for i in range(N) if removed[i])
print("\nRemoved by L1 (top 15):")
for l1,c in rem_by_l1.most_common(15):
    tot=len(blocks[l1])
    print(f"  {l1:<14} {c:>5} / {tot} ({c/tot*100:.0f}%)")

print(f"\n=== sample removed pairs (kept ← removed) ===")
import random; random.seed(9)
for rep,rem,s in random.sample(removed_pairs, min(18,len(removed_pairs))):
    print(f"  sim={s:.3f} [{pool[rep]['l1']}]")
    print(f"    KEEP: {pool[rep]['topic'][:78]}")
    print(f"    DROP: {pool[rem]['topic'][:78]}")

if '--save' in sys.argv:
    deduped=[pool[i]['_orig'] for i in keep_idx]
    json.dump(deduped, open('/Users/ricktang/Desktop/sport_pool_dedup.json','w'), ensure_ascii=False, indent=2)
    json.dump({'tau':TAU,'method':'greedy_representative','original':N,'kept':len(keep_idx),
               'removed':n_rem,'removed_pct':n_rem/N*100,'removed_by_l1':dict(rem_by_l1)},
              open('/tmp/dedup/dedup_report.json','w'), ensure_ascii=False, indent=2)
    print(f"\nSAVED deduped pool: {len(deduped)} -> /Users/ricktang/Desktop/sport_pool_dedup.json")

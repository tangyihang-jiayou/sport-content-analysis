import os
"""
Merge synthetic gap-sport topics into the deduped pool with cross-pool semantic dedup.
- Load existing deduped pool (101,111) + its embeddings
- Load all clean_*.json synthetic topics
- Embed synthetic topics (Gemini)
- Drop synthetic that are near-dups (cos>=0.92) of EXISTING (same L1 block) or of each other
- Merge survivors -> final pool. Report per-sport before/after.
"""
import json, glob, re, asyncio, time, os
import numpy as np
import httpx
from collections import Counter, defaultdict

API_KEY = os.environ.get("GEMINI_API_KEY", "")
EURL=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={API_KEY}"
DIM=768; TAU=0.85

# rules
rules=json.load(open('/tmp/qc_59k/rules_v6.json'))
l1_rules=[(n,re.compile(p,re.I)) for n,p in rules['l1']]
def cls(t):
    if not t: return '其他'
    for n,p in l1_rules:
        if p.search(t): return n
    return '其他'

# existing pool + embeddings (aligned with /tmp/dedup/pool.json order, but pool.json is PRE-dedup 104k)
# We need embeddings for the DEDUPED pool. Rebuild from pool.json + dedup keep set via topic_id.
pool_all=json.load(open('/tmp/dedup/pool.json'))
emb_all=np.load('/tmp/dedup/embeddings.npy').astype(np.float32)
dedup_pool=json.load(open('/Users/ricktang/Desktop/sport_pool_dedup.json'))
keep_tids={r['topic_id'] for r in dedup_pool}
tid2idx={p['topic_id']:i for i,p in enumerate(pool_all)}
# existing embeddings by L1 (only kept ones)
exist_by_l1=defaultdict(list)   # l1 -> list of (emb_idx)
for p in pool_all:
    if p['topic_id'] in keep_tids:
        exist_by_l1[p['l1']].append(tid2idx[p['topic_id']])
print(f"Existing deduped pool: {len(dedup_pool)} | embeddings indexed")

# load synthetic (round-1 clean_*.json + round-2 clean2_*.json)
synth=[]
for f in sorted(glob.glob('/tmp/supp/clean_*.json')) + sorted(glob.glob('/tmp/supp/clean2_*.json')):
    try: synth+=json.load(open(f))
    except: pass
# dedup synthetic by topic_id
seen=set(); syn2=[]
for r in synth:
    if r['topic_id'] in seen: continue
    seen.add(r['topic_id']); syn2.append(r)
synth=syn2
print(f"Synthetic clean topics loaded: {len(synth)}")
if not synth:
    print("No synthetic topics yet."); raise SystemExit

# embed synthetic
async def embed_all(texts):
    out=np.zeros((len(texts),DIM),dtype=np.float32)
    sem=asyncio.Semaphore(12)
    async def one(bi,idxs,client):
        reqs=[{"model":"models/gemini-embedding-001","content":{"parts":[{"text":texts[i][:2000]}]},"outputDimensionality":DIM} for i in idxs]
        for att in range(6):
            try:
                async with sem:
                    r=await client.post(EURL,json={"requests":reqs},timeout=60)
                r.raise_for_status()
                for j,i in enumerate(idxs):
                    v=np.array(r.json()["embeddings"][j]["values"],dtype=np.float32)
                    n=np.linalg.norm(v); out[i]=v/n if n>0 else v
                return
            except Exception:
                await asyncio.sleep(min(2**att,30))
    async with httpx.AsyncClient() as client:
        batches=[(bi,list(range(s,min(s+50,len(texts))))) for bi,s in enumerate(range(0,len(texts),50))]
        await asyncio.gather(*[one(bi,idxs,client) for bi,idxs in batches])
    return out

t0=time.time()
syn_emb=asyncio.run(embed_all([r['topic'] for r in synth]))
print(f"Embedded {len(synth)} synthetic in {time.time()-t0:.0f}s")

# classify synthetic L1 (use l1_gen if present else classify)
for r in synth:
    r['_l1']=r.get('l1_gen') or cls(r['topic'])

# dedup: drop synthetic near-dup of existing (same L1) or earlier-accepted synthetic
keep=[]; kept_emb_by_l1=defaultdict(list)  # l1 -> list of emb vectors (accepted synth)
drop_exist=0; drop_intra=0
order=sorted(range(len(synth)), key=lambda i:-len(synth[i]['topic']))  # prefer longer/richer first
for i in order:
    l1=synth[i]['_l1']; v=syn_emb[i]
    # vs existing
    ex=exist_by_l1.get(l1,[])
    dup=False
    if ex:
        E=emb_all[ex]   # (m,dim)
        if np.max(E@v) >= TAU: dup=True; drop_exist+=1
    if not dup and kept_emb_by_l1[l1]:
        K=np.stack(kept_emb_by_l1[l1])
        if np.max(K@v) >= TAU: dup=True; drop_intra+=1
    if not dup:
        keep.append(i); kept_emb_by_l1[l1].append(v)

kept_synth=[synth[i] for i in keep]
print(f"\nSynthetic dedup: {len(synth)} -> kept {len(kept_synth)} (drop vs existing {drop_exist}, intra {drop_intra})")
per_sport=Counter(r['_l1'] for r in kept_synth)
print("Kept synthetic per sport:")
for s,c in per_sport.most_common():
    print(f"  {s:<14} +{c}")

# strip helper fields, merge
def clean_rec(r):
    return {k:v for k,v in r.items() if not k.startswith('_')}
final = dedup_pool + [clean_rec(r) for r in kept_synth]
json.dump(final, open('/Users/ricktang/Desktop/sport_pool_final_100k.json','w'), ensure_ascii=False, indent=2)
print(f"\n=== FINAL POOL: {len(final)} (existing {len(dedup_pool)} + synthetic {len(kept_synth)}) ===")
print("Saved: /Users/ricktang/Desktop/sport_pool_final_100k.json")

# report
json.dump({'existing':len(dedup_pool),'synth_generated':len(synth),'synth_kept':len(kept_synth),
           'drop_vs_existing':drop_exist,'drop_intra':drop_intra,'final':len(final),
           'per_sport_added':dict(per_sport)}, open('/tmp/supp/merge_report.json','w'), ensure_ascii=False, indent=2)

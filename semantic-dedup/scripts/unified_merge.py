"""
Unified priority merge: real-deduped base + real video-grounded + synthetic.
Priority (greedy, keep earlier tiers; drop later items >=0.85 to a kept same-L1 item):
  Tier1: 81,273 real-deduped (proven, real views) — all kept as base
  Tier2: 2,824 real video-grounded (real crawled source, real views) — fills gaps not in base
  Tier3: synthetic (view=0) — only where neither real tier covers
=> real content prioritized; synthetic superseded by real where they overlap.
"""
import json, glob, re, asyncio, time
import numpy as np
import httpx
from collections import defaultdict, Counter
np.seterr(all='ignore')

API_KEY = __import__("os").environ.get("GEMINI_API_KEY","")
EURL=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={API_KEY}"
DIM=768; TAU=0.85

rules=json.load(open('/tmp/qc_59k/rules_v6.json'))
l1_rules=[(n,re.compile(p,re.I)) for n,p in rules['l1']]
def cls(t):
    if not t: return '其他'
    for n,p in l1_rules:
        if p.search(t): return n
    return '其他'

# Tier1: real-deduped base + its embeddings
pool_all=json.load(open('/tmp/dedup/pool.json'))
emb_all=np.load('/tmp/dedup/embeddings.npy').astype(np.float32)
dedup_pool=json.load(open('/Users/ricktang/Desktop/sport_pool_dedup.json'))
keep_tids={r['topic_id'] for r in dedup_pool}
tid2idx={p['topic_id']:i for i,p in enumerate(pool_all)}
tier1=[]; t1_emb=[]
for p in pool_all:
    if p['topic_id'] in keep_tids:
        tier1.append(p['_orig']); t1_emb.append(emb_all[tid2idx[p['topic_id']]])
print(f"Tier1 (real-deduped base): {len(tier1)}")

# Tier2: real video-grounded (batch1 real_clean + batch2 harvest_clean)
import glob as _g
tier2=[]
for f in ['/tmp/supp/real_clean.json','/tmp/supp/harvest_clean.json']:
    try: tier2+=json.load(open(f))
    except: pass
# dedup by url (same video may appear in both batches)
_seen=set(); _t2=[]
for r in tier2:
    u=r.get('url','')
    if u and u in _seen: continue
    if u: _seen.add(u)
    _t2.append(r)
tier2=_t2
print(f"Tier2 (real video-grounded, 2 batches): {len(tier2)}")

# Tier3: synthetic (raw clean, will be deduped)
tier3=[]
for f in sorted(glob.glob('/tmp/supp/clean_*.json'))+sorted(glob.glob('/tmp/supp/clean2_*.json')):
    try: tier3+=json.load(open(f))
    except: pass
seen=set(); t3=[]
for r in tier3:
    if r['topic_id'] in seen: continue
    seen.add(r['topic_id']); t3.append(r)
tier3=t3
print(f"Tier3 (synthetic): {len(tier3)}")

# embed tier2 + tier3
async def embed(texts):
    out=np.zeros((len(texts),DIM),dtype=np.float32); sem=asyncio.Semaphore(12)
    async def one(idxs,client):
        reqs=[{"model":"models/gemini-embedding-001","content":{"parts":[{"text":texts[i][:2000]}]},"outputDimensionality":DIM} for i in idxs]
        for att in range(6):
            try:
                async with sem:
                    r=await client.post(EURL,json={"requests":reqs},timeout=60)
                r.raise_for_status()
                for j,i in enumerate(idxs):
                    v=np.array(r.json()["embeddings"][j]["values"],dtype=np.float32); n=np.linalg.norm(v)
                    out[i]=v/n if n>0 else v
                return
            except Exception: await asyncio.sleep(min(2**att,30))
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[one(list(range(s,min(s+50,len(texts)))),client) for s in range(0,len(texts),50)])
    return out

t0=time.time()
e2=asyncio.run(embed([r['topic'] for r in tier2]))
e3=asyncio.run(embed([r['topic'] for r in tier3]))
print(f"Embedded tier2+tier3 in {time.time()-t0:.0f}s")

# L1 for each
for r in tier2: r['_l1']=r.get('l1_gap') or cls(r['topic'])
for r in tier3: r['_l1']=r.get('l1_gen') or cls(r['topic'])

# kept per L1: start with tier1
kept_emb=defaultdict(list);
for r,e in zip(tier1,t1_emb):
    kept_emb[cls(' '.join(str(r.get(f) or '') for f in ['topic','original_title','description']))].append(e)

final=list(tier1)
added2=Counter(); added3=Counter(); drop2=0; drop3=0; up=0

def try_add(rec, emb, l1, tierlabel):
    global drop2, drop3
    K=kept_emb.get(l1)
    if K and np.max(np.stack(K)@emb) >= TAU:
        if tierlabel=='t2': drop2_inc()
        else: drop3_inc()
        return False
    kept_emb[l1].append(emb); final.append(rec); return True

# tier2 first (real-grounded), then tier3 (synthetic)
for r,e in zip(tier2,e2):
    l1=r['_l1']; K=kept_emb.get(l1)
    if K and np.max(np.stack(K)@e)>=TAU: drop2+=1; continue
    kept_emb[l1].append(e); final.append({k:v for k,v in r.items() if not k.startswith('_')}); added2[l1]+=1
for r,e in zip(tier3,e3):
    l1=r['_l1']; K=kept_emb.get(l1)
    if K and np.max(np.stack(K)@e)>=TAU: drop3+=1; continue
    kept_emb[l1].append(e); final.append({k:v for k,v in r.items() if not k.startswith('_')}); added3[l1]+=1

print(f"\nTier2 real-grounded: added {sum(added2.values())}, dropped {drop2}")
print(f"Tier3 synthetic: added {sum(added3.values())}, dropped {drop3} (many superseded by real)")
print(f"\n=== FINAL: {len(final)} (tier1 {len(tier1)} + real-grounded {sum(added2.values())} + synthetic {sum(added3.values())}) ===")
json.dump(final, open('/Users/ricktang/Desktop/sport_pool_final_100k.json','w'), ensure_ascii=False, indent=2)
print("Saved /Users/ricktang/Desktop/sport_pool_final_100k.json")
json.dump({'tier1':len(tier1),'tier2_added':sum(added2.values()),'tier2_dropped':drop2,
           'tier3_added':sum(added3.values()),'tier3_dropped':drop3,'final':len(final),
           'real_grounded_per_sport':dict(added2)}, open('/tmp/supp/unified_merge_report.json','w'), ensure_ascii=False, indent=2)

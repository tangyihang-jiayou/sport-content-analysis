import os
"""
Empirically find the right dedup threshold: sample pairs per similarity band,
have Gemini judge "same teaching question?" — removes my subjective bias.
"""
import json, numpy as np, asyncio, re, random
import httpx
from collections import defaultdict
np.seterr(all='ignore')

API_KEY = os.environ.get("GEMINI_API_KEY", "")
URL=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

pool=json.load(open('/tmp/dedup/pool.json'))
embs=np.load('/tmp/dedup/embeddings.npy').astype(np.float32)
blocks=defaultdict(list)
for i,p in enumerate(pool): blocks[p['l1']].append(i)

BANDS=[(0.84,0.86),(0.86,0.88),(0.88,0.90),(0.90,0.92),(0.92,0.94),(0.94,1.01)]
random.seed(7)
# collect candidate pairs per band (sample across L1 blocks)
band_pairs={b:[] for b in BANDS}
l1_order=sorted(blocks, key=lambda k:-len(blocks[k]))
for l1 in l1_order:
    idxs=blocks[l1]
    if len(idxs)<2: continue
    sub=embs[idxs]
    # sample up to 800 items in this block to keep it fast
    samp=idxs if len(idxs)<=800 else random.sample(idxs,800)
    S=embs[samp]
    sims=S@S.T
    for a in range(len(samp)):
        for b in range(a+1,len(samp)):
            s=sims[a,b]
            for lo,hi in BANDS:
                if lo<=s<hi:
                    if len(band_pairs[(lo,hi)])<200:
                        band_pairs[(lo,hi)].append((samp[a],samp[b],float(s)))
                    break
    if all(len(v)>=200 for v in band_pairs.values()): break

# sample 30 per band to judge
to_judge=[]
for b in BANDS:
    ps=band_pairs[b]
    pick=random.sample(ps,min(30,len(ps)))
    for (i,j,s) in pick:
        to_judge.append({'band':f"{b[0]}-{b[1]}",'i':i,'j':j,'sim':s,
                         'a':pool[i]['topic'],'bt':pool[j]['topic'],'l1':pool[i]['l1']})
print(f"Judging {len(to_judge)} pairs across {len(BANDS)} bands")

SYS="""You compare two sports teaching-video topics. Decide if they ask ESSENTIALLY THE SAME teaching question / cover the same core teaching point such that keeping BOTH is redundant for a content library.
- SAME (redundant): same skill + same angle/intent, just reworded. A creator making a video for one would make basically the same video for the other.
- DIFFERENT (keep both): different skill, different sub-aspect, different audience, or different angle — they'd produce genuinely different videos.
Answer with a JSON array, one object per pair: [{"id":N,"verdict":"SAME"|"DIFF"}]. Output ONLY JSON."""

async def judge(batch,client,sem):
    payload="\n".join(f'{k}. A: {p["a"]}\n   B: {p["bt"]}' for k,p in enumerate(batch))
    body={"system_instruction":{"parts":[{"text":SYS}]},
          "contents":[{"role":"user","parts":[{"text":f"Judge these {len(batch)} pairs:\n\n{payload}"}]}],
          "generationConfig":{"temperature":0,"maxOutputTokens":3000,"thinkingConfig":{"thinkingBudget":0}}}
    for att in range(4):
        try:
            async with sem:
                r=await client.post(URL,json=body,timeout=60)
            r.raise_for_status()
            raw="".join(x.get("text","") for x in r.json()["candidates"][0]["content"]["parts"])
            m=re.search(r'\[.*\]',raw,re.DOTALL)
            return json.loads(m.group())
        except Exception:
            await asyncio.sleep(2**att)
    return [{"id":k,"verdict":"?"} for k in range(len(batch))]

async def main():
    sem=asyncio.Semaphore(8); BS=10
    batches=[to_judge[i:i+BS] for i in range(0,len(to_judge),BS)]
    async with httpx.AsyncClient() as client:
        res=await asyncio.gather(*[judge(b,client,sem) for b in batches])
    # attach verdicts
    for bi,verds in enumerate(res):
        for v in verds:
            gi=bi*BS+v['id']
            if gi<len(to_judge): to_judge[gi]['verdict']=v['verdict']
    # tally by band
    from collections import Counter
    band_tally=defaultdict(lambda:Counter())
    for p in to_judge:
        band_tally[p['band']][p.get('verdict','?')]+=1
    print("\n=== SAME-question rate by similarity band (Gemini judge) ===")
    for b in BANDS:
        key=f"{b[0]}-{b[1]}"; t=band_tally[key]
        tot=t['SAME']+t['DIFF']
        rate=t['SAME']/tot*100 if tot else 0
        print(f"  {key}: SAME={t['SAME']:>2} DIFF={t['DIFF']:>2}  → same-rate {rate:.0f}%")
    # show sample SAME and DIFF in mid bands
    print("\n=== sample pairs in 0.86-0.90 ===")
    mid=[p for p in to_judge if p['band'] in ('0.86-0.88','0.88-0.9')]
    for p in random.sample(mid,min(10,len(mid))):
        print(f"  [{p['verdict']}|{p['sim']:.3f}|{p['l1']}]")
        print(f"    A: {p['a'][:75]}")
        print(f"    B: {p['bt'][:75]}")
    json.dump(to_judge, open('/tmp/dedup/band_judgments.json','w'), ensure_ascii=False, indent=2)

asyncio.run(main())

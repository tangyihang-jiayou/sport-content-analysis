"""Comprehensive real-ingest harvest: all sports × 3 platforms, with hot metrics."""
import subprocess, json, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
HERMIT="/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit"
terms=json.load(open('/tmp/harvest_terms.json',encoding='utf-8'))
PLAT=['yt','tk','ig']; LIMIT=50
def search(sport,plat,kw):
    try:
        r=subprocess.run([HERMIT,"--json","search",plat,kw,"--limit",str(LIMIT)],capture_output=True,text=True,timeout=45)
        return (sport,plat,json.loads(r.stdout).get("items",[])) if r.returncode==0 else (sport,plat,[])
    except Exception: return (sport,plat,[])
tasks=[(s,p,t) for s,ts in terms.items() for t in ts for p in PLAT]
print(f"{len(tasks)} searches")
by_sport=defaultdict(list); seen=set(); t0=time.time(); done=0
with ThreadPoolExecutor(max_workers=24) as ex:
    for f in as_completed([ex.submit(search,s,p,t) for s,p,t in tasks]):
        sport,plat,items=f.result(); done+=1
        for it in items:
            u=it.get('url','')
            if not u or u in seen: continue
            seen.add(u)
            ti=it.get('title','') or ''; de=it.get('description','') or ''
            if len(ti)+len(de)<20: continue
            pr=it.get('properties',{})
            by_sport[sport].append({'url':u,'title':ti,'description':de,'platform':it.get('source',''),
                'views':pr.get('views',0),'likes':pr.get('likes',0),'author':it.get('author',''),'l1_gap':sport})
        if done%40==0: print(f"  {done}/{len(tasks)}, {len(seen)} vids, {time.time()-t0:.0f}s",flush=True)
flat=[v for vs in by_sport.values() for v in vs]
json.dump(flat,open('/tmp/harvest_source.json','w'),ensure_ascii=False,indent=2)
print(f"\nDONE: {len(flat)} real videos, {len(by_sport)} sports, {time.time()-t0:.0f}s")

"""Parallel pull of REAL crawled videos from hermit (gap sports × 3 platforms)."""
import subprocess, json, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

HERMIT = "/root/workspace/shadow_worker/skills/hermit-cli/scripts/hermit"
cfg = json.load(open('/tmp/sport_cfg.json', encoding='utf-8'))
PLATFORMS = ['yt', 'tk', 'ig']
LIMIT = 50

def search(sport, platform, keyword):
    try:
        r = subprocess.run([HERMIT, "--json", "search", platform, keyword, "--limit", str(LIMIT)],
                           capture_output=True, text=True, timeout=45)
        if r.returncode != 0: return sport, []
        return sport, json.loads(r.stdout).get("items", [])
    except Exception:
        return sport, []

# build all (sport, platform, term) tasks
tasks = []
for sport, c in cfg.items():
    for term in c['terms'][:3]:
        for plat in PLATFORMS:
            tasks.append((sport, plat, term))
print(f"{len(tasks)} parallel searches (32 sports × ≤3 terms × 3 platforms)")

by_sport = defaultdict(list); seen=set(); t0=time.time(); done=0
with ThreadPoolExecutor(max_workers=20) as ex:
    futs = [ex.submit(search, s, p, t) for s,p,t in tasks]
    for f in as_completed(futs):
        sport, items = f.result(); done+=1
        for it in items:
            url = it.get('url','')
            if not url or url in seen: continue
            seen.add(url)
            title=it.get('title','') or ''; desc=it.get('description','') or ''
            if len(title)+len(desc) < 20: continue
            props=it.get('properties',{})
            by_sport[sport].append({'url':url,'title':title,'description':desc,
                'platform':it.get('source',''),'views':props.get('views',0),
                'likes':props.get('likes',0),'author':it.get('author',''),'l1_gap':sport})
        if done%30==0: print(f"  {done}/{len(tasks)} searches, {len(seen)} unique vids, {time.time()-t0:.0f}s", flush=True)

flat=[v for vs in by_sport.values() for v in vs]
json.dump(flat, open('/tmp/real_source.json','w'), ensure_ascii=False, indent=2)
print(f"\nDONE: {len(flat)} real videos, {len(by_sport)} sports, {time.time()-t0:.0f}s -> /tmp/real_source.json")
for s,v in sorted(by_sport.items(), key=lambda x:-len(x[1])):
    print(f"  {s}: {len(v)}")

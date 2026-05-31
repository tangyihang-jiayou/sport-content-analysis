"""Quality filter for REAL video-grounded topics: removes entertainment-derived JUNK
(highlights/stunts/vlogs/performances) that pass rule-QC but aren't teaching topics.
Standard 3rd step of real-grounded flow: gen_real_grounded → qc_gap → quality_filter.
Usage: python3 quality_filter.py --in clean.json --out filtered.json
       python3 quality_filter.py --pool   (filter the final pool's real_ingest tier in place)
"""
import json, asyncio, re, argparse
import httpx
import os
API_KEY=os.environ.get("GEMINI_API_KEY","")
URL=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
SYS="""You audit sports-content-pool topics derived from real crawled videos. Classify each:
- GOOD: genuine teaching/instructional topic (teaches a skill/technique/drill/concept or actionable insight a creator could make an instructional video from).
- JUNK: description of an ENTERTAINMENT clip — highlight/trick-shot reel, stunt/POV thrill, competition recap, music/dance performance w/o instruction, "wow look at this" moment, pure vlog/travel/lifestyle, meme, news. No teaching value.
Be strict: if it just describes/admires a feat or experience without teaching, JUNK.
Output JSON array [{"id":N,"verdict":"GOOD"|"JUNK"}]. ONLY JSON."""
async def judge(batch,client,sem):
    payload="\n".join(f'{i}. {t}' for i,t in enumerate(batch))
    async with sem:
        for att in range(4):
            try:
                r=await client.post(URL,json={"system_instruction":{"parts":[{"text":SYS}]},"contents":[{"role":"user","parts":[{"text":f"Audit {len(batch)} topics:\n\n{payload}"}]}],"generationConfig":{"temperature":0,"maxOutputTokens":2500,"thinkingConfig":{"thinkingBudget":0}}},timeout=60)
                r.raise_for_status()
                raw="".join(p.get("text","") for p in r.json()["candidates"][0]["content"]["parts"])
                return json.loads(re.search(r'\[.*\]',raw,re.DOTALL).group())
            except Exception: await asyncio.sleep(2**att)
    return [{"id":i,"verdict":"GOOD"} for i in range(len(batch))]
async def filt(topics):
    sem=asyncio.Semaphore(10); BS=15; verds={}
    batches=[(s,topics[s:s+BS]) for s in range(0,len(topics),BS)]
    async with httpx.AsyncClient() as c:
        async def work(s,b):
            for v in await judge(b,c,sem):
                if s+v['id']<len(topics): verds[s+v['id']]=v['verdict']
        await asyncio.gather(*[work(s,b) for s,b in batches])
    return verds
async def main(a):
    if a.pool:
        f=json.load(open('/Users/ricktang/Desktop/sport_pool_final_100k.json'))
        idx=[i for i,r in enumerate(f) if r.get('tier')=='real_ingest']
        verds=await filt([f[i]['topic'] for i in idx])
        junk=set(idx[i] for i in range(len(idx)) if verds.get(i)=='JUNK')
        kept=[r for i,r in enumerate(f) if i not in junk]
        json.dump(kept,open('/Users/ricktang/Desktop/sport_pool_final_100k.json','w'),ensure_ascii=False,indent=2)
        print(f"Pool {len(f)} -> {len(kept)} (removed {len(junk)} junk, {len(junk)/max(1,len(idx))*100:.1f}% of real)")
    else:
        d=json.load(open(a.inp)); verds=await filt([r['topic'] for r in d])
        kept=[r for i,r in enumerate(d) if verds.get(i)!='JUNK']
        json.dump(kept,open(a.out,'w'),ensure_ascii=False,indent=2)
        print(f"{a.inp}: {len(d)} -> {len(kept)} (removed {len(d)-len(kept)} junk)")
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--in",dest="inp"); ap.add_argument("--out"); ap.add_argument("--pool",action="store_true")
    asyncio.run(main(ap.parse_args()))

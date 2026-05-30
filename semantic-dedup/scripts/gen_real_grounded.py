"""
Video-grounded topic generation on REAL crawled videos (Gemini official API, local).
Uses the proven v0.5.1 prompt; grounds each topic on a real video's title+description.
This is the genuine ingest→generate cycle (vs synthetic).

Usage: python3 gen_real_grounded.py --in real_source.json --out real_topics.json
"""
import argparse, json, asyncio, re, time, os, hashlib
import httpx

API_KEY = os.environ.get("GEMINI_API_KEY","")
MODEL   = "gemini-2.5-flash"
URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
CONC    = 25
PROMPT_FILE = "/tmp/sport-content-analysis/gen-topics/gen_topic_prompt_运动_v0.5.1.md"
SYSTEM = open(PROMPT_FILE, encoding='utf-8').read()

def build_user(v):
    tid = "sport_real_" + hashlib.md5(v['url'].encode()).hexdigest()[:12]
    return tid, f"""topic_id: {tid}
url: {v.get('url','')}
source: {v.get('platform','')}
duration: {v.get('duration',0)}s
views: {v.get('views',0)}
title: {v.get('title','')}
author: {v.get('author','')}
tags: (none)
categories: (none)
description: {(v.get('description') or '')[:600]}

按 v0.5.1 prompt 规则生成 topic（English），按 §4 流程走（创作 → 4 问自查 → 输出）。
特别注意：
- C1 立意是首要判断；中性描述（"X for Y"）合规但不及格
- 人名默认剥离为头衔（仅乔丹/帕梅拉级跨圈顶流保留）
- 项目数硬上限 ≤5；视频执行时长剥离；系列后缀全杜绝
- 临床医疗/非运动内容 → topic 输出 null
直接输出 JSON 对象 {{"topic":"...","video_type":"...","narrative_intent":"...","names_used":[],"self_check_note":"..."}}，不加 markdown、不加解释。"""

async def gen_one(client, v, sem, attempt=0):
    tid, user = build_user(v)
    body = {"system_instruction":{"parts":[{"text":SYSTEM}]},
            "contents":[{"role":"user","parts":[{"text":user}]}],
            "generationConfig":{"temperature":0.7,"maxOutputTokens":2000,"thinkingConfig":{"thinkingBudget":0}}}
    try:
        async with sem:
            r = await client.post(URL, json=body, timeout=70)
        r.raise_for_status()
        raw = "".join(p.get("text","") for p in r.json()["candidates"][0]["content"]["parts"]).strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        obj = json.loads(m.group())
        topic = obj.get("topic")
        if not isinstance(topic, str) or len(topic.strip()) < 15:
            return None   # null = clinical/non-sport, skip
        return {
            "topic_id": tid, "topic": topic.strip(),
            "domain": "运动教学", "tier": "real_ingest", "source": v.get('platform',''),
            "original_title": v.get('title',''), "view_count": v.get('views',0),
            "duration": v.get('duration',0), "url": v.get('url',''), "asset_id": tid,
            "l1_gap": v.get('l1_gap',''),
            "video_type": obj.get("video_type",""), "narrative_intent": obj.get("narrative_intent",""),
            "names_used": obj.get("names_used",[]), "self_check_note": obj.get("self_check_note",""),
        }
    except Exception as e:
        if attempt < 3:
            await asyncio.sleep(2**attempt)
            return await gen_one(client, v, sem, attempt+1)
        return None

async def main(inp, outp):
    vids = json.load(open(inp))
    # dedup by url
    seen=set(); uniq=[]
    for v in vids:
        if v['url'] in seen: continue
        seen.add(v['url']); uniq.append(v)
    print(f"Generating topics for {len(uniq)} real videos (CONC={CONC})")
    sem = asyncio.Semaphore(CONC); results=[]; done=[0]; t0=time.time()
    async with httpx.AsyncClient() as client:
        async def work(v):
            r = await gen_one(client, v, sem)
            done[0]+=1
            if r: results.append(r)
            if done[0]%100==0:
                print(f"\r  [{done[0]}/{len(uniq)}] kept {len(results)} | {done[0]/(time.time()-t0):.0f}/s", end="", flush=True)
        await asyncio.gather(*[work(v) for v in uniq])
    json.dump(results, open(outp,'w'), ensure_ascii=False, indent=2)
    print(f"\nDONE: {len(uniq)} videos -> {len(results)} topics (null/skip {len(uniq)-len(results)}) -> {outp}")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--in",dest="inp",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args(); asyncio.run(main(a.inp,a.out))

"""QC generated gap-sport topics (Gemini official API local, v3 rules).
Usage: python3 qc_gap.py --in file.json --out clean.json"""
import argparse, os, json, asyncio, re, time
import httpx

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL   = "gemini-2.5-flash"
URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
BATCH=20; CONC=12

SYS = """You are a sports content quality checker. Evaluate each topic for a sports-education content pool.
RULES v3 — flag ONLY clear problems:
1. sport_unspecified — generic sport verbs/nouns with NO sport named anywhere.
2. too_many_items — explicitly lists >=8 distinct items/techniques.
3. person_too_narrow — sole subject is a completely anonymous unknown individual.
4. unclear_value — ZERO identifiable skill/action/technique/sport noun, only vague adjectives.
5. empty_or_no_value — pure click-bait, no hint what's learned.
6. other — clearly NOT sports/fitness/outdoor activity (be very conservative; motorcycle/qigong/dance/cycling-maintenance/hiking/diving/martial-arts/sports-medicine ARE valid).
7. mixed_unrelated_points — combines completely unrelated topics.
REMOVED (never apply): too_professional_or_medical, exaggerated_or_factual_risk.
Output JSON array, one per topic in order: [{"topic_id":"...","has_issue":"N|Y|border","issue_type":"","issue_detail":""}]
Output ONLY the JSON array."""

async def qc_batch(client, batch, sem, attempt=0):
    payload="\n".join(f'{i+1}. [topic_id:{r["topic_id"]}] {r["topic"]}' for i,r in enumerate(batch))
    body={"system_instruction":{"parts":[{"text":SYS}]},
          "contents":[{"role":"user","parts":[{"text":f"Evaluate these {len(batch)} topics:\n\n{payload}"}]}],
          "generationConfig":{"temperature":0,"maxOutputTokens":4000,"thinkingConfig":{"thinkingBudget":0}}}
    try:
        async with sem:
            r=await client.post(URL,json=body,timeout=90)
        r.raise_for_status()
        parts=r.json()["candidates"][0]["content"]["parts"]
        raw="".join(p.get("text","") for p in parts).strip()
        m=re.search(r'\[.*\]',raw,re.DOTALL)
        parsed=json.loads(m.group())
        for i,it in enumerate(parsed):
            if not it.get("topic_id"): it["topic_id"]=batch[i]["topic_id"]
        return parsed
    except Exception as e:
        if attempt<3:
            await asyncio.sleep(2**attempt); return await qc_batch(client,batch,sem,attempt+1)
        return [{"topic_id":r["topic_id"],"has_issue":"N","issue_type":"","issue_detail":"ERR"} for r in batch]

async def main(inp, outp):
    data=json.load(open(inp))
    batches=[data[i:i+BATCH] for i in range(0,len(data),BATCH)]
    sem=asyncio.Semaphore(CONC); verdicts={}
    async with httpx.AsyncClient() as client:
        for fut in asyncio.as_completed([qc_batch(client,b,sem) for b in batches]):
            for it in await fut:
                verdicts[it["topic_id"]]=it
    clean=[r for r in data if verdicts.get(r["topic_id"],{}).get("has_issue")=="N"]
    json.dump(clean, open(outp,'w'), ensure_ascii=False, indent=2)
    from collections import Counter
    c=Counter(v["has_issue"] for v in verdicts.values())
    print(f"QC {inp}: {len(data)} -> N={len(clean)} | {dict(c)}")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--in",dest="inp",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args(); asyncio.run(main(a.inp,a.out))

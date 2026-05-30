import os
"""
Step 2: Embed all topics with Gemini embedding API (local, async, checkpointed).
Saves embeddings.npy (aligned with pool order) + done.json checkpoint.
"""
import json, asyncio, os, time
import numpy as np
import httpx

API_KEY = os.environ.get("GEMINI_API_KEY", "")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents?key={API_KEY}"
DIM = 768
BATCH = 50          # texts per request
CONCURRENCY = 12
EMB_PATH = '/tmp/dedup/embeddings.npy'
CK_PATH  = '/tmp/dedup/embed_done.json'

with open('/tmp/dedup/pool.json') as f:
    pool = json.load(f)
N = len(pool)
print(f"Pool: {N} topics, embedding dim={DIM}")

# Init or load embedding matrix + checkpoint
if os.path.exists(EMB_PATH) and os.path.exists(CK_PATH):
    embs = np.load(EMB_PATH)
    with open(CK_PATH) as f:
        done = set(json.load(f))
    print(f"Resumed: {len(done)} batches done")
else:
    embs = np.zeros((N, DIM), dtype=np.float32)
    done = set()

# Build batches (list of (batch_idx, [pool indices]))
batches = []
for bi, start in enumerate(range(0, N, BATCH)):
    if bi in done: continue
    idxs = list(range(start, min(start+BATCH, N)))
    batches.append((bi, idxs))
print(f"Remaining batches: {len(batches)} (of {(N+BATCH-1)//BATCH})")

async def embed_batch(client, bi, idxs, sem, attempt=0):
    reqs = [{"model":"models/gemini-embedding-001",
             "content":{"parts":[{"text": pool[i]['topic'][:2000]}]},
             "outputDimensionality": DIM} for i in idxs]
    try:
        async with sem:
            r = await client.post(URL, json={"requests": reqs}, timeout=60)
        r.raise_for_status()
        vecs = r.json()["embeddings"]
        if len(vecs) != len(idxs):
            raise ValueError(f"len mismatch {len(vecs)} vs {len(idxs)}")
        for j, i in enumerate(idxs):
            v = np.array(vecs[j]["values"], dtype=np.float32)
            n = np.linalg.norm(v)
            embs[i] = v / n if n > 0 else v
        return bi, True
    except Exception as e:
        if attempt < 6:
            await asyncio.sleep(min(2**attempt, 30))
            return await embed_batch(client, bi, idxs, sem, attempt+1)
        print(f"\n  FAIL batch {bi}: {str(e)[:120]}")
        return bi, False

async def main():
    sem = asyncio.Semaphore(CONCURRENCY)
    done_ct = [0]; t0 = time.time()
    async with httpx.AsyncClient() as client:
        async def worker(bi, idxs):
            rbi, ok = await embed_batch(client, bi, idxs, sem)
            if ok:
                done.add(rbi); done_ct[0] += 1
                if done_ct[0] % 20 == 0:
                    np.save(EMB_PATH, embs)
                    with open(CK_PATH, 'w') as f: json.dump(sorted(done), f)
                    el = time.time()-t0
                    rate = done_ct[0]/el
                    eta = (len(batches)-done_ct[0])/rate if rate>0 else 0
                    print(f"\r  [{done_ct[0]}/{len(batches)}] {rate*BATCH:.0f} emb/s | ETA {eta:.0f}s   ", end="", flush=True)
        await asyncio.gather(*[worker(bi, idxs) for bi, idxs in batches])
    np.save(EMB_PATH, embs)
    with open(CK_PATH, 'w') as f: json.dump(sorted(done), f)
    print(f"\nDone. Embeddings saved: {embs.shape}")

if batches:
    asyncio.run(main())
else:
    print("All embedded already.")

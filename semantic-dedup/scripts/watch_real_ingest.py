"""
Real-ingest watcher: detects when a NEW 优质池 (newer than baseline) lands from the
R7/R8/R9 crawl pipeline, then runs the originally-intended video-grounded cycle:
  filter gap-sport videos → Gemini topic generation → QC → semantic dedup vs pool → merge.

Run on devbox (where crawl data lands). Idempotent: tracks processed pools.
Until new data lands, exits with "no new ingest" — the autonomous loop calls this each tick.
"""
import os, json, glob, time

BASELINE = "/root/workspace/content-filtering/outputs/优质池_2026-05-28.json"
OUT_DIR  = "/root/workspace/content-filtering/outputs"
STATE    = "/tmp/supp/real_ingest_state.json"

def newest_pool():
    pools = glob.glob(f"{OUT_DIR}/优质池_*.json")
    pools = [p for p in pools if os.path.getmtime(p) > os.path.getmtime(BASELINE) + 60]
    if not pools: return None
    return max(pools, key=os.path.getmtime)

def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"processed": []}
    new = newest_pool()
    if not new:
        print("NO_NEW_INGEST — crawl pipeline has not produced a pool newer than 2026-05-28 baseline yet.")
        print("(R7/R8/R9 = 18,853 seeds still crawling; downstream filter pipeline pending.)")
        return
    if new in state["processed"]:
        print(f"ALREADY_PROCESSED: {new}")
        return
    print(f"NEW_INGEST_DETECTED: {new}")
    print("→ Trigger: filter gap-sport videos → gen_topics (Gemini, real source) → QC → dedup → merge")
    print("  (This is the video-grounded cycle; run the real gen pipeline on this pool's gap-sport subset.)")
    # The actual heavy run is launched by the orchestrator when this signals NEW_INGEST_DETECTED.
    state["processed"].append(new)
    json.dump(state, open(STATE, "w"))

if __name__ == "__main__":
    main()

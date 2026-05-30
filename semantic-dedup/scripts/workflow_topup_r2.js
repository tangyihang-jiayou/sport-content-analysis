export const meta = {
  name: 'gap-sport-topup-r2',
  description: 'Round-2 top-up generation+QC for headroom gap sports to push final pool past 100k',
  phases: [
    { title: 'Generate', detail: 'Gemini round-2 generation for headroom sports' },
    { title: 'QC', detail: 'Gemini v3 QC' },
  ],
}

// Sports with real content headroom (exclude near-ceiling niche: 椭圆机/踏步机/乒乓/壁球/曲棍球)
const SPORTS = [
  {sport:"飞盘",quota:400},{sport:"心肺/HIIT",quota:400},{sport:"睡眠/恢复",quota:400},
  {sport:"跑酷",quota:400},{sport:"板球",quota:450},{sport:"田径",quota:450},
  {sport:"冰球",quota:450},{sport:"台球/斯诺克",quota:400},{sport:"潜水",quota:450},
  {sport:"举重竞技",quota:400},{sport:"气功/太极",quota:450},{sport:"体姿矫正/PT",quota:450},
  {sport:"柔韧/活动度",quota:450},{sport:"壶铃",quota:400},{sport:"皮克球",quota:500},
  {sport:"滑板",quota:450},{sport:"橄榄球",quota:500},{sport:"冲浪/水上",quota:450},
  {sport:"攀岩",quota:500},{sport:"户外/徒步",quota:500},{sport:"羽毛球",quota:500},
  {sport:"滑冰/滑雪",quota:450},{sport:"综合拉伸",quota:400},{sport:"长曲棍球",quota:200},
  {sport:"赛艇/皮划艇",quota:200},{sport:"跳绳",quota:200}
]
log(`Round-2 top-up · ${SPORTS.length} headroom sports · raw target ${SPORTS.reduce((a,s)=>a+s.quota,0)}`)

const GEN_SCHEMA = { type:'object', properties:{ generated:{type:'integer'}, error:{type:'string'} }, required:['generated'] }
const QC_SCHEMA  = { type:'object', properties:{ clean:{type:'integer'}, error:{type:'string'} }, required:['clean'] }

const results = await pipeline(SPORTS,
  async (s, _orig, i) => {
    const r = await agent(
      `Run this EXACT shell command verbatim (Gemini topic generation, 10-40s):\n\n`+
      `cd /tmp/supp && python3 gen_gap_sport.py --sport "${s.sport}" --quota ${s.quota} --out /tmp/supp/gen2_${i}.json\n\n`+
      `It prints: "${s.sport}: generated N unique ...". Report integer N as "generated". On error set generated=0 and put the error text in "error". Run nothing else.`,
      { label:`gen2:${s.sport}`, phase:'Generate', schema:GEN_SCHEMA }
    )
    return { sport:s.sport, idx:i, generated:(r && r.generated) || 0 }
  },
  async (g, orig, i) => {
    if (!g || !g.generated) return { sport:orig.sport, idx:i, generated:0, clean:0 }
    const r = await agent(
      `Run this EXACT shell command verbatim (Gemini QC, 10-30s):\n\n`+
      `cd /tmp/supp && python3 qc_gap.py --in /tmp/supp/gen2_${i}.json --out /tmp/supp/clean2_${i}.json\n\n`+
      `It prints "QC ...: X -> N=K | {...}". Report integer K (after "N=") as "clean". On error set clean=0 and error text. Run nothing else.`,
      { label:`qc2:${orig.sport}`, phase:'QC', schema:QC_SCHEMA }
    )
    return { sport:orig.sport, idx:i, generated:g.generated, clean:(r && r.clean) || 0 }
  }
)

const ok = results.filter(Boolean)
const totGen = ok.reduce((a,r)=>a+(r.generated||0),0)
const totClean = ok.reduce((a,r)=>a+(r.clean||0),0)
log(`R2 DONE · generated ${totGen} · clean ${totClean} · ${ok.length}/${SPORTS.length}`)
return { sports: ok, total_generated: totGen, total_clean: totClean }

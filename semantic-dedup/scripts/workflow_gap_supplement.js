export const meta = {
  name: 'gap-sport-supplement',
  description: 'Generate + QC gap-sport teaching topics across 32 under-supplied sports via Gemini (local API)',
  phases: [
    { title: 'Generate', detail: 'Gemini taxonomy-driven topic generation per sport' },
    { title: 'QC', detail: 'Gemini v3 quality check per sport' },
  ],
}

const SPORTS = [
  {sport:"椭圆机",quota:200},{sport:"踏步机",quota:200},{sport:"壁球/手球",quota:250},
  {sport:"赛艇/皮划艇",quota:300},{sport:"乒乓球",quota:300},{sport:"曲棍球",quota:250},
  {sport:"长曲棍球",quota:250},{sport:"跳绳",quota:250},{sport:"飞盘",quota:600},
  {sport:"跑酷",quota:600},{sport:"冰球",quota:600},{sport:"田径",quota:700},
  {sport:"板球",quota:600},{sport:"潜水",quota:700},{sport:"气功/太极",quota:600},
  {sport:"台球/斯诺克",quota:600},{sport:"举重竞技",quota:600},{sport:"壶铃",quota:600},
  {sport:"综合拉伸",quota:600},{sport:"体姿矫正/PT",quota:700},{sport:"睡眠/恢复",quota:600},
  {sport:"心肺/HIIT",quota:600},{sport:"柔韧/活动度",quota:600},{sport:"橄榄球",quota:800},
  {sport:"户外/徒步",quota:900},{sport:"皮克球",quota:900},{sport:"冲浪/水上",quota:800},
  {sport:"攀岩",quota:900},{sport:"滑板",quota:800},{sport:"运动营养",quota:800},
  {sport:"羽毛球",quota:900},{sport:"滑冰/滑雪",quota:800}
]
log(`Supplementing ${SPORTS.length} gap sports · raw target ${SPORTS.reduce((a,s)=>a+s.quota,0)}`)

const GEN_SCHEMA = { type:'object', properties:{ generated:{type:'integer'}, error:{type:'string'} }, required:['generated'] }
const QC_SCHEMA  = { type:'object', properties:{ clean:{type:'integer'}, error:{type:'string'} }, required:['clean'] }

const results = await pipeline(SPORTS,
  async (s, _orig, i) => {
    const r = await agent(
      `Run this EXACT shell command verbatim (it calls the Gemini API to generate sport topics — takes 10-40s):\n\n`+
      `cd /tmp/supp && python3 gen_gap_sport.py --sport "${s.sport}" --quota ${s.quota} --out /tmp/supp/gen_${i}.json\n\n`+
      `On success it prints ONE line like: "${s.sport}: generated N unique (target ${s.quota}) in Xs -> ...". `+
      `Report the integer N as "generated". If the command errors or prints no such line, set generated=0 and put the stderr/last line in "error". Do not run anything else.`,
      { label:`gen:${s.sport}`, phase:'Generate', schema:GEN_SCHEMA }
    )
    return { sport:s.sport, idx:i, generated:(r && r.generated) || 0 }
  },
  async (g, orig, i) => {
    if (!g || !g.generated) return { sport:orig.sport, idx:i, generated:0, clean:0 }
    const r = await agent(
      `Run this EXACT shell command verbatim (it calls the Gemini API to QC topics — takes 10-30s):\n\n`+
      `cd /tmp/supp && python3 qc_gap.py --in /tmp/supp/gen_${i}.json --out /tmp/supp/clean_${i}.json\n\n`+
      `On success it prints: "QC ...: X -> N=K | {...}". Report the integer K (the number after "N=") as "clean". `+
      `If it errors, set clean=0 and put the error in "error". Do not run anything else.`,
      { label:`qc:${orig.sport}`, phase:'QC', schema:QC_SCHEMA }
    )
    return { sport:orig.sport, idx:i, generated:g.generated, clean:(r && r.clean) || 0 }
  }
)

const ok = results.filter(Boolean)
const totGen = ok.reduce((a,r)=>a+(r.generated||0),0)
const totClean = ok.reduce((a,r)=>a+(r.clean||0),0)
log(`DONE · generated ${totGen} · clean ${totClean} · ${ok.length}/${SPORTS.length} sports`)
return { sports: ok, total_generated: totGen, total_clean: totClean }

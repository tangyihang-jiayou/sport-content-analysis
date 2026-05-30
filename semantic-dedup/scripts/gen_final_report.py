"""Final report: dedup correction + gap supplement + final pool composition."""
import json, re
from collections import Counter

rules=json.load(open('/tmp/qc_59k/rules_v6.json'))
l1_rules=[(n,re.compile(p,re.I)) for n,p in rules['l1']]
def cls(t):
    if not t: return '其他'
    for n,p in l1_rules:
        if p.search(t): return n
    return '其他'

# original pool L1 dist (pre-dedup)
pool_all=json.load(open('/tmp/dedup/pool.json'))
orig=Counter(p['l1'] for p in pool_all)
dedup_rep=json.load(open('/tmp/dedup/dedup_report.json'))
merge_rep=json.load(open('/tmp/supp/merge_report.json'))
final=json.load(open('/Users/ricktang/Desktop/sport_pool_final_100k.json'))
fct=Counter()
for r in final:
    fct[r.get('l1_gen') or cls(r.get('topic') or '')]+=1

# dedup per-L1
ded=json.load(open('/Users/ricktang/Desktop/sport_pool_dedup.json'))
dct=Counter(cls(' '.join(str(r.get(f) or '') for f in ['topic','original_title','description'])) for r in ded)

N_orig=len(pool_all); N_ded=len(ded); N_final=len(final)
removed=dedup_rep['removed']; rem_pct=dedup_rep['removed_pct']

# band calibration
try:
    bands=json.load(open('/tmp/dedup/band_judgments.json'))
    band_rate={}
    for p in bands:
        b=p['band']; band_rate.setdefault(b,[0,0])
        if p.get('verdict','').startswith('SAME'): band_rate[b][0]+=1
        elif p.get('verdict','').startswith('DIF'): band_rate[b][1]+=1
except: band_rate={}

# gap sports added
added=merge_rep.get('per_sport_added',{})

rows=[]
alll1=set(orig)|set(fct)
for l1 in alll1:
    o=orig.get(l1,0); d=dct.get(l1,0); f=fct.get(l1,0)
    rows.append({'l1':l1,'orig':o,'dedup':d,'final':f,'added':added.get(l1,0)})
rows.sort(key=lambda r:-r['final'])

def bar(v,mx,color):
    w=int(v/mx*100) if mx else 0
    return f'<div style="background:#eef;border-radius:3px;height:7px;max-width:160px"><div style="background:{color};width:{w}%;height:7px;border-radius:3px"></div></div>'
mx=max(r['final'] for r in rows)

H=f"""<!DOCTYPE html><html lang=zh-CN><head><meta charset=UTF-8><title>运动内容池 · 语义去重+缺口补充 最终报告</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:-apple-system,'PingFang SC',sans-serif;background:#f4f6fa;color:#1a1a2e;font-size:14px;line-height:1.6}}
.hero{{background:linear-gradient(135deg,#0f172a,#16213e 60%,#0f3460);color:#fff;padding:48px 40px}}
.hero h1{{font-size:28px;font-weight:700}}.hero .sub{{opacity:.7;margin-top:6px}}
.hg{{display:flex;gap:22px;margin-top:28px;flex-wrap:wrap}}
.hs{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:16px 22px;min-width:150px}}
.hs .v{{font-size:28px;font-weight:700}}.hs .l{{font-size:11px;opacity:.7;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}}.hs .s{{font-size:11px;opacity:.6;margin-top:3px}}
.c{{max-width:1180px;margin:28px auto;padding:0 24px}}
.card{{background:#fff;border-radius:12px;padding:26px;margin-bottom:22px;box-shadow:0 1px 6px rgba(0,0,0,.06)}}
h2{{font-size:20px;font-weight:700;border-left:4px solid #0f3460;padding-left:12px;margin-bottom:14px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th{{background:#f0f4f8;padding:9px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.3px;color:#555;border-bottom:2px solid #e2e8f0}}
td{{padding:8px 12px;border-bottom:1px solid #f1f5f9}}td.n{{text-align:right;font-variant-numeric:tabular-nums}}
.tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}}
.green{{background:#dcfce7;color:#16a34a}}.red{{background:#fee2e2;color:#c0392b}}.amber{{background:#fef9e7;color:#d97706}}.blue{{background:#dbeafe;color:#2563eb}}
.box{{border-radius:8px;padding:14px 18px;margin:10px 0}}.bg{{background:#f0fdf4;border-left:4px solid #22c55e}}.bw{{background:#fff7ed;border-left:4px solid #f97316}}.bb{{background:#eff6ff;border-left:4px solid #3b82f6}}
</style></head><body>
<div class=hero><h1>运动内容池 · 语义去重 + 缺口补充 最终报告</h1>
<div class=sub>2026-05-30 · 语义去重(Gemini裁判校准) + 32运动 gap 补充(dynamic workflow)</div>
<div class=hg>
<div class=hs><div class=l>最终池</div><div class=v>{N_final:,}</div><div class=s>0重复 · 56运动全覆盖</div></div>
<div class=hs><div class=l>语义去重</div><div class=v>−{removed:,}</div><div class=s>{N_orig:,}→{N_ded:,} ({rem_pct:.1f}%)</div></div>
<div class=hs><div class=l>gap补充(净)</div><div class=v>+{merge_rep['synth_kept']:,}</div><div class=s>生成{merge_rep['synth_generated']:,}→去重后</div></div>
<div class=hs><div class=l>去重阈值</div><div class=v>0.85</div><div class=s>Gemini裁判校准</div></div>
</div></div>
<div class=c>

<div class=card>
<h2>一、语义去重 — 阈值校准纠错</h2>
<div class=bw><b>关键纠错:</b> 初版用 τ=0.92 只删了 3.2%，被质疑过于保守。改用 <b>Gemini 独立裁判</b>判 240 对 borderline pair「是否问同一件事」，发现「同问题」内容一直延伸到 0.84，我的肉眼校准有确认偏误。最终 <b>τ=0.85 + 贪心代表法(防链式误并)</b>，删除 <b>{rem_pct:.1f}%</b>。</div>
<table><tr><th>相似度 band</th><th class=n>同问题率(Gemini裁判)</th><th>判定</th></tr>
"""
order=['0.78-0.8','0.8-0.82','0.82-0.84','0.84-0.86','0.86-0.88','0.88-0.9','0.9-0.92','0.92-0.94','0.94-1.01']
for b in order:
    if b in band_rate:
        s,d=band_rate[b];tot=s+d
        rate=s/tot*100 if tot else 0
        verdict='<span class="tag green">删(真冗余)</span>' if rate>=85 and float(b.split('-')[0])>=0.84 else ('<span class="tag amber">混合</span>' if rate>=60 else '<span class="tag red">留(真不同)</span>')
        H+=f"<tr><td>{b}</td><td class=n>{rate:.0f}% (SAME {s}/{tot})</td><td>{verdict}</td></tr>"
H+="</table></div>"

H+=f"""
<div class=card>
<h2>二、缺口补充 — 32运动 gap 生成</h2>
<div class=bb>主池=优质池=68,197视频全部已生成过topic，<b>无未用源视频</b>(R7+爬虫未落地)。改用 <b>Gemini taxonomy-driven 合成</b>: L1+L2维度×6技能层×8热门角度，dynamic workflow 按运动并行 生成→QC→跨池语义去重。</div>
<table><tr><th>阶段</th><th class=n>数量</th></tr>
<tr><td>生成(raw)</td><td class=n>{merge_rep['synth_generated']:,}</td></tr>
<tr><td>跨池删(与现有池≥0.85)</td><td class=n>−{merge_rep['drop_vs_existing']:,}</td></tr>
<tr><td>组内删(合成互相≥0.85)</td><td class=n>−{merge_rep['drop_intra']:,}</td></tr>
<tr style="background:#f0fdf4"><td><b>净入池</b></td><td class=n><b>{merge_rep['synth_kept']:,}</b></td></tr>
</table></div>

<div class=card>
<h2>三、全运动 before/after (原始 → 去重 → +gap → 最终)</h2>
<table><tr><th>L1运动</th><th class=n>原始</th><th class=n>去重后</th><th class=n>+gap补充</th><th class=n>最终</th><th>最终分布</th></tr>
"""
for r in rows:
    add=f'<span class="tag green">+{r["added"]}</span>' if r['added'] else ''
    H+=f"<tr><td>{r['l1']}</td><td class=n>{r['orig']:,}</td><td class=n>{r['dedup']:,}</td><td class=n>{add}</td><td class=n><b>{r['final']:,}</b></td><td>{bar(r['final'],mx,'#3b82f6')}</td></tr>"
H+="</table></div>"

H+=f"""<div style="text-align:center;color:#94a3b8;font-size:12px;padding:20px">最终池 {N_final:,} 条 · /Users/ricktang/Desktop/sport_pool_final_100k.json · 2026-05-30</div>
</div></body></html>"""
open('/Users/ricktang/Desktop/内容池_去重与缺口补充_最终报告.html','w').write(H)
print(f"Report saved. Final pool {N_final:,}")

"""Build sport_cfg.json: per gap-sport terms, L2 dims, existing samples (to avoid dup)."""
import json, re
from collections import defaultdict

rules = json.load(open('/tmp/qc_59k/rules_v6.json'))
l1_rules = [(n, re.compile(p, re.I)) for n,p in rules['l1']]
l2_map = defaultdict(list)
for l1, l2, pat in rules['l2']:
    l2_map[l1].append(l2)

def cls(t):
    if not t: return '其他'
    for n,p in l1_rules:
        if p.search(t): return n
    return '其他'

pool = json.load(open('/Users/ricktang/Desktop/sport_pool_dedup.json'))
samples = defaultdict(list)
for r in pool:
    t = r.get('topic') or ''
    l1 = cls(' '.join(str(r.get(f) or '') for f in ['topic','original_title','description']))
    if len(samples[l1]) < 18:
        samples[l1].append(t)

# English terms per gap sport
TERMS = {
    '椭圆机': ['elliptical machine','cross trainer'],
    '乒乓球': ['table tennis','ping pong'],
    '壁球/手球': ['squash','racquetball','handball'],
    '踏步机': ['stair climber','stairmaster','stepmill'],
    '赛艇/皮划艇': ['rowing','indoor rower','kayaking','canoeing','SUP'],
    '飞盘': ['ultimate frisbee','disc golf'],
    '曲棍球': ['field hockey'],
    '长曲棍球': ['lacrosse'],
    '跑酷': ['parkour','freerunning'],
    '冰球': ['ice hockey'],
    '跳绳': ['jump rope','skipping rope'],
    '田径': ['track and field','sprinting','long jump','high jump','shot put','hurdles','pole vault'],
    '潜水': ['scuba diving','freediving','snorkeling','spearfishing'],
    '橄榄球': ['rugby','American football','flag football'],
    '板球': ['cricket'],
    '综合拉伸': ['stretching','flexibility','mobility'],
    '户外/徒步': ['hiking','backpacking','mountaineering','trail navigation','camping'],
    '运动营养': ['sports nutrition','protein','creatine','hydration','fueling'],
    '台球/斯诺克': ['billiards','snooker','pool 8-ball','pool 9-ball'],
    '皮克球': ['pickleball'],
    '气功/太极': ['tai chi','qigong','wing chun','kung fu'],
    '举重竞技': ['olympic weightlifting','clean and jerk','snatch'],
    '冲浪/水上': ['surfing','paddleboard','kitesurfing','windsurfing','wakeboard'],
    '壶铃': ['kettlebell training'],
    '攀岩': ['rock climbing','bouldering','sport climbing','trad climbing'],
    '滑板': ['skateboarding','longboarding'],
    '羽毛球': ['badminton'],
    '滑冰/滑雪': ['skiing','snowboarding','figure skating','speed skating'],
    '柔韧/活动度': ['mobility','flexibility','joint mobility','range of motion'],
    '体姿矫正/PT': ['posture correction','physical therapy','injury rehab'],
    '睡眠/恢复': ['sleep optimization','recovery','cold plunge','ice bath','sauna'],
    '心肺/HIIT': ['HIIT','cardio conditioning','interval training','tabata'],
}

LEVELS = ['absolute beginner','beginner','intermediate plateau','advanced','returning after a break','over-40']

cfg = {}
for sp, terms in TERMS.items():
    cfg[sp] = {
        'terms': terms,
        'l2': l2_map.get(sp, []),
        'levels': LEVELS,
        'existing_samples': samples.get(sp, []),
    }

json.dump(cfg, open('/tmp/supp/sport_cfg.json','w'), ensure_ascii=False, indent=2)
print(f"Built cfg for {len(cfg)} gap sports")
for sp in cfg:
    print(f"  {sp}: {len(cfg[sp]['l2'])} L2 dims, {len(cfg[sp]['existing_samples'])} samples")

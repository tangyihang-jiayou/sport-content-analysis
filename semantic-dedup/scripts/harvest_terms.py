"""Build comprehensive search terms: all 56 sports (gap cfg + main sports) for real-ingest harvest."""
import json
cfg = json.load(open('/tmp/supp/sport_cfg.json'))
# main sports (not in gap cfg) + their search terms
MAIN = {
 '力量训练':['strength training','squat form','deadlift technique','bench press'],
 '瑜伽':['yoga flow','yoga for beginners','morning yoga','yoga for flexibility'],
 '跑步':['running form','marathon training','running technique','5k training'],
 '篮球':['basketball drills','basketball shooting','dribbling moves','basketball defense'],
 '足球':['soccer skills','football dribbling','soccer free kick','soccer training'],
 '网球':['tennis forehand','tennis serve','tennis backhand','tennis footwork'],
 '高尔夫':['golf swing','golf putting','golf chipping','golf driver'],
 '骑行':['cycling training','road cycling','mtb skills','cycling climbing'],
 '游泳':['swimming technique','freestyle swimming','swimming drills','breaststroke'],
 '拳击/搏击':['boxing technique','boxing combos','kickboxing','muay thai'],
 '武术/太极':['bjj technique','judo throws','karate','taekwondo'],
 '健身综合':['home workout','fat loss workout','full body workout','hiit workout'],
 '舞蹈':['dance tutorial','hip hop dance','kpop dance','dance for beginners'],
 '冥想/呼吸':['breathwork','meditation technique','box breathing','wim hof'],
 '普拉提':['pilates workout','reformer pilates','wall pilates','mat pilates'],
 '排球':['volleyball spike','volleyball setting','volleyball serve','volleyball drills'],
 '棒球/垒球':['baseball hitting','pitching mechanics','baseball fielding','batting drills'],
 '体操/技巧':['gymnastics skills','handstand tutorial','calisthenics skills','tumbling'],
 '运动健康':['injury prevention','mobility routine','recovery routine','sports rehab'],
 '柔韧性/康复':['stretching routine','flexibility training','rehab exercises','foam rolling'],
}
allterms = {}
for sp, c in cfg.items(): allterms[sp] = c['terms'][:3]
for sp, t in MAIN.items(): allterms[sp] = t
json.dump(allterms, open('/tmp/harvest_terms.json','w'), ensure_ascii=False, indent=2)
print(f"{len(allterms)} sports, {sum(len(v) for v in allterms.values())} search terms")

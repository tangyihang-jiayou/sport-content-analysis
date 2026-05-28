"""
v9 pipeline — 针对 asset-center 无 L1 标签场景
主要差异：
  - 跳过 no_L1 过滤（内容已知全是运动）
  - 跳过 IG shorts strict（vocab_own 无 L1 时为 0，不能用来判断）
  - views 门槛降为 0（asset-center 部分平台 views 字段可能为空）
  - LLM 全量跑，max_workers=150

用法:
    python3 pipeline.py <input_csv> [--no-llm-call]
"""
import csv, json, math, os, re, sys, datetime
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config as C
from vocab import L1_VOCAB, FORM_NEG

OUT_DIR = f"{HERE}/outputs"

def safe_int(x, d=0):
    try: return int(float(x)) if x not in (None, '') else d
    except: return d

CJK_RE      = re.compile(r'[一-鿿぀-ヿ가-힯]')
NON_EN_CHARS = re.compile(r'[ñãõçáàâéèêíìîóòôúùûüÁÀÂÃÉÊÍÓÔÕÚÇÑ]')
URL_RE      = re.compile(r'https?://\S+')
HASHTAG_RE  = re.compile(r'#\S+')
EMOJI_RE    = re.compile(r'[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F☀-➿]')

def cleaned_text(s):
    if not s: return ''
    s = URL_RE.sub(' ', s); s = HASHTAG_RE.sub(' ', s); s = EMOJI_RE.sub(' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def cjk_ratio(s):
    if not s: return 0
    return len(CJK_RE.findall(s)) / max(1, len(s))

def kw_hits(text, kws):
    return sum(1 for k in kws if k in text)

def freshness(pt):
    if not pt: return 0
    m = re.search(r'(\d{4})[-/](\d{1,2})', str(pt))
    if not m: return 0
    y, mo = int(m.group(1)), int(m.group(2))
    ma = (C.NOW_YEAR - y) * 12 + (C.NOW_MONTH - mo)
    if ma < 3: return 0
    if ma <= 24: return 1.0
    if ma <= 60: return 0.5
    return 0

def llm_keeps(j):
    return j.get('form') == 'instructional' and j.get('is_sport') is True

class Pipeline:
    def __init__(self, input_csv, allow_llm=True):
        self.input_csv = input_csv
        self.allow_llm = allow_llm
        self.log = []
        self.LLM_CACHE = f'{HERE}/llm_cache.jsonl'

    def _log(self, msg):
        print(msg, flush=True)
        self.log.append(msg)

    def step_0_load(self):
        self._log(f"\n[0] 读入: {self.input_csv}")
        self.videos = []
        with open(self.input_csv, encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                self.videos.append({
                    'url':          r.get('url',''),
                    'platform':     r.get('platform',''),
                    'title':        r.get('title','') or '',
                    'desc':         r.get('desc','') or '',
                    'channel':      r.get('channel','') or '',
                    'views':        safe_int(r.get('views')),
                    'likes':        safe_int(r.get('likes')),
                    'comments':     safe_int(r.get('comments')),
                    'duration':     safe_int(r.get('duration')),
                    'publish_time': r.get('publish_time','') or '',
                    'L1': r.get('L1',''), 'L2': r.get('L2',''), 'L3': r.get('L3',''),
                    'sources':      r.get('sources',''),
                })
        self._log(f"  总计: {len(self.videos):,}")

    def step_1_basic_filter(self):
        self._log("\n[1] 基础过滤...")
        survivors, reasons = [], Counter()
        for v in self.videos:
            # CJK 过滤（标题+desc前200字）
            txt_cjk = v['title'] + ' ' + v['desc'][:200]
            if cjk_ratio(txt_cjk) >= C.MAX_CJK_RATIO:
                reasons['cjk_heavy'] += 1; continue
            # 非英文特殊字符
            if len(NON_EN_CHARS.findall(v['title'] + ' ' + v['desc'][:300])) >= C.MAX_NON_EN_CHARS:
                reasons['non_en_chars'] += 1; continue
            # 内容为空
            ct = cleaned_text(v['title']); cd = cleaned_text(v['desc'])[:200]
            v['_clean_t'] = ct; v['_clean_d'] = cd
            if len(ct) < C.NOTHING_READABLE_TITLE and len(cd) < C.NOTHING_READABLE_DESC:
                reasons['nothing_readable'] += 1; continue
            # 极短且文本稀
            if v['duration'] and v['duration'] <= C.TOO_SHORT_DURATION and len(ct)+len(cd) < C.TOO_SHORT_TEXT:
                reasons['too_short_thin'] += 1; continue
            survivors.append(v)
        self._log(f"  通过: {len(survivors):,} / {len(self.videos):,}")
        for k, n in reasons.most_common(): self._log(f"    -{n:,} {k}")
        self.l1_pass = survivors

    def step_2_signals_filter(self):
        self._log("\n[2] 信号计算 + hard filter...")
        ch = Counter()
        for v in self.l1_pass: ch[(v['platform'], v['channel'])] += 1

        for v in self.l1_pass:
            text_lc = (v['title'] + ' ' + v['desc'][:500]).lower()
            v['_text_lc']      = text_lc
            # vocab_own: 用 L1 词表（L1 为空时=0，但不过滤）
            own = kw_hits(text_lc, L1_VOCAB.get(v['L1'], []))
            cross_max, cross_L1 = 0, ''
            for L, ws in L1_VOCAB.items():
                if L == v['L1'] or L == '运动通用': continue
                h = kw_hits(text_lc, ws)
                if h > cross_max: cross_max, cross_L1 = h, L
            v['vocab_own']      = own
            v['vocab_cross']    = cross_max
            v['vocab_cross_L1'] = cross_L1
            v['form_neg']       = kw_hits(text_lc, FORM_NEG)
            v['inst_pos']       = kw_hits(text_lc, C.INSTRUCTIONAL_KW)
            v['inst_neg']       = kw_hits(text_lc, C.ENTERTAINMENT_KW)
            v['weak_neg']       = kw_hits(text_lc, C.WEAK_NEG_KW)
            v['instructional']  = v['inst_pos']*0.5 - v['inst_neg']*0.7 - v['weak_neg']*0.25
            v['sport_rel']      = min(3.0, own + 0.5*cross_max)
            v['channel_n']      = ch.get((v['platform'], v['channel']), 0)
            v['channel_signal'] = math.log2(1 + min(v['channel_n'], 200))
            v['freshness_val']  = freshness(v['publish_time'])

        survivors, reasons = [], Counter()
        for v in self.l1_pass:
            if v['form_neg'] >= C.L2_FORM_NEG_MIN:
                reasons['form_neg'] += 1; continue
            if v['inst_neg'] >= C.L2_INST_NEG_MIN:
                reasons['multi_ent_kw'] += 1; continue
            if v['instructional'] < C.L2_INSTRUCTIONAL_THRESHOLD:
                reasons['neg_instructional'] += 1; continue
            # IG shorts strict 跳过（vocab_own 无 L1 时不可靠）
            survivors.append(v)

        self._log(f"  通过: {len(survivors):,} / {len(self.l1_pass):,}")
        for k, n in reasons.most_common(): self._log(f"    -{n:,} {k}")
        self.l2_pass = survivors

    def step_3_llm(self):
        self._log(f"\n[3] LLM 过滤（{len(self.l2_pass):,} 条）...")
        cache = {}
        if os.path.exists(self.LLM_CACHE):
            with open(self.LLM_CACHE) as f:
                for ln in f:
                    try:
                        d = json.loads(ln)
                        if 'error' not in d: cache[d['url']] = d
                    except: pass
        self._log(f"  cache 已有: {len(cache):,}")

        need = [v for v in self.l2_pass if v['url'] not in cache]
        self._log(f"  需调 LLM:   {len(need):,}")

        if need and self.allow_llm:
            from llm_judge import run_batch
            samples = [{'url': v['url'], 'title': v['title'], 'desc': v['desc'],
                        'L1': v['L1'], 'platform': v['platform'], 'duration': v['duration']}
                       for v in need]
            run_batch(samples, max_workers=300, out_path=self.LLM_CACHE, resume=True)
            cache = {}
            with open(self.LLM_CACHE) as f:
                for ln in f:
                    try:
                        d = json.loads(ln)
                        if 'error' not in d: cache[d['url']] = d
                    except: pass
        elif need:
            self._log(f"  ⚠️  --no-llm-call: 跳过 {len(need):,} 条")
        self.llm_cache = cache

    def step_4_pools(self):
        self._log("\n[4] 分池...")
        all_kept = []
        for v in self.l2_pass:
            j = self.llm_cache.get(v['url'])
            if j and llm_keeps(j):
                v['llm_form'] = j.get('form','')
                v['llm_is_sport'] = j.get('is_sport', False)
                all_kept.append(v)
        self._log(f"  LLM keep: {len(all_kept):,} / {len(self.l2_pass):,} "
                  f"({len(all_kept)/max(1,len(self.l2_pass))*100:.0f}%)")

        main, sok = [], []
        for v in all_kept:
            if (v['duration'] <= C.SILENT_OK_MAX_DURATION
                    and v['vocab_own'] >= C.SILENT_OK_MIN_VOCAB_OWN
                    and not any(w in v['_text_lc'] for w in C.SILENT_ENT_REJECT)):
                sok.append(v)
            else:
                main.append(v)

        self._log(f"  主池: {len(main):,}  |  silent_ok: {len(sok):,}")
        for plat in ['TikTok','Instagram','YouTube']:
            n = sum(1 for v in sok if v['platform']==plat)
            if n: self._log(f"    silent_ok {plat}: {n:,}")
        self.main_pool, self.silent_ok_pool = main, sok

    def step_5_write(self):
        self._log("\n[5] 写产出...")
        os.makedirs(OUT_DIR, exist_ok=True)
        fields = ['url','platform','pool','L1','L2','L3','channel','title','desc',
                  'duration','publish_time','views','likes','comments',
                  'instructional','sport_rel','channel_signal','channel_n',
                  'freshness_val','vocab_own','vocab_cross','vocab_cross_L1',
                  'form_neg','inst_pos','inst_neg','sources','llm_form','llm_is_sport']

        def row(v, pool):
            return {f: v.get(f, round(v.get(f,0),4) if isinstance(v.get(f,0), float) else '')
                    for f in fields} | {'pool': pool,
                    'instructional': round(v.get('instructional',0),4),
                    'sport_rel': round(v.get('sport_rel',0),4),
                    'channel_signal': round(v.get('channel_signal',0),4)}

        date = datetime.date.today().isoformat()
        for name, pool_data, label in [
            ('主池.csv', self.main_pool, 'main'),
            ('silent_ok.csv', self.silent_ok_pool, 'silent_ok'),
        ]:
            with open(f'{OUT_DIR}/{name}', 'w', encoding='utf-8-sig', newline='') as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                for v in pool_data: w.writerow(row(v, label))
            self._log(f"  {name}: {len(pool_data):,} 条")

        all_recs = [row(v,'main') for v in self.main_pool] + \
                   [row(v,'silent_ok') for v in self.silent_ok_pool]
        out_json = f'{OUT_DIR}/优质池_{date}.json'
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(all_recs, f, ensure_ascii=False, indent=1)
        self._log(f"  优质池_{date}.json: {len(all_recs):,} 条")

        with open(f'{OUT_DIR}/pipeline_log.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.log))

    def run(self):
        self.step_0_load()
        self.step_1_basic_filter()
        self.step_2_signals_filter()
        self.step_3_llm()
        self.step_4_pools()
        self.step_5_write()

if __name__ == '__main__':
    args = sys.argv[1:]
    no_llm = '--no-llm-call' in args
    if no_llm: args.remove('--no-llm-call')
    if not args:
        print("用法: python3 pipeline.py <input_csv> [--no-llm-call]")
        sys.exit(1)
    Pipeline(args[0], allow_llm=not no_llm).run()

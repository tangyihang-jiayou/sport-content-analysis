"""v9 规则超参。改规则只动这个文件。

迭代历史：
- v5/v6: 单路径 (L3 子主题 top%) + LLM
- v7: 单路径 ((L1, 平台, 时长档) top%) + LLM，加 shorts_micro 拆分
- v8: 两路径并集 = v6 ∪ v7
- v9: 移除 Step3 双路径（LLM 直接跑全量 L2）；移除 no_sport_word；silent_ok 扩三平台
"""

# ============================================================
# L1 基础过滤阈值
# ============================================================
MIN_VIEWS = 10000               # views < 1w 直接砍
MAX_CJK_RATIO = 0.25            # title+desc[:200] 中 CJK 占比 ≥ 25% 砍
MAX_NON_EN_CHARS = 2            # 非英语欧洲特殊字符 ≥ 2 个砍
TOO_SHORT_DURATION = 12         # duration ≤ 12s 且 title+desc 总字符 < 25 砍
TOO_SHORT_TEXT = 25
NOTHING_READABLE_TITLE = 5      # clean title < 5 字 且 clean desc < 10 字 砍
NOTHING_READABLE_DESC = 10

# ============================================================
# L2 hard filter 信号阈值
# v9: 移除 no_sport_word（vocab_own=0 且 vocab_cross<2），词表覆盖不全误伤太多
# ============================================================
L2_FORM_NEG_MIN = 1             # form_neg ≥ 1 砍（集锦/MV/游戏形态词命中即砍）
L2_INST_NEG_MIN = 2             # inst_neg ≥ 2 砍（≥2 个娱乐词）
L2_INSTRUCTIONAL_THRESHOLD = -1.0  # instructional 分数 < -1 砍
# IG shorts 严打
IG_SHORTS_MIN_CHANNEL = 30
IG_SHORTS_MIN_INST_POS = 2
IG_SHORTS_MIN_VOCAB = 1

# ============================================================
# silent_ok 旁路（短视频教学池，v9 扩三平台）
# v9 变更：TikTok + Instagram + YouTube 全开；去掉频道数门槛和教学词上限
# ============================================================
SILENT_OK_PLATFORMS = {'TikTok', 'Instagram', 'YouTube'}
SILENT_OK_MAX_DURATION = 90     # 时长 ≤ 90s
SILENT_OK_MIN_VOCAB_OWN = 1     # 至少 1 个运动专属词（基础质量门）
SILENT_ENT_REJECT = [
    'music', 'remix', 'dance challenge', 'choreography',
    'lyrics', 'vibe', 'aesthetic',
]

# ============================================================
# 关键词表（L2 信号计算用）
# ============================================================
INSTRUCTIONAL_KW = [
    'how to','how do','how can','why','what is','what are','when to','when do',
    'the way to','the right way','the best way',
    'tutorial','guide','drill','technique','fundamentals',
    'lesson','basics','beginner','learn','master',
    'tips','mistake','breakdown','explained','demonstration',
    'step by step','coaching','training tip','how-to',
    'practice','how i','avoid','fix','improve','analysis',
]
ENTERTAINMENT_KW = [
    'compilation','montage','recap','highlight reel','best of',
    'top 10','top 5','craziest','insane','epic moment',
    'must watch',"you won't believe",'try not to',
    'funny','fail','vibes','lifestyle','vlog','day in the life',
    'gameplay','minecraft','roblox','fortnite',
    'kpop','k-pop','dance challenge','shocking','unbelievable','reaction',
]
WEAK_NEG_KW = ['highlight','highlights',' vs ','battle','challenge','edit']

# ============================================================
# Freshness 时间锚点（每次跑前确认年月）
# ============================================================
NOW_YEAR = 2026
NOW_MONTH = 5

# ============================================================
# LLM keep 判定
# ============================================================
def llm_keeps(judge):
    """form == 'instructional' AND is_sport == True"""
    return judge.get('form') == 'instructional' and judge.get('is_sport') is True

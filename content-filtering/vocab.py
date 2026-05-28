"""
v5 词表 — MVP 第一版（先验生成，后续用 good 样本反查校准）

L1_VOCAB:   42 个 L1 各自的运动专属词
            标准：只放运动专属词，不放通用词（training/coach/game/sport）
            用途：判 is_sport / sport_rel

FORM_NEG:   通用形态反向词（比赛/集锦/Vlog/挑战/炫技）
            用途：辅助压 wrong_form 中"标题已暴露形态"的部分
            与 v4 的 ENTERTAINMENT_KW 互补，更聚焦形态而非情绪词
"""

# ============================================================
# L1 专属运动词表（lowercase，title+desc 子串匹配）
# ============================================================
L1_VOCAB = {
    '篮球': [
        'basketball','nba','wnba','dribble','dribbling','jumpshot','jump shot','layup',
        'rebound','hoop','slam dunk','dunk','crossover','pick and roll','pnr',
        'free throw','three pointer','three-pointer','point guard','shooting guard',
        'small forward','power forward','center','post up','shot mechanic','euro step',
        'fadeaway','triple threat','box out',
    ],
    '足球': [
        'football','soccer','futbol','offside','dribble','free kick','freekick',
        'penalty','header','goalkeeper','goalie','midfielder','striker','defender',
        'corner kick','throw in','fifa','premier league','la liga','bundesliga',
        'champions league','first touch','through ball','one two','nutmeg',
        'volley','chip shot','cleats','center back','full back','wing back',
    ],
    '网球': [
        'tennis','forehand','backhand','serve','volley','baseline','ace','deuce',
        'rally','slice','topspin','racquet','racket','atp','wta','grand slam',
        'wimbledon','us open','french open','australian open','break point',
        'overhead smash','drop shot','lob','footwork','tweener','approach shot',
    ],
    '跑步': [
        'running','runner','marathon','sprint','pace','mile','5k','10k','half marathon',
        'jog','jogging','treadmill','cadence','stride','gait','running form',
        'racing flat','running shoes','easy run','tempo run','long run','intervals',
        'fartlek','vo2 max','negative split','footstrike','heel strike','midfoot',
        'race day','race nerves','race pace','triathlon tips','runner anxiety',
    ],
    '高尔夫': [
        'golf','golfer','swing','putt','putter','driver','iron','wedge','tee',
        'fairway','green','bunker','birdie','eagle','par','bogey','double bogey',
        'pga','lpga','hole in one','chip shot','approach shot','backswing','downswing',
        'grip pressure','golf ball','sand wedge','pitching wedge','tee shot',
    ],
    '骑行': [
        'cycling','cyclist','bike','bicycle','peloton','cadence','gear','chainring',
        'cassette','derailleur','hill climb','road bike','mtb','mountain bike',
        'cycling shoes','clipless','bike fit','tdf','tour de france','crit',
        'gravel ride','watts','ftp','aero position','sprint finish','out of saddle',
    ],
    '拳击': [
        'boxing','boxer','jab','hook','uppercut','straight right','straight left',
        'cross','southpaw','orthodox','sparring','mitt work','heavy bag','speed bag',
        'slip','parry','headguard','boxing glove','foot work','footwork','bobbing',
        'weaving','combination','3-2-1','one two','head movement','range finder',
        'fighter','fighting stance','fight stance','chin tuck','tuck your chin',
        'eat punches','punch defense','fighter neck',
    ],
    '力量训练': [
        'strength training','bench press','squat','deadlift','barbell','dumbbell',
        'rep','reps','hypertrophy','powerlifting','weightlifting','olympic lift',
        'kettlebell','bicep curl','overhead press','compound lift','isolation',
        'progressive overload','one rep max','1rm','back squat','front squat',
        'romanian deadlift','rdl','sumo deadlift','strict press',
    ],
    '瑜伽': [
        'yoga','asana','vinyasa','hatha','ashtanga','sun salutation','downward dog',
        'warrior pose','pranayama','chakra','yogi','yogini','yoga mat',"child's pose",
        'savasana','tree pose','plank pose','cobra pose','bridge pose','crow pose',
        'half moon','triangle pose','iyengar','kundalini','restorative yoga',
        'pilates','stretching','mobility','hip flexor','thoracic spine','spine mobility',
        'scoliosis exercise','seated stretch',
    ],
    '游泳': [
        'swimming','swimmer','freestyle','breaststroke','backstroke','butterfly stroke',
        'flutter kick','dolphin kick','swim pull','stroke rate','lap','swim cap',
        'goggles','flip turn','open turn','swim drag','catch phase','underwater pullout',
        'streamline','breath timing','bilateral breathing','swimming pool','swim lane',
        'swim','float in the water','swim relaxed','swim faster','swim technique',
    ],
    '羽毛球': [
        'badminton','shuttlecock','shuttle','smash','drop shot','clear shot',
        'drive shot','net play','defensive lift','attacking lob','bwf','singles match',
        'doubles match','racquet head','high serve','low serve','flick serve',
        'forehand smash','backhand clear','footwork','split step','net kill',
    ],
    '棒球': [
        'baseball','pitcher','batter','hitter','swing','mlb','home run','strike',
        'bunt','outfielder','infielder','shortstop','catcher','fastball','curveball',
        'slider','changeup','sinker','cutter','splitter','strikeout','walk-off',
        'grand slam','rbi','batting average','on base','stolen base','double play',
    ],
    '体操': [
        'gymnastics','gymnast','vault','balance beam','uneven bars','floor exercise',
        'salto','somersault','handstand','cartwheel','tumble','tumbling','rings event',
        'pommel horse','parallel bars','high bar','leotard','round off','back handspring',
        'aerial cartwheel','elite gymnastics','fig','code of points','split leap',
    ],
    'MMA综合格斗': [
        'mma','ufc','octagon','takedown','ground game','submission','guard pass',
        'mount position','kimura','armbar','triangle choke','knee strike','elbow strike',
        'clinch work','rear naked choke','rnc','sprawl','top control','side control',
        'half guard','open guard','closed guard','heel hook','d\'arce choke',
        'cage work','dirty boxing','grappling',
    ],
    '乒乓球': [
        'table tennis','ping pong','paddle','rubber','topspin loop','backspin',
        'sidespin','smash','chop','serve return','flick','ittf','pimples',
        'short pip','long pip','penhold','shakehand','forehand loop','backhand loop',
        'push shot','block return','counter loop','tabletennis','blade racket',
    ],
    '滑冰': [
        'ice skating','figure skating','speed skating','axel','lutz','salchow',
        'toe loop','flip jump','loop jump','combination spin','sit spin','camel spin',
        'edge work','blade edge','ice rink','short program','free skate','choreo sequence',
        'spiral sequence','triple jump','quad jump','skater','isu','skating boot',
    ],
    '排球': [
        'volleyball','spike','setter','dig','passer','serve receive','blocker',
        'libero','outside hitter','middle hitter','opposite hitter','attack approach',
        'jump serve','float serve','overhand pass','bump pass','rotation','net kill',
        'soft block','swing block','3-step approach','4-step approach','reset ball',
    ],
    '攀岩': [
        'climbing','climber','bouldering','climbing route','climbing hold','crimp',
        'jug hold','sloper','pinch grip','beta','top rope','lead climbing','anchor',
        'belay','belayer','harness','climbing shoe','sport climbing','trad climbing',
        'crag','send','flash','onsight','project route','heel hook','toe hook',
        'dyno','campus board','fingerboard','hangboard','v-grade','5.10','5.11','5.12',
    ],
    '柔术与摔跤': [
        'wrestling','jiu-jitsu','jiu jitsu','bjj','takedown','single leg','double leg',
        'pin','mount','side control','closed guard','half guard','escape mount',
        'submission','gi training','no gi','sweep','back take','kimura grip',
        'butterfly guard','x guard','de la riva','spider guard','folkstyle','freestyle wrestling',
        'greco roman','jiujitsu',
    ],
    '滑板': [
        'skateboarding','skater','ollie','kickflip','heelflip','manual','grind',
        'slide trick','skate deck','skate truck','skate wheel','bowl','vert ramp',
        'halfpipe','drop in','pop shuvit','varial','tre flip','nollie','switch stance',
        'fakie','grip tape','skatepark','rail slide','board slide','crooked grind',
    ],
    '传统武术': [
        'kung fu','wushu','martial arts','tai chi','taichi','taiji','qigong',
        'kung-fu','traditional form','horse stance','bow stance','front kick',
        'side kick','jab punch','straight punch','block','sword form','staff form',
        'broadsword','spear form','shaolin','wing chun','baguazhang','xingyi',
    ],
    '滑雪': [
        'skiing','snowboarding','snowboard','ski slope','piste','mogul','powder ski',
        'carve turn','parallel turn','ski lift','ski pole','ski binding','edge control',
        'race gate','downhill','slalom','giant slalom','super g','snowpark',
        'freeride','off-piste','backcountry','snow park','halfpipe','terrain park',
        'cross country ski','cross country skier','avalanche safety','short turns',
        'ski fitness','ski exercise','ski tips',
    ],
    '冲浪': [
        'surfing','surfer','wave','pop up','paddle out','paddling','takeoff',
        'bottom turn','top turn','cutback','surfboard','longboard','shortboard',
        'lineup','swell','barrel','tube ride','duck dive','turtle roll','wax',
        'fin setup','thruster','quad fin','wsl','asp','reef break','beach break',
    ],
    '舞蹈': [
        'dance','dancer','choreography','choreo','ballet','hip hop dance','contemporary dance',
        'jazz dance','tap dance','salsa dance','waltz','foxtrot','ballroom','dance step',
        'dance routine','dance class','pirouette','plié','fouetté','arabesque',
        'tendu','jeté','popping','locking','breaking','b-boy','b-girl','floorwork',
    ],
    '徒步与登山': [
        'hiking','hiker','trekking','mountaineering','backpacking','trail','summit',
        'peak bagging','switchback','hiking gear','hiking boots','backpack','layering',
        'base camp','ridge walk','alpine','via ferrata','scrambling','through hike',
        'thru hike','pct','at trail','appalachian trail','glacier travel','ice axe',
        'crampon','trail running shoe','trekking pole',
    ],
    '潜水': [
        'diving','scuba','snorkel','freediving','scuba dive','regulator','bcd',
        'dive mask','dive fin','decompression','wreck dive','reef dive','padi',
        'ssi','dive depth','neutral buoyancy','dive computer','dive tank','safety stop',
        'open water diver','advanced diver','rescue diver','dive log','equalize',
    ],
    '跑酷': [
        'parkour','freerunning','free running','precision jump','wall run','kong vault',
        'lazy vault','dash vault','speed vault','traceur','traceuse','urban movement',
        'obstacle course','gap jump','wall climb','tic tac','cat leap','arm jump',
        'pre run','flow movement','adapt','natural movement','rooftop','flip combo',
    ],
    '铁人三项': [
        'triathlon','triathlete','ironman','swim bike run','transition zone','t1',
        't2','brick workout','open water swim','road bike','cycling shoes','running pace',
        'half ironman','olympic distance','sprint distance','swim leg','bike leg',
        'run leg','wetsuit','transition area','aid station','draft legal',
    ],
    '综合运动健康': [
        'sports performance','athlete training','recovery protocol','mobility drill',
        'conditioning','athletic training','plyometric','hiit workout','prehab',
        'rehab','performance training','functional fitness','foam rolling','dynamic warmup',
        'static stretching','active recovery','sports nutrition','periodization',
        'speed training','agility ladder','reaction drill',
        'r.i.c.e','rice injury','sports injury','injury recovery','injury prevention',
        'rest ice compression','sprain','strain treatment','tendinitis','knee injury',
        'ankle sprain','shoulder pain','rotator cuff','acl injury','meniscus',
        'physical therapy','sports therapy','prehab exercise','warmup routine',
    ],
    '运动通用': [
        # 通用兜底：运动通用 L1 词表更宽松，包含跨项目运动概念
        'sports','athlete','athletics','fitness','exercise','workout','training program',
        'sport performance','endurance','strength','agility','speed work','coordination',
        'flexibility training','sports science','warmup routine','cooldown',
    ],
    '飞盘': [
        'ultimate frisbee','disc golf','frisbee','ultimate disc','disc throw',
        'forehand throw','flick throw','backhand throw','hammer throw','huck',
        'layout catch','disc pull','vertical stack','horizontal stack','cutter',
        'handler','poach','force flick','force backhand','d-line','o-line','wfdf',
    ],
    '台球': [
        'billiards','snooker','cue ball','rack','pocket shot','english spin',
        'eight ball','nine ball','ten ball','bridge hand','cue tip','jump shot',
        'masse','draw shot','follow shot','stop shot','break shot','safety play',
        'bank shot','combination shot','pool table','snooker table',
    ],
    '橄榄球': [
        'rugby','rugby league','rugby union','scrum','lineout','ruck','maul',
        'try score','conversion kick','fly half','scrum half','hooker','prop forward',
        'kick off','lineout throw','tackling technique','offload','breakdown','penalty kick',
        'drop goal','american football','nfl','quarterback','running back','wide receiver',
        'touchdown','field goal','pass route',
    ],
    '板球': [
        'cricket','batsman','bowler','wicket','run scored','over bowled','boundary',
        'six runs','ipl','test match','odi','t20','fielder','stumps','lbw',
        'leg before','no ball','wide ball','cover drive','pull shot','square cut',
        'leg spin','off spin','fast bowler','medium pacer','yorker','bouncer',
    ],
    '冰球': [
        'ice hockey','nhl','puck','hockey stick','goalie','slap shot','wrist shot',
        'snap shot','faceoff','power play','penalty box','blue line','red line',
        'hat trick','body check','stick handle','one timer','breakaway','icing',
        'offside hockey','butterfly save','glove save','five hole',
    ],
    '泰拳': [
        'muay thai','thai boxing','low kick','roundhouse kick','teep kick','push kick',
        'clinch knee','flying knee','elbow strike','horizontal elbow','spinning elbow',
        'check kick','nak muay','padwork','muay thai gym','muay thai shorts','mongkol',
        'wai khru','thai pad','heavy bag work',
    ],
    'CrossFit': [
        'crossfit','wod','amrap','emom','kipping pull up','muscle up','butterfly pull up',
        'snatch','clean and jerk','thruster','box jump','double under','hero wod',
        'rx workout','scaled','crossfit games','crossfit open','metcon','rope climb',
        'wall ball','toes to bar','t2b','handstand push up','hspu','kettlebell swing',
    ],
    '皮克球': [
        'pickleball','dink shot','third shot drop','no volley zone','kitchen line',
        'pickleball paddle','pickleball doubles','pickleball serve','volley rally',
        'dink rally','ernie shot','around the post','atp shot','soft game','hard game',
        'pickleball court','pickleball ball','non-volley zone',
    ],
    '跆拳道': [
        'taekwondo','tae kwon do','dobok','side kick','roundhouse kick','axe kick',
        'spinning hook kick','tornado kick','crescent kick','poomsae','taekwondo sparring',
        'kukkiwon','hogu chest protector','dojang','belt rank','black belt taekwondo',
        'taekwondo kicks','jump kick','flying kick',
    ],
    '柔道': [
        'judo','judoka','ippon','judo throw','sweep','harai','osoto gari','ouchi gari',
        'seoi nage','uchi mata','tai otoshi','ne waza','randori','judo dojo','judo gi',
        'kano','newaza','tachi waza','kuzushi','breakfall','ukemi','judo competition',
    ],
    '空手道': [
        'karate','karateka','kata','kumite','kihon','karate dojo','sensei',
        'karate gi','obi belt','mae geri','mawashi geri','gyaku zuki','jodan strike',
        'chudan strike','shotokan','goju ryu','wado ryu','shito ryu','kyokushin',
        'oss','kiai shout','karate stance','zenkutsu dachi',
    ],
    '其他运动': [
        # 兜底类，词表宽松
        'sport','athlete','athletic','competition','tournament','training','technique',
        'fundamentals','drill practice',
    ],
}

# ============================================================
# 形态反向词（通用，跨 L1 适用）
# 这些词出现意味着视频形态是"非教学"
# ============================================================
FORM_NEG = [
    # 比赛/集锦
    'highlight reel','highlights','full match','match recap','game recap','recap',
    'best of','compilation','montage',
    'craziest moments','epic moments','greatest moments','best moments',
    # Vlog/闲聊
    'vlog','day in the life','day in my life','q&a','q and a','story time','storytime',
    'podcast episode','interview with','reaction to','reacts to','reacting to',
    # Challenge/炫技
    'challenge accepted','tiktok challenge','dance challenge','viral challenge',
    'try not to laugh',"you won't believe",'shocking','unbelievable',
    'insane plays','crazy plays','epic fail','fails compilation',
    # 游戏/娱乐（含视频游戏）
    'gameplay','game play','minecraft','roblox','fortnite','fifa game','madden',
    'nba 2k','mlb the show','ea sports','ufc 5','#easports','#madden','#fifa',
    '#nba2k','arknights','pokerstars','#minecraft',
    # 音乐 MV
    'official music video','official video','lyric video','lyrics video','remix song',
    '(lyrics)','- lyrics','lyrics ]',
    # 影视
    'movie clip','movie scene','hd clip','official trailer','tv show',
]

# 已与 v4 INSTRUCTIONAL_KW 互补：v4 已有 fyp/foryou/funny/fail/vibes/dance challenge 等
# 这里聚焦"形态"而非"情绪/标签词"


if __name__ == '__main__':
    print(f"L1_VOCAB: {len(L1_VOCAB)} L1, 总词数 {sum(len(v) for v in L1_VOCAB.values())}")
    for L1, words in L1_VOCAB.items():
        print(f"  {L1:<15} {len(words):>3} 词")
    print(f"\nFORM_NEG: {len(FORM_NEG)} 词")

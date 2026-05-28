# Topic 提炼 Prompt · v0.5.1（运动垂类 · 英文专项）

> v0.5.1 是基于 1006 条人工 review 反馈的精修版本（46 条问题 → 4 类系统性问题）：
> 1. 人名失守（≈65%）：v0.5 让 LLM 自判"跨圈层认知度"不可靠 → 改为默认剥离 + 后处理 wiki 校验
> 2. 项目数过载（≈17%）：下游 4 分钟视频拍不下 10/15/40 项 → 硬上限 5
> 3. 视频执行时长/系列后缀（≈11%）：下游执行不出 20+ min 视频 → 时间特征剥离，保留实质内容
> 4. 信息保真偏移（个案）：曲解原视频主语/动作 → 加严 B1
>
> 设计原则不变：**判内容不判形式**，C1 立意仍是主防线。

---

## §1 · Topic 是什么 · 给谁用 · 核心价值

### Topic 定位

Topic 是给下游 AI 导演 agent 的**创作种子**：

- 不是视频摘要
- 不是 SEO/营销标题
- 不是评分模板
- 是这条视频"值得被做出来"的最锋利切入点的一句话表达

### Topic 的核心价值（4 条）

1. **立意精彩**：找到这条视频区别于同主题视频的最锋利切入点——**这是首要价值**。
2. **保真 + 延展**：基于源信息（title / description / tags）的具体性合理延展立意。源里没有的具体事实不脑补。
3. **AI agent 可执行**：留出创作空间——讲选题维度 / 场景 / 受众 / 痛点 / 价值；不剧透具体方法步骤。
4. **下游 agent 可接住**：topic 里的人物只能是信息源 / 背书，不能是出镜讲述者。

### Topic 的核心失败模式（这是你最容易踩的坑）

1. **中性描述**（合规但平）：`"X for Y"` / `"X's protocol for Z"` / `"Fundamentals of X for Y"`
   - 描述了视频内容，但没找到任何切入角度
   - 下游 agent 看完没有"必须做出来"的冲动
   - **这是 v0.4 时代最严重的失败模式**

2. **包装无实质**（形式精彩内容空）：`"X decoded: mastering Y"` / `"The science of X"`
   - 看起来像有立意，但拆开看不知道讲什么
   - 装饰词替代了内容

3. **焦虑 / 承诺式 click-bait**：`"Why your X fails: 3 ways to..."` / `"The exact X you need to..."`
   - 冒号前制造焦虑/悬念，冒号后给方法清单
   - 这是 v0.3 时代最严重的失败模式

### 输出语言

- **Topic 一律输出 English**，写给英文运动受众读
- 解释性字段（`self_check_note`）输出**中文**——这是给我们内部审核用的
- 其他字段（`video_type` / `narrative_intent`）保持 enum 英文值

---

## §2 · 好 Topic 长什么样（理解原理，不是模仿样式）

> ⚠️ **关键警告**：下面 10 条是历史样本，仅供你理解"什么算好立意角度"。
> 你的输出**绝对不能**与任何样例的内容、关键词、句式骨架一致。
> 如果你 input 的视频不是网球但你写出了 "X tennis singles strategies"，
> 不是 Pamela Reif 但你写出了 "Pamela Reif's 10-minute morning routine"，
> 不是孕期瑜伽但你写出了 "from snowplough to parallel"——
> 那你就是在抄样例，必须基于 input 的源材料重新生成。
> **样例 ≠ 模板**。你要做的是吸收"角度"这个抽象概念，不是复用具体词。

下面 10 条是经过一航人工 review + 立意判定双重通过的样本。**重点不是"抄这些样式"**，而是**理解为什么这些 topic 满足核心价值——特别是它们的"立意角度"是什么**。

```
1. "4 tennis singles strategies to stop getting broken and consistently hold serve"
   立意角度 · 痛点切入（getting broken）+ 价值锚点（consistently hold serve）
   why 好 · 数字盘点提供清晰预期；"getting broken"是网球真痛点，
          下游 agent 看到就知道"这视频是给经常被破发的人看的"。

2. "Why most people overreact when dodging: the efficiency of micro head movements"
   立意角度 · 反常识（多数人闪躲过度）
   why 好 · 一句话挑战了一个广泛误区，"micro head movements"提供具体价值锚点。
          虽然以 Why 起手，但承载的是真立意，不是套路化包装。

3. "A kettlebell coach's 3 technique adjustments to smooth out a clunky Turkish Get-up"
   立意角度 · 痛点切入（clunky）+ 受众限定
   why 好 · "clunky" 是 coach 真会用的口语词；
          头衔做背书（不出真名，下游 agent 不用复刻这个 coach）。

4. "Pool technique won't work in choppy water: 3 stroke tweaks for faster open water swimming"
   立意角度 · 跨场景反差（泳池 vs 开放水域）
   why 好 · 一句话给出一个明确的"假设破坏"——你以为会的不管用，
          数字盘点给到预期。

5. "Why ankle and hip mobility aren't the only blockers for your pistol squat"
   立意角度 · 反常识（不只是柔韧度的问题）
   why 好 · 挑战了 pistol squat 训练里最常见的误区。
          注意：这里 "isn't just" 不是套路反差，是基于源里真实立意点。

6. "From snowplough to parallel: how to control the natural drift once you commit to the downhill ski"
   立意角度 · 进阶过程中的具体卡点
   why 好 · 冒号前后共同服务"滑雪进阶"价值锚点；
          冒号后是过程中的具体问题，不是方法步骤。

7. "10 backcountry safety essentials for trail runners: packing for unpredictable conditions"
   立意角度 · 场景限定（不可预测环境）
   why 好 · 数字盘点 + 受众场景双重锚定；
          这是"立意较弱但场景具体"的合格 topic——不是每条都需要反常识，
          但必须有清晰的具体性锚点。

8. "I Tested 100 Years of Pre-Workout History: From 1930s Stimulants to Modern Supplements"
   立意角度 · 历史跨度反差
   why 好 · 真人创作者口吻"I Tested"自然；
          数字（100 years / 1930s）是时间跨度不是训练参数。

9. "A physical therapist's protocol for lateral ankle sprains: when to load and when to wait"
   立意角度 · 判断标准（不是动作清单）
   why 好 · 头衔背书 + 冒号后是判断维度（when to）不是方法步骤；
          下游 agent 拿到能自己组织"什么情况下怎么判"。

10. "Pamela Reif's 10-minute morning routine: no-equipment warm-up sequence"
    立意角度 · 名人方法引用 + 场景具体
    why 好 · Pamela 跨圈层独立认知度够（用户会主动搜她）；
          "routine"是方法名（合法引用），不是讲述形态。
```

**关键观察**：这 10 条覆盖了不同的立意角度——反常识 / 痛点 / 反差 / 进阶卡点 / 历史跨度 / 判断标准 / 场景限定 / 名人引用。**重点是它们都有"角度"，不只是"描述"**。

---

## §3 · 规则

规则分两层。**底线规则 (B)** 是不可妥协的硬禁；**形态规则 (F+W)** 是条件触发；**核心立意规则 (C1)** 是主防线。

---

### 底线规则（B1-B3，无条件硬禁）

```
B1 · 信息保真
─────────────────────────────────
源里（title / description / tags）没有的具体事实不脑补：
  - 数字（除明显的 1-5 盘点数及 duration 派生的合理表达）
  - 协议名 / 研究名 / 方法学名词（FAI / Mifflin-St Jeor / NSCA 等）
  - 专业术语（posterior chain / Zone 2 / VO2max 等——源里有才能用）
  - 年份（除时效性表达，参见结尾）
  - 动作执行参数（角度 / 次数 / 组数 / 心率区间）

专业词的等价转换允许：
  ✓ 源里有 "RDL" → topic 可写 "Romanian Deadlift" 或 "RDL"
  ✗ 源里没有 "posterior chain" → topic 不能加这个词

**B1.加严 · 不曲解原视频主体（v0.5.1 新增）**
  Topic 的主语 / 动作 / 受众 必须与原视频一致。
  特别注意：当原视频在说"X 做不到的事"时，topic 不能改述成"X 能做到的事"。
  
  ✗ 错误曲解案例：
    原 title: "Robotics just don't have the touch for this work" + 提到 saturation divers
    → 错的 topic: "living weeks underwater for tasks robotics can't handle"
       （把"机器人做不到"曲解成"人能在水下生存数周"，主体错位）
    ✓ 对的 topic: "Why some underwater work still requires human saturation divers"
  
  自查：topic 删掉装饰词后剩下的核心 claim，是否就是原视频在讲的那件事？

B2 · 方法边界
─────────────────────────────────
Topic 讲：选题维度 / 场景 / 受众 / 痛点 / 价值 / 关键对比锚点 / 判断标准
Topic 不讲：具体方法步骤 / 训练量参数 / 动作执行细节

  ✓ "when to load and when to wait"（判断标准）
  ✗ "Load with 3 sets of 10 reps at week 1, then ..."（方法步骤）

原则：留出 agent 的创作空间——topic 是"拍什么角度"，不是"怎么拍"。

B3 · 人物身份保真
─────────────────────────────────
不发明任何人物头衔 / 资质 / 履历 / 奖项 / 数字成就。
源里写 "a physical therapist" → topic 就用 "a physical therapist"
不要脑补成 "a renowned physical therapist with 20 years experience"
```

---

### 形态规则（F1-F3）

这 3 条都是**内容判定**，不是形式禁——它们禁的是"形式背后真实存在的内容问题"。

```
F1 · 人名（默认剥离 + 顶流白名单 + 后处理 wiki 校验）─────────────

  **v0.5.1 关键变更**：默认所有人名都剥离为身份头衔。
  仅当人物是"真顶流"（圈外人也认识，乔丹/奥尼尔/帕梅拉那种）时才保留。
  
  Step 1（判定：圈外人会主动搜索这个名字吗？）
  
  ✓ 保留真名（圈外独立搜索意愿）—— 极小集合
    - 历史/当代体育超级巨星：
      Michael Jordan / Kobe Bryant / LeBron James / Shaquille O'Neal /
      Cristiano Ronaldo / Lionel Messi / Mike Tyson / Tiger Woods /
      Roger Federer / Serena Williams / Usain Bolt / Michael Phelps /
      Arnold Schwarzenegger / Conor McGregor / Floyd Mayweather
    - 大众跨圈 KOL（订阅 10M+ / 出过大众媒体）：
      Pamela Reif / Chloe Ting / Joe Wicks / Andrew Huberman / Peter Attia /
      Chris Bumstead / Jeff Cavaliere (Athlean-X) / Yoga With Adriene
    - 不确定时默认归到 ✗ 不要赌
  
  ✗ 默认剥离 —— 改为身份头衔
    - 任何"小众教练 / 普通运动员 / mid-tier 创作者 / 圈内有名但圈外不认识"的名字
    - 包括但不限于：Tony Jeffries / Coach Donny / Bobby Tewksbary /
      Will John / Todd Kolb / Coach Chijo / Spencer Nuzzi / Dan Blewett /
      Katy Appleton / Andy Chong / Taylor Feld / Mike Israetel / Mario Tomic
    - 所有视频里出镜讲解但标题没他名字的博主
  
  Step 2（头衔替换规则）

  **极重要**：剥离人名 ≠ 削平立意。
  原 topic 如果有反常识 / 痛点 / 反差 / 对比 / 受众限定 等立意角度，
  剥人名时必须保住这些立意，**不要退到 "A coach's foundation for X" 中性描述**。
  
  重点是立意不是句式——只要立意还在，"why X" / 冒号反差 / 痛点开头 这些句式继续用，不要怕。
  
  ✓✓ 立意 + 头衔 双在（理想）
    "An Olympic boxing medalist on why footwork and weight transfer beat arm power for the perfect jab"
    "A pro footballer's 3 mental adjustments to stop second-guessing on the pitch"
    "Why elite midfielders always seem to have more time: 4 positioning habits from top players"
    "An MLB hitting coach on why bat drag is the #1 swing flaw and how to fix it permanently"
  
  ✓ 至少立意在（可接受）
    "Why footwork and weight transfer matter more than arm power for a perfect boxing jab"
    （没头衔也没人名，但反常识立意还在）
  
  ✗ 立意被削平（v0.5.1 易踩坑——上一版 #3 就是这样）
    原 v0.5: "Tony Jeffries' foundation for boxing beginners: why your stance and footwork matter more than the punch"
    错改: "A boxing coach's complete foundation for absolute beginners starting from scratch"
        → 立意"why 站位/步法 > 拳头"被丢了，退回中性描述
    对改: "Why stance and footwork matter more than the punch: a boxing coach's foundation for beginners"
        → 立意保住，头衔做背书
  
  ✗ 名字硬留
    "Tony Jeffries' 4-minute beginner framework"
    "Bobby Tewksbary's method to fix bat drag"
  
  头衔写法准则：
  - 资质来源必须在源信息里能找到（author bio / desc / hashtag）
  - 不要脑补"renowned" / "world-class" / "with 20 years experience"
  - 如源里无背书 → 退到中性表达："A coach's..." / "A pro player's..."
  - 即使退到中性，**立意/角度仍要保住**
  
  Step 3（句式约束 —— 下游 agent 兼容性）
  
  Topic 里的人物（无论真名还是头衔）只能是**信息源 / 背书 / 方法引用**，
  绝不能是"讲述者"。原因：下游 agent 拍视频时这个人不会出镜。
  
  ✓ 引用形态（OK）
     "X's method / X's protocol / X's logic on Y"
     "Methods from X / Inspired by X"
     "Built on X's framework / X's case for Y"
  
  ✗ 讲述形态（禁）
     "X teaches you / X explains why / X breaks down"
     "A coach explains / A therapist breaks down"
     "Learn X from [Person] / Train with [Person]"
  
  Step 4（后处理校验 —— 由生成脚本执行）
  
  生成后由 wiki API 校验：
  - 候选人名 → Wikipedia → sitelinks ≥ 10 OR page views (30d) ≥ 5000 → 保留
  - 不达标 → 重写为头衔
  这是兜底机制，不影响你按 Step 1-3 的规则生成。
  
  Step 2（句式约束 —— 下游 agent 兼容性，不是形式禁）
  
  Topic 里的人物只能是**信息源 / 背书 / 方法引用**，绝不能是"讲述者"。
  原因：下游 agent 拍视频时这个人不会出镜，topic 预设"由 X 讲述"
  会让 agent 无法组织叙事。这是真实的内容约束，不是形式偏好。
  
  ✓ 引用形态（OK）
     "X's method / X's protocol / X's logic on Y"
     "Methods from X / Practiced by X / Inspired by X"
     "Built on X's framework / X's case for Y"
  
  ✗ 讲述形态（禁）
     "X teaches you / X explains why / X breaks down"
     "A coach explains / A therapist breaks down"
     "Learn X from [Person] / Train with [Person]"

F2 · 冒号陷阱（内容判定 —— 反空悬念，不是反冒号）────

  冒号本身不禁。但冒号承载的内容关系必须有实质：
  
  ✓ OK 的冒号组合（前后都是实体信息）
     - 限定/聚焦："10 essentials for trail runners: packing for unpredictable conditions"
     - 对比/反差："Glute-focused vs. traditional DB RDLs: the single setup difference that shifts the tension"
     - 场景过渡："From snowplough to parallel: how to control the natural drift"
     - 判断标准："A physical therapist's protocol for ankle sprains: when to load and when to wait"
  
  ✗ 禁的冒号组合（一边悬念/焦虑，另一边方法/数字）
     - 悬念 + 方法："Why your X fails: 3 essential techniques to unlock Y"
     - 焦虑 + 数字："The score you need to survive: 3 ways to test your limits"
     - 抽象 + 升华："X positioning decoded: mastering the specific tactical runs"
  
  判别问题：冒号前是钩子还是实体？冒号后是承诺还是实体？
            前后两个都是实体且共同服务一个价值锚点 = OK。

F3 · 数字 + 时长 + 系列后缀（v0.5.1 重写）────────────

  下游 AI 导演 agent 当前只能生成 ≤4 分钟的视频。
  规则要服务这个约束。

  ─ F3-a · 项目数（硬上限 ≤5）─
  
  无论原 title 是 10/15/20/40 tips，topic 改写时必须收敛到 ≤5。
  
  ✗ "15 common freestyle drills ranked: ..."
  ✗ "40 pro tips on midfield control from ..."
  ✗ "10 essentials for trail runners: ..."
  
  ✓ 改写策略：
    - 归并主类："4 categories of freestyle drills: from essential to overrated"
    - 抓核心痛点："The single fix behind most midfield possession mistakes"
    - 去数字保实质："Choosing a dive computer for beginners: what actually matters"
  
  注：源 title 数字是 1-5 范围的，直接保留。
  
  ─ F3-b · 视频执行时长（剥离时间词，保实质）─
  
  原视频时长 / 跟练时长 是"视频本身要看多久"，下游 4 分钟拍不出来。
  必须去掉时间特征，但用其他实质信息撑起 topic。
  
  ✗ "Adriene's 20-minute morning yoga flow: a breath-centric sequence..."
  ✗ "A 45-minute deep stretch routine to release the lower back"
  ✗ "A 21-minute lower body stability routine for skiers"
  
  ✓ "A breath-centric morning yoga flow to wake up the core and build mobility"
  ✓ "A deep stretch flow built to release the lower back and hips"
  ✓ "A lower-body stability routine for skiers: targeting the weak links"
  
  规则：保留训练性质 / 目标受众 / 关键效果，删除分钟数。
  
  ─ F3-c · 教学方案周期（可保留，须是内容主体）─
  
  如果"N 天 / N 周"是教学方案本身（且单视频讲明白整体结构），保留：
  
  ✓ "A 7-day mobility plan structured in a single video"
  ✓ "How to structure an 8-week marathon build for first-time runners"
  ✓ "From couch to 5k: how to map the running progression over 8 weeks"
  
  如果"N 天 / N 周"是视频系列（每天一集 / 每周一集），全删：
  
  ✗ "Day 1 of the 21-day fitness challenge: ..."
  ✗ "Week 3 of an 8-week strength program: ..."
  ✓ "A lower-body stability foundation for skiers learning the basics"
  
  判别 trick：
  把时长/周期词删掉后，topic 还成立吗？
  - 删后变残破 → 是内容主体 → 保留
  - 删后仍完整 → 是执行格式 → 删除
  
  ─ F3-d · 系列后缀全部杜绝 ─
  
  Topic 必须是独立内容，不能依赖"前后集"才看懂。
  
  ✗ "Day 1 of..." / "Episode 1 of..." / "Part 2 of..." / "Ep. 3" / "S01E04"
  ✗ "Continued from the previous video" / "as part of the 21-day series"
  
  ─ F3-e · 其他数字规则（沿用 v0.5）─
  
  ✗ 禁：猎奇具体（70+ rating / 1.5 年 / 400kg）/ 视频时长自指（90秒揭秘）/
        view_count 类社交指标
  ✓ OK：对比锚点（A vs B / 1mm difference）/ 基础量级（每周 3 次）/
        源里真实数字（"3-8% cadence increase" 来自源视频研究就保留）
  
  核心问句：这个数字让用户能预期到具体东西吗？或能对应到自己吗？
```

---

### 用词与语言规则（W1-W2）

```
W1 · 用词保真 · 不空升华 ──────────────

  底线（衔接 B1）：源里没有的术语不引入。
  
  形态层面禁：
  
  ✗ 空升华动词（说"改变了/转变了"但不说改成什么样）
     "completely change X" 
     "shifts X" / "transforms X" / "unlocks X"
     （除非紧跟具体描述改成什么样）
     
  ✗ 拔高表达（用 academic 词替代能讲清的普通词）
     foundational mechanics（→ basics / fundamentals）
     biomechanical sequencing（→ movement order）
     movement architecture（→ how the movement is built）

W2 · Conversational + Native ──────────────

  默认像懂行的爱好者/coach 在说话，不像论文摘要。
  
  专业词在源里有的：照用（不强制通俗化）
  专业词在源里没有的：默认 conversational 表达
  
  英文地道要求：
  - American English（spelling / idiom 选美式）
  - 用英文母语者真用的搭配，不要"中文思维直译"
     ✗ "the persistence of knee pain"（直译"膝盖疼的持续性"）
     ✓ "why knee pain keeps coming back"
     ✗ "the importance of foot placement"（直译"脚位置的重要性"）
     ✓ "why foot placement matters more than you think"
  - 不要 comma splice
  - 可用 contractions（don't / can't / it's）
  
  内容深度由源视频决定，不强制通俗化也不强制专业化。
  专业 vs 大众是内容偏好，不是质量问题。
```

---

### 核心立意规则（C1 · 主防线）

```
C1 · 立意必须有实体支撑 ─────────────────────────────

  每条 topic 必须传达 substantive 立意或潜在价值。
  
  3 种失败模式（任一命中即不及格）：
  
  ✗ 中性描述（合规但平）
     例：A physical therapist's 3-minute routine to stretch and strengthen hip flexors
        → 描述了视频内容，但没有任何切入角度，没有差异化
        → 下游 agent 看不出"为什么这条值得做"
  
  ✗ 包装无实质（形式精彩内容空）
     例：Striker positioning decoded: mastering the specific tactical runs
        → "decoded" / "mastering" 是装饰词，拆开看不知道讲什么
        → 没有实体内容
  
  ✗ 焦虑 / 承诺式 click-bait
     例：Why your X fails: 3 essential techniques to unlock Y
        → 悬念头 + 方法尾，是标题党组合，无真立意
  
  通过条件：用户读完，能预期到具体的——
  
  ✓ 认知（"原来是这样" —— 反常识 / 隐藏角度 / 新视角）
  ✓ 痛点（"我也有这个问题" —— 具体场景 / 受众痛点）
  ✓ 价值（"看完会知道..." —— 判断标准 / 关键决策 / 对比维度）
  ✓ 对比（"A vs B 的差异" —— 跨场景 / 跨方法 / 跨受众）
  ✓ 反差（"以为 X 其实 Y" —— 假设破坏 / 反误区）
  
  中至少一种。
  
  允许的特例：
  源信息确实薄到无法支撑任何切入角度时（例如 vlog 类、纯科普类
  没有特别角度），可保留中性描述，**但必须在 self_check_note 中
  说明"源信息不支撑更锋利的立意"，否则按失败处理**。
```

---

### 时效条款

源 title/description 里出现过去年份（2024 / 2025 / 2026）时，topic 一律替换为**当前年份 2026**，或直接省略年份。未来年份（2027+）保留不动。

---

## §4 · 生成流程（3 段式自查）

```
[第一段 · 创作]
看完源信息（title + description + tags + biz_domain + duration + author），
问自己：这条视频区别于同主题视频的最锋利切入点是什么？

可能的切入角度（不限于）：
- 反常识（破广泛误区）
- 隐藏切入点（视频里讲了但同类视频没人这么切）
- 跨域类比（跨运动 / 跨学科 / 跨场景）
- 受众反差（不教初学者教进阶 / 反常规受众）
- 价值反差（看似 X 其实 Y）
- 痛点具体化（不泛泛说"提升 X"，说"X 时的某个具体卡点"）

找到立意，自由表达——不要被规则牵着走。
不要回避 Why X / 冒号 / 反差 这些有立意承载力的句式。

[第二段 · 价值判断式自查（4 问，C1 是首问）]

  问 1（C1 立意判定 —— 最重要）
  这条 topic 是真有立意/价值，还是中性描述 / 包装无实质 / click-bait？
  
  具体测试：用户读完，能不能预期到一个具体的
  认知 / 痛点 / 价值 / 对比 / 反差？
  
  - 如果只是 "X for Y" 的中性描述 → 失败
  - 如果只是 "X decoded: mastering Y" 的包装 → 失败
  - 如果只是 "Why X fails: 3 ways to..." 的 click-bait → 失败
  
  → 失败必须重写。除非源信息真的薄到无法支撑立意——
    那种情况下，必须在 self_check_note 里说明这个边界。
  
  问 2（C1 的语言表达）
  读起来像一个懂行的 coach 在说话（conversational + native），
  还是 academic / clinical / 中式直译？
  
  问 3（B1-B3 底线核查）
  - 源里没有的具体事实有没有脑补？（数字 / 协议 / 术语 / 人名 / 头衔）
  - 有没有剧透方法步骤 / 训练参数？
  - 有没有脑补人物头衔履历？
  
  问 4（F + W 形态核查）
  - F1：人物是否默认剥离为头衔？只保留了真顶流？
  - F1：**剥离人名时立意是否被削平**？如果原始切入是"why X / 反差 / 痛点"，
        剥人名后必须保住这个立意，不能退回 "A coach's foundation for X" 中性描述
  - F1：人物是引用形态还是讲述形态？
  - F2：用了冒号的话，前后都是实体内容吗？
  - F3-a：项目数 ≤5？
  - F3-b：视频执行时长（如 20-min/45-min）是否剥离？
  - F3-c：教学方案周期是否是内容主体（删了 topic 不完整）？
  - F3-d：有没有 "Day N of" / "Episode N" 系列后缀？
  - W1：有没有"completely change X 但不说改成啥"的空升华？

[第三段 · 输出]
通过 4 问的，输出 JSON。
直接输出 JSON，不加 markdown 注释、不加任何解释文字。
```

---

## §5 · 输出格式

```json
{
  "topic_id": "<透传>",
  "source": "<YouTube | Bilibili>",
  "url": "<透传>",
  "original_title": "<透传>",
  "topic": "<English string，符合本 prompt 所有规则>",
  "description": "<透传 description，最多 300 字符截断>",
  "video_type": "<single_skill | multi_skill | knowledge | follow_along | highlight | other>",
  "narrative_intent": "<answer_question | teach_method | explore_principle | build_cognition | take_stance>",
  "names_used": ["<topic 中保留的真人名，按 F1 Step 1 白名单标准；空数组 [] 表示无人名>"],
  "self_check_note": "<中文，必须包含两部分：(1) 立意角度是什么——反常识/痛点/反差/对比/价值/认知 中的哪一个；(2) 用了什么具体源信息支撑立意。如果是中性描述，说明源信息为何不支撑更锋利立意。>"
}
```

**`names_used` 字段说明**：列出 topic 文本里所有保留下来的人名（按 F1 Step 1 已经过你的判定，认为是真顶流的）。这个字段由后处理脚本二次校验：每个名字会被独立判定是否真"乔丹/帕梅拉级跨圈层认知"，不达标的会触发自动重写为头衔。所以你不要乱填——保守原则，不确定就空数组 + 用头衔。

**Null 触发条件**（topic 字段可为 null）：
- 纯画面 / 纯情绪 vlog（没有具体动作 / 技术 / 原理 / 人物信号）
- 跑题（非运动内容）
- 源信息单薄到无法支撑任何具体声明
- **纯临床诊断 / 医疗手段**（如 "TFCC tear diagnosis" / 纯查体测试 / 病理诊断）
  ─ 运动康复、伤后训练、预防性训练 OK
  ─ 单纯医疗诊断、临床检查、病理判断不属于本垂类，输出 null

**空描述 fallback（TikTok 类）**：
- 当 description 为空 / 仅 hashtag 时，topic 应从 caption 主体（去 hashtag）+
  hashtag 关键词合成
- caption 也无实质内容时（如 "Do you agree?" / "Check bio to learn how to swim"），
  输出 null —— 不要硬凑

**不要因为基线 / 描述写得不够好就 null**——title 含具体动作名 / 技术名 / 训练主题 / 受众的，禁止 null，以 title 里的具体性为锚点合理延展立意。

---

## 附录 · video_type 与 narrative_intent 定义

沿用 v0.3 定义，**详见 `gen_topic_prompt_运动_v0.1.md`**：

- **video_type 6 分类**（§3）：single_skill / multi_skill / knowledge / follow_along / highlight / other
  - 每类有必要维度门槛（§3 表）——必要维度都凑不齐 → null
- **narrative_intent 5 分类**（§3.5）：answer_question / teach_method / explore_principle / build_cognition / take_stance
  - 一条 topic 必须能归为且仅归为一种 intent

---

## 收尾提醒

- 直接输出 JSON，**不加** markdown 代码块标记、**不加**解释文字
- Topic 是 English；self_check_note 是中文
- **C1 立意是首要判断**——遇到边界 case，回到 §1 核心价值想问题，不要硬套规则
- 不要为了避免规则而退守"中性描述"——那是 v0.4 最严重的失败模式

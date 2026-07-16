# 交接文档:求签沉浸式改版(签桶动画 + LLM 解读 + 收藏/静心集)

> 2026-07-16 由 Claude Code 调研整理,交接给 Codex 继续实现。
> 所有"现状"均已在代码里逐条核实过,文件行号可直接点开对照。

## 一、需求(用户原话归纳)

参考视觉稿:一张「山间·清宁签」截图 —— 暗色寺院背景,米色签文卡片,标题"心定身安",
正文一段处境映照,下方「心绪指引」(今日可做的具体建议)+ 一句收束语
"心若从容,万事皆缓",底部两个按钮:深红「收藏 存入静心集」、金边「分享 生成签文图」。

要做的事:

1. **求签动画**:点击求签后,签桶移动到画面中央 → 晃动 → 摇出一支签 → 展示签文卡片。
2. **LLM 解读**:卡片带简单解读,用 LLM 生成(不是签谱静态文案)。
3. **收藏**:可收藏到"我的签文"(静心集)。
4. 目标是**更沉浸**:仪式有归宿,个人页能回看。

## 二、已确认的产品决策(用户拍板,勿再问)

1. **个人页「我的签文」只展示收藏过的签**(不是全部摇签历史)。
   结果卡加「收藏 存入静心集」按钮,收藏才进列表 → 有"我选择留下"的仪式感。
   后端给 `qian_draws` 加 `saved` 标记 + 列表接口。
2. **LLM 解读要结合用户命盘/所问,个性化**。
   把四柱命盘 + 本次所问的殿(主题)+ 签面一起喂给 LLM。
3. 「分享 生成签文图」(canvas 出图)**放到最后或下一轮**,先不挡主流程。
4. 产品红线:**不预测吉凶、不承诺、观照式语气**(全站现有调性,见 chat.py 的 SYSTEM_PROMPT)。
   解读结构照截图:处境映照一段 + 「心绪指引」一条具体可做的事 + 一句收束语。

## 三、现状(逐条核实过的代码事实)

### 前端 `apps/web-desktop/`

- 页面:`src/pages/` 下 Chat/Home/Incense/Lamp/Library/Palm/Profile/Qian/Wishes。
- **`src/pages/Qian.tsx`(114 行)**:
  - `draw()`(第 27-37 行)调 `api.drawQian(hall)`,拿到结果后
    **`setTimeout 1250ms` 占位 + 容器加 `is-drawing` class**(第 31、41 行)——
    动画状态机正好接在这里,后端节奏不用改。
  - 结果卡 `QianReading`(第 95-114 行)只有「再问一事」和
    「带此签去问卦」(`/chat?qian=<id>`)两个动作,**没有收藏按钮**。
  - 背景图 `/images/qian-chamber-premium.webp`:暗色签房,签筒立在案上(见下"视觉调性")。
- **`src/pages/Profile.tsx` 第 28、31 行**:两处「我的签文 · 回看曾经照见的念头」
  都是 `Link to="/qian"` —— 点进去是重新摇签页,**不存在签文列表页**。
- **`src/api.ts`**:qian 相关只有两个方法(第 55-56 行):
  - `drawQian: POST /api/qian/draw` body `{hall, topic}`
  - `qianQuota: GET /api/qian/quota`
  - 另有 `streamChat`(第 85 行起)是现成的 SSE 消费实现,可照抄它做解读流。
- 整个前端代码库 **grep 不到「收藏 / 静心集 / saved / collect」** —— 截图里那两个按钮是目标稿,不是现状。

### 后端 `apps/api/`

- **`app/routers/qian.py`**:只有 `POST /api/qian/draw` 和 `GET /api/qian/quota` 两条路由。
- **`app/services/qian.py`**:
  - `draw()`:先 `quota.consume(db, user_id, "qian")` 扣每日额度(超限抛 429),
    再 `_weighted_pick(topic)`(殿主题权重 3:1,`secrets.randbelow` 加密级随机),
    落库 `QianDraw`,返回 `QianOut`。
  - `get_by_draw_id(db, user_id, draw_id)` 已存在(校验归属),chat 正在用它把签面喂 LLM。
- **`app/models.py` 第 80-91 行 `QianDraw`**:
  `id / user_id / hall / topic / qian_slug` + TimestampMixin,
  索引 `ix_qian_user_created(user_id, created_at)`。**没有 saved 字段。**
- **签谱来源**:`app/knowledge/qianpu.py` —— 关帝灵签一百签,来自 knowledge_wiki 图谱
  (全站单一语料源,books/passages 表已删除,别再引用)。
  `QianEntry` 字段:`no/level/story/text/src/note/topics/slug`。
- **`app/schemas.py`**:`DrawQianIn`(hall 校验 `HALL_KEYS`)、
  `QianOut`(id/no/level/story/text/src/note/topic/drawn_at,CamelModel 自动驼峰)。
- **LLM**:`app/providers/llm/__init__.py` 的 `get_llm()` →
  deepseek(`OpenAICompatibleLlm`)或 `MockLlm`(CI/无 key 时)。
  接口:`llm.stream(messages, temperature=..., max_tokens=...)` 异步生成器吐 delta。
  **注意 mock 分支**:chat.py 里 `_expand_query` 对 `llm.name == "mock"` 有专门降级,解读接口也要给 mock 一个确定性兜底(比如直接返回签谱 note),保证测试可跑。
- **chat 里现成的参考实现**(`app/services/chat.py`):
  - 第 233-339 行 `stream_reply`:SSE 事件字典模式 `{type: session|delta|citation|done|error}`,路由层怎么包装成 SSE 看 `app/routers/chat.py`。
  - 第 268-277 行:**把签面塞进 system message 的现成写法**
    (`【用户刚求得的签】{q.no}·{q.level}(签题:{q.story}):{q.text} 签解:{q.note}`)。
  - 第 34-47 行 SYSTEM_PROMPT:山问人设 + 合规边界(≤150 字、不预测、不给医疗/法律/投资决策),解读 prompt 照这个调性写。
- **命盘**:`app/services/bazi.py` + `app/services/profile.py` 已能排四柱;
  chart 含 `dayMaster / pillars / fiveElements / zodiac / summary`。用户可能没填生辰 —— 解读要能优雅降级(没命盘就只按殿+签面解)。
- **迁移**:`apps/api/alembic.ini` 存在,加字段走 alembic 迁移。
- 测试在 `apps/api/tests/`(pytest)。

### 视觉调性(动画要贴这套语言)

- 现有签室背景 `qian-chamber-premium.webp`:暗色木构寺院内景,左侧窗棂透进**暖金体积光束**,
  深炭黑石案,**红漆铜箍竹签筒**立于案上,签筒里插满竹签,背景有香炉青烟、烛火,电影感写实。
- 目标卡片(截图):米色宣纸质感卡片、细金描边、衬线字、深红实心按钮 + 金边描线按钮。

## 四、实现计划(按此顺序做)

### 后端

1. `QianDraw` 加 `saved: Mapped[bool] = mapped_column(default=False)` + alembic 迁移。
2. `services/qian.py` 加三个函数:
   - `set_saved(db, user_id, draw_id, saved: bool)`(校验归属,参考 `get_by_draw_id`)
   - `list_saved(db, user_id)` → 按 created_at 倒序,join 签谱内容(`qian_by_slug`)
   - `interpret(db, user_id, draw_id)` → 异步生成器:
     读命盘(可能为 None)+ 殿/topic + 签面,组 messages,`llm.stream` 吐 delta;
     mock provider 时直接吐签谱 `note` 兜底。
     解读输出结构(约 120 字内):处境映照 2-3 句 + 「今日可做」一条 + 一句收束语。
3. `routers/qian.py` 加三条路由(鉴权都用现有 `get_current_user`):
   - `POST /api/qian/{draw_id}/save` body `{saved: bool}` → `{saved}`
   - `GET /api/qian/saved` → 收藏列表
   - `GET /api/qian/{draw_id}/reading` → SSE(照 chat 路由的包装方式)
4. `schemas.py`:`QianOut` 加 `saved: bool = False`;新增列表响应模型。
5. pytest:save/unsave、越权(别人的 draw_id 404)、列表只含 saved、mock 下 reading 可用。

### 前端

6. `api.ts` 加 `saveQian` / `listSavedQian` / `streamQianReading`(SSE 消费照 `streamChat` 抄)。
7. **`Qian.tsx` 动画状态机**(核心体验,纯 CSS keyframes,不引动画库):
   `idle → summoning(签桶从背景位置放大/移到画面中央) → shaking(左右摇晃 2~3 轮,竹签轻响感) → ejecting(一支签跳出、升起) → revealing(签放大淡出,翻出签文卡片)`。
   - 接在现有 `draw()` 的 1250ms 占位处:请求已在动画开始时发出,结果到手后等 shaking 播完再进 ejecting,体感"摇出来的"。
   - 签桶/签可以用独立 DOM 元素(图片或 CSS 绘制)盖在背景上;`prefers-reduced-motion` 时直接跳到结果。
8. **结果卡**改版:
   - 保留签面(no/story/text/level/src);
   - 加「心绪指引」区块:调 `streamQianReading` 流式渐显;
   - 加「收藏 存入静心集」按钮(已收藏态:实心→"已存入静心集");保留「带此签去问卦」。
9. **个人页签文列表**:新组件(路由如 `/profile/qians` 或 Profile 内嵌区块),
   只列收藏的签,卡片风格沿用米色宣纸;`Profile.tsx` 第 28、31 行两处链接指过去。
   支持取消收藏。空态文案给一句(比如"还没有留下的签,去摇一支")。
10. CSS 写在现有样式体系里(全局 css,类名沿用 `qian-*` / `premium-*` 前缀习惯)。

### 放最后 / 下一轮

11. 「分享 生成签文图」:canvas 把签文卡片渲染成图下载。

## 五、开发环境(重要,别踩)

- API:uv + uvicorn,**端口 3001**;用户经常自己开着 `--reload`,
  启动前先探测 3001 是否已被占用,占用就直接用,不要杀进程。
- 桌面前端:Vite,**端口 5174**,代理到 3001。
- 备用端口(如需另起不影响用户的实例):api-b **3021** / web-desktop-b **5194**。
- `graph.json`(知识图谱数据)**只读**,不要写它。
- 语料唯一来源是 knowledge_wiki 图谱;books/passages 表已删,别引用。

## 六、生图任务(交接给 Codex 直接用自家 imagegen)

用户指定用 Codex 生图。本会话通过 `codex exec --enable image_generation` 包装尝试,遇到的坑:

- codex-cli 0.141.0 + ChatGPT 账号:默认模型 `gpt-5.6-sol` 报 400
  "requires a newer version of Codex"(CLI 版本旧);`gpt-5.1` 报
  "not supported when using Codex with a ChatGPT account";`gpt-5.5` 未验证。
  → **Codex 交互会话里自己调 imagegen 工具即可绕开这些**,或先升级 CLI。

需要的成品图(两张,风格必须贴合 `apps/web-desktop/public/images/qian-chamber-premium.webp`:
暗色寺院、暖金光束、红漆铜箍签筒、电影感写实;建议把该图作为参考图喂进去):

1. **四格分镜示意图**(给用户确认动画节奏用,16:9 横幅):
   已写好的英文 prompt(可直接用):

   > A four-panel horizontal storyboard filmstrip for a mobile app 'draw a fortune stick' (qiu qian) animation. Cinematic photorealistic style, dark moody Chinese temple interior, warm golden god-ray light beams from a latticed wooden window on the left, deep charcoal shadows, drifting incense smoke haze, a dark polished black marble altar table. Consistent art direction and lighting across all four equal panels, separated by thin elegant gold vertical dividing lines. A small refined serif Chinese caption label centered beneath each panel. Panel 1 caption 入场: a red-lacquered bamboo fortune-stick tube with brass hoops, full of slender bamboo fortune sticks, gliding to the center of the dark table and settling into a warm pool of light. Panel 2 caption 摇签: the same tube tilted and shaking, the bamboo sticks rattling and fanning outward, soft motion-blur streaks conveying vibration, dust and incense drifting through the light. Panel 3 caption 出签: one single bamboo fortune stick rising and ejecting straight up out of the tube, catching a bright golden light beam, its tip softly glowing. Panel 4 caption 成签: the one chosen bamboo stick floating upright and alone inside a warm spotlight halo, the tube softly out of focus behind it, poised to be read. Warm amber and deep charcoal palette, volumetric light, restrained luxury editorial mood, no extra text beyond the four short panel labels.

2. **动画用素材(如决定用图片而非纯 CSS 绘制)**:
   - 签桶精灵:透明背景 PNG,红漆铜箍竹签筒正面略俯视,插满竹签,约 600×900;
   - 单支竹签:透明背景 PNG,竖直,签头有编号红字、微金光。
   - 存放到 `apps/web-desktop/public/images/`,压成 webp 与现有资产一致。

## 七、验收清单

- [ ] 摇签全程动画流畅,`prefers-reduced-motion` 有直达结果的降级;
- [ ] 解读流式渐显,断流/LLM 挂了有兜底文案(不阻塞签面展示);
- [ ] 收藏/取消收藏即时生效,刷新后个人页列表一致;
- [ ] 越权访问他人 draw_id 返回 404;
- [ ] mock LLM 下 pytest 全绿;
- [ ] 文案全程不出现吉凶断言/预测承诺。

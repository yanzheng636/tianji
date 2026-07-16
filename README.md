# 赛博天机寺 · 可上线版

把 `docs/` 里的单文件 demo，做成**前后端分离**、可商用可上线的 Web 应用。

> 定位：**传统文化娱乐 + 心理疗愈**。所有解读由 AI 生成，不预测命运、不承诺改命。

---

## 这不是换皮 demo

原 demo 是纯前端空壳——摇签是 `Math.random()`、上香靠 `localStorage` 计时、AI 问卦是写死的正则话术、支付点一下弹 toast。本项目把每一处都做成了**服务端权威**的真实闭环：

| 能力       | demo              | 本项目                                           |
|----------|-------------------|-----------------------------------------------|
| AI 问卦    | 正则匹配固定话术          | 真 LLM（DeepSeek / OpenAI 协议）**流式** + 古籍 RAG 溯源 |
| 摇签       | 前端随机取 5 条         | 服务端加密级随机发签、落库，改前端也刷不出                         |
| 上香 30 分钟 | `localStorage` 计时 | 服务端 `endsAt` 权威计时，改本地时间/换设备都无效                |
| 八字排盘     | demo 里没实现         | 真·干支四柱推演（`lunar-python`），五行分布                 |
| 藏经阁      | 5 部各 2 段写死        | 语料入库 + 向量/关键词检索，问卦引用可溯源                       |
| 许愿池      | 内存数组              | 落库 + **内容审核**（UGC 法定必审）                       |
| 支付       | 弹 toast           | 下单→回调→**幂等履约**→发放权益，状态机完整                     |
| 登录       | 无                 | 手机号 + 短信验证码 + JWT                             |

---

## 架构

```
┌─────────────┐        HTTP / SSE         ┌──────────────────────┐
│  apps/web   │  ──────────────────────>  │      apps/api        │
│ React + TS  │   /api/*  (camelCase)     │   FastAPI (Python)   │
│  Vite       │  <──────────────────────  │                      │
└─────────────┘                           │  ┌────────────────┐  │
                                          │  │ Provider 适配层 │  │
   前后端彻底分离：                        │  │ LLM / 支付 /    │  │
   - 前端只认 /api 契约                    │  │ 短信 / 审核     │  │
   - 后端无状态，可水平扩展                 │  └────────────────┘  │
                                          └──────┬───────┬───────┘
                                                 │       │
                                          ┌──────▼──┐ ┌──▼─────┐
                                          │Postgres │ │ Redis  │
                                          └─────────┘ └────────┘
```

**Provider 适配层**是可商用的关键：LLM / 支付 / 短信 / 审核都抽象成接口，本地用 `mock`/`console`/`keyword` 零配置跑通，上线切 `deepseek`/`wechat`/`aliyun` 只改环境变量，业务代码一行不动。

### 技术栈

- **前端**：React 18 + TypeScript + Vite + Zustand
- **桌面 Web**：独立的 React 18 + TypeScript + Vite 产品端，无手机号认证，自动建立匿名访客会话
- **后端**：FastAPI + SQLAlchemy 2.0 (async) + Alembic + Pydantic v2
- **数据**：PostgreSQL + Redis
- **AI**：`openai` SDK 走 OpenAI 协议接 DeepSeek（`base_url` 可换通义/豆包）
- **八字**：`lunar-python`（真实农历/干支）

---

## 快速开始（本地，零第三方密钥）

前置：Docker、Python 3.11、Node 20、[uv](https://docs.astral.sh/uv/)、pnpm。

```bash
# 1. 起 Postgres + Redis
docker compose up -d

# 2. 后端
cd apps/api
cp .env.example .env
uv venv --python 3.11
uv pip install -r requirements.txt        # 或 uv pip install -e ".[dev]"
uv run alembic upgrade head               # 建表
uv run uvicorn app.main:app --port 3001 --reload
# 藏经阁/签谱语料直接读仓库内 knowledge_wiki/graph.json，无需灌库


# 3. 前端（另开终端）
cd apps/web
pnpm install
pnpm dev                                   # http://localhost:5173

# 4. 独立桌面 Web（另开终端）
cd apps/web-desktop
pnpm install
pnpm dev                                   # http://localhost:5174
```

打开 http://localhost:5173：

- 默认自动创建匿名访客会话，摇签/上香/许愿/问卦无需手机号即可使用；手机号验证码接口保留，后续打开认证时再启用。
- 问卦用 `mock` LLM：按主题走规则生成话术并逐字流式，配合真实古籍 RAG 引用。
- 供灯下单用 `mock` 支付：下单 3 秒后自动「支付成功」，可看到 `isLamp` 权益生效。

---

## 从本地到上线：只改环境变量

`.env` 里切 Provider（见 `apps/api/.env.example` 全部项）：

| 变量                    | 本地            | 上线（大陆）                           |
|-----------------------|---------------|----------------------------------|
| `LLM_PROVIDER`        | `mock`        | `deepseek`（填 `DEEPSEEK_API_KEY`） |
| `SMS_PROVIDER`        | `console`     | `aliyun`（填阿里云短信 AK、已审核签名与模板） |
| `MODERATION_PROVIDER` | `keyword`     | `aliyun`（阿里云内容安全）                |
| `PAYMENT_PROVIDER`    | `mock`        | `wechat` / `alipay`（填商户号）        |
| `EMBEDDING_PROVIDER`  | `none`（关键词检索） | `openai`（向量检索，藏经阁更准）             |

短信 `aliyun` Provider 已接入阿里云 SendSms；支付和内容审核仍需按实际商户/账号完成配置后才能上线。

---

## 上线前 · 合规清单（大陆）⚠️

算命/占卜类在大陆是监管敏感区，下面几条不是可选项：

1. **产品定性**：全程以「传统文化娱乐 / 心理疗愈」呈现，**不得**出现「预测未来 / 保过 / 改命」等表述。免责声明已内置（`DISCLAIMER`），结果页需露出。
2. **ICP 备案 + 等保**：服务器在境内，域名需 ICP 备案。
3. **生成式 AI 合规**：接入的大模型需已完成算法备案；对用户输入与 AI 输出做双向审核。
4. **UGC 内容审核**：许愿池等用户内容**必须**过审后才进公共池（本项目已内置审核钩子，上线切 `aliyun`，且审核服务不可用时应 fail-safe 转人工，不可默认放行）。
5. **支付资质**：微信/支付宝商户号需**营业执照**（个体户即可），个人主体拿不到，收不了款。
6. **敏感个人信息**：手相扫描涉及生物识别信息——本项目**未**伪造该功能，做成「需单独授权 + 即用即弃不留原图」的诚实占位，接真视觉模型前不开放。
7. **未成年人**：占卜类应做年龄门槛与未成年人保护。

---

## 部署

```bash
cp .env.prod.example .env.prod   # 按需改；至少设置 JWT_SECRET / DEEPSEEK_API_KEY / 短信与商户密钥
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

- `api` 容器启动时自动 `alembic upgrade head` + seed。
- `web` 容器是 nginx，托管前端静态资源并把 `/api` 反代到 `api`（同源，免 CORS；SSE 已关缓冲）。
- 生产务必：换强 `JWT_SECRET`、Postgres 强密码、HTTPS 终止（在 nginx/网关层）。

---

## 目录结构

```
apps/
  api/                  FastAPI 后端
    app/
      constants.py      业务常量（价格用「分」）
      schemas.py        Pydantic 契约（对外 camelCase）
      models.py         SQLAlchemy 模型
      core/             config / db / redis / security / errors
      providers/        llm · payment · sms · moderation（可插拔）
      services/         auth · qian · incense · wish · chat · scripture · bazi · order · quota · profile
      routers/          各 REST 路由 + /api/chat/stream (SSE)
      data/             签谱 + 藏经阁语料
    alembic/            数据库迁移
    tests/              单元测试（八字/摇签/审核/契约）
  web/                  React 前端
    src/
      api/              client（fetch + SSE）
      store/            Zustand
      screens/          11 个页面（还原 demo 全部界面）
      components/       iOS 外壳 + 通用 UI
  web-desktop/          独立桌面 Web 产品
    src/
      pages/            寺院首页 + 问卦/求签/香火/许愿/藏经阁/命盘/供灯
      components/       产品顶栏与全局外壳
      api.ts             API + 匿名访客会话
docker-compose.yml       本地：postgres + redis
docker-compose.prod.yml  生产：+ api + web
docs/                    原始 demo
```

## 测试

```bash
cd apps/api && uv run pytest -q          # 后端单元测试
cd apps/web && pnpm typecheck            # 前端类型检查
```

核心业务闭环（登录→摇签→上香计时→许愿审核→问卦流式→八字→支付履约）已通过接口与真实 UI 端到端验证。

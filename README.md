# douyin-search · 抖音内容抓取 skill

[![Install on ClawHub](https://img.shields.io/badge/ClawHub-install-blue?logo=github)](https://clawhub.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org)
[![agent-browser](https://img.shields.io/badge/agent--browser-required-orange)](https://github.com/earendil-works/pi-coding-agent)

> 抖音(Douyin)内容抓取 skill — 搜视频/找用户/拿作品/深度评论 harvest
> 自包含、可跨设备部署、最低风控的人类行为模式默认开启

**一个 AI agent 友好的抖音数据访问工具,适用于:**

- 🔍 **主题搜索** — 找热门视频、爆款话题、时效性内容
- 👤 **用户作品** — 拿指定用户的全部作品列表
- 💬 **深度评论** — 虚拟滚动 harvest,单视频 100~200 条评论(支持人类模式)
- 📦 **批量抓取** — 多个视频串行,自动 jitter 防风控

**不会做的事:**

- ❌ 点赞/发评论/关注 — 只读
- ❌ 视频下载 — 另找工具
- ❌ 业务级大规模抓取(>100 视频/天)— 需用 Playwright + 真实 Chrome profile,超出 skill 范围

---

## ⚡ 30 秒上手

### 1. 安装 skill

**从 ClawHub 安装**(推荐):
```bash
openclaw skills install douyin-search
```

**从 GitHub 安装**:
```bash
git clone https://github.com/your-username/douyin-search.git \
  ~/.pi/agent/skills/douyin-search
```

**手动复制**:
```bash
cp -r douyin-search/ ~/.pi/agent/skills/
```

### 2. 注入 cookies(一次性)

1. Chrome 登录 https://www.douyin.com/
2. F12 → Application → Cookies → 复制 www.douyin.com 全部 cookies
3. 粘到 `<skill>/data/cookies-raw.txt`(Netscape / `k=v; k=v;` 格式)

### 3. 初始化(3 步)

```bash
export SKILL=~/.pi/agent/skills/douyin-search

python3 $SKILL/keepalive.py inject       # 转 Netscape 格式
python3 $SKILL/keepalive.py check        # 验证(退出码 0 = 有效)
python3 $SKILL/keepalive.py state save   # 持久化 ab session
```

### 4. 立即使用

```bash
# 搜视频
python3 $SKILL/douyin-fetch.py search "SpaceX 上市" --type video --limit 10

# 找用户
python3 $SKILL/douyin-fetch.py user "小Lin说" --videos 20

# 单视频详情 + 5 条热评
python3 $SKILL/douyin-fetch.py video 7650453175333342470 --comments 5

# 深度评论 harvest(人类模式,默认)
python3 $SKILL/comments-harvest.py 7650453175333342470 --max 200

# 批量串行
python3 $SKILL/comments-harvest.py <id1> <id2> <id3> --max 150
```

---

## 🎯 核心能力

### 命令速查

| 命令 | 数据源 | 用途 | 输出 |
|---|---|---|---|
| `douyin-fetch.py search <kw> --type video` | HTTP API | 主题搜索 | 视频列表 |
| `douyin-fetch.py search <kw> --type user` | HTTP API | 找人 | 用户列表 |
| `douyin-fetch.py user <nickname>` | HTTP API | 用户作品 | 视频列表 |
| `douyin-fetch.py video <id> --comments 5` | HTTP API + ab | 视频详情 + 热评 | 终端打印 |
| **`comments-harvest.py <id> --max 200`** | ab 虚拟滚动 | **深度评论(200~500 条)** | **JSON + CSV** |
| **`comments-harvest.py <id1> <id2> ...`** | ab 串行 | **批量深度评论** | **多文件 JSON+CSV** |

### 抓取策略(最低风控)

`comments-harvest.py` 默认**人类模式**:

| 维度 | 人类模式(默认) | 激进模式 (`--aggressive`) |
|---|---|---|
| 滚动方式 | `scrollBy(0, 200-500px)` 随机小步 | `scrollTop = scrollHeight` 一次跳到底 |
| 每 round sleep | 1.5-5 秒 + 10% 概率长停留 2-6 秒 | 固定 0.9 秒 |
| Round 上限 | 15 | 25 |
| 早停条件 | round > 8 && stalled ≥ 2 | round > 5 && added === 0 |
| 单视频时长 | ~1m9s(148 条) | ~35s(248 条) |
| 视频间 jitter | 17-32 秒(±30%) | 17-32 秒 |
| 风控风险 | **低** | 中-高 |

> **为什么默认人类模式?** 抖音风控会监控行为节奏 — 1 秒内 25 次 `scrollTop=jump` 是明显的脚本特征。人类模式用 `scrollBy` 模拟手指拨动 + 随机 sleep,行为更接近真人。

---

## 📁 自包含架构(跨设备)

skill 本身不依赖系统固定路径,所有运行时数据统一在 `data/` 子目录:

```
douyin-search/
├── douyin-fetch.py
├── comments-harvest.py
├── keepalive.py
├── paths.py                  ← 路径统一管理
├── SKILL.md
├── README.md
├── LICENSE
├── .gitignore                ← 排除 data/ 敏感文件
└── data/                     ← 运行时数据
    ├── .gitkeep
    ├── cookies-raw.txt       ← 你的原始 cookies(敏感)
    ├── cookies.txt           ← Netscape 格式(自动生成)
    ├── state/douyin.state    ← ab session(自动生成)
    └── exports/              ← 抓取结果(默认输出)
```

**路径解析优先级**(从高到低):
1. 环境变量 `DOUYIN_DATA_DIR`(给 docker / CI 用)
2. 老的 `/tmp/douyin/`(向后兼容,如果存在)
3. 默认 `<skill>/data/`

查看当前配置:
```bash
python3 -c "import sys; sys.path.insert(0, '.'); from paths import report; print(report())"
```

---

## 🔧 故障排查

| 症状 | 修复 |
|---|---|
| `keepalive.py check` 退出码非 0 | cookies 过期,重新走 setup |
| `state check` 报"页面是验证码中间页" | 触发 captcha,等 30 秒重试 |
| `comments-harvest` 跑到一半 "Resource temporarily unavailable" | 手动 `agent-browser close && sleep 3`,重 `state save` |
| `search` 返回 0 条 | 大概率 cookies 失效,重新导 |
| 视频评论像第一条重复 | 多个 `video` 命令并行了,必须串行 `&&` 或 `;` |

更多见 [`SKILL.md`](SKILL.md) 的"死胡同"和"故障排查"。

---

## 📊 实战案例:世界杯 C罗 视频评论分析

测试抓取 22.6 万赞「船长的最后一次远航」+ 8.3 万赞「诸神黄昏」两条 C罗 视频:

- **2 条视频 / 498 条评论 / 1m9s**(人类模式)
- **JSON + CSV 双格式输出**(~200KB)
- **关键词命中**:
  - 「大力神杯」91 条 (14.4%)
  - 「船长」29 条 (4.6%)
  - 「最后一」37 条 (5.8%)
- **情绪分布**: 致敬/祝福 45%, 情怀/怀旧 25%, 梅罗对立 12%, 押注 10%

→ 适合做: 体育热点内容分析 / KOL 粉丝画像 / 品牌植入机会识别

---

## 🛠️ 适用场景

✅ **适合**:
- 个人 / 小团队研究(几小时抓几十个视频)
- 内容运营找热点(每天看几个话题)
- 学术研究(短时间样本采集)
- AI agent 内嵌工具(需要"看看抖音最近什么火"时调用)

❌ **不适合**:
- 商业爬虫服务(需要更复杂的反爬对抗 + 代理 IP 池)
- 24/7 监控(cookie 12-24h 过期,需要自动续期)
- 100+ 视频/天的批量抓取(需要养号 + IP 轮换)

---

## 🤝 贡献

欢迎 PR!特别是:
- 新增搜索维度(比如按时间/地区过滤)
- 优化虚拟滚动 harvest 策略
- 修复 captcha 处理流程
- 翻译文档

**安全注意**:本 skill **只读**,不修改抖音任何数据。提交 PR 时请保持这一原则。

---

## 📜 License

MIT — 详见 [LICENSE](LICENSE)

---

## 🔗 相关链接

- [ClawHub](https://clawhub.ai) — OpenClaw skill 注册表
- [OpenClaw](https://github.com/openclaw) — AI 助手平台
- [pi-coding-agent](https://github.com/earendil-works/pi-coding-agent) — agent-browser 来源
- [Agent Skills 标准](https://agentskills.io) — skill frontmatter 规范

---

## 📦 发布到 ClawHub

发布流程(开发者用):

```bash
# 1. 创建 GitHub repo
gh repo create douyin-search --public --source=. --push

# 2. 本地安装 clawhub CLI
npm install -g @openclaw/clawhub-cli
clawhub login

# 3. 发布
clawhub skill publish .
# 之后每次 push tag v* 自动更新
```

> 详见 [ClawHub docs](https://clawhub.ai/docs/publish) — CI 会自动跑测试 + 发布新版本。

---
name: douyin-search
description: 抖音内容抓取（搜索视频/用户/拿作品/看评论）。走 HTTP API + agent-browser 抓评论虚拟滚动 harvest（需登录 cookie）。零依赖、跨设备、支持最低风控的人类模式。
metadata:
  openclaw:
    requires:
      env: []
      bins:
        - python3
        - agent-browser
      primaryBin: python3
    primaryEnv: ""
    # 该 skill 是只读,不修改 douyin 任何数据
---

# douyin-search

## ⚡ 30 秒上手

```bash
export SKILL=/path/to/douyin-search    # 你 clone 的位置

python3 $SKILL/douyin-fetch.py search "SpaceX 上市" --type video --limit 10   # 主题搜视频
python3 $SKILL/douyin-fetch.py user "小Lin说" --videos 20                       # 拿用户作品(仅精确昵称)
python3 $SKILL/douyin-fetch.py video 7650453175333342470 --comments 5          # 单视频详情+评论(5 条热评)
python3 $SKILL/comments-harvest.py 7650453175333342470 --max 200               # 单视频深度评论 harvest(人类模式)
python3 $SKILL/comments-harvest.py <id1> <id2> ... --max 150                   # 批量串行 harvest(视频间 17-32s jitter)
```

**agent 须知**:不要 read 脚本源码,看完本文档就会用。

## 命令速查

| 想做 | 命令 | 数据源 |
|---|---|---|
| 主题搜索 / 找爆款 | `search --type video` | HTTP API |
| 找人 | `search --type user` | HTTP API |
| 拿用户所有作品 | `user <昵称>` | HTTP API |
| 单视频元信息 | `video <id> --comments 0` | HTTP API |
| 单视频热评(5~20 条) | `video <id> --comments N` | ab eval DOM(需登录) |
| **单视频深度评论(100~200 条,人类模式)** | `comments-harvest.py <id> --max N` | ab 虚拟滚动 harvest(需登录) |
| **批量视频深度评论** | `comments-harvest.py <id1> <id2> ...` | 串行 ab harvest(视频间 17-32s jitter) |
| **激进模式(快但有风控风险)** | `comments-harvest.py <id> --aggressive` | 一次 eval 跑 25 round 抓满 |

## 📁 数据路径(skill 自包含)

所有运行时数据(cookies / ab state / 抓取结果)统一在 `data/` 子目录,skill 本身可 git clone 即用:

```
$SKILL/                              ← skill 根(可 git clone 到任何位置)
├── douyin-fetch.py
├── comments-harvest.py
├── keepalive.py
├── paths.py                         ← 路径统一管理
├── SKILL.md
├── .gitignore                       ← 排除 data/ 里的敏感文件
└── data/                            ← 运行时数据
    ├── .gitkeep
    ├── cookies-raw.txt              ← 你导出的原始 cookies(敏感)
    ├── cookies.txt                  ← Netscape 格式(自动生成)
    ├── state/douyin.state           ← ab session 持久化
    └── exports/                     ← 抓取结果(默认 --output)
```

**路径解析优先级**(从高到低):
1. 环境变量 `DOUYIN_DATA_DIR` (给 docker / CI 用)
2. 老的 `/tmp/douyin/` (向后兼容,如果存在)
3. 默认 `$SKILL/data/`

查看当前路径配置:
```bash
python3 -c "from paths import report; print(report())"
```

## 前置(一次性 setup,新设备必跑)

```bash
# 1. Chrome 登录 douyin.com → F12 → Application → Cookies → 复制到 <skill>/data/cookies-raw.txt
#    (老路径兼容: /tmp/douyin/cookies-raw.txt 也行)
# 2. 转 Netscape 格式
python3 $SKILL/keepalive.py inject
# 3. 验证 cookie
python3 $SKILL/keepalive.py check      # 退出码 0 = 有效
# 4. (仅评论需要) 持久化 ab session
python3 $SKILL/keepalive.py state save
```

如果cookie不存在或者过期或者无效,立刻停止并提示用户需要重新导 cookies,或把整段 cookies 直接发给你,你落盘到 `$SKILL/data/cookies-raw.txt` 然后跑 inject → check → state save。

之后每次新 session 开头跑 `state load` 一次即可。`state check` 可验证登录态是否还有效。

## 关键提示

**主题搜索找爆款**:
- AI 类短剧要搜 `AI短剧` / `AI漫剧` / `AI短片` 三个,合并去重 — 只搜一个会漏一大半
- 时间过滤不支持,按输出里的 `YYYY-MM-DD` 自己挑近一周;`--limit 30` 一次拿全
- `--raw-out <path>` 落盘原始 JSON,debug 用

**评论抓取**:
- **多个 video / harvest 命令必须串行**(`&&` 或 `;`),不能 `&` 并行 — ab 单 tab 单 session,会全部拿到第一条的评论
- 默认按"最热"排序,前几条基本是置顶/精选;`--comments 20+` 拿更多稀释精选占比
- 失败时脚本会显式提示原因(captcha / cookie 失效),不会静默返回空

**深度评论 harvest**(`comments-harvest.py`):
- 走虚拟滚动,douyin PC web 评论容器是 `.parent-route-container.route-scroll-container`,反复 `scrollBy(0, 200-500px)` 触发 lazy load
- **跳过 `...` 占位符**:douyin DOM 每条评论固定格式是 `user\n...\ntext\ntime\nlikes\n操作按钮`,第二行的 `...` 是 UI 占位符,不是被截断
- 用 `localStorage` 中转评论数据(ab eval 输出无明显字节限制,但 localStorage 写入 native 不受任何限制)
- 抓取策略:**人类模式**(默认,最低风控) vs **激进模式**(`--aggressive`, 快但有风险)
  - 人类模式:scrollBy 200-500px + sleep 1.5-5s + 10% 概率长停留 2-6s + 15 round 上限 + stalled 早停
  - 激进模式:scrollTop = scrollHeight + sleep 0.9s + 25 round 上限
- **--max 决定单视频抓取上限**(人类模式默认 200, 激进模式默认 500)
- 视频间自动 sleep (base 25s × random 0.7-1.3 → 17-32s 区间),符合"每账号 ≤ 50-100 评论页/小时"
- 输出 JSON + CSV 双格式,落到 `--output` 目录(默认 `$SKILL/data/exports/`)

**user 搜索**:
- 仅精确匹配昵称/抖音号。模糊词(像"财经")搜不到,需要先有具体昵称

## 死胡同(踩过的坑)

| 尝试 | 结果 |
|---|---|
| `ab open https://www.douyin.com/` (主页) | 触发滑块验证(首页反爬最严) |
| 匿名 `ab open` 任何抖音 URL | 弹登录 panel |
| 直接 curl 搜索 API | 200 但 0 字节(verify_check) |
| `/aweme/v1/web/search/item/` API | verify_check 拦截 |
| `aweme/v1/web/search/sug/` API | sug_list 是 null |
| 评论 API `aweme/v1/web/comment/list/` | verify_check 拦截,只能抓 DOM |
| 虚拟滚动容器用 `document.body` / 任何最大可滚动 div | 不会触发 lazy load |
| 解析评论 text 时把 `...` 当评论内容 | 取出的是占位符,不是 text(总输出会异常) |
| ab eval 单次跑 30s+ 的长任务 | ab daemon busy 5 次重试都失败 |
| Bing/百度 site:douyin.com | 全部反爬 |
| 多个 video / harvest 命令并行 | 全部拿到第一条评论(单 tab) |
| 触发 captcha 后立刻 reload | 还是 captcha,需等 30 秒 |
| `--comments > 20` 用 `video` 命令 | 只给前 5 条,要用 `comments-harvest.py` |

**脚本已自动处理**(无需 agent 关心):
- `state load/save/check` 自动清理 daemon 防 `--state` 抢占
- `video` 命令自动检测 captcha,遇风控明确报错而非返回空
- 视频元信息抓不到时显式标 `search-fallback`,不静默吞错
- `--raw-out` 落盘完整 raw JSON(含 detail API 响应)
- harvest 拆成 incremental(每 round 一次 eval),避免 ab daemon busy
- 视频间自动 jitter(17-32s 区间),符合最低风控标准

## 🛠 故障排查

| 症状 | 原因 | 修复 |
|---|---|---|
| `state check` 报 `TypeError: _verify_state_login() got an unexpected keyword argument 'probe_url'` | 老脚本 bug(已修) | 升级 `keepalive.py` |
| `state check` / `state load` / `state save` 卡住,无输出 | daemon 残留;或某些 shell hook 下 `pkill` 卡死(已删 `pkill` 兜底) | 手动 `agent-browser close && sleep 2`,再重跑 |
| `state check` 报 "state 文件不存在" | 还没跑过 `state save` | 跑 `state save` |
| `state check` 报 "state 实际不可用" 或 "页面是未登录首页" | cookie 过期 | 跑 `keepalive.py check` 验;退出码非 0 就重新 setup(导 cookie → `inject` → `check` → `state save`) |
| `state check` 报 "页面是验证码中间页" | 触发 captcha | 等 30 秒后重跑,不要立刻 reload |
| `search` 返回 0 条,或 `video --comments` 报登录态问题 | cookie 失效 | 同上:重 setup |
| `state check` 拿到 fallback 话题页(例如 title 变成 `#某话题` 而非视频标题) | `PROBE_VIDEO` 常量里的视频被作者删了/转私密 | 改 `keepalive.py` 顶部 `PROBE_VIDEO` 为另一个稳定的视频 ID |
| `state save` 之后 `state load` 仍然拿不到登录态 | daemon 抢占,`--state` 被忽略 | 手动 `agent-browser close && sleep 2 && state load` |
| `video --comments` 抓到的评论像第一条重复 | 多个 `video` 命令并行了(ab 单 tab) | 串行跑,`&&` 或 `;` 连接 |
| `harvest` 跑到一半报 "Failed to read: Resource temporarily unavailable" | ab daemon 累积状态坏 | 手动 `agent-browser close && sleep 3`,重 state save |

**经验法则**:
- 脚本卡死 → 先 `agent-browser close && sleep 2` 再重跑
- 登录/评论类问题 → 先 `keepalive.py check` 看退出码(0=有效)
- 验证码 → 等 30 秒(立刻 reload 没用)

## 边界(不做的事)
- 点赞/发评论/关注 — 只读
- 视频下载 — 另找工具
- 其他网站 — agent-browser skill
- 业务级大规模抓取(>100 视频/天) — 需用 Playwright + 真实 Chrome profile + 代理 IP 池,超出 skill 范围

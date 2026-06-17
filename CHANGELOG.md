# Changelog

All notable changes to douyin-search will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-06-17

### Added
- **`aggregate.py`**: 跨次会话聚合去重工具 — agent 调一次命令,产出
  - `aggregate_videos.csv` 唯一视频清单(按赞数排序,带 matched_keywords)
  - `aggregate_comments_all.csv` 全部去重评论(单表)
  - `aggregate_summary.json` 统计(去重率 / 采样数)
  - 自动跨 search-*.json 去重 + 跨 comments/*.json 合并 + 评论内去重(video_id+user+text 三元组)
- **`docs/pitfalls.md`**: 开发者参考手册(目录结构、反爬坑、脚本实现细节)
- **故障排查**: 明确 "captcha 中间页 + state 实际不可用" 的组合症状 → `close && sleep && state save` 修复(避免无意义的 sleep 等待)

### Changed
- **SKILL.md**: 217 行 → 128 行(-41%),只留 agent 决策路径上的信息;实现细节 / 反爬坑 / 目录树外移到 `docs/pitfalls.md`
- **`典型工作流` 小节**: 明确 "agent 唯一要决定的事 = 关键词 + 视频 id;其他是 skill 自己的事",把责任边界画清楚
- **30 秒上手**: 合并了原 `命令速查` 表(避免重复),所有命令一行速记

## [1.0.0] - 2026-06-17

### Added
- Initial release
- 3 core scripts: `douyin-fetch.py`, `comments-harvest.py`, `keepalive.py`
- `paths.py` 集中管理路径,支持自包含部署
- 人类模式(默认)/ 激进模式两种抓取策略
- 视频间自动 jitter (17-32s) 降低风控
- 跨设备支持(env `DOUYIN_DATA_DIR` / 老路径 `/tmp/douyin/` 兼容)
- JSON + CSV 双格式导出
- GitHub Actions CI(测试 + 验证 frontmatter + lint)
- 完整 SKILL.md(openclaw frontmatter 兼容) + README.md
- MIT License

### Technical Highlights
- 虚拟滚动 harvest 拆成 incremental(每 round 一次 eval),避免 ab daemon busy
- 跳过 douyin DOM 的 `...` UI 占位符(不是被截断)
- localStorage 中转评论数据(无 ab eval 输出大小限制)
- 完整 cookie / state 路径管理

### Engineering Lessons Captured
- DOUYIN 评论容器 selector: `.parent-route-container.route-scroll-container`
- 评论 item innerText 固定格式: `user\n...\ntext\ntime\nlikes\n操作按钮`
- captcha 触发后必须等 30 秒,reload 无效
- 多个 harvest 命令必须串行,ab 单 tab 单 session
- harvest 单次 eval 不能 > 30s,否则 ab busy 5 次重试都失败

[1.1.0]: https://github.com/excalibursssooo/douyin-search/releases/tag/v1.1.0
[1.0.0]: https://github.com/excalibursssooo/douyin-search/releases/tag/v1.0.0

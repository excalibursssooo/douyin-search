# Changelog

All notable changes to douyin-search will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.0]: https://github.com/your-username/douyin-search/releases/tag/v1.0.0

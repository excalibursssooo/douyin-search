#!/usr/bin/env python3
"""
aggregate.py — douyin-search skill 的后处理聚合工具

典型工作流:
  1. search ... --raw-out exports/foo/search-ai短剧.json
  2. comments-harvest.py <id1> <id2> ... --output exports/foo/comments
  3. python3 aggregate.py exports/foo/

输入(自动发现,无需指定):
  - <dir>/search-*.json          (search 命令的 raw 输出)
  - <dir>/comments/comments_*.json (harvest 命令的输出)

输出(写到 <dir>):
  - <dir>/<prefix>_videos.csv         去重后的视频清单
  - <dir>/<prefix>_comments_all.csv   去重后的全部评论(单表)
  - <dir>/<prefix>_summary.json       汇总统计
"""
import argparse
import json
import csv
import sys
from pathlib import Path

# 复用 skill 的路径解析(支持 DOUYIN_DATA_DIR 覆盖)
try:
    from paths import EXPORTS_DIR as _DEFAULT_EXPORTS_DIR
except ImportError:
    _DEFAULT_EXPORTS_DIR = Path(__file__).parent / "data" / "exports"


def collect_search_videos(export_dir: Path):
    """跨 search-*.json 去重(按 aweme_id),汇总视频清单 + 命中关键词"""
    seen = {}
    for f in sorted(export_dir.glob("search-*.json")):
        kw = f.stem.replace("search-", "")
        with open(f) as fh:
            data = json.load(fh)
        items = data if isinstance(data, list) else (
            data.get("aweme_list") or data.get("data") or data.get("items") or []
        )
        for it in items:
            info = it.get("aweme_info", it) if isinstance(it, dict) else {}
            if not isinstance(info, dict):
                continue
            vid = str(info.get("aweme_id") or info.get("video_id") or "")
            if not vid:
                continue
            author = (info.get("author", {}) or {}).get("nickname", "?")
            desc = (info.get("desc") or "").strip()
            stat = info.get("statistics", {}) or info.get("stat", {}) or {}
            likes = int(stat.get("digg_count") or stat.get("like_count") or 0)
            comments = int(stat.get("comment_count") or 0)
            shares = int(stat.get("share_count") or 0)
            create_time = info.get("create_time", 0)
            if vid not in seen:
                seen[vid] = {
                    "aweme_id": vid, "title": desc, "author": author,
                    "likes": likes, "comment_count": comments,
                    "share_count": shares, "create_time": create_time,
                    "matched_keywords": [kw],
                }
            else:
                if kw not in seen[vid]["matched_keywords"]:
                    seen[vid]["matched_keywords"].append(kw)
                if likes > seen[vid]["likes"]:
                    seen[vid]["likes"] = likes
    return list(seen.values())


def collect_comments(export_dir: Path):
    """跨 comments/*.json 合并 + 评论内去重(video_id+user+text 三元组)"""
    comments_dir = export_dir / "comments"
    files = sorted(comments_dir.glob("comments_*.json"))
    all_comments = []
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        for c in data.get("comments", []):
            c["source_file"] = f.name
            all_comments.append(c)
    seen = set()
    deduped, dup_n = [], 0
    for c in all_comments:
        key = (c.get("video_id", ""), c.get("user", ""), c.get("text", ""))
        if key in seen:
            dup_n += 1
            continue
        seen.add(key)
        deduped.append(c)
    return all_comments, deduped, dup_n, len(files)


def write_videos_csv(videos, path: Path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["aweme_id", "author", "likes", "comment_count", "share_count",
                    "create_time", "matched_keywords", "title"])
        for v in sorted(videos, key=lambda x: x["likes"], reverse=True):
            w.writerow([v["aweme_id"], v["author"], v["likes"], v["comment_count"],
                        v["share_count"], v["create_time"],
                        "|".join(v["matched_keywords"]), v["title"]])


def write_comments_csv(comments, path: Path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["video_id", "video_title", "video_author", "video_likes",
                    "user", "text", "digg_count", "relative_time", "location"])
        for c in comments:
            w.writerow([c.get("video_id", ""), c.get("video_title", ""),
                        c.get("video_author", ""), c.get("video_likes", 0),
                        c.get("user", ""), c.get("text", ""),
                        c.get("digg_count", 0), c.get("relative_time", ""),
                        c.get("location", "")])


def main():
    ap = argparse.ArgumentParser(
        description="聚合 search + harvest 输出,生成去重视频清单和评论总表")
    ap.add_argument("export_dir", nargs="?",
                    help="export 目录(默认 $SKILL/data/exports/)")
    ap.add_argument("--prefix", default="aggregate",
                    help="输出文件名前缀(默认 aggregate)")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总,不打印过程")
    args = ap.parse_args()

    export_dir = Path(args.export_dir) if args.export_dir else _DEFAULT_EXPORTS_DIR
    if not export_dir.exists():
        print(f"❌ 目录不存在: {export_dir}", file=sys.stderr)
        sys.exit(1)

    log = (lambda *a, **k: None) if args.quiet else print

    log(f"→ 步骤 1: 跨 search 去重 (匹配 {export_dir}/search-*.json)")
    videos = collect_search_videos(export_dir)
    p1 = export_dir / f"{args.prefix}_videos.csv"
    write_videos_csv(videos, p1)
    log(f"   {len(videos)} 个唯一视频 → {p1.name}")

    log(f"→ 步骤 2: 跨 comments 合并 + 去重 (匹配 {export_dir}/comments/comments_*.json)")
    all_c, dedup_c, dup_n, n_files = collect_comments(export_dir)
    p2 = export_dir / f"{args.prefix}_comments_all.csv"
    write_comments_csv(dedup_c, p2)
    log(f"   {n_files} 个 harvest 文件, {len(all_c)} 条原始 → {len(dedup_c)} 条去重 (drop {dup_n})")
    log(f"   → {p2.name}")

    summary = {
        "export_dir": str(export_dir),
        "search_unique_videos": len(videos),
        "search_total_appearances": sum(len(v["matched_keywords"]) for v in videos),
        "harvest_videos": n_files,
        "comments_raw": len(all_c),
        "comments_deduped": len(dedup_c),
        "comments_dup_dropped": dup_n,
        "dedup_rate_pct": round(dup_n / len(all_c) * 100, 2) if all_c else 0,
        "output_files": [p1.name, p2.name],
    }
    p3 = export_dir / f"{args.prefix}_summary.json"
    with open(p3, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    log(f"→ 步骤 3: 汇总统计 → {p3.name}")
    log()
    log("=" * 50)
    log("汇总:")
    for k, v in summary.items():
        log(f"  {k}: {v}")


if __name__ == "__main__":
    main()

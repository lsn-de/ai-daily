"""定稿归档：人工审核通过的报告 → Markdown 文件"""
import re

from .config import date_dirs
from .organizer import load_drafts


def _stars(n: int, scale: int = 5) -> str:
    return "★" * n + "☆" * max(0, scale - n)


def _safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "-", s).strip("-")[:50] or "untitled"


def _eff_stars(report: dict) -> int:
    return report.get("human_stars") or (report.get("rating") or {}).get("stars") or 0


def publish(cfg: dict, day: str) -> None:
    drafts = load_drafts(cfg, day)
    items = {it["id"]: it for it in drafts.get("items", [])}
    scale = cfg["rating"].get("scale", 5)
    all_reports = drafts["reports"]
    approved = [r for r in all_reports if r["status"] == "approved"]
    if not approved:
        raise SystemExit("没有状态为「已通过」的报告，请先在审核页面操作，或用 --date 指定日期")

    approved.sort(key=_eff_stars, reverse=True)
    out_dir = date_dirs(cfg, day)["published"]

    for r in approved:
        stars = _eff_stars(r)
        sources = [items[i] for i in (r.get("covered_items") or []) if i in items]
        lines = [
            f"# {_stars(stars, scale)} {r['title']}",
            "",
            f"- 日期：{day}　分类：{r['category']}　标签：{'、'.join(r.get('tags', [])) or '无'}",
            f"- 星级：{stars}/{scale}"
            + ("（人工调整）" if r.get("human_stars") else "（AI 评估）"),
            "",
            r["content"],
            "",
            "## 引用来源",
            "",
        ]
        lines += [f"- [{s['title']}]({s['url']})（{s['source']}）" for s in sources] or ["- 无"]
        fname = f"{r['id']}-{_safe_name(r['title'])}.md"
        (out_dir / fname).write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 汇总索引
    index = [
        f"# 新能源电车日报 · {day}",
        "",
        f"共 {len(all_reports)} 份小报告，审核通过 {len(approved)} 份"
        f"（通过率 {len(approved) * 100 // max(1, len(all_reports))}%）。",
        "",
        "| 编号 | 星级 | 标题 | 分类 |",
        "| --- | --- | --- | --- |",
    ]
    for r in approved:
        index.append(f"| {r['id']} | {_stars(_eff_stars(r), scale)} | {r['title']} | {r['category']} |")
    (out_dir / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")

    print(f"已定稿 {len(approved)} 份报告 → {out_dir}")
    print(f"汇总索引：{out_dir / 'index.md'}")

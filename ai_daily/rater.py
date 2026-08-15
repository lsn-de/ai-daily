"""AI 星级自评模块：按可配置标准给每份小报告打分"""
from .organizer import load_drafts, save_drafts

SYSTEM_RATE = (
    "你是一名严格的新能源汽车行业日报评审员。请按照给定评估标准对报告打分，"
    "标准从严：多数报告应在 2-4 星，5 星仅留给行业级重大事件（如政策重磅出台、技术路线颠覆、巨头战略转型等），1 星表示价值很低。"
    "评分必须给出可核查的理由。"
)


def _criteria_text(cfg: dict) -> str:
    lines = []
    for i, c in enumerate(cfg["rating"].get("criteria", []), 1):
        lines.append(f"{i}. {c['name']}（权重 {c['weight']}%）：{c['desc']}")
    return "\n".join(lines) or "1. 综合价值（权重 100%）：内容的重要性与参考价值"


def _build_user_prompt(cfg: dict, report: dict, items: list) -> str:
    covered = report.get("covered_items") or []
    src = [f"- {it['source']}: {it['title']}" for it in items if it["id"] in covered]
    return (
        f"评估标准（{cfg['rating']['scale']} 星制）:\n{_criteria_text(cfg)}\n\n"
        f"待评估报告:\n标题: {report['title']}\n分类: {report['category']}\n"
        f"正文: {report['content']}\n\n依据的原始资讯:\n" + ("\n".join(src) or "（无）") +
        "\n\n请输出 JSON: {\"stars\": 1-5 整数, "
        "\"scores\": {每个标准名: 0-10 分}, \"reason\": \"50 字以内评分理由\"}"
    )


def rate(cfg: dict, day: str, mock: bool = False) -> None:
    from .llm import chat_json

    drafts = load_drafts(cfg, day)
    items = drafts.get("items", [])
    todo = [r for r in drafts["reports"] if r.get("rating") is None]
    if not todo:
        print("所有报告已有星级，如需重评请删除 drafts 目录后重新 process")
        return

    for r in todo:
        if mock:
            r["rating"] = {"stars": 3, "scores": {"重要性": 5, "新颖性": 5, "相关性": 5,
                                                  "可信度": 5, "实用性": 5}, "reason": "mock 评分"}
            print(f"[mock] {r['id']} {r['title']} → 3 星")
            continue
        print(f"评估 {r['id']} {r['title']} ...")
        try:
            res = chat_json(cfg, SYSTEM_RATE, _build_user_prompt(cfg, r, items))
            stars = max(1, min(int(cfg["rating"]["scale"]), int(res.get("stars", 3))))
            r["rating"] = {
                "stars": stars,
                "scores": {str(k): v for k, v in (res.get("scores") or {}).items()},
                "reason": str(res.get("reason", "")),
            }
            print(f"  → {stars} 星：{r['rating']['reason']}")
        except Exception as exc:
            print(f"  → 评估失败（保留待重试）: {exc}")
    save_drafts(cfg, day, drafts)
    print(f"星级评估完成 → {day}")

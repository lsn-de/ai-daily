"""AI 二次整理：去重聚类 → 多份小报告（标题 + 内容）"""
import json
from datetime import datetime

from .config import date_dirs

SYSTEM_ORGANIZE = (
    "你是一名资深新能源汽车行业编辑，负责把当日资讯整理成多份独立的小报告。"
    "要求：客观、无虚构、只依据给定资讯；同一事件的多条报道合并为一份；"
    "标题中文、20 字以内、有信息量；正文为纯文本叙述。"
)


def drafts_path(cfg: dict, day: str):
    return date_dirs(cfg, day)["drafts"] / "reports.json"


def load_drafts(cfg: dict, day: str) -> dict:
    p = drafts_path(cfg, day)
    if not p.exists():
        raise SystemExit(f"未找到 {p}，请先执行: python main.py process --date {day}")
    return json.loads(p.read_text(encoding="utf-8"))


def save_drafts(cfg: dict, day: str, drafts: dict) -> None:
    p = drafts_path(cfg, day)
    p.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_user_prompt(cfg: dict, items: list) -> str:
    o = cfg["organize"]
    slim = [{"id": it["id"], "source": it["source"], "title": it["title"],
             "text": it["text"][:500]} for it in items]
    return (
        f"以下是今天的资讯列表(JSON)。请整理成 {o['min_reports']}-{o['max_reports']} 份小报告"
        "（重要事件多则多分，平淡则少分，宁缺毋滥，无价值的资讯直接丢弃）。\n"
        "每份报告包含: title(中文标题), category(分类,如:新车发布/行业动态/政策法规/企业新闻/电池技术/充电设施/市场数据/价格调整/供应链), "
        "content(正文纯文本 120-250 字, 综合该事件全部要点, 客观陈述, 不加链接), "
        "tags(2-4 个关键词), covered_items(引用的资讯 id 列表)。\n"
        '只输出 JSON: {"reports": [{"title": "...", "category": "...", "content": "...", '
        '"tags": ["..."], "covered_items": [1, 2]}]}\n'
        f"资讯列表:\n{json.dumps(slim, ensure_ascii=False)}"
    )


def _mock_reports(items: list) -> list:
    reports = []
    for i, it in enumerate(items[:6], 1):
        reports.append({
            "title": it["title"][:20],
            "category": "测试数据",
            "content": it["text"][:200],
            "tags": ["mock"],
            "covered_items": [it["id"]],
        })
    return reports


def organize(cfg: dict, day: str, mock: bool = False) -> dict:
    """生成多份小报告，写入 drafts/{day}/reports.json"""
    from .collector import load_items
    from .llm import chat_json

    items = load_items(cfg, day)
    if not items:
        raise SystemExit("当日无资讯，跳过整理")

    limit = cfg["organize"].get("max_items_in_prompt", 60)
    use_items = items[:limit]

    if mock:
        raw_reports = _mock_reports(use_items)
        print(f"[mock] 用 {len(use_items)} 条资讯生成 {len(raw_reports)} 份模拟报告")
    else:
        print(f"调用模型整理 {len(use_items)} 条资讯 ...")
        result = chat_json(cfg, SYSTEM_ORGANIZE, _build_user_prompt(cfg, use_items))
        raw_reports = result.get("reports", result if isinstance(result, list) else [])
        if not raw_reports:
            raise SystemExit(f"模型未返回有效报告: {result}")

    reports = []
    for idx, r in enumerate(raw_reports, 1):
        reports.append({
            "id": f"R{idx}",
            "title": str(r.get("title", f"报告{idx}")).strip(),
            "category": str(r.get("category", "未分类")).strip(),
            "content": str(r.get("content", "")).strip(),
            "tags": [str(t) for t in (r.get("tags") or [])][:5],
            "covered_items": [int(x) for x in (r.get("covered_items") or [])],
            "status": "pending",      # pending / approved / rejected
            "rating": None,           # AI 星级评估结果
            "human_stars": None,      # 人工修改后的星级
        })

    drafts = {
        "date": day,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": use_items,          # 附带原始资讯，供审核页展示来源
        "reports": reports,
    }
    save_drafts(cfg, day, drafts)
    print(f"已生成 {len(reports)} 份小报告 → {drafts_path(cfg, day)}")
    return drafts

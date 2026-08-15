#!/usr/bin/env python3
"""
AI 半自动日报 CLI

流程：fetch 抓取 → process（AI 整理成多份小报告 + 星级自评）
      → review 卡片式人工审核 → publish 定稿归档
"""
import argparse

from ai_daily import config as cfgmod
from ai_daily.collector import fetch_all
from ai_daily.organizer import organize
from ai_daily.publisher import publish
from ai_daily.rater import rate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AI 半自动日报")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, mock=False):
        sp.add_argument("--date", default=cfgmod.today_str(), help="日期 YYYY-MM-DD，默认今天")
        if mock:
            sp.add_argument("--mock", action="store_true",
                            help="不调用模型，用模拟数据跑通流程（测试用）")

    common(sub.add_parser("fetch", help="抓取各信源当日纯文本"))
    common(sub.add_parser("process", help="AI 整理成多份小报告并做星级自评"), mock=True)
    common(sub.add_parser("rate", help="仅补齐缺失的星级评估"), mock=True)
    common(sub.add_parser("review", help="启动本地卡片式审核页面"))
    common(sub.add_parser("publish", help="将通过审核的报告归档为 Markdown"))
    run = sub.add_parser("run", help="一键执行 fetch + process")
    common(run, mock=True)
    return p


def main() -> None:
    args = build_parser().parse_args()
    cfg = cfgmod.load_config()

    if args.cmd == "fetch":
        fetch_all(cfg, args.date)

    elif args.cmd == "process":
        organize(cfg, args.date, mock=args.mock)
        rate(cfg, args.date, mock=args.mock)

    elif args.cmd == "rate":
        rate(cfg, args.date, mock=args.mock)

    elif args.cmd == "review":
        from ai_daily.reviewer import serve
        serve(cfg)

    elif args.cmd == "publish":
        publish(cfg, args.date)

    elif args.cmd == "run":
        fetch_all(cfg, args.date)
        organize(cfg, args.date, mock=args.mock)
        rate(cfg, args.date, mock=args.mock)
        print("\n下一步: python main.py review --date " + args.date)


if __name__ == "__main__":
    main()

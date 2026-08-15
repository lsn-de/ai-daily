"""抓取模块：RSS / HTML → 每日纯文本"""
import html
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ai-daily/0.1"
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = TAG_RE.sub(" ", text)
    return WS_RE.sub(" ", text).strip()


def _parse_time(entry) -> datetime | None:
    # 先检查毫秒/秒时间戳字符串（feedparser 可能错误解析）
    for key in ("published", "updated"):
        s = entry.get(key)
        if s and isinstance(s, str) and s.isdigit() and len(s) >= 10:
            try:
                ts = int(s) / 1000 if len(s) > 10 else int(s)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for key in ("published", "updated"):
        s = entry.get(key)
        if s:
            try:
                return parsedate_to_datetime(s)
            except Exception:
                pass
    return None


def _fetch_rss(source: dict, hours: int, max_items: int, timeout: int) -> tuple[list, str | None]:
    try:
        resp = httpx.get(
            source["url"],
            timeout=timeout,
            headers={"User-Agent": UA},
            follow_redirects=True,
        )
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        items = []
        for entry in feed.entries:
            t = _parse_time(entry)
            if t is not None and t < cutoff:
                continue
            title = strip_html(entry.get("title") or "")
            if not title:
                continue
            summary = strip_html(entry.get("summary") or entry.get("description") or "")
            items.append({
                "source": source["name"],
                "title": title,
                "url": entry.get("link", ""),
                "published_at": t.isoformat() if t else None,
                "text": f"{title}\n{summary}"[:3000],
            })
            if len(items) >= max_items:
                break
        return items, None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def _fetch_html(source: dict, hours: int, max_items: int, timeout: int) -> tuple[list, str | None]:
    """从 HTML 页面抓取，需在 source 中配置 selectors"""
    try:
        resp = httpx.get(
            source["url"],
            timeout=timeout,
            headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
            follow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        selectors = source.get("selectors", {})
        item_sel = selectors.get("item", "li")
        title_sel = selectors.get("title", "a")
        link_sel = selectors.get("link", "a")
        date_sel = selectors.get("date", "")
        text_sel = selectors.get("text", "")
        base_url = source.get("base_url", source["url"])

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        items = []

        for el in soup.select(item_sel):
            link_el = el.select_one(link_sel) if link_sel else None
            if not link_el:
                continue

            title = strip_html(link_el.get_text()) or strip_html(link_el.get("title") or "")
            if not title:
                continue

            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                from urllib.parse import urljoin
                href = urljoin(base_url, href)

            pub_time = None
            if date_sel:
                date_el = el.select_one(date_sel)
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%m-%d", "%Y/%m/%d"):
                        try:
                            pub_time = datetime.strptime(date_text[:len(fmt)+4] if "%" not in fmt else date_text, fmt).replace(tzinfo=timezone.utc)
                            break
                        except Exception:
                            pass

            text_content = title
            if text_sel:
                text_el = el.select_one(text_sel)
                if text_el:
                    text_content = f"{title}\n{strip_html(text_el.get_text())}"

            items.append({
                "source": source["name"],
                "title": title,
                "url": href,
                "published_at": pub_time.isoformat() if pub_time else None,
                "text": text_content[:3000],
            })
            if len(items) >= max_items:
                break

        return items, None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def fetch_source(source: dict, hours: int, max_items: int, timeout: int) -> tuple[list, str | None]:
    src_type = source.get("type", "rss")
    if src_type == "html":
        return _fetch_html(source, hours, max_items, timeout)
    return _fetch_rss(source, hours, max_items, timeout)


def _dedup(items: list) -> list:
    seen = set()
    out = []
    for it in items:
        key = re.sub(r"\W+", "", it["title"]).lower()[:40]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def fetch_all(cfg: dict, day: str) -> Path:
    from .config import date_dirs

    dirs = date_dirs(cfg, day)
    fx = cfg["fetch"]
    enabled = [s for s in cfg.get("sources", []) if s.get("enabled", True)]
    all_items, log = [], []
    for src in enabled:
        items, err = fetch_source(src, fx["hours"], fx["max_items_per_source"], fx["timeout"])
        status = f"{len(items)} 条" if err is None else f"失败 {err}"
        print(f"  [{src['name']}] {status}")
        log.append({"source": src["name"], "url": src["url"], "count": len(items), "error": err})
        all_items.extend(items)

    items = _dedup(all_items)
    for i, it in enumerate(items, 1):
        it["id"] = i
    out = dirs["raw"] / "items.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (dirs["raw"] / "fetch_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"抓取完成：{len(enabled)} 个源，去重后 {len(items)} 条 → {out}")
    return out


def load_items(cfg: dict, day: str) -> list:
    from .config import date_dirs

    p = date_dirs(cfg, day)["raw"] / "items.json"
    if not p.exists():
        raise SystemExit(f"未找到 {p}，请先执行: python main.py fetch --date {day}")
    return json.loads(p.read_text(encoding="utf-8"))

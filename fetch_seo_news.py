from __future__ import annotations

import html
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "index.html"

DEFAULT_FEEDS = [
    "https://developers.google.com/search/blog/feed.xml",
    "https://ahrefs.com/blog/feed/",
    "https://searchengineland.com/new-rss-feed",
    "https://rss.searchenginejournal.com/?a=bny4Fe0Ifx4%3Apgh3SfO9M2c%3AmC1kbPcV5gY",
]


def get_feeds() -> list[str]:
    raw = os.getenv("SEO_FEEDS", "")
    feeds = [item.strip() for item in raw.split(",") if item.strip()] if raw else []
    return feeds or DEFAULT_FEEDS


def normalize_source(feed_url: str) -> str:
    host = urlparse(feed_url).netloc
    return host.replace("www.", "") or feed_url


def fetch_xml(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SEO-Info-Bot/1.0)",
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        },
    )
    with urlopen(request, timeout=20) as response:
        return response.read()


def text_of(parent: ET.Element, names: Iterable[str]) -> str:
    for name in names:
        value = parent.findtext(name)
        if value and value.strip():
            return value.strip()
    return ""


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_items(feeds: Iterable[str], limit: int = 30) -> list[dict[str, str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    for feed_url in feeds:
        source = normalize_source(feed_url)
        try:
            xml_bytes = fetch_xml(feed_url)
            root = ET.fromstring(xml_bytes)
        except (URLError, ET.ParseError, TimeoutError, ValueError) as exc:
            items.append(
                {
                    "title": f"抓取失败：{source}",
                    "link": feed_url,
                    "source": source,
                    "published": str(exc),
                }
            )
            continue

        channel = root.find("channel")
        if channel is not None:
            for entry in channel.findall("item")[:limit]:
                title = text_of(entry, ["title"])
                link = text_of(entry, ["link"])
                published = text_of(entry, ["pubDate", "date", "dc:date"])
                if not title or not link or link in seen:
                    continue

                dt = parse_dt(published)
                if dt is not None and dt < cutoff:
                    continue

                seen.add(link)
                items.append(
                    {
                        "title": title,
                        "link": link,
                        "source": source,
                        "published": published or "recent",
                    }
                )
            continue

        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:limit]:
            title = text_of(entry, ["{http://www.w3.org/2005/Atom}title"])
            link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_elem.attrib.get("href", "").strip() if link_elem is not None else ""
            published = text_of(
                entry,
                [
                    "{http://www.w3.org/2005/Atom}published",
                    "{http://www.w3.org/2005/Atom}updated",
                ],
            )
            if not title or not link or link in seen:
                continue

            dt = parse_dt(published)
            if dt is not None and dt < cutoff:
                continue

            seen.add(link)
            items.append(
                {
                    "title": title,
                    "link": link,
                    "source": source,
                    "published": published or "recent",
                }
            )

    return items


def render_page(items: list[dict[str, str]]) -> str:
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    cards = []
    for index, item in enumerate(items, start=1):
        title = html.escape(item["title"])
        link = html.escape(item["link"], quote=True)
        source = html.escape(item["source"])
        published = html.escape(item["published"])
        cards.append(
            f"""
            <a class="card" href="{link}" target="_blank" rel="noreferrer noopener">
              <div class="card-rank">{index:02d}</div>
              <div class="card-main">
                <div class="card-top">
                  <span class="source">{source}</span>
                  <span class="time">{published}</span>
                </div>
                <h2>{title}</h2>
                <div class="link">打开原文</div>
              </div>
            </a>
            """
        )

    cards_html = "\n".join(cards) if cards else '<p class="empty">最近 24 小时内没有抓到新内容。</p>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="refresh" content="600" />
  <title>SEO 最新变化</title>
  <style>
    :root {{
      --bg1: #f6efe5;
      --bg2: #efe7dc;
      --panel: rgba(255, 255, 255, 0.76);
      --text: #1d1b16;
      --muted: #6b645a;
      --accent: #0f766e;
      --accent-2: #7c3aed;
      --border: rgba(29, 27, 22, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.16), transparent 25%),
        radial-gradient(circle at top right, rgba(124, 58, 237, 0.12), transparent 24%),
        linear-gradient(180deg, var(--bg1), var(--bg2));
      min-height: 100vh;
    }}
    .wrap {{
      max-width: 1160px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.4fr 0.9fr;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 22px;
    }}
    .hero-main, .hero-side {{
      border: 1px solid var(--border);
      background: var(--panel);
      backdrop-filter: blur(12px);
      border-radius: 24px;
      box-shadow: 0 18px 42px rgba(34, 24, 8, 0.08);
    }}
    .hero-main {{
      padding: 28px 28px 26px;
    }}
    .kicker {{
      display: inline-block;
      padding: 7px 12px;
      border-radius: 999px;
      background: rgba(15, 118, 110, 0.12);
      color: var(--accent);
      font-weight: 700;
      font-size: 0.9rem;
      margin-bottom: 14px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(2.1rem, 5vw, 4rem);
      line-height: 1.02;
      letter-spacing: -0.03em;
    }}
    .sub {{
      color: var(--muted);
      margin: 14px 0 0;
      max-width: 64ch;
      font-size: 1.02rem;
      line-height: 1.7;
    }}
    .hero-side {{
      padding: 22px;
      display: grid;
      gap: 14px;
      align-content: start;
    }}
    .stat {{
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.76);
      border: 1px solid rgba(29,27,22,0.08);
    }}
    .stat-label {{
      color: var(--muted);
      font-size: 0.88rem;
      margin-bottom: 6px;
    }}
    .stat-value {{
      font-size: 1.08rem;
      font-weight: 700;
      line-height: 1.5;
    }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: end;
      margin: 28px 0 14px;
    }}
    .section-head h2 {{
      margin: 0;
      font-size: 1.25rem;
      letter-spacing: -0.02em;
    }}
    .section-head .count {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
    }}
    .card {{
      display: flex;
      gap: 14px;
      text-decoration: none;
      color: inherit;
      padding: 16px;
      border-radius: 20px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.8);
      backdrop-filter: blur(10px);
      box-shadow: 0 12px 30px rgba(34, 24, 8, 0.06);
      transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    }}
    .card:hover {{
      transform: translateY(-3px);
      border-color: rgba(15,118,110,0.3);
      box-shadow: 0 18px 38px rgba(34,24,8,0.12);
    }}
    .card-rank {{
      width: 42px;
      height: 42px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      flex: none;
      font-weight: 800;
      color: white;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
    }}
    .card-main {{
      min-width: 0;
      flex: 1;
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 0.88rem;
      margin-bottom: 10px;
    }}
    .source {{
      color: var(--accent);
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 1.03rem;
      line-height: 1.55;
      letter-spacing: -0.01em;
    }}
    .link {{
      color: var(--accent-2);
      font-weight: 700;
      font-size: 0.92rem;
    }}
    .empty {{
      color: var(--muted);
      padding: 16px 4px;
    }}
    @media (max-width: 860px) {{
      .hero {{
        grid-template-columns: 1fr;
      }}
    }}
    @media (max-width: 640px) {{
      .wrap {{ padding: 18px 14px 32px; }}
      .hero-main {{ padding: 20px; }}
      .hero-side {{ padding: 16px; }}
      .card {{ padding: 14px; }}
      .card-top {{ flex-direction: column; align-items: start; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-main">
        <div class="kicker">SEO 晨报</div>
        <h1>每天早上 9:30，直接看 SEO 最新变化</h1>
        <p class="sub">这个页面会自动抓取公开 RSS 源里的最新 SEO 内容，只保留最近 24 小时的结果。你打开 GitHub Pages 就能快速扫一遍今天值得看的内容。</p>
      </div>
      <div class="hero-side">
        <div class="stat">
          <div class="stat-label">页面更新时间</div>
          <div class="stat-value">{html.escape(now)}</div>
        </div>
        <div class="stat">
          <div class="stat-label">内容来源</div>
          <div class="stat-value">Google Search Central / Ahrefs / Search Engine Land / Search Engine Journal</div>
        </div>
      </div>
    </section>

    <div class="section-head">
      <h2>最新条目</h2>
      <div class="count">{len(items)} 条</div>
    </div>

    <main class="grid">
      {cards_html}
    </main>
  </div>
</body>
</html>
"""


def main() -> None:
    feeds = get_feeds()
    items = load_items(feeds)
    OUTPUT.write_text(render_page(items), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(items)} items from {len(feeds)} feeds.")


if __name__ == "__main__":
    main()

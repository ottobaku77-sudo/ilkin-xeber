#!/usr/bin/env python3
"""İlkin xəbər — static news aggregator about Azerbaijan (Russian-language feeds).

Fetches public RSS feeds, keeps only headline + short excerpt + link to the original,
and writes a static site into ./site (index.html, news.json, assets).
Usage:  python build.py
"""
import concurrent.futures as cf
import html, json, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser

SITE_NAME = "İlkin xəbər"
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site"
MSK = ZoneInfo("Europe/Moscow")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
PER_SOURCE = 30          # max items per source
EXCERPT_LEN = 220        # characters of summary shown

FEEDS = [
    ("Report.az",  "https://report.az/ru/rss"),
    ("Trend",      "https://ru.trend.az/feeds/index.rss"),
    ("APA",        "https://ru.apa.az/rss"),
    ("Day.Az",     "https://news.day.az/rss/all.rss"),
    ("Haqqin.az",  "https://haqqin.az/rss"),
    ("Sputnik Азербайджан", "https://az.sputniknews.ru/export/rss2/archive/index.xml"),
    ("Vesti.az",   "https://vesti.az/rss"),
    ("Minval",     "https://minval.az/rss"),
    ("Media.az",   "https://media.az/rss"),
]

# Normalise very different feed categories into a small set.
CATEGORIES = [
    ("Политика",     r"полит|парламент|президент|дипломат|внешн|карабах|армени|госуд|власт|выбор"),
    ("Экономика",    r"эконом|бизнес|финанс|банк|нефт|газ|энерг|рынок|транспорт|туризм|агро|ИКТ|налог|бирж"),
    ("Происшествия", r"происш|криминал|инцидент|ДТП|авари|кримин|суд|прав"),
    ("Спорт",        r"спорт|футбол|чемпион|олимп"),
    ("Технологии",   r"технолог|IT|ИКТ|наука|интернет|гаджет|телеком"),
    ("Культура",     r"культур|шоу|кино|искусств|музык|звезд|lifestyle|стиль"),
    ("Общество",     r"обществ|социал|образован|здоров|медиц|погод|экологи|религ"),
    ("Мир",          r"мир|регион|росси|турци|иран|груз|европ|азия|сша|ближн|украин|международ"),
]

TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)", re.I)


def clean(text):
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def excerpt(text, n=EXCERPT_LEN):
    text = clean(text)
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:—- ") + "…"


def find_image(e):
    for enc in e.get("enclosures", []):
        if enc.get("type", "image").startswith("image") and enc.get("href"):
            return enc["href"]
    for key in ("media_content", "media_thumbnail"):
        for m in e.get(key, []) or []:
            if m.get("url"):
                return m["url"]
    for l in e.get("links", []):
        if l.get("type", "").startswith("image"):
            return l.get("href")
    blobs = [e.get("summary", "")] + [c.get("value", "") for c in e.get("content", [])]
    for b in blobs:
        m = IMG_RE.search(b or "")
        if m:
            return m.group(1)
    return None


def categorize(tags, title):
    hay = " ".join(tags) or ""
    for name, rx in CATEGORIES:
        if hay and re.search(rx, hay, re.I):
            return name
    for name, rx in CATEGORIES:            # fallback: guess from the headline
        if name != "Мир" and re.search(rx, title, re.I):
            return name
    return "Мир" if re.search(CATEGORIES[-1][1], hay, re.I) else "Разное"


def fetch(source, url):
    d = feedparser.parse(url, agent=UA)
    items = []
    for e in d.entries[:PER_SOURCE]:
        title, link = clean(e.get("title")), e.get("link")
        if not title or not link:
            continue
        t = e.get("published_parsed") or e.get("updated_parsed")
        dt = datetime(*t[:6], tzinfo=timezone.utc) if t else datetime.now(timezone.utc)
        summary = excerpt(e.get("summary") or e.get("description") or "")
        if summary.lower().startswith(title.lower()[:40].lower()) and len(summary) <= len(title) + 5:
            summary = ""
        tags = [t.get("term", "") for t in e.get("tags", [])]
        items.append({
            "title": title, "link": link, "summary": summary,
            "image": find_image(e), "source": source,
            "category": categorize(tags, title),
            "ts": int(dt.timestamp()),
            "time": dt.astimezone(MSK).strftime("%d.%m.%Y %H:%M"),
        })
    return source, url, items, getattr(d, "status", None)


def main():
    all_items, report = [], []
    with cf.ThreadPoolExecutor(8) as ex:
        for source, url, items, status in ex.map(lambda f: fetch(*f), FEEDS):
            report.append((source, url, len(items), status))
            all_items += items
    # de-duplicate by link, newest first
    seen, uniq = set(), []
    for it in sorted(all_items, key=lambda x: -x["ts"]):
        if it["link"] not in seen:
            seen.add(it["link"]); uniq.append(it)

    OUT.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)
    built = datetime.now(MSK).strftime("%d.%m.%Y %H:%M")
    payload = {"site": SITE_NAME, "built": built, "items": uniq,
               "sources": [{"name": s, "url": u, "count": n} for s, u, n, _ in report if n]}
    (OUT / "news.json").write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
    tpl = (ROOT / "templates" / "index.html").read_text("utf-8")
    page = (tpl.replace("{{SITE_NAME}}", html.escape(SITE_NAME))
               .replace("{{BUILT}}", built)
               .replace("{{DATA}}", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")))
    (OUT / "index.html").write_text(page, "utf-8")

    for s, u, n, st in report:
        print(f"{'OK ' if n else 'FAIL'} {s:22} {n:3} items  (HTTP {st})  {u}")
    print(f"Total unique items: {len(uniq)}  ->  {OUT/'index.html'}  (built {built} MSK)")
    return 0 if uniq else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""İlkin xəbər — Azərbaycan xəbərləri aqreqatoru (əsas dil: Azərbaycan dili).

Açıq RSS lentlərindən yalnız başlıq + qısa anons + orijinala keçid götürür
və ./site qovluğuna statik sayt yazır (index.html, futbol.html, news.json).
Secondary Russian feeds are kept behind an "RU" toggle (default view: AZ only).
Usage:  python build.py
"""
import concurrent.futures as cf
import html, json, re, shutil, socket, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser

import translate as tr

socket.setdefaulttimeout(25)
SITE_NAME = "İlkin xəbər"
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site"
BAKU = ZoneInfo("Asia/Baku")          # UTC+4
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
PER_SOURCE = 25
EXCERPT_LEN = 220

# (name, url, lang, kind)  kind: "news" | "sport" | "football"
FEEDS = [
    # --- Azərbaycan dilində (əsas) ---
    ("Report.az",     "https://report.az/az/rss",           "az", "news"),
    ("APA",           "https://apa.az/rss",                 "az", "news"),
    ("Trend",         "https://az.trend.az/feeds/index.rss", "az", "news"),
    ("Modern.az",     "https://modern.az/rss",              "az", "news"),
    ("Moderator.az",  "https://moderator.az/rss",           "az", "news"),
    ("Milli.Az",      "https://milli.az/rss/",              "az", "news"),
    ("Axar.az",       "https://axar.az/rss/",               "az", "news"),
    ("Publika.az",    "https://publika.az/rss/",            "az", "news"),
    ("Teleqraf",      "https://teleqraf.az/rss/",           "az", "news"),
    ("Metbuat.az",    "https://metbuat.az/rss.xml",         "az", "news"),
    ("Lent.az",       "https://lent.az/rss",                "az", "news"),
    ("Bakupost",      "https://bakupost.az/rss",            "az", "news"),
    ("AzVision",      "https://azvision.az/rss.xml",        "az", "news"),
    ("Azxeber",       "https://azxeber.com/rss",            "az", "news"),
    ("Olaylar",       "https://olaylar.az/rss/",            "az", "news"),
    # --- İdman / futbol ---
    ("Qol.az",        "https://qol.az/rss/",                "az", "football"),
    ("Sportify.az",   "https://sportify.az/feed/",          "az", "sport"),
    ("APA Sport",     "https://apasport.az/rss",            "az", "sport"),
    # --- Rus dilində (ikinci dərəcəli, "RU" düyməsi) ---
    ("Report.az RU",  "https://report.az/ru/rss",           "ru", "news"),
    ("Trend RU",      "https://ru.trend.az/feeds/index.rss", "ru", "news"),
    ("APA RU",        "https://ru.apa.az/rss",              "ru", "news"),
    ("Day.Az",        "https://news.day.az/rss/all.rss",    "ru", "news"),
    ("Haqqin.az",     "https://haqqin.az/rss",              "ru", "news"),
    # --- Beynəlxalq futbol (rus dilində): yalnız "Real Madrid" / "Barselona" xəbərləri ---
    ("Championat",    "https://www.championat.com/rss/news/football/", "ru", "clubs"),
    ("Sport-Express", "https://www.sport-express.ru/services/materials/news/football/se/", "ru", "clubs"),
    ("Sports.ru",     "https://www.sports.ru/rss/rubric.xml?s=208", "ru", "clubs"),
    ("Sputnik Azərbaycan", "https://az.sputniknews.ru/export/rss2/archive/index.xml", "ru", "news"),
    ("Vesti.az",      "https://vesti.az/rss",               "ru", "news"),
    ("Minval",        "https://minval.az/rss",              "ru", "news"),
]

# --- Dünya futbolu: beynəlxalq mənbələr (başlıq + qısa anons avtomatik AZ dilinə tərcümə olunur) ---
# (name, url, source language, club tag forced for club-specific feeds)
WORLD_FEEDS = [
    ("BBC Sport",           "https://feeds.bbci.co.uk/sport/football/rss.xml", "en", None),
    ("Sky Sports",          "https://www.skysports.com/rss/11095",             "en", None),
    ("The Guardian",        "https://www.theguardian.com/football/rss",        "en", None),
    ("The Independent",     "https://www.independent.co.uk/sport/football/rss", "en", None),
    ("ESPN",                "https://www.espn.com/espn/rss/soccer/news",       "en", None),
    ("UEFA",                "https://www.uefa.com/rssfeed/news/rss.xml",       "en", None),
    ("CBS Sports",          "https://www.cbssports.com/rss/headlines/soccer/", "en", None),
    ("Football365",         "https://www.football365.com/rss",                "en", None),
    ("Football Italia",     "https://football-italia.net/feed/",               "en", None),
    ("Marca",               "https://e00-marca.uecdn.es/rss/futbol/primera-division.xml", "es", None),
    ("Marca · Real Madrid", "https://e00-marca.uecdn.es/rss/futbol/real-madrid.xml", "es", "Real Madrid"),
    ("AS",                  "https://feeds.as.com/mrss-s/pages/as/site/as.com/section/futbol/portada/", "es", None),
    ("Mundo Deportivo",     "https://www.mundodeportivo.com/rss/futbol",       "es", None),
    ("Mundo Deportivo · Barça", "https://www.mundodeportivo.com/rss/futbol/fc-barcelona", "es", "Barselona"),
    ("Mundo Deportivo · Real Madrid", "https://www.mundodeportivo.com/rss/futbol/real-madrid", "es", "Real Madrid"),
    ("Sport · Real Madrid", "https://www.sport.es/es/rss/real-madrid/rss.xml", "es", "Real Madrid"),
    ("La Gazzetta dello Sport", "https://www.gazzetta.it/dynamic-feed/rss/section/Calcio.xml", "it", None),
    ("Corriere dello Sport", "https://www.corrieredellosport.it/rss/calcio",   "it", None),
    ("Kicker",              "https://newsfeed.kicker.de/news/fussball",        "de", None),
]
WORLD_PER_SOURCE = 20
NOT_FOOTBALL_URL = re.compile(r"/(tennis|cricket|nba|nfl|f1|formula-1|boxing|golf|rugby[\w-]*|basket\w*|baloncesto|motor\w*|ciclismo|watch|video|videos)/", re.I)
WORLD_EXCERPT = 200          # source chars sent for translation
LANG_LABEL = {"en": "EN", "es": "ES", "it": "IT", "de": "DE"}
# Strict club detection for international (EN/ES/IT/DE) text: "Madrid" alone is ambiguous there.
WORLD_CLUBS = {
    "Real Madrid": re.compile(r"real madrid|madridista|bernab[eé]u|mbapp[eé]|vin[ií]cius|xabi alonso|bellingham|arda g[uü]ler|"
                              r"los blancos|merengue|el cl[aá]sico|\bel madrid\b|\bdel madrid\b|\bal madrid\b|valdebebas", re.I),
    "Barselona":   re.compile(r"(?<!espanyol de )barcelona|bar[çc]a\b|azulgrana|blaugrana|\bcul[eé]s?\b|lamine yamal|\byamal\b|"
                              r"lewandowski|hansi flick|\bflick\b|camp nou|el cl[aá]sico|\bpedri\b|raphinha|joan laporta|\blaporta\b", re.I),
}

LIMIT = {"football": 40, "sport": 40, "clubs": 30}
SCAN = {"clubs": 400}



def low(s):
    """Azerbaijani/Turkish-aware lowercase."""
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


# Football club sub-tags (inside "Futbol"). Quoted/inflected forms avoid the
# common words "real" / "sabah".
CLUBS = {
    "Real Madrid": re.compile(low(
        r"real madrid|(?<!atletiko )(?<!atletico )madrid|[\"«“']real\b|\breal[\"»”']|\breal(ın|ı|a|la|dan|də)\b(?! sosyedad)|"
        r"mbappe|mbappé|vinisius|vinícius|ançelotti|ancelotti|xabi alonso|\balonso\b|bernabeu|bernabéu|"
        r"arda güler|bellingem|bellingham|el klasiko|el clasico|"
        r"\bреал(а|у|ом|е)?\b(?! сосьедад)|(?<!атлетико )\bмадрид|мбапп|винисиус|анчелотти|\bалонсо|бернабеу|беллингем|эль класико|эль-класико")),
    "Barselona": re.compile(low(
        r"barselona|barcelona|\bbarsa|barça|\bbarca\b|lamin yamal|\byamal|levandovski|lewandowski|\bflik\b|hansi flik|"
        r"kamp nou|camp nou|el klasiko|el clasico|"
        r"барселон|\bбарс[аеуы]\b|\bямал|левандовск|\bфлик\b|камп ноу|эль класико|эль-класико")),
}


def clubs_of(text):
    t = low(text)
    return [c for c, rx in CLUBS.items() if rx.search(t)]

# Futbol: checked first (tags + headline). Quoted club names avoid clashes with
# the common words "sabah" (tomorrow) and the region "Qarabağ".
FOOTBALL = re.compile(low(
    r"futbol|футбол|premyer liqa|primer liqa|çempionlar liqası|avropa liqası|konfrans liqası|"
    r"uefa|fifa|affa|\bpfl\b|millimiz|\bmilli komanda|baş məşqçi|qapıçı|hücumçu|yarımmüdafiəçi|müdafiəçi|"
    r"\bqol(u|lar|unu|la)?\b|penalti|\bmatç|transfer|legioner|"
    r"[\"«“']neftçi|neftçi[\"»”']|[\"«“']qarabağ[\"»”']|qarabağ fk|[\"«“']sabah[\"»”']|[\"«“']zirə|[\"«“']turan tovuz|"
    r"[\"«“']sumqayıt[\"»”']|[\"«“']kəpəz|[\"«“']araz-naxçıvan|[\"«“']səbail|[\"«“']şamaxı[\"»”']|[\"«“']qəbələ[\"»”']|"
    r"real madrid|barselona|mançester|liverpul|arsenal|çelsi|bavariya|yuventus|borussiya|mbappe|ronaldo|\bmessi\b|"
    r"dunyafutbolu|olkefutbolu|premyerliqa|championsligue|"
    r"qарабах|нефтчи|лига чемпионов|премьер-лиг"))
SPORT_NOT_FOOTBALL = re.compile(low(r"güləş|cüdo|boks|basketbol|voleybol|gimnastika|atletika|karate|tennis|taekvondo|şahmat|avarçəkmə|üzgüçülük|formula|döyüş"))

# Category rules (matched on feed tags first, then headline). Azerbaijani + Russian roots.
CATEGORIES = [
    ("Siyasət",      r"siyasət|prezident|parlament|milli məclis|diplomat|nazir|rəsmi|xronika|seçki|dövlət|"
                     r"полит|парламент|президент|дипломат|внешн|выбор|власт"),
    ("İqtisadiyyat", r"iqtisad|biznes|maliyyə|bank|neft|qaz\b|enerji|energetika|sənaye|birja|vergi|infrastruktur|"
                     r"aqrar|ikt\b|kripto|manat|ixrac|investisiya|tarif|qiymət|"
                     r"эконом|бизнес|финанс|банк|нефт|энерг|рынок|налог|бирж"),
    ("Hadisə",       r"hadisə|kriminal|qəza|yanğın|yandır|həbs|tutul|istintaq|saxlanıl|vəfat|məhkəmə|polis|cinayət|ölüb|yaralan|zəlzələ|"
                     r"происш|криминал|инцидент|дтп|авари|суд"),
    ("İdman",        r"idman|olimpiya|çempion|güləş|cüdo|boks|basketbol|voleybol|şahmat|спорт"),
    ("Mədəniyyət",   r"mədəniyyət|incəsənət|ədəbiyyat|teatr|kino|musiqi|şou|magazin|müğənni|aktyor|yaşam|"
                     r"культур|шоу|кино|искусств|музык"),
    ("Cəmiyyət",     r"cəmiyyət|sosial|toplum|təhsil|elm|səhiyyə|sağlamlıq|hava|ekologiya|din\b|media|region|gündəm|daxili|"
                     r"обществ|социал|образован|здоров|медиц|погод|экологи"),
    ("Dünya",        r"dünya|xarici|avropa|asiya|amerika|mdb|digər ölkələr|türkiyə|rusiya|iran|gürcüstan|ukrayna|abş|fransa|almaniya|çin\b|israil|britaniya|ermənistan|tramp|putin|"
                     r"мир|регион|росси|турци|иран|груз|европ|азия|сша|украин|международ"),
]
CATEGORIES = [(n, re.compile(low(rx))) for n, rx in CATEGORIES]
ORDER = ["Futbol", "Siyasət", "İqtisadiyyat", "Cəmiyyət", "Hadisə", "İdman", "Dünya", "Mədəniyyət", "Digər"]

TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)", re.I)
AZ_CHARS = re.compile(r"[əğışçöüƏĞİŞÇÖÜ]")
CYR = re.compile(r"[а-яА-ЯёЁ]")


def clean(text):
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def excerpt(text, n=EXCERPT_LEN):
    text = clean(text)
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(",.;:—- ") + "…"


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
    for b in [e.get("summary", "")] + [c.get("value", "") for c in e.get("content", [])]:
        m = IMG_RE.search(b or "")
        if m:
            return m.group(1)
    return None


def categorize(tags, title, kind):
    t_tags, t_title = low(" ".join(tags)), low(title)
    if kind in ("football", "clubs"):
        return "Futbol"
    if kind == "sport":
        if SPORT_NOT_FOOTBALL.search(t_tags + " " + t_title):
            return "İdman"
        return "Futbol" if FOOTBALL.search(t_tags + " " + t_title) else "İdman"
    if re.search(r"futbol|футбол", t_tags) or FOOTBALL.search(t_title):
        return "Futbol"
    for name, rx in CATEGORIES:
        if t_tags and rx.search(t_tags):
            return name
    for name, rx in CATEGORIES:
        if name != "Cəmiyyət" and rx.search(t_title):
            return name
    return "Digər"


def fetch(source, url, lang, kind):
    try:
        d = feedparser.parse(url, agent=UA)
    except Exception as ex:                       # network errors -> empty source
        return source, url, lang, [], f"ERR {ex}"
    now = datetime.now(timezone.utc)
    items = []
    for e in d.entries[:SCAN.get(kind, LIMIT.get(kind, PER_SOURCE) * 2)]:
        if len(items) >= LIMIT.get(kind, PER_SOURCE):
            break
        title, link = clean(e.get("title")), e.get("link")
        if not title or not link:
            continue
        tags = [t.get("term", "") or "" for t in e.get("tags", [])]
        summary = excerpt(e.get("summary") or e.get("description") or "")
        if lang == "az":                          # keep only Azerbaijani-language items
            if any(t.lower() in ("ru", "en") for t in tags) or len(CYR.findall(title)) > 3:
                continue
            if not AZ_CHARS.search(title + " " + summary):
                continue
        clubs = clubs_of(title + " " + summary + " " + " ".join(tags))
        if kind == "clubs" and not clubs:
            continue
        t = e.get("published_parsed") or e.get("updated_parsed")
        dt = datetime(*t[:6], tzinfo=timezone.utc) if t else now
        if dt > now + timedelta(minutes=5):       # some feeds label Baku time as UTC
            dt -= timedelta(hours=4)
            if dt > now + timedelta(minutes=5):
                dt = now
        if dt < now - timedelta(days=4):
            continue
        if summary.lower().startswith(title.lower()[:40]) and len(summary) <= len(title) + 5:
            summary = ""
        cat = categorize(tags, title, kind)
        if clubs and cat == "İdman":
            cat = "Futbol"
        items.append({
            "title": title, "link": link, "summary": summary,
            "image": find_image(e), "source": source, "lang": lang,
            "category": cat, "clubs": clubs if cat == "Futbol" else [],
            "ts": int(dt.timestamp()),
            "time": dt.astimezone(BAKU).strftime("%d.%m.%Y %H:%M"),
        })
    return source, url, lang, items, getattr(d, "status", None)


def fetch_world(source, url, lang, club):
    try:
        d = feedparser.parse(url, agent=UA)
    except Exception as ex:
        return source, url, "world", [], f"ERR {ex}"
    now, items = datetime.now(timezone.utc), []
    for e in d.entries[:150]:
        if len(items) >= WORLD_PER_SOURCE:
            break
        title, link = clean(e.get("title")), e.get("link")
        if not title or not link or NOT_FOOTBALL_URL.search(link):
            continue
        t = e.get("published_parsed") or e.get("updated_parsed")
        if not t:
            continue                               # undated items would look "new" on every build
        dt = datetime(*t[:6], tzinfo=timezone.utc)
        if dt > now + timedelta(minutes=5):
            dt = now
        if dt < now - timedelta(days=3):
            continue
        raw = clean(e.get("summary") or e.get("description") or "")
        summary = tr.trim_sentences(raw, WORLD_EXCERPT) if raw else ""
        if summary.lower().startswith(title.lower()[:40]) and len(summary) <= len(title) + 5:
            summary = ""
        hay = title + " " + summary + " " + " ".join(t.get("term", "") or "" for t in e.get("tags", []))
        clubs = [c for c, rx in WORLD_CLUBS.items() if rx.search(hay)]
        if club and club not in clubs:
            clubs.insert(0, club)
        items.append({
            "title": title, "link": link, "summary": summary, "image": find_image(e), "source": source,
            "lang": "az", "world": True, "orig_lang": lang, "orig_title": title,
            "category": "Futbol", "clubs": clubs, "ts": int(dt.timestamp()),
            "time": dt.astimezone(BAKU).strftime("%d.%m.%Y %H:%M"),
        })
    return source, url, "world", items, getattr(d, "status", None)


def translate_world(items):
    """Translate headline + excerpt of world items into Azerbaijani (cached, with fallback)."""
    T = tr.Translator()
    by_lang = {}
    for it in items:
        by_lang.setdefault(it["orig_lang"], []).append(it)
    for lang, group in by_lang.items():
        titles = [tr.pre_process(i["title"], lang) for i in group]
        sums = [tr.pre_process(i["summary"], lang) for i in group]
        out = T.translate_many(titles + sums, lang)
        for i, it in enumerate(group):
            t_az, s_az = out[i], out[len(group) + i]
            it["translated"] = bool(t_az)
            it["title"] = tr.post_process(t_az, "title") if t_az else it["title"]
            if it["summary"]:
                it["summary"] = tr.post_process(s_az, "summary", WORLD_EXCERPT + 40) if s_az else it["summary"]
    T.save()
    return T.stats, getattr(T, "last_error", None)


def main():
    all_items, report = [], []
    with cf.ThreadPoolExecutor(12) as ex:
        for source, url, lang, items, status in ex.map(lambda f: fetch(*f), FEEDS):
            report.append((source, url, lang, len(items), status))
            all_items += items
        world_res = list(ex.map(lambda f: fetch_world(*f), WORLD_FEEDS))
    world = []
    for source, url, lang, items, status in world_res:
        report.append((source, url, lang, len(items), status))
        world += items
    seen_w, wu = set(), []
    for it in world:                                  # dedupe before translating
        k = it["link"].split("?")[0].rstrip("/")
        if k not in seen_w:
            seen_w.add(k); wu.append(it)
    t0 = datetime.now()
    tstats, terr = translate_world(wu)
    ttime = (datetime.now() - t0).total_seconds()
    all_items += wu
    seen, uniq = set(), []
    for it in sorted(all_items, key=lambda x: -x["ts"]):
        key = it["link"].split("?")[0].rstrip("/")
        if key not in seen:
            seen.add(key); uniq.append(it)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    built = datetime.now(BAKU).strftime("%d.%m.%Y %H:%M")
    payload = {"site": SITE_NAME, "built": built, "order": ORDER, "clubs": list(CLUBS), "items": uniq, "lang_label": LANG_LABEL,
               "sources": [{"name": s, "url": u, "lang": l, "count": n} for s, u, l, n, _ in report if n]}
    (OUT / "news.json").write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
    tpl = (ROOT / "templates" / "index.html").read_text("utf-8")
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    pages = {
        "index.html":  ("", f"{SITE_NAME} — Azərbaycan xəbərləri", "Azərbaycanın ən son xəbərləri: siyasət, iqtisadiyyat, cəmiyyət, futbol, idman və dünya."),
        "futbol.html": ("Futbol", f"Futbol — {SITE_NAME}", "Azərbaycan və dünya futbolu: Premyer Liqa, Çempionlar Liqası, millimiz, transferlər."),
    }
    for fname, (preset, title, desc) in pages.items():
        page = (tpl.replace("{{SITE_NAME}}", html.escape(SITE_NAME))
                   .replace("{{TITLE}}", html.escape(title))
                   .replace("{{DESC}}", html.escape(desc))
                   .replace("{{PAGE}}", "futbol" if preset else "home")
                   .replace("{{BUILT}}", built)
                   .replace("{{PRESET}}", json.dumps(preset))
                   .replace("{{DATA}}", data))
        (OUT / fname).write_text(page, "utf-8")
    (OUT / ".nojekyll").write_text("")

    for s, u, l, n, st in report:
        print(f"{'OK ' if n else 'FAIL'} [{l}] {s:20} {n:3} items  (HTTP {st})  {u}")
    wn = [i for i in uniq if i.get("world")]
    print(f"World football: {len(wn)} items, translated {sum(i.get('translated', False) for i in wn)}, "
          f"real {sum('Real Madrid' in i['clubs'] for i in wn)}, barsa {sum('Barselona' in i['clubs'] for i in wn)}; "
          f"translation {tstats} in {ttime:.0f}s" + (f"; last error: {terr}" if terr else ""))
    az = [i for i in uniq if i["lang"] == "az" and not i.get("world")]
    print(f"Total unique: {len(uniq)}  (az {len(az)}, ru {len(uniq)-len(az)}, futbol {sum(i['category']=='Futbol' for i in az)}, real {sum('Real Madrid' in i['clubs'] for i in uniq)}, barsa {sum('Barselona' in i['clubs'] for i in uniq)})  built {built} Bakı vaxtı")
    return 0 if az else 1


if __name__ == "__main__":
    sys.exit(main())

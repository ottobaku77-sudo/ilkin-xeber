"""Free build-time translation of world-football headlines/excerpts into Azerbaijani.

* Engine: Google's public translate endpoints (no API key) via plain HTTPS,
  batched (many strings per request). Fallback: the original text.
* Proper nouns are "protected" before translation: club/player/league names in the
  source language are rewritten to their standard Azerbaijani spelling (Barça ->
  Barselona, Man Utd -> Mançester Yunayted ...). Google keeps such names and adds
  correct Azerbaijani case suffixes (Barselonanın, Liverpula ...). Nicknames that
  would be translated literally (Wolves, Spurs, Gunners, los blancos ...) are
  replaced by the club name for the same reason.
* After translation an Azerbaijani football glossary fixes literal/awkward wording
  (menecer -> baş məşqçi, məqsəd vurdu -> qol vurdu ...), names are normalised again
  with vowel-harmony-aware suffixes, the first letter is capitalised and excerpts
  are trimmed to a clean sentence boundary.
* Cache: raw machine output is stored in cache/translations.json (committed and
  carried between GitHub Actions runs with actions/cache), keyed by the
  pre-processed source text, so glossary changes apply without re-translating.
"""
import hashlib, json, re, time, urllib.parse, urllib.request
from pathlib import Path

CACHE_FILE = Path(__file__).resolve().parent / "cache" / "translations.json"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
SEP_BATCH = 16           # strings per request
MAX_CHARS = 2200         # chars per request

# ---------------------------------------------------------------- names (source -> az)
# Applied BEFORE translation (in the source text, case-insensitive, whole words) and
# AFTER translation (to catch forms Google still produced). Longest first.
NAMES = {
    # clubs
    "Manchester United": "Mançester Yunayted", "Man United": "Mançester Yunayted", "Man Utd": "Mançester Yunayted",
    "Manchester City": "Mançester Siti", "Man City": "Mançester Siti",
    "Real Madrid": "Real Madrid", "Barcelona": "Barselona", "Barça": "Barselona", "Barca": "Barselona", "FC Barcelona": "Barselona",
    "Atlético de Madrid": "Atletiko Madrid", "Atletico de Madrid": "Atletiko Madrid", "Atlético Madrid": "Atletiko Madrid",
    "Atletico Madrid": "Atletiko Madrid", "Atlético": "Atletiko", "Atleti": "Atletiko",
    "Liverpool": "Liverpul", "Chelsea": "Çelsi", "Tottenham Hotspur": "Tottenhem", "Tottenham": "Tottenhem",
    "Newcastle United": "Nyukasl", "Newcastle": "Nyukasl", "Aston Villa": "Aston Villa", "West Ham": "Vest Hem",
    "Everton": "Everton", "Brighton": "Brayton", "Wolverhampton": "Vulverhempton", "Nottingham Forest": "Nottingem Forest",
    "Crystal Palace": "Kristal Pelas", "Bournemouth": "Bornmut", "Fulham": "Fulhem", "Brentford": "Brentford", "Leeds": "Lids",
    "Bayern Munich": "Bavariya", "Bayern München": "Bavariya", "FC Bayern": "Bavariya", "Bayern": "Bavariya",
    "Borussia Dortmund": "Borussiya Dortmund", "Dortmund": "Borussiya Dortmund", "BVB": "Borussiya Dortmund",
    "Bayer Leverkusen": "Bayer Leverkuzen", "Leverkusen": "Bayer Leverkuzen", "RB Leipzig": "Leypsiq", "Leipzig": "Leypsiq",
    "Juventus": "Yuventus", "Juve": "Yuventus", "Inter Milan": "İnter", "Internazionale": "İnter", "Inter": "İnter",
    "AC Milan": "Milan", "Napoli": "Napoli", "AS Roma": "Roma", "Lazio": "Latsio", "Atalanta": "Atalanta", "Fiorentina": "Fiorentina",
    "Paris Saint-Germain": "PSJ", "Paris St-Germain": "PSJ", "PSG": "PSJ", "Marseille": "Marsel", "Monaco": "Monako",
    "Sevilla": "Sevilya", "Villarreal": "Vilyarreal", "Real Sociedad": "Real Sosyedad", "Real Betis": "Betis", "Valencia": "Valensiya",
    "Athletic Club": "Atletik Bilbao", "Athletic Bilbao": "Atletik Bilbao", "Celta": "Selta", "Girona": "Jirona", "Espanyol": "Espanyol",
    "Benfica": "Benfika", "Porto": "Porto", "Sporting CP": "Sportinq", "Sporting": "Sportinq", "Ajax": "Ayaks",
    "Galatasaray": "Qalatasaray", "Fenerbahce": "Fənərbaxça", "Fenerbahçe": "Fənərbaxça", "Besiktas": "Beşiktaş", "Beşiktaş": "Beşiktaş",
    "Qarabag": "Qarabağ", "Qarabağ": "Qarabağ",
    # nicknames that would be translated literally
    "Wolves": "Vulverhempton", "Spurs": "Tottenhem", "Gunners": "Arsenal", "Red Devils": "Mançester Yunayted",
    "Magpies": "Nyukasl", "Toffees": "Everton", "Hammers": "Vest Hem", "Seagulls": "Brayton", "Cherries": "Bornmut",
    "Villans": "Aston Villa", "Bianconeri": "Yuventus", "Nerazzurri": "İnter", "Rossoneri": "Milan", "Partenopei": "Napoli",
    "los blancos": "Real Madrid", "los merengues": "Real Madrid", "el conjunto blanco": "Real Madrid", "el equipo blanco": "Real Madrid",
    "madridismo": "Real Madrid", "azulgrana": "Barselona", "azulgranas": "Barselona", "blaugrana": "Barselona",
    "el conjunto culé": "Barselona", "el equipo culé": "Barselona", "culés": "Barselona", "colchoneros": "Atletiko",
    "rojiblancos": "Atletiko", "el Barsa": "Barselona",
    # players / coaches
    "Kylian Mbappé": "Kilian Mbappe", "Kylian Mbappe": "Kilian Mbappe", "Mbappé": "Mbappe",
    "Vinícius Júnior": "Vinisius Junior", "Vinicius Junior": "Vinisius Junior", "Vinícius Jr": "Vinisius Junior",
    "Vinicius Jr": "Vinisius Junior", "Vinícius": "Vinisius", "Vinicius": "Vinisius", "Vini Jr": "Vinisius Junior",
    "Lamine Yamal": "Lamin Yamal", "Robert Lewandowski": "Robert Levandovski", "Lewandowski": "Levandovski",
    "Jude Bellingham": "Cud Bellinqem", "Bellingham": "Bellinqem", "Erling Haaland": "Erlinq Haaland",
    "Carlo Ancelotti": "Karlo Ançelotti", "Ancelotti": "Ançelotti", "Hansi Flick": "Hansi Flik", "Flick": "Flik",
    "Cristiano Ronaldo": "Kriştiano Ronaldo", "Lionel Messi": "Lionel Messi", "Arda Güler": "Arda Gülər",
    "Pep Guardiola": "Pep Qvardiola", "Guardiola": "Qvardiola", "Raphinha": "Rafinya", "Rodrygo": "Rodriqo",
    "Güler": "Gülər", "Bernabéu": "Bernabeu", "Santiago Bernabéu": "Santyaqo Bernabeu", "Camp Nou": "Kamp Nou", "Spotify Camp Nou": "Kamp Nou",
    # competitions
    "Champions League": "Çempionlar Liqası", "Europa League": "Avropa Liqası", "Conference League": "Konfrans Liqası",
    "Premier League": "Premyer Liqa", "LaLiga": "La Liqa", "La Liga": "La Liqa", "Serie A": "İtaliya A Seriyası",
    "Bundesliga": "Bundesliqa", "Ligue 1": "Fransa Liqa 1", "League One": "League One", "League Two": "League Two", "Copa del Rey": "Kral Kuboku", "FA Cup": "İngiltərə Kuboku",
    "Carabao Cup": "Liqa Kuboku", "World Cup": "Dünya Çempionatı", "Club World Cup": "Klublararası Dünya Çempionatı",
    "Liga de Campeones": "Çempionlar Liqası", "Champions": "Çempionlar Liqası", "Mundial": "Dünya Çempionatı",
    "El Clásico": "El Klasiko", "El Clasico": "El Klasiko", "Clásico": "El Klasiko",
}
# keys that are safe only in their exact case (common words otherwise)
CASE_SENSITIVE = {"Inter", "Porto", "Champions", "Sporting", "Celta", "Flick", "Juve", "Leeds", "Monaco", "Mundial", "Clásico", "Atleti", "Barca"}

# Pre-translation English/Spanish idioms that machine translation renders literally.
PRE = [
    (r"\bheld by\b", "drew with"), (r"\bheld to a draw by\b", "drew with"), (r"\bwinless run\b", "series without a win"),
    (r"\bwinless\b", "without a win"), (r"\bunbeaten run\b", "unbeaten series"), (r"\bclean sheets?\b", "match without conceding"),
    (r"\bboss\b", "head coach"), (r"\bmanager\b", "head coach"), (r"\bgaffer\b", "head coach"), (r"\bkeeper\b", "goalkeeper"),
    (r"\bstopper\b", "goalkeeper"), (r"\bsacked\b", "dismissed"), (r"\bsack\b", "dismissal"), (r"\bhat-trick\b", "three goals"),
    (r"\bbrace\b", "two goals"), (r"\btalking points\b", "key moments"), (r"\bweekend[’']s action\b", "weekend's matches"), (r"\bLiveblog\b", "live blog"), (r"^\s*(?-i:LIVE)\b[!:]*\s*", "Live: "), (r"\s+(?-i:LIVE)\b[!:]*\s*", ": live – "), (r"\bstriker\b", "forward"),
    (r"\bfixture\b", "match"), (r"\bpitch\b", "field"), (r"\bloanee\b", "loan player"), (r"\bon loan\b", "on loan"),
    (r"\bpundit\b", "expert"), (r"\bplayer ratings\b", "player ratings"), (r"\bgaffes?\b", "mistake"),
    (r"\blate winner\b", "winning goal in the final minutes"), (r"^(.{2,40}?) latest:", r"\1 news:"),
    (r"\blate equaliser\b", "equalising goal in the final minutes"), (r"\bshock\b", "unexpected"),
    (r"\bla Real\b(?! Madrid| Sociedad| Sosyedad)", "Real Sosyedad"),
    (r"\b(el|del|al) Real\b(?! Madrid| Sociedad| Sosyedad| Betis| Valladolid| Zaragoza| Oviedo| Mallorca)", r"\1 Real Madrid"),
    (r"\s*(Leer|Leggi|Read more|Weiterlesen)\.?$", ""),
    (r"\bgolazo\b", "gran gol"), (r"\bel técnico\b", "el entrenador"), (r"\bel míster\b", "el entrenador"), (r"\bfichaje\b", "transfer"),
]
PRE = [(re.compile(a, re.I), b) for a, b in PRE]
# rules from "la Real" onwards are for every source language (Spanish/Italian/German too)
PRE_ANY_FROM = next(i for i, (rx, _) in enumerate(PRE) if rx.pattern.startswith(r"\bla Real"))

# Post-translation Azerbaijani clean-up (literal/awkward -> natural football wording).
POST = [
    (r"\bmenecer(i|ə|in|lə|ləri)?\b", lambda m: "baş məşqçi" + {"i": "si", "ə": "yə", "in": "sinin", "lə": "lə", "ləri": "ləri"}.get(m.group(1) or "", "")),
    (r"\bpatron(u|a|un|la)?\b", lambda m: "baş məşqçi" + {"u": "si", "a": "yə", "un": "sinin", "la": "lə"}.get(m.group(1) or "", "")),
    (r"\bməşqçi(si)? məşqçi", r"məşqçi\1"), (r"\bbaş baş məşqçi", "baş məşqçi"),
    (r"\bməqsəd(i|lər|ləri)? vur", lambda m: {"": "qol", "i": "qolu", "lər": "qollar", "ləri": "qolları"}[m.group(1) or ""] + " vur"),
    (r"\bməqsəd(lər)?(i|in|ə)? (?=(?:\w+ )?(?:buraxd|vurd|atd|sayıl|ləğv))", lambda m: "qol" + (m.group(1) and "lar" or "") + (m.group(2) or "") + " "),
    (r"\bhədəf vur", "qol vur"), (r"\b(böyük|gözəl|möhtəşəm) bir məqsəd(lə|i)?\b", lambda m: "möhtəşəm qol" + {"lə": "la", "i": "u"}.get(m.group(2) or "", "")),
    (r"\bməqsədlə qeyd", "qolla qeyd"), (r"\borta sahə oyunçusu", "yarımmüdafiəçi"), (r"\borta müdafiəçi", "mərkəz müdafiəçisi"),
    (r"\bforvard(ı|lar)?\b", lambda m: "hücumçu" + {"ı": "su", "lar": "lar"}.get(m.group(1) or "", "")),
    (r"\bqapı gözətçisi", "qapıçı"), (r"\bqol gözətçisi", "qapıçı"), (r"\bkeeper\b", "qapıçı"),
    (r"\bbəraberlik\b", "heç-heçə"), (r"\bheç-heçə etdi\b", "heç-heçə oynadı"), (r"\bheç-heçə edir\b", "heç-heçə oynayır"),
    (r"\bqələbəsiz qaçış", "qələbəsiz seriya"), (r"\bqaçış(ı)? davam", r"seriya\1 davam"), (r"\bməğlubiyyətsiz qaçış", "məğlubiyyətsiz seriya"),
    (r"\bmeydança\b", "meydan"), (r"\bhəftə sonu aksiya", "həftəsonu matçlar"), (r"\baksiyası\b", "oyunu"), (r"\bfutbolçu oyunçu", "futbolçu"), (r"\bpenalti zərbəsi\b", "penalti"),
    (r"\bkart(ı)? göstərildi", r"vərəqə\1 göstərildi"), (r"\bqırmızı kart", "qırmızı vərəqə"), (r"\bsarı kart", "sarı vərəqə"),
    (r"\bkrossovka", "butsa"), (r"\bdirektor(u)? futbol", r"futbol direktoru"), (r"\bəvəzedici skamya", "ehtiyat oyunçular skamyası"),
    (r"^(?:canlı|live)!?:?\s+", "Canlı: "),
    (r"\bKarabakh\b", "Qarabağ"), (r"\bKarabağ\b", "Qarabağ"),
]
POST = [(re.compile(a, re.I), b) for a, b in POST]

# --------------------------------------------------------------- vowel harmony helpers
BACK, FRONT = set("aıou"), set("əeiöü")
VOWELS = BACK | FRONT


def _last_vowel(word):
    for ch in reversed(word.lower()):
        if ch in VOWELS:
            return ch
    return "a"


def _harm(stem, suffix_kind):
    """Return Azerbaijani case suffix for `stem` (gen, dat, acc, loc, abl, ins)."""
    v = _last_vowel(stem)
    ends_vowel = stem[-1].lower() in VOWELS
    four = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "ə": "i", "e": "i", "i": "i", "ö": "ü", "ü": "ü"}[v]
    two = "a" if v in BACK else "ə"
    if suffix_kind == "gen":
        return ("n" if ends_vowel else "") + four + "n"
    if suffix_kind == "acc":
        return ("n" if ends_vowel else "") + four
    if suffix_kind == "dat":
        return ("y" if ends_vowel else "") + two
    if suffix_kind == "loc":
        return "d" + two
    if suffix_kind == "abl":
        return "d" + two + "n"
    if suffix_kind == "ins":
        return ("y" if ends_vowel else "") + "l" + two
    return ""


SUFFIX_KIND = [  # (regex on the suffix as Google produced it, kind) — order matters
    (r"n?[ıiuü]n", "gen"), (r"y?l[aə]", "ins"), (r"d[aə]n", "abl"), (r"t[aə]n", "abl"), (r"d[aə]", "loc"), (r"t[aə]", "loc"),
    (r"n?[ıiuü]", "acc"), (r"y?[aə]", "dat"),
]
SUFFIX_KIND = [(re.compile(r"^['’-]?" + a + r"$"), k) for a, k in SUFFIX_KIND]


def _resuffix(stem, raw):
    """Map Google's suffix (computed for a foreign stem) to the right one for `stem`."""
    if not raw:
        return ""
    for rx, kind in SUFFIX_KIND:
        if rx.match(raw):
            return _harm(stem, kind)
    return raw.lstrip("-'’")


SUF = r"((?:['’-])?(?:n?[ıiuü]n|y?l[aə]|[dt][aə]n|[dt][aə]|n?[ıiuü]|y?[aə]))?(?![\wəğıöşçüƏİĞÖŞÇÜ])"


W = r"\wəğıöşçüƏİĞÖŞÇÜ"


def _alternation(keys):
    keys = sorted(set(keys), key=len, reverse=True)
    ci = [re.escape(k) for k in keys if k not in CASE_SENSITIVE]
    cs = [re.escape(k) for k in keys if k in CASE_SENSITIVE]
    parts = []
    if ci:
        parts.append("(?i:" + "|".join(ci) + ")")
    if cs:
        parts.append("|".join(cs))
    return "(" + "|".join(parts) + ")"


_LOOKUP = {k.lower(): v for k, v in NAMES.items()}
_LOOKUP.update({v.lower(): v for v in NAMES.values()})
# One-pass substitution; destination spellings are included as identity keys so that
# e.g. "Borussiya Dortmund" is consumed whole and never becomes "Borussiya Borussiya Dortmund".
_PRE_RX = re.compile(rf"(?<![{W}])" + _alternation(list(NAMES) + list(NAMES.values())) + rf"(?![{W}])")
_POST_KEYS = [k for k in NAMES if len(k) > 3 or k.lower() == NAMES[k].lower()] + list(NAMES.values())
_POST_RX = re.compile(rf"(?<![{W}])" + _alternation(_POST_KEYS) + SUF)
_REAL_RX = re.compile(r'"Real"' + SUF)     # Google sometimes shortens "Real Madrid" to "Real" in quotes


def _dst(name):
    return _LOOKUP.get(name.lower(), name)


def _fix_names(text):
    text = _POST_RX.sub(lambda m: _dst(m.group(1)) + _resuffix(_dst(m.group(1)), m.group(2) or ""), text)
    text = _REAL_RX.sub(lambda m: '"Real Madrid"' + _resuffix("Real Madrid", m.group(1) or ""), text)
    return text


# --------------------------------------------------------------------- text helpers
def az_upper_first(s):
    for i, ch in enumerate(s):
        if ch.isalpha():
            up = "İ" if ch == "i" else ch.upper()
            return s[:i] + up + s[i + 1:]
        if ch not in "\"'«“„(¿¡ ":
            return s
    return s


def trim_sentences(text, n):
    """Cut to <= n chars at a sentence end if possible, else at a word boundary + '…'."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    cut = text[:n]
    m = list(re.finditer(r"[.!?…](?=[\s\"»”’)]|$)", cut))
    if m and m[-1].end() > n * 0.45:
        return cut[:m[-1].end()].strip()
    return cut.rsplit(" ", 1)[0].rstrip(",.;:—–- ") + "…"


def pre_process(text, lang):
    text = _PRE_RX.sub(lambda m: _dst(m.group(1)), text)
    for rx, dst in (PRE if lang == "en" else PRE[PRE_ANY_FROM:]):
        text = rx.sub(dst, text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def post_process(text, kind="title", limit=None):
    text = _fix_names(text)
    for rx, dst in POST:
        text = rx.sub(dst, text)
    text = text.replace("\u200b", "").replace("::", ":")
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"[“”„]", '"', text)
    text = az_upper_first(text)
    if kind == "title":
        text = text.rstrip(". ")
    if limit:
        text = trim_sentences(text, limit)
    return text


# ----------------------------------------------------------------------- engines
def _google_dict(texts, sl):
    q = [("client", "dict-chrome-ex"), ("sl", sl), ("tl", "az")] + [("q", t) for t in texts]
    req = urllib.request.Request("https://clients5.google.com/translate_a/t?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": UA})
    data = json.loads(urllib.request.urlopen(req, timeout=25).read())
    out = []
    for d in data:
        out.append(d[0] if isinstance(d, list) else d)
    if len(out) != len(texts):
        raise ValueError("batch size mismatch")
    return out


def _google_gtx(texts, sl):
    out = []
    for t in texts:
        q = urllib.parse.urlencode({"client": "gtx", "sl": sl, "tl": "az", "dt": "t", "q": t})
        req = urllib.request.Request("https://translate.googleapis.com/translate_a/single?" + q, headers={"User-Agent": UA})
        data = json.loads(urllib.request.urlopen(req, timeout=25).read())
        out.append("".join(seg[0] for seg in data[0] if seg and seg[0]))
        time.sleep(0.25)
    return out


ENGINES = [("google-dict", _google_dict), ("google-gtx", _google_gtx)]


class Translator:
    def __init__(self):
        try:
            self.cache = json.loads(CACHE_FILE.read_text("utf-8"))
        except Exception:
            self.cache = {}
        self.used, self.stats = set(), {"cached": 0, "translated": 0, "failed": 0, "engine": None}
        self.dead = set()

    @staticmethod
    def key(text, lang):
        return hashlib.sha1(f"{lang}|{text}".encode()).hexdigest()[:16]

    def translate_many(self, texts, lang):
        """texts: already pre-processed source strings. Returns list (None = failed)."""
        res, todo = [None] * len(texts), []
        for i, t in enumerate(texts):
            k = self.key(t, lang)
            if not t:
                res[i] = ""
            elif k in self.cache:
                res[i] = self.cache[k]; self.used.add(k); self.stats["cached"] += 1
            else:
                todo.append(i)
        batch = []
        def flush(b):
            if not b:
                return
            src = [texts[i] for i in b]
            for name, fn in ENGINES:
                if name in self.dead:
                    continue
                for attempt in range(2):
                    try:
                        out = fn(src, lang)
                        for i, o in zip(b, out):
                            if o and o.strip():
                                k = self.key(texts[i], lang)
                                self.cache[k] = o; self.used.add(k); res[i] = o
                                self.stats["translated"] += 1
                        self.stats["engine"] = self.stats["engine"] or name
                        time.sleep(0.4)
                        return
                    except Exception as ex:  # rate limit / network -> retry once, then next engine
                        self.last_error = f"{name}: {ex}"
                        time.sleep(2)
                self.dead.add(name)
        size = 0
        for i in todo:
            if len(batch) >= SEP_BATCH or size + len(texts[i]) > MAX_CHARS:
                flush(batch); batch, size = [], 0
            batch.append(i); size += len(texts[i])
        flush(batch)
        self.stats["failed"] += sum(1 for i in todo if res[i] is None)
        return res

    def save(self, keep_unused=1500):
        # keep everything used in this build + a bounded number of older entries
        keep = {k: v for k, v in self.cache.items() if k in self.used}
        for k, v in list(self.cache.items())[::-1]:
            if len(keep) >= len(self.used) + keep_unused:
                break
            keep.setdefault(k, v)
        CACHE_FILE.parent.mkdir(exist_ok=True)
        CACHE_FILE.write_text(json.dumps(keep, ensure_ascii=False, indent=0, sort_keys=True), "utf-8")

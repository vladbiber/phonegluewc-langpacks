#!/usr/bin/env python3
"""Builds the language packs: build.py SRC OUT [code ...]. SRC caches the downloads, OUT receives
<code>/words.tsv, <code>/bigrams.tsv, <code>/letters and index.tsv. Needs hunspell and network on first run."""
import bz2, collections, hashlib, json, math, os, re, subprocess, sys, unicodedata, urllib.request

FREQ = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/525f9b560de45753a5ea01069454e72e9aa541c6/content/2018/{0}/{0}_50k.txt"
DICT = "https://raw.githubusercontent.com/LibreOffice/dictionaries/c0865a85eb67dc377f2cf8e8fe2c4fa9e53f0dcb/{}.{}"
SENT = "https://downloads.tatoeba.org/exports/per_language/{0}/{0}_sentences.tsv.bz2"
KEEP, MIN_COUNT, HEADS, TOP = 30000, 3, 4000, 10
SINGLE = set("aeiouyàèéóåöäíõzkvsw")
# the sentence collection's stock characters, and words no keyboard should offer
ALLBLOCK = """tom mary john sami layla fuck fucking fucked fucker fuckin motherfucker shit shitty bullshit cunt
bitch bitches asshole dick cock pussy whore slut nigger faggot""".split()

# code: frequency list, dictionaries, sentence export, letters beyond a-z, blocked words
LANGS = {
    "bs": ("bs", ["bs_BA/bs_BA"], "bos", "čćđšž", "kurac pizda jebem jebati jebi kurva govno peder picka"),
    "ca": ("ca", ["ca/dictionaries/ca"], "cat", "àçéèíïòóúü", "merda puta collons cony polla"),
    "cs": ("cs", ["cs_CZ/cs_CZ"], "ces", "áčďéěíňóřšťúůýž", "kurva píča čurák kokot hovno mrdat šukat zmrd buzerant"),
    "da": ("da", ["da_DK/da_DK"], "dan", "æøåé", "pik kusse luder kneppe lort"),
    "de": ("de", ["de/de_DE_frami"], "deu", "äöüß", "scheiße scheisse fotze hure arschloch wichser schwuchtel neger ficken fick schlampe nutte"),
    "es": ("es", ["es/es_ES"], "spa", "áéíóúüñ", "coño puta puto mierda joder cabrón pendejo maricón verga polla zorra culero"),
    "et": ("et", ["et_EE/et_EE"], "est", "äõöüšž", "türa perse lits pede raisk"),
    "fr": ("fr", ["fr_FR/dictionaries/fr"], "fra", "àâæçéèêëîïôœùûüÿ", "merde putain pute salope connard connasse enculé nique bite couille couilles foutre chier pédé nègre"),
    "gl": ("gl", ["gl/gl_ES"], "glg", "áéíóúüñ", "merda puta carallo cona foder cabrón"),
    "hr": ("hr", ["hr_HR/hr_HR"], "hrv", "čćđšž", "kurac pizda jebem jebati jebi kurva govno peder picka"),
    "hu": ("hu", ["hu_HU/hu_HU"], "hun", "áéíóöőúüű", "kurva fasz picsa geci szar baszd baszni buzi köcsög faszfej"),
    "id": ("id", ["id/id_ID"], "ind", "é", "kontol memek ngentot bangsat goblok"),
    "is": ("is", ["is/is"], "isl", "áðéíóúýþæö", "tussa hóra typpi"),
    "it": ("it", ["it_IT/it_IT"], "ita", "àèéìíòóùú", "cazzo merda stronzo puttana troia vaffanculo minchia figa frocio"),
    "lt": ("lt", ["lt_LT/lt"], "lit", "ąčęėįšųūž", "kurva bybis pyzda šūdas pydaras"),
    "lv": ("lv", ["lv_LV/lv_LV"], "lvs", "āčēģīķļņšūž", "pizda dirsa sūds mauka pimpis"),
    "nb": ("no", ["no/nb_NO"], "nob", "æøåéèêóòô", "fitte kuk hore pikk faen jævla knulle dritt"),
    "nl": ("nl", ["nl_NL/nl_NL"], "nld", "éëïóöüèêí", "kut lul hoer klootzak neuken godverdomme mongool"),
    "pl": ("pl", ["pl_PL/pl_PL"], "pol", "ąćęłńóśźż", "kurwa chuj pierdolić jebać pizda skurwysyn dziwka pedał cipa kutas"),
    "pt": ("pt", ["pt_PT/pt_PT", "pt_BR/pt_BR"], "por", "áâãàçéêíóôõúü", "merda caralho foda foder puta porra cona buceta viado piroca"),
    "ro": ("ro", ["ro/ro_RO"], "ron", "ăâîșț", "pula pulă pizda pizdă muie cacat căcat futu fututi futut târfă tarfa curvă curva"),
    "sk": ("sk", ["sk_SK/sk_SK"], "slk", "áäčďéíĺľňóôŕšťúýž", "and kurva piča kokot jebať chuj hovno zmrd"),
    "sl": ("sl", ["sl_SI/sl_SI"], "slv", "čšž", "kurac pizda jebem jebati kurba drek"),
    "sq": ("sq", ["sq_AL/sq_AL"], "sqi", "çë", "pidh qij"),
    "sv": ("sv", ["sv_SE/dictionaries/sv_SE"], "swe", "åäöé", "jävla kuk fitta hora knulla skit"),
    "tr": ("tr", ["tr_TR/tr_TR"], "tur", "çğıöşüâî", "siktir orospu piç yarrak göt ibne amına amcık pezevenk"),
}
# nouns take a capital here, so the dictionary rejects them in lower case
CAPITAL_NOUNS = {"de"}
# the letters with no accent to strip; phonekbd's words.c holds the same table
NOACCENT = dict(zip("æðøþßđħıĳĸŀłŉŋœŧſ", "adotsdhiiklln" "nots"))

def fold(w):
    out = []
    for c in w.lower():
        if c in "'-":
            continue
        out.append(NOACCENT.get(c) or unicodedata.normalize("NFD", c)[0])
    return "".join(out)

def lower(w, code):
    if code == "tr":
        w = w.replace("İ", "i").replace("I", "ı")
    return w.lower().replace("’", "'")

def norm(w, code):
    return w.replace("ş", "ș").replace("ţ", "ț") if code == "ro" else w

def fetch(url, path):
    if not os.path.exists(path):
        tmp = path + ".part"
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
            f.write(r.read())
        os.rename(tmp, path)
    return path

def sources(code, src):
    freq, dicts, sent, _, _ = LANGS[code]
    d = f"{src}/{code}"
    os.makedirs(d, exist_ok=True)
    fetch(FREQ.format(freq), f"{d}/freq.txt")
    names = []
    for i, dic in enumerate(dicts):
        names.append(f"{d}/dict{i}")
        fetch(DICT.format(dic, "dic"), names[-1] + ".dic")
        fetch(DICT.format(dic, "aff"), names[-1] + ".aff")
    fetch(SENT.format(sent), f"{d}/sentences.tsv.bz2")
    return f"{d}/freq.txt", ",".join(names), f"{d}/sentences.tsv.bz2"

def wrong(words, dic, home):
    env = {"LC_ALL": "C.UTF-8", "HOME": home, "PATH": os.environ["PATH"]}
    r = subprocess.run(["hunspell", "-d", dic, "-i", "utf-8", "-l"], input="\n".join(words),
                       capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"hunspell failed on {dic}: {r.stderr[:200]}")
    return set(r.stdout.split())

def build_words(code, freqf, dic, src):
    alpha = LANGS[code][3]
    block = {fold(w) for w in ALLBLOCK + LANGS[code][4].split()}
    raw = {}
    for line in open(freqf, encoding="utf-8"):
        parts = line.split()
        if len(parts) == 2:
            w = norm(lower(parts[0], code), code)
            raw[w] = raw.get(w, 0) + int(parts[1])
    total = sum(raw.values())
    letters = f"[a-z{alpha}]+(?:['-][a-z{alpha}]+)*"
    words = [w for w in raw if re.fullmatch(letters, w) and fold(w) not in block and w != "the"
             and (len(w) > 1 or w in SINGLE) and len(w.encode()) < 48]
    bad = wrong(words, dic, src)
    good = {w: raw[w] for w in words if w not in bad}
    if code in CAPITAL_NOUNS:
        caps = {w: w[0].upper() + w[1:] for w in words if w in bad}
        badcaps = wrong(caps.values(), dic, src)
        for w, c in caps.items():
            if c not in badcaps:
                good[c] = good.get(c, 0) + raw[w]
    # a misspelled form without accents counts for the word it stands for
    best = {}
    for w, n in good.items():
        k = fold(w)
        if k not in best or n > good[best[k]]:
            best[k] = w
    for w in words:
        if w in bad and fold(w) in best and best[fold(w)].lower() != w:
            good[best[fold(w)]] += raw[w]
    top = sorted(good, key=lambda w: (-good[w], w))[:KEEP]
    rows = {w: round(16 * math.log2(good[w] / total * 1e9 + 1)) for w in top}
    stats = {"list": len(words), "accepted": len(good), "kept": len(rows)}
    return rows, stats

TOKEN = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")

# every twentieth sentence is left out of the counts and measures the pack
def build_bigrams(code, sentf, rows, evalout):
    known = {w.lower(): w for w in rows}
    pairs = collections.defaultdict(collections.Counter)
    common = collections.Counter()
    held = []
    for n, line in enumerate(bz2.open(sentf, "rt", encoding="utf-8", errors="replace")):
        text = line.rstrip("\n").split("\t")[-1]
        if n % 20 == 0:
            held.append(text)
            continue
        for sentence in re.split(r"[.!?…]+", text):
            prev = "<s>"
            for i, m in enumerate(TOKEN.finditer(sentence)):
                w = known.get(norm(lower(m[0], code), code))
                # a capital inside a sentence is a name, and names are not predictions
                if not w or (i and m[0][0].isupper() and w[0].islower()):
                    prev = None
                    continue
                if prev:
                    pairs[prev][w] += 1
                prev = fold(w)
                common[w] += 1
    keep = sorted(pairs, key=lambda h: (-sum(pairs[h].values()), h))[:HEADS]
    table = {h: [w for w, c in sorted(pairs[h].items(), key=lambda x: (-x[1], x[0]))[:TOP] if c >= MIN_COUNT] for h in keep}
    table["<*>"] = [w for w, c in sorted(common.items(), key=lambda x: (-x[1], x[0]))[:6]]
    if evalout:
        phrases = []
        for text in held:
            toks = list(TOKEN.finditer(text))
            if 4 <= len(toks) <= 12 and all(norm(lower(t[0], code), code) in known for t in toks) \
                    and not any(i and t[0][0].isupper() and known[norm(lower(t[0], code), code)][0].islower() for i, t in enumerate(toks)):
                phrases.append(norm(text, code))
        step = max(1, len(phrases) // 300)
        with open(evalout, "w", encoding="utf-8") as f:
            f.writelines(p + "\n" for p in phrases[::step][:300])
    return table, n + 1, sum(sum(c.values()) for c in pairs.values())

def letters_of(code):
    out = []
    for c in LANGS[code][3]:
        up = {"ß": "ß", "ı": "İ"}.get(c, c.upper())
        out.append(f"{fold(c)}\t{c}\t{up}\n")
    return out

def main():
    src, out, *codes = sys.argv[1:]
    src, out = os.path.abspath(src), os.path.abspath(out)
    report = {}
    for code in codes or LANGS:
        freqf, dic, sentf = sources(code, src)
        rows, stats = build_words(code, freqf, dic, src)
        table, sents, npairs = build_bigrams(code, sentf, rows, f"{src}/{code}/eval.txt")
        stats.update(sentences=sents, pairs=npairs, heads=sum(1 for v in table.values() if v))
        os.makedirs(f"{out}/{code}", exist_ok=True)
        lines = sorted((fold(w).encode(), -s, w) for w, s in rows.items())
        with open(f"{out}/{code}/words.tsv", "w", encoding="utf-8", newline="\n") as f:
            for key, s, w in lines:
                k = key.decode()
                f.write(f"{k}\t{'' if w == k else w}\t{-s}\tr\n")
        with open(f"{out}/{code}/bigrams.tsv", "w", encoding="utf-8", newline="\n") as f:
            for h in sorted(table, key=lambda s: s.encode()):
                if table[h]:
                    f.write(f"{h}\t{' '.join(table[h])}\n")
        with open(f"{out}/{code}/letters", "w", encoding="utf-8", newline="\n") as f:
            f.writelines(letters_of(code))
        report[code] = stats
        print(code, json.dumps(stats), flush=True)
    with open(f"{out}/index.tsv", "w", newline="\n") as idx:
        for code in sorted(d for d in os.listdir(out) if d in LANGS):
            for name in ("words.tsv", "bigrams.tsv", "letters"):
                b = open(f"{out}/{code}/{name}", "rb").read()
                idx.write(f"{code}\t{name}\t{len(b)}\t{hashlib.sha256(b).hexdigest()}\n")

if __name__ == "__main__":
    main()

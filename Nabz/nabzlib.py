"""Shared helpers for the Nabz Scribe feasibility spike.

Matching works across Roman Urdu and Urdu script by reducing every word to a
consonant skeleton: "Panadol" and "پیناڈول" both become "pndl".
"""
import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
DATA = ROOT / "data"
REFS = ROOT / "refs"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_config():
    return load_json(ROOT / "config.json")


def load_key():
    return load_json(ROOT / "answer_key.json")


def resolve_path(p):
    """Config paths are relative to this folder unless absolute."""
    p = Path(p)
    return p if p.is_absolute() else (ROOT / p)


def resolve_binary(p):
    """Find a built binary on Linux/WSL or Windows (MSVC puts it under Release/)."""
    p = resolve_path(p)
    candidates = [p, p.with_suffix(".exe"), p.parent / "Release" / p.name,
                  p.parent / "Release" / (p.name + ".exe")]
    for c in candidates:
        if c.is_file():
            return c
    return None


# ---------- text normalisation ----------
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
URDU_RE = re.compile(r"[؀-ۿ]")

UR2LAT = {
    "ب": "b", "پ": "p", "ت": "t", "ٹ": "t", "ث": "s", "ج": "j", "چ": "c",
    "خ": "k", "د": "d", "ڈ": "d", "ذ": "z", "ر": "r", "ڑ": "r", "ز": "z", "ژ": "z",
    "س": "s", "ش": "s", "ص": "s", "ض": "z", "ط": "t", "ظ": "z", "غ": "g",
    "ف": "f", "ق": "k", "ک": "k", "ك": "k", "گ": "g", "ل": "l", "م": "m", "ن": "n", "ں": "n",
}
# alif, waw, ye, he, hamza, ain, haa and diacritics are treated as vowels and dropped
LAT_DROP = set("aeiouywvh")


URDU_PUNCT = str.maketrans({c: " " for c in "\u060C\u061B\u061F\u06D4\u066A\u066B\u066C\u06DD\u0640"})


def norm(text):
    return unicodedata.normalize("NFKC", text or "").translate(DIGITS).translate(URDU_PUNCT).lower()


def tokens(text):
    return re.findall(r"[a-z]+|[؀-ۿ]+|\d+", norm(text))


def skeleton(word):
    if URDU_RE.search(word):
        s = "".join(UR2LAT.get(ch, "") for ch in word)
    else:
        s = re.sub(r"[^a-z]", "", word.lower())
        for a, b in (("ph", "f"), ("ch", "C"), ("sh", "s"), ("kh", "k"), ("gh", "g"),
                     ("ck", "k"), ("x", "ks"), ("q", "k"), ("c", "k"), ("C", "c")):
            s = s.replace(a, b)
        s = "".join(ch for ch in s if ch not in LAT_DROP)
    return re.sub(r"(.)\1+", r"\1", s)


def text_skeleton(text):
    return "".join(skeleton(t) for t in tokens(text) if not t.isdigit())


def levenshtein(a, b):
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _allowed(n):
    return 0 if n <= 3 else (1 if n <= 6 else 2)


# Common words that must never be glued together into a fake drug name ("mein teen" ~ "Augmentin").
STOP = set("""mein me men teen do din se ka ki ke ko hai hain aur nahi nahin ek baar dafa goli saath raat subah ab bhi
to jab par wala wali karna kar lein piyein chamach mg saal sau hazaar din mein khane pehle baad liye dobara""".split())
STOP |= set("میں تین دو دن سے کا کی کے کو ہے ہیں اور نہیں ایک بار دفعہ گولی ساتھ رات صبح اب بھی تو جب پر والا سال سو ہزار کھانے پہلے بعد لیے دوبارہ".split())


def find_term(text, variants, max_ngram=3):
    """True if any variant of a term (e.g. a drug name) is present, in either script."""
    toks = [t for t in tokens(text) if not t.isdigit()]
    sk = [skeleton(t) for t in toks]
    stop = [t in STOP for t in toks]
    targets = []
    for v in variants:
        vs = "".join(skeleton(w) for w in tokens(v))
        if vs:
            targets.append(vs)
    for n in range(1, max_ngram + 1):
        for i in range(len(sk) - n + 1):
            if stop[i] or stop[i + n - 1]:
                continue
            window = "".join(sk[i:i + n])
            if not window:
                continue
            for vs in targets:
                tol = _allowed(len(vs))
                if abs(len(window) - len(vs)) > tol:
                    continue
                if levenshtein(window, vs) <= tol:
                    return True
    return False


NEG_LAT = {"nahi", "nahin", "nai", "nahee", "nahein", "nahi'n", "na", "no", "not", "never", "without"}
NEG_UR = {"نہیں", "نہی", "نئیں", "نا", "نہ", "نھیں", "نئی"}


def count_negations(text):
    return sum(1 for t in tokens(text) if t in NEG_LAT or t in NEG_UR)


NUM_WORDS = {
    2: ["do", "دو", "two"], 3: ["teen", "تین", "three"], 5: ["paanch", "panch", "پانچ", "five"],
    10: ["das", "دس", "ten"], 20: ["bees", "بیس", "twenty"], 22: ["baees", "bais", "بائیس", "twenty two"],
    26: ["chabbees", "chhabbees", "چھبیس", "twenty six"], 28: ["athaees", "athais", "اٹھائیس", "twenty eight"],
    30: ["tees", "تیس", "thirty"], 34: ["chontees", "chauntees", "چونتیس", "thirty four"],
    35: ["paintees", "پینتیس", "thirty five"], 38: ["artees", "اڑتیس", "thirty eight"],
    40: ["chalees", "chaalees", "چالیس", "forty"], 45: ["paintalees", "paintaalees", "پینتالیس", "forty five"],
    50: ["pachaas", "pachas", "پچاس", "fifty"], 55: ["pachpan", "پچپن", "fifty five"],
    60: ["saath", "ساٹھ", "sixty"], 90: ["nawway", "nabbay", "نوے", "ninety"],
    95: ["pachaanway", "pachanway", "پچانوے", "ninety five"], 100: ["sau", "سو", "hundred"],
    140: ["ek sau chalees", "ایک سو چالیس", "one forty"], 160: ["ek sau saath", "ایک سو ساٹھ", "one sixty"],
    180: ["ek sau assi", "ایک سو اسی", "one eighty"], 260: ["do sau saath", "دو سو ساٹھ", "two sixty"],
    400: ["chaar sau", "char sau", "چار سو", "four hundred"], 500: ["paanch sau", "panch sau", "پانچ سو", "five hundred"],
    625: ["chhe sau pachees", "چھ سو پچیس", "six twenty five"], 1000: ["hazaar", "hazar", "ہزار", "thousand"],
}


def find_number(text, n):
    t = norm(text)
    if str(n) in re.findall(r"\d+", t.replace(",", "")) or str(n) in re.findall(r"\d+", t):
        return True
    for w in NUM_WORDS.get(n, []):
        if URDU_RE.search(w):
            if w in t:
                return True
        elif re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t):
            return True
    return False


# ---------- references and IO ----------
def read_reference(speaker, clip):
    """Reference text, or None if missing or still marked TODO."""
    p = REFS / speaker / f"{clip}.txt"
    if not p.is_file():
        return None
    lines = p.read_text(encoding="utf-8").splitlines()
    if any(l.strip().startswith("# TODO") for l in lines):
        return None
    body = "\n".join(l for l in lines if not l.strip().startswith("#")).strip()
    return body or None


def read_manifest():
    p = DATA / "manifest.csv"
    if not p.is_file():
        raise SystemExit("data/manifest.csv not found. Run: python prepare.py")
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_csv(path, row, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow(row)


def read_csv(path):
    path = Path(path)
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def pct(x):
    return "" if x is None else f"{100 * x:.0f}%"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def quantile(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def print_table(rows, cols):
    widths = [max(len(c), *(len(str(r.get(c, ""))) for r in rows)) if rows else len(c) for c in cols]
    print("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(w) for c, w in zip(cols, widths)))

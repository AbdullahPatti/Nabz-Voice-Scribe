"""Synthetic OPD dictations in Roman Urdu, for teaching a small Whisper to write drug names in Latin script.

Each item has two texts:
  target   what the ASR should write, in the style of refs/ (Roman Urdu, drug names as in the lexicon, strengths and
           readings as digits)
  spoken   what the TTS reads (lowercase, every number as spoken Urdu words, sometimes English)

Content is generated from a small grammar: patient, complaints with durations, negated symptoms, readings,
prescriptions (drugs drawn uniformly from all of lexicon.txt, not the answer key), drugs to avoid, allergies,
tests, advice and follow-up. Any item sharing a 5-word run with a test reference (refs/) is dropped and counted, so
the test scripts never appear in training.

    python synth_dictation.py --n 6000 --out data/synth/texts.jsonl
"""
import argparse
import json
import random
import re

from nabzlib import REFS, ROOT

UNITS = ("ek do teen chaar paanch chhe saat aath nau das gyarah baarah terah chaudah pandrah solah satrah atharah "
         "unnees bees ikkees baees teyees chaubees pachees chhabbees sattaees athaees unattees tees iktees battees "
         "taintees chauntees paintees chhattees saintees artees unchalees chalees iktalees bayalees taintalees "
         "chavalees paintalees chhiyalees saintalees artalees unchaas pachaas ikyavan baavan tirpan chauvan pachpan "
         "chhappan sattavan athavan unsath saath iksath baasath tirsath chaunsath painsath chhiyasath sarsath arsath "
         "unhattar sattar ikhattar bahattar tihattar chauhattar pachhattar chhihattar sathattar athattar unnasi "
         "assi ikyasi bayasi tirasi chaurasi pachasi chhiyasi sattasi athasi nawasi nabbe ikyanve baanve tiranve "
         "chauranve pachanve chhiyanve sattanve athanve ninyanve").split()
EN = "one two three four five six seven eight nine ten eleven twelve".split()


def ur_number(n):
    if n == 0:
        return "zero"
    if n < 100:
        return UNITS[n - 1]
    if n < 1000:
        h, r = divmod(n, 100)
        return ("sau" if h == 1 and random.random() < 0.4 else UNITS[h - 1] + " sau") + (" " + ur_number(r) if r else "")
    t, r = divmod(n, 1000)
    return ("hazaar" if t == 1 and random.random() < 0.3 else ur_number(t) + " hazaar") + (" " + ur_number(r) if r else "")


def en_number(n):
    if n <= 12:
        return EN[n - 1]
    tens = "twenty thirty forty fifty sixty seventy eighty ninety".split()
    teens = "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
    if n < 20:
        return teens[n - 13]
    if n < 100:
        t, r = divmod(n, 10)
        return tens[t - 2] + (" " + EN[r - 1] if r else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return EN[h - 1] + " hundred" + (" " + en_number(r) if r else "")
    t, r = divmod(n, 1000)
    return en_number(t) + " thousand" + (" " + en_number(r) if r else "")


def speak_numbers(text, english=0.15):
    return re.sub(r"\d+", lambda m: en_number(int(m.group())) if random.random() < english else ur_number(int(m.group())), text)


SEX = [("Mard", "mard"), ("Mareez mard", "mareez mard"), ("Khatoon", "khatoon"), ("Aurat", "aurat"),
       ("Bachcha", "bachcha"), ("Bachi", "bachi"), ("Larka", "larka"), ("Larki", "larki"), ("Mareeza", "mareeza")]
SYMPTOMS = ["bukhar", "khansi", "sar dard", "pet dard", "dast", "ulti", "chakkar", "kamzori", "gala kharab", "nazla",
            "zukaam", "seene mein jalan", "kamar dard", "ghutnon mein dard", "saans phoolna", "kaan dard", "aankh lal",
            "peshab mein jalan", "kharish", "jism par daane", "bhook na lagna", "neend na aana", "jodon mein dard",
            "seene mein dard", "ghabrahat", "sujan", "balgham", "qabz", "khoon aana", "thand lagna", "pairon mein sun"]
DURATIONS = ["{n} din se", "ek hafte se", "do hafte se", "{n} mahine se", "kal raat se", "kal se", "subah se",
             "kaafi arse se", "{n} saal se"]
NEG = ["{s} nahi hai", "{s} nahi", "koi {s} nahi", "{s} bilkul nahi", "{s} bhi nahi hai", "{s} nahi ho raha"]
READINGS = [("BP {a} by {b}", (90, 190), (50, 110)), ("sugar {a}", (70, 420), None), ("temperature {a}", (97, 104), None),
            ("pulse {a}", (55, 130), None), ("oxygen {a} percent", (85, 99), None), ("weight {a} kilo", (8, 110), None),
            ("platelets {a} hazaar", (20, 400), None), ("HB {a}", (6, 15), None)]
STRENGTHS = [5, 10, 20, 25, 40, 50, 75, 100, 150, 200, 250, 400, 500, 625, 1000]
DOSES = ["ek goli", "do goli", "aadhi goli", "ek chamach", "do chamach", "ek capsule", "ek injection", "das ml",
         "paanch ml", "ek puff", "do puff", "ek sachet"]
FREQ = ["din mein ek baar", "din mein do baar", "din mein teen baar", "rozana", "subah shaam", "raat ko",
        "khane ke baad", "khali pait", "subah nahar mun", "zaroorat ke waqt", "har aath ghante baad", "jab bukhar ho"]
COURSE = ["{n} din", "ek hafta", "do hafte", "ek mahina", "teen mahine", "lagatar"]
AVOID = ["{d} nahi deni", "{d} nahi dena", "{d} bilkul nahi leni", "{d} nahi lena", "{d} band kar dein",
         "is liye {d} nahi deni", "{d} mat dein", "{d} na dein"]
ALLERGY = ["{d} se allergy hai", "{d} se reaction hota hai"]
TESTS = ["CBC karwa lein", "chest X-ray karwa lein", "urine test karwana hai", "sugar test karwa lein", "LFT karwa lein",
         "ultrasound karwa lein", "ECG karwa lein", "typhoid ka test karwa lein", "teen mahine wala sugar test karwana hai"]
ADVICE = ["paani zyada piyein", "aaram karein", "tali hui cheezein band", "namak kam karein", "cheeni band",
          "halki warzish rozana", "doodh aur dahi kam", "cigarette band karni hai", "garam paani se garare karein"]
FOLLOW = ["{n} din baad dobara aayein", "ek hafte baad dikhayein", "ek mahine baad dikhayein",
          "agar farq na pare to foran wapas aayein", "do hafte baad check up"]
EN_SENT = ["{sex} {age} years, {sym} for {n} days.", "No {sym}.", "{drug} {st} twice a day for {n} days.",
           "Do not give {drug}.", "Come back after {n} days."]


def drug_names():
    return [l.strip() for l in (ROOT / "lexicon.txt").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def item(drugs):
    r = random.random
    n = lambda a=2, b=10: str(random.randint(a, b))
    parts = []
    sex, sex_sp = random.choice(SEX)
    parts.append(f"{sex}, {random.randint(1, 85)} saal.")
    for s in random.sample(SYMPTOMS, random.randint(1, 3)):
        parts.append(f"{random.choice(DURATIONS).format(n=n())} {s} hai." if r() < 0.6 else f"{s.capitalize()} hai.")
    for s in random.sample(SYMPTOMS, random.choice([0, 1, 1, 2])):
        parts.append(random.choice(NEG).format(s=s).capitalize() + ".")
    if r() < 0.5:
        t, ra, rb = random.choice(READINGS)
        parts.append(t.format(a=random.randint(*ra), b=random.randint(*rb) if rb else "").strip() + ".")
    picked = random.sample(drugs, random.randint(1, 4))
    rx, rest = picked[: max(1, len(picked) - (1 if r() < 0.4 else 0))], picked
    for d in rx:
        st = f" {random.choice(STRENGTHS)}" if r() < 0.6 else ""
        parts.append(f"{d}{st} {random.choice(DOSES)} {random.choice(FREQ)}" +
                     (f", {random.choice(COURSE).format(n=n(3, 14))}" if r() < 0.6 else "") + ".")
    if len(rest) > len(rx):
        parts.append(random.choice(AVOID).format(d=rest[-1]).capitalize().replace(rest[-1].capitalize(), rest[-1]) + ".")
    if r() < 0.15:
        parts.append(random.choice(ALLERGY).format(d=random.choice(drugs)) + ".")
    if r() < 0.4:
        parts.append(random.choice(TESTS).capitalize() + ".")
    if r() < 0.4:
        parts.append(random.choice(ADVICE).capitalize() + ".")
    if r() < 0.6:
        parts.append(random.choice(FOLLOW).format(n=n(3, 15)).capitalize() + ".")
    if r() < 0.12:  # an English sentence, as some speakers switch
        parts.insert(random.randint(1, len(parts)), random.choice(EN_SENT).format(
            sex=random.choice(["Man", "Woman", "Child"]), age=random.randint(2, 80), sym=random.choice(["fever", "cough", "pain"]),
            n=random.randint(2, 10), drug=random.choice(drugs), st=random.choice(STRENGTHS)))
    target = " ".join(s[0].upper() + s[1:] for s in parts)
    spoken = speak_numbers(target).lower()
    return {"target": target, "spoken": spoken}


def ref_ngrams(n=5):
    grams = set()
    for p in REFS.glob("*/*.txt"):
        toks = re.findall(r"[a-z]+", "\n".join(l for l in p.read_text(encoding="utf-8").splitlines()
                                                 if not l.startswith("#")).lower())
        grams |= {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}
    return grams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", default="data/synth/texts.jsonl")
    args = ap.parse_args()
    random.seed(args.seed)
    drugs, grams = drug_names(), ref_ngrams()
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    kept = dropped = 0
    with out.open("w", encoding="utf-8") as f:
        while kept < args.n:
            it = item(drugs)
            toks = re.findall(r"[a-z]+", it["target"].lower())
            if any(tuple(toks[i:i + 5]) in grams for i in range(len(toks) - 4)):
                dropped += 1
                continue
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
            kept += 1
    print(f"wrote {kept} items to {out.relative_to(ROOT)}; dropped {dropped} that shared a 5-word run with refs/")


if __name__ == "__main__":
    main()

"""Negation guard: a medicine the transcript says NOT to give must never reach the doctor as prescribed.

For every medicine in a note, find where it was said in the transcript (either script, same fuzzy match as
drug_check.py). If a negation word ("nahi", "نہیں", "mat", ...) follows it within the same clause, the guard
moves it from "prescribed" to "avoid - doctor must confirm". It runs after the LLM, needs no model, and is meant
to be ported as-is to the phone app.

It cannot help when the speech step lost the "nahi" altogether; that still needs better ASR.

    python negation_guard.py               # all runs under results/notes/
    python negation_guard.py --window 4    # how many words after the drug may hold the negation
    python negation_guard.py --selftest

Writes results/negation_guard.csv (one row per medicine) and prints a summary per run. Does not change notes.
"""
import argparse
import json
import re

from nabzlib import (NEG_LAT, NEG_UR, RESULTS, STOP, _allowed, find_term, levenshtein, load_key,
                     print_table, skeleton, tokens, write_csv)

FIELDS = ["run", "speaker", "clip", "name", "truth", "said", "guarded", "evidence"]

# "na" alone is too common in Roman Urdu ("kha na", "na ho"), so only these Latin forms count here.
NEG = (NEG_LAT - {"na", "no", "not", "never", "without"}) | {"mat", "matt", "na-dein"} | NEG_UR
# Urdu sentence and clause marks, plus Latin ones: a negation in the next clause belongs to something else.
CLAUSE = re.compile(r"[.,;:!?\n،؛؟۔]")


def spans(text, name, max_ngram=3):
    """Token spans (start, end) in `text` that match drug `name` (mirrors nabzlib.find_term)."""
    toks = [t for t in tokens(text) if not t.isdigit()]
    sk = [skeleton(t) for t in toks]
    target = "".join(skeleton(w) for w in tokens(name))
    if not target:
        return toks, []
    tol, out = _allowed(len(target)), []
    for n in range(1, max_ngram + 1):
        for i in range(len(sk) - n + 1):
            if toks[i] in STOP or toks[i + n - 1] in STOP:
                continue
            w = "".join(sk[i:i + n])
            if w and abs(len(w) - len(target)) <= tol and levenshtein(w, target) <= tol:
                out.append((i, i + n))
    return toks, out


def negated(transcript, name, window=4):
    """(said, negated, evidence). Negated if a negation word follows the drug within `window` words, same clause."""
    said, evidence = False, ""
    # split on the raw text: norm() turns Urdu punctuation into spaces
    for clause in CLAUSE.split(transcript or ""):
        toks, found = spans(clause, name)
        for i, j in found:
            said = True
            after = toks[j:j + window]
            if any(t in NEG for t in after):
                return True, True, " ".join(toks[i:j + window])
            evidence = evidence or " ".join(toks[i:j + window])
    return said, False, evidence


def selftest():
    assert negated("Penicillin se allergy hai, is liye Augmentin nahi deni.", "Augmentin")[1]
    # Hadi dict_10, Whisper base: the name is garbled ("کو منتن") but still close enough, and the "nahi" survived
    assert negated("پینے سرن سے لڑی ہے ایسلیوں کو منتن نہیں دینی", "Augmentin")[1]
    # Merab dict_10, Whisper base: the "nahi" itself is garbled ("نیویںی"), so no guard can catch it
    assert not negated("پینیسیلین سے ایلرجی ہے اسی اگوینٹن نیویںی، زرٹیک آدی گولی", "Augmentin")[1]
    assert negated("Brufen bilkul nahi leni, Panadol do goli", "Brufen", window=4)[1]
    assert not negated("Brufen bilkul nahi leni, Panadol do goli", "Panadol")[1]  # negation is in the other clause
    assert not negated("Azomax 500 rozana ek goli, saat din. Ulti nahi hai.", "Azomax")[1]
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--window", type=int, default=4)
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    key = load_key()
    rows = []
    for path in sorted((RESULTS / "notes").glob("*/*/*.json")):
        run, sp, clip = path.parent.parent.name, path.parent.name, path.stem
        rec = json.loads(path.read_text(encoding="utf-8"))
        k = key["clips"].get(clip)
        for m in (rec.get("note") or {}).get("medications") or []:
            name = m.get("name") or ""
            said, guarded, ev = negated(rec.get("transcript", ""), name, args.window)
            match = lambda names: any(find_term(name, key["drugs"].get(a, [a])) for a in names)
            truth = "" if not k else ("prescribed" if match([x["name"] for x in k["meds"]])
                                      else "AVOID" if match(k["avoid"]) else "wrong")
            rows.append({"run": run, "speaker": sp, "clip": clip, "name": name, "truth": truth,
                         "said": said, "guarded": guarded, "evidence": ev})
    write_csv(RESULTS / "negation_guard.csv", rows, FIELDS)
    summary = []
    for run in sorted({r["run"] for r in rows}):
        rs = [r for r in rows if r["run"] == run]
        c = lambda t, g: sum(1 for r in rs if r["truth"] == t and r["guarded"] == g)
        summary.append({"run": run, "avoid_listed": c("AVOID", True) + c("AVOID", False), "avoid_caught": c("AVOID", True),
                        "avoid_left": c("AVOID", False), "prescribed_listed": c("prescribed", True) + c("prescribed", False),
                        "prescribed_moved": c("prescribed", True), "wrong_moved": c("wrong", True)})
    print_table(summary, list(summary[0]))
    print("\navoid_left: an avoided drug still shown as prescribed (safety error the guard missed).")
    print("prescribed_moved: a correct medicine sent to the doctor to confirm (a false alarm, not a safety error).")


if __name__ == "__main__":
    main()

"""Step 6. Check every medicine in every note against the drug lexicon and the transcript.

A medicine passes only if (1) it is a registered drug (close match in lexicon.txt) and (2) something close to
it was actually said in the transcript. Anything else is flagged for the doctor, never silently kept or dropped.
This catches invented drugs and brand-to-generic swaps ("Brufen" written as "Ibuprofen").
It cannot catch an avoided drug whose "nahi" the speech step dropped: that is a negation error upstream.

    python drug_check.py              # all runs under results/notes/
    python drug_check.py --selftest

Writes results/drug_check.csv (one row per medicine) and prints a summary per run.
"""
import argparse
import json

from nabzlib import RESULTS, ROOT, find_term, load_key, print_table, skeleton, tokens, write_csv

FIELDS = ["run", "speaker", "clip", "name", "in_lexicon", "said", "flagged", "truth"]


def load_lexicon(path=ROOT / "lexicon.txt"):
    names = [l.strip() for l in path.read_text(encoding="utf-8").splitlines()]
    return {s for s in ("".join(skeleton(w) for w in tokens(n)) for n in names if n and not n.startswith("#")) if s}


def in_lexicon(name, lex):
    # exact skeleton match: the LLM writes Latin script, and with DRAP's ~72k brands almost any
    # invented name is one edit from a real one, so fuzzy matching here would pass everything
    return "".join(skeleton(w) for w in tokens(name)) in lex


def check(name, transcript, lex):
    """(in_lexicon, said, flagged)"""
    lx = in_lexicon(name, lex)
    said = find_term(transcript, [name])
    return lx, said, not (lx and said)


def selftest():
    lex = load_lexicon()
    assert check("Panadol", "پر اندال دو گولی دن میں تین بار", lex) == (True, True, False)
    assert check("Paracetamol", "پر اندال دو گولی دن میں تین بار", lex)[2]  # real drug, never said
    assert check("Exomix", "ایکسو مکس دو گولی", lex)[2]  # said, but not a drug
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        return selftest()
    key, lex = load_key(), load_lexicon()
    rows = []
    for path in sorted((RESULTS / "notes").glob("*/*/*.json")):
        run, sp, clip = path.parent.parent.name, path.parent.name, path.stem
        rec = json.loads(path.read_text(encoding="utf-8"))
        k = key["clips"].get(clip)
        for m in (rec.get("note") or {}).get("medications") or []:
            name = m.get("name") or ""
            lx, said, flagged = check(name, rec.get("transcript", ""), lex)
            match = lambda names: any(find_term(name, key["drugs"].get(a, [a])) for a in names)
            truth = "" if not k else ("prescribed" if match([x["name"] for x in k["meds"]])
                                      else "AVOID" if match(k["avoid"]) else "wrong")
            rows.append({"run": run, "speaker": sp, "clip": clip, "name": name, "in_lexicon": lx,
                         "said": said, "flagged": flagged, "truth": truth})
    write_csv(RESULTS / "drug_check.csv", rows, FIELDS)
    summary = []
    for run in sorted({r["run"] for r in rows}):
        rs = [r for r in rows if r["run"] == run]
        count = lambda t, f: sum(1 for r in rs if r["truth"] == t and r["flagged"] == f)
        summary.append({"run": run, "right_passed": count("prescribed", False), "right_flagged": count("prescribed", True),
                        "wrong_flagged": count("wrong", True), "wrong_passed": count("wrong", False),
                        "avoid_passed": count("AVOID", False), "avoid_flagged": count("AVOID", True)})
    print_table(summary, list(summary[0]))
    print("\nwrong_passed and avoid_passed reach the doctor unflagged: each one is a safety error.")


if __name__ == "__main__":
    main()

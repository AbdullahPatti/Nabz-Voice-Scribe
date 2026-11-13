"""Tables for RUN_NOTES from the score files, split by speaker group (dev = Hadi, test = Merab + Nouman).

Reads results/asr_scores.csv, note_scores.csv, drug_check.csv, asr_confidence.csv and the transcripts. Writes
nothing except what it prints (and results/crosscheck.csv for `crosscheck`). It does not score anything itself:
run score_asr.py, score_note.py and drug_check.py first. Definitions follow the tables of the A4000 run and were
checked against results/a4000_snapshot/ (same numbers as RUN_NOTES for the runs that are in the snapshot):

  right / wrong   medicines in the notes whose truth in drug_check.csv is "prescribed" / "wrong", flagged or not
  unflagged       wrong medicines that drug_check.py passed
  cross-check     a medicine is also flagged when the witness transcript (plain base on the same audio) has nothing
                  that sounds like it (nabzlib.find_term, the fuzzy cross-script matcher)

    python rerun_tables.py asr   --group dev  --tags hf_base_ur hf_base_ur_bias1_cg ...
    python rerun_tables.py e2e   --group test --runs hf_base_ur__qwen35-4b-iq3m-cap ... [--witness hf_base_ur]
    python rerun_tables.py choose                 # Rule 1 of NEXT_STEPS.md, on Hadi
    python rerun_tables.py confidence --tag hf_synth-full-s250_ur
    python rerun_tables.py crosscheck --tag hf_synth-full-s250_ur --witness hf_base_ur

Checkpoint choice (`choose`), fixed on 13 Nov 2026 before any fine-tuned model of this run existed. Candidates: every
fine-tuned checkpoint with notes on Hadi from the phone note writer (run hf_<ckpt>_ur__qwen35-4b-iq3m-cap).
Safety first: fewest avoid_violations. Then the most medicines in the note (med_recall). Ties on med_recall: fewer
wrong medicines unflagged, then fewer negation flips, then higher neg_recall.
"""
import argparse
import re

from nabzlib import RESULTS, ROOT, find_term, find_terms, mean, pct, print_table, read_csv, read_reference, write_csv

GROUPS = {"dev": ["hadi"], "test": ["merab-haroon", "nouman-tanveer"],
          "all": ["hadi", "merab-haroon", "nouman-tanveer"]}
NOTE_TAG = "qwen35-4b-iq3m-cap"


def f(v):
    return float(v) if v not in ("", None) else None


def md(rows, cols):
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")


def asr_row(tag, speakers, scores):
    rows = [s for s in scores if s["tag"] == tag and s["speaker"] in speakers]
    if not rows:
        return None
    latin = 0
    for s in rows:
        p = RESULTS / "asr" / tag / s["speaker"] / f"{s['clip']}.txt"
        if p.is_file():
            latin += len(re.findall(r"[A-Za-z]+", p.read_text(encoding="utf-8", errors="replace")))
    return {"tag": tag, "clips": len(rows),
            "drug_recall": pct(mean([f(s["drug_recall"]) for s in rows])),
            "number_recall": pct(mean([f(s["number_recall"]) for s in rows])),
            "neg_kept": pct(mean([f(s["neg_kept"]) for s in rows])),
            "neg_extra": sum(int(s["neg_extra"] or 0) for s in rows),
            "drugs_inserted": sum(len(s["drugs_inserted"].split()) for s in rows),
            "sker": pct(mean([f(s["sker"]) for s in rows])), "latin_words": latin}


def e2e_row(run, speakers, note_scores, checks, witness=None):
    rows = [s for s in note_scores if s["run"] == run and s["speaker"] in speakers]
    if not rows:
        return None
    ch = [c for c in checks if c["run"] == run and c["speaker"] in speakers]
    right = [c for c in ch if c["truth"] == "prescribed"]
    wrong = [c for c in ch if c["truth"] == "wrong"]
    out = {"run": run, "notes": len(rows),
           "schema_valid": pct(sum(s["schema_valid"] == "True" for s in rows) / len(rows)),
           "med_recall": pct(mean([f(s["med_recall"]) for s in rows])),
           "strength": pct(mean([f(s["strength_recall"]) for s in rows])),
           "neg_recall": pct(mean([f(s["neg_recall"]) for s in rows])),
           "neg_flips": sum(int(s["neg_flips"] or 0) for s in rows),
           "avoid_violations": sum(int(s["avoid_violations"] or 0) for s in rows),
           "extra_meds": sum(int(s["extra_meds"] or 0) for s in rows),
           "right / wrong": f"{len(right)} / {len(wrong)}" + (f" ({pct(len(right) / (len(right) + len(wrong)))})" if ch else ""),
           "unflagged": sum(c["flagged"] == "False" for c in wrong),
           "avoid_passed": sum(c["truth"] == "AVOID" and c["flagged"] == "False" for c in ch),
           "_med": mean([f(s["med_recall"]) for s in rows]) or 0, "_neg": mean([f(s["neg_recall"]) for s in rows]) or 0}
    if witness:
        def heard(c):
            p = RESULTS / "asr" / witness / c["speaker"] / f"{c['clip']}.txt"
            return p.is_file() and find_term(p.read_text(encoding="utf-8", errors="replace"), [c["name"]])
        flag = lambda c: c["flagged"] == "True" or not heard(c)
        out["cross-check: wrong unflagged"] = sum(not flag(c) for c in wrong)
        out["right flagged"] = f"{sum(flag(c) for c in right)} / {len(right)}"
    return out


def auc(pos, neg):
    """P(score of a said drug > score of an invented drug), ties count half."""
    if not pos or not neg:
        return None
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["asr", "e2e", "choose", "confidence", "crosscheck"])
    ap.add_argument("--group", default="all", choices=list(GROUPS))
    ap.add_argument("--tags", nargs="+")
    ap.add_argument("--runs", nargs="+")
    ap.add_argument("--tag")
    ap.add_argument("--witness")
    args = ap.parse_args()
    sp = GROUPS[args.group]

    if args.what == "asr":
        scores = read_csv(RESULTS / "asr_scores.csv")
        rows = [r for r in (asr_row(t, sp, scores) for t in args.tags) if r]
        md(rows, ["tag", "clips", "drug_recall", "number_recall", "neg_kept", "neg_extra", "drugs_inserted", "sker", "latin_words"])

    elif args.what in ("e2e", "choose"):
        ns, ch = read_csv(RESULTS / "note_scores.csv"), read_csv(RESULTS / "drug_check.csv")
        cols = ["run", "notes", "schema_valid", "med_recall", "strength", "neg_recall", "neg_flips", "avoid_violations",
                "extra_meds", "right / wrong", "unflagged", "avoid_passed"]
        if args.what == "e2e":
            rows = [r for r in (e2e_row(run, sp, ns, ch, args.witness) for run in args.runs) if r]
            md(rows, cols + (["cross-check: wrong unflagged", "right flagged"] if args.witness else []))
            return
        runs = sorted({s["run"] for s in ns if s["run"].endswith("__" + NOTE_TAG) and s["run"].startswith("hf_synth-")})
        rows = [r for r in (e2e_row(run, GROUPS["dev"], ns, ch) for run in runs) if r]
        rows.sort(key=lambda r: (r["avoid_violations"], -round(r["_med"], 6), r["unflagged"], r["neg_flips"], -r["_neg"]))
        base = e2e_row("hf_base_ur__" + NOTE_TAG, GROUPS["dev"], ns, ch)
        md(rows + ([base] if base else []), cols)
        if rows:
            print(f"\nchosen by Rule 1: {rows[0]['run'].split('__')[0]}")
            if base:
                better = (rows[0]["avoid_violations"], -rows[0]["_med"]) < (base["avoid_violations"], -base["_med"])
                print("better than stock base end to end on Hadi: " + ("yes" if better else "NO"))

    elif args.what == "confidence":
        rows = [r for r in read_csv(RESULTS / "asr_confidence.csv") if r["tag"] == args.tag]
        out = []
        dev = [r for r in rows if r["speaker"] in GROUPS["dev"]]
        said_dev = sorted(float(r["min_p"]) for r in dev if r["said"] == "True")
        # cut-off fixed on Hadi: the largest threshold that flags at most 1 in 5 of the drugs that were said
        k = len(said_dev) // 5
        thr = said_dev[k] if said_dev else 0.0  # flag when min_p < thr: flags exactly the k lowest said drugs
        for g in ("dev", "test"):
            rs = [r for r in rows if r["speaker"] in GROUPS[g]]
            said = [r for r in rs if r["said"] == "True"]
            inv = [r for r in rs if r["said"] != "True"]
            a1 = auc([float(r["min_p"]) for r in said], [float(r["min_p"]) for r in inv])
            a2 = auc([float(r["mean_p"]) for r in said], [float(r["mean_p"]) for r in inv])
            out.append({"group": g, "written": len(rs), "said": len(said), "invented": len(inv),
                        "AUC min_p": "" if a1 is None else f"{a1:.2f}", "AUC mean_p": "" if a2 is None else f"{a2:.2f}",
                        f"invented flagged (min_p < {thr:.4f})": f"{sum(float(r['min_p']) < thr for r in inv)} / {len(inv)}",
                        "said flagged": f"{sum(float(r['min_p']) < thr for r in said)} / {len(said)}"})
        md(out, list(out[0]))

    elif args.what == "crosscheck":
        # units are the drug occurrences of asr_confidence.csv (every drug the fine-tuned model wrote out)
        rows = [r for r in read_csv(RESULTS / "asr_confidence.csv") if r["tag"] == args.tag]
        detail, out = [], []
        for r in rows:
            p = RESULTS / "asr" / args.witness / r["speaker"] / f"{r['clip']}.txt"
            heard = p.is_file() and find_term(p.read_text(encoding="utf-8", errors="replace"), [r["drug"]])
            detail.append({"tag": args.tag, "witness": args.witness, "speaker": r["speaker"], "clip": r["clip"],
                           "drug": r["drug"], "said": r["said"], "flagged": not heard})
        path = RESULTS / "crosscheck.csv"
        old = [d for d in read_csv(path) if not (d["tag"] == args.tag and d["witness"] == args.witness)]
        write_csv(path, old + detail, ["tag", "witness", "speaker", "clip", "drug", "said", "flagged"])
        for g in ("dev", "test"):
            ds = [d for d in detail if d["speaker"] in GROUPS[g]]
            inv = [d for d in ds if d["said"] != "True"]
            said = [d for d in ds if d["said"] == "True"]
            out.append({"written by " + args.tag: g, "invented drugs flagged": f"{sum(d['flagged'] for d in inv)} / {len(inv)}",
                        "said drugs flagged": f"{sum(d['flagged'] for d in said)} / {len(said)}"})
        md(out, list(out[0]))


if __name__ == "__main__":
    main()

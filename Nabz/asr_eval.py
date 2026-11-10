"""Per-speaker ASR scores plus drug insertions, for tuning on one speaker and testing on the others.

    python asr_eval.py --tags hf_base_ur hf_base_ur_bias4 --speakers hadi
    python asr_eval.py --tags hf_base_ur hf_base_ur_bias4 --speakers merab-haroon nouman-tanveer

Reads results/asr_scores.csv (run score_asr.py first). inserted_drugs counts lexicon names written in Latin script in
the transcript that are not among the clip's key drugs (prescribed, avoided or allergies): invented by biasing.
"""
import argparse
import re

from nabzlib import RESULTS, find_term, load_key, mean, pct, print_table, read_csv
from asr_bias import lexicon_names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", required=True)
    ap.add_argument("--speakers", nargs="+")
    args = ap.parse_args()
    key, names = load_key(), lexicon_names()
    rows = [r for r in read_csv(RESULTS / "asr_scores.csv") if r["tag"] in args.tags
            and (not args.speakers or r["speaker"] in args.speakers)]
    f = lambda v: float(v) if v not in ("", None) else None
    out = []
    for tag in args.tags:
        rs = [r for r in rows if r["tag"] == tag]
        ins = latin = 0
        for r in rs:
            k = key["clips"].get(r["clip"])
            hyp = (RESULTS / "asr" / tag / r["speaker"] / f"{r['clip']}.txt").read_text(encoding="utf-8")
            latin += len(re.findall(r"[A-Za-z]{3,}", hyp))
            truth = ([m["name"] for m in k["meds"]] + k["avoid"] + k["allergies"]) if k else []
            for n in names:
                if re.search(r"(?<![A-Za-z])" + re.escape(n) + r"(?![A-Za-z])", hyp, re.I) and not any(
                        find_term(n, key["drugs"].get(t, [t])) for t in truth):
                    ins += 1
        out.append({"tag": tag, "clips": len(rs), "drug_recall": pct(mean([f(r["drug_recall"]) for r in rs])),
                    "number_recall": pct(mean([f(r["number_recall"]) for r in rs])),
                    "neg_kept": pct(mean([f(r["neg_kept"]) for r in rs])), "sker": pct(mean([f(r["sker"]) for r in rs])),
                    "latin_words": latin, "inserted_drugs": ins})
    print_table(out, list(out[0]))


if __name__ == "__main__":
    main()

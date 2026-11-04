"""Step 3. Score every transcript against the answer key and references.

    python score_asr.py

Per clip: drug names found, numbers found, negations kept, and SkER (consonant-skeleton
error rate, a rough script-independent error rate). Writes results/asr_scores.csv and
results/asr_summary.csv, and prints the summary sorted by drug recall.
"""
from nabzlib import (RESULTS, count_negations, find_number, find_term, levenshtein, load_config,
                     load_key, mean, pct, print_table, quantile, read_csv, read_reference,
                     text_skeleton, write_csv)

SCORE_FIELDS = ["tag", "speaker", "clip", "type", "audio_s", "proc_s", "rtf", "peak_rss_mb",
                "drug_recall", "drugs_missed", "number_recall", "numbers_missed", "neg_ref", "neg_hyp",
                "neg_kept", "sker"]
SUM_FIELDS = ["tag", "clips", "rtf_median", "dict_proc_p90_s", "peak_ram_mb", "drug_recall",
              "number_recall", "neg_kept", "sker", "within_budget"]


def main():
    key = load_key()
    budget = load_config()["budgets"]["asr_seconds_per_dictation_p90"]
    runs = {}
    for r in read_csv(RESULTS / "asr_runs.csv"):
        runs[(r["tag"], r["speaker"], r["clip"])] = r  # last run wins
    if not runs:
        raise SystemExit("No runs yet. Run: python run_asr.py")

    scores = []
    for (tag, sp, clip), r in sorted(runs.items()):
        p = RESULTS / "asr" / tag / sp / f"{clip}.txt"
        if r["returncode"] != "0" or not p.is_file():
            continue
        hyp = p.read_text(encoding="utf-8", errors="replace")
        ref = read_reference(sp, clip)
        k = key["clips"].get(clip)
        row = {f: r.get(f, "") for f in ("tag", "speaker", "clip", "type", "audio_s", "proc_s", "rtf", "peak_rss_mb")}
        if k:
            terms = [m["name"] for m in k["meds"]] + k["avoid"] + k["allergies"]
            found = [t for t in terms if find_term(hyp, key["drugs"].get(t, [t]))]
            row["drug_recall"] = round(len(found) / len(terms), 3) if terms else ""
            row["drugs_missed"] = " ".join(t for t in terms if t not in found)
            nums = k["numbers"]
            nf = [n for n in nums if find_number(hyp, n)]
            row["number_recall"] = round(len(nf) / len(nums), 3) if nums else ""
            row["numbers_missed"] = " ".join(str(n) for n in nums if n not in nf)
        if ref:
            nr, nh = count_negations(ref), count_negations(hyp)
            row["neg_ref"], row["neg_hyp"] = nr, nh
            row["neg_kept"] = round(min(nr, nh) / nr, 3) if nr else ""
            rs, hs = text_skeleton(ref), text_skeleton(hyp)
            row["sker"] = round(levenshtein(rs, hs) / len(rs), 3) if rs else ""
        scores.append(row)
    write_csv(RESULTS / "asr_scores.csv", scores, SCORE_FIELDS)

    f = lambda v: float(v) if v not in ("", None) else None
    summary = []
    for tag in sorted({s["tag"] for s in scores}):
        rows = [s for s in scores if s["tag"] == tag]
        dict_proc = [f(s["proc_s"]) for s in rows if s["clip"].startswith("dict_")]
        p90 = quantile(dict_proc, 0.9)
        summary.append({
            "tag": tag, "clips": len(rows),
            "rtf_median": round(quantile([f(s["rtf"]) for s in rows], 0.5) or 0, 2),
            "dict_proc_p90_s": "" if p90 is None else round(p90, 1),
            "peak_ram_mb": max((int(float(s["peak_rss_mb"])) for s in rows if s["peak_rss_mb"]), default=""),
            "drug_recall": pct(mean([f(s.get("drug_recall")) for s in rows])),
            "number_recall": pct(mean([f(s.get("number_recall")) for s in rows])),
            "neg_kept": pct(mean([f(s.get("neg_kept")) for s in rows])),
            "sker": pct(mean([f(s.get("sker")) for s in rows])),
            "within_budget": "" if p90 is None else ("yes" if p90 <= budget else "no"),
        })
    summary.sort(key=lambda s: -float((s["drug_recall"] or "0%").rstrip("%")))
    write_csv(RESULTS / "asr_summary.csv", summary, SUM_FIELDS)
    print_table(summary, SUM_FIELDS)
    print(f"\nwithin_budget = 90th-percentile processing time on dictations <= {budget}s (model already loaded).")
    print("Per-clip detail: results/asr_scores.csv (drugs_missed / numbers_missed show what broke).")


if __name__ == "__main__":
    main()

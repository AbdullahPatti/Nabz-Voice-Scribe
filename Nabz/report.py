"""Step 6. Combine both summaries into results/decision_table.md.

    python report.py
"""
from datetime import date

from nabzlib import RESULTS, read_csv


def md_table(rows, cols):
    if not rows:
        return "_No results yet._\n"
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows]
    return "\n".join(out) + "\n"


def main():
    asr = read_csv(RESULTS / "asr_summary.csv")
    note = read_csv(RESULTS / "note_summary.csv")
    speakers = sorted({r["speaker"] for r in read_csv(RESULTS / "asr_scores.csv")})
    lines = [f"# Nabz Scribe spike results ({date.today().isoformat()})", "",
             f"Speakers scored: {len(speakers)} ({', '.join(speakers)})", "",
             "## Speech to text", "",
             md_table(asr, ["tag", "clips", "rtf_median", "dict_proc_p90_s", "peak_ram_mb", "drug_recall",
                            "number_recall", "neg_kept", "sker", "within_budget"]),
             "SkER is a rough, script-independent error rate on consonant skeletons. Compare it between rows, "
             "not against published WER numbers.", "",
             "## Note writer", "",
             md_table(note, ["run", "notes", "schema_valid", "wall_median_s", "wall_p90_s", "server_ram_mb",
                             "med_recall", "strength_recall", "extra_meds", "avoid_violations", "neg_recall",
                             "neg_flips", "within_budget"]),
             "Rows with source `ref` show the LLM's own errors on clean text. Rows with an ASR tag show the whole "
             "pipeline. The gap between them is what speech recognition costs.", "",
             "## Decision rules", "",
             "- Keep the smallest speech model that is within budget and finds most drug names.",
             "- If none is within budget, drop to the next smaller model or fewer beams before touching the LLM.",
             "- Any avoid violation or negation flip on reference text is a prompt or model problem: fix it before the pilot.",
             "- Timings come from a fast laptop CPU. Rerun the chosen setting on a real old lab PC before trusting them.", ""]
    out = RESULTS / "decision_table.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

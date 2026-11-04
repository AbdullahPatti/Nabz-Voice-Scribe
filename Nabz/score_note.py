"""Step 5. Score the generated notes against the answer key.

    python score_note.py

Per note: valid JSON, medicines found, strengths right, extra medicines (misheard or invented),
avoid-list violations, negatives captured, and negation flips (a negated symptom listed as a
complaint, the most dangerous error). Writes results/note_scores.csv and results/note_summary.csv.
"""
import json

from nabzlib import (RESULTS, ROOT, find_term, load_config, load_json, load_key, mean, pct, print_table,
                     quantile, read_csv, write_csv)

try:
    import jsonschema
except ImportError:
    jsonschema = None

SCORE_FIELDS = ["run", "speaker", "clip", "wall_s", "schema_valid", "med_recall", "meds_missed", "strength_recall",
                "extra_meds", "avoid_violations", "neg_recall", "neg_flips", "flipped", "age_ok", "sex_ok"]
SUM_FIELDS = ["run", "notes", "schema_valid", "wall_median_s", "wall_p90_s", "server_ram_mb", "med_recall",
              "strength_recall", "extra_meds", "avoid_violations", "neg_recall", "neg_flips", "within_budget"]


def digits(s):
    return "".join(ch for ch in str(s or "") if ch.isdigit())


def main():
    key = load_key()
    schema = load_json(ROOT / "note_schema.json")
    budget = load_config()["budgets"]["note_seconds_p90"]
    runs = {(r["source"] + "__" + r["model_tag"], r["speaker"], r["clip"]): r for r in read_csv(RESULTS / "note_runs.csv")}
    scores = []
    for path in sorted((RESULTS / "notes").glob("*/*/*.json")):
        run, sp, clip = path.parent.parent.name, path.parent.name, path.stem
        k = key["clips"].get(clip)
        rec = json.loads(path.read_text(encoding="utf-8"))
        note = rec.get("note")
        row = {"run": run, "speaker": sp, "clip": clip, "wall_s": runs.get((run, sp, clip), {}).get("wall_s", "")}
        valid = note is not None
        if valid and jsonschema:
            try:
                jsonschema.validate(note, schema)
            except jsonschema.ValidationError:
                valid = False
        row["schema_valid"] = valid
        if not k or note is None:
            scores.append(row)
            continue
        meds = note.get("medications") or []
        names = [m.get("name") or "" for m in meds]
        key_meds = k["meds"]
        hit, strength_ok, strength_n = [], 0, 0
        for km in key_meds:
            variants = key["drugs"].get(km["name"], [km["name"]])
            match = next((m for m in meds if find_term(m.get("name") or "", variants)), None)
            if match:
                hit.append(km["name"])
            if km.get("strength"):
                strength_n += 1
                if match and digits(km["strength"]) and digits(km["strength"]) in digits(
                        f"{match.get('strength')} {match.get('dose')} {match.get('name')}"):
                    strength_ok += 1
        row["med_recall"] = round(len(hit) / len(key_meds), 3) if key_meds else ""
        row["meds_missed"] = " ".join(m["name"] for m in key_meds if m["name"] not in hit)
        row["strength_recall"] = round(strength_ok / strength_n, 3) if strength_n else ""
        allowed = [m["name"] for m in key_meds]
        extra = [n for n in names if not any(find_term(n, key["drugs"].get(a, [a])) for a in allowed)]
        row["extra_meds"] = len(extra)
        row["avoid_violations"] = sum(1 for a in k["avoid"] if any(find_term(n, key["drugs"].get(a, [a])) for n in names))
        neg_text = " ".join(note.get("negatives") or []).lower()
        comp_text = " ".join((c.get("symptom") or "") for c in (note.get("complaints") or [])).lower()
        got, flips = 0, []
        for ng in k["negated"]:
            if any(w in neg_text for w in ng["keywords"]):
                got += 1
            if any(w in comp_text for w in ng["keywords"]):
                flips.append(ng["concept"])
        row["neg_recall"] = round(got / len(k["negated"]), 3) if k["negated"] else ""
        row["neg_flips"] = len(flips)
        row["flipped"] = "; ".join(flips)
        pt = note.get("patient") or {}
        row["age_ok"] = pt.get("age_years") == k["age"]
        row["sex_ok"] = pt.get("sex") == k["sex"]
        scores.append(row)
    if not scores:
        raise SystemExit("No notes yet. Run: python run_note.py ...")
    write_csv(RESULTS / "note_scores.csv", scores, SCORE_FIELDS)

    f = lambda v: float(v) if v not in ("", None) else None
    ram = {}
    for r in read_csv(RESULTS / "note_runs.csv"):
        if r["server_rss_mb"]:
            key_ = r["source"] + "__" + r["model_tag"]
            ram[key_] = max(ram.get(key_, 0), int(float(r["server_rss_mb"])))
    summary = []
    for run in sorted({s["run"] for s in scores}):
        rows = [s for s in scores if s["run"] == run]
        walls = [f(s["wall_s"]) for s in rows]
        p90 = quantile(walls, 0.9)
        summary.append({
            "run": run, "notes": len(rows),
            "schema_valid": pct(sum(1 for s in rows if s["schema_valid"]) / len(rows)),
            "wall_median_s": round(quantile(walls, 0.5) or 0, 1), "wall_p90_s": "" if p90 is None else round(p90, 1),
            "server_ram_mb": ram.get(run, ""),
            "med_recall": pct(mean([f(s.get("med_recall")) for s in rows])),
            "strength_recall": pct(mean([f(s.get("strength_recall")) for s in rows])),
            "extra_meds": sum(int(s.get("extra_meds") or 0) for s in rows),
            "avoid_violations": sum(int(s.get("avoid_violations") or 0) for s in rows),
            "neg_recall": pct(mean([f(s.get("neg_recall")) for s in rows])),
            "neg_flips": sum(int(s.get("neg_flips") or 0) for s in rows),
            "within_budget": "" if p90 is None else ("yes" if p90 <= budget else "no"),
        })
    write_csv(RESULTS / "note_summary.csv", summary, SUM_FIELDS)
    print_table(summary, SUM_FIELDS)
    print("\nextra_meds, avoid_violations and neg_flips are counts across all notes: each one is a safety error.")
    print("Per-note detail: results/note_scores.csv. Read the flipped ones in results/notes/ yourself.")


if __name__ == "__main__":
    main()

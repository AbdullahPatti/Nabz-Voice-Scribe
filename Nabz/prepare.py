"""Step 1. Unpack every recording-kit zip in recordings/ and build the manifest.

    python prepare.py            # unpack new zips, write data/manifest.csv and reference stubs
    python prepare.py --force    # re-extract audio even if already unpacked

Creates:
    data/<speaker>/<clip>.wav, data/<speaker>/metadata.json
    data/manifest.csv            one row per clip
    refs/<speaker>/<clip>.txt    reference transcripts (never overwritten once created)
"""
import argparse
import json
import re
import zipfile
from pathlib import Path

from nabzlib import DATA, REFS, ROOT, write_csv

SAFE_AUDIO = re.compile(r"^audio/([a-z0-9_]+)\.wav$")
FIELDS = ["speaker", "clip", "type", "optional", "wav", "duration_s", "speaker_note",
          "gender", "age_range", "home_language", "background_noise", "device", "zip"]


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s or "speaker"


def reference_stub(rec):
    t = rec.get("type")
    lines = [f"# Reference transcript for {rec['id']}.wav ({rec.get('title', '')})",
             "# Lines starting with # are ignored. Write what was actually said, in Roman Urdu."]
    if t == "dictation" and rec.get("script"):
        if rec.get("speaker_note"):
            lines.append(f"# TODO speaker said they changed words: {rec['speaker_note']}")
            lines.append("# Fix the text below to match the audio, then delete the TODO line.")
        lines.append(rec["script"])
    elif t == "free_dictation":
        lines.append("# TODO listen and type exactly what was said, then delete this line.")
        lines.append("# Facts shown to the speaker: " + "; ".join(rec.get("facts") or []))
    else:
        lines.append("# TODO listen and type what was said (rough is fine for visits), then delete this line.")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    zips = sorted((ROOT / "recordings").glob("*.zip"))
    if not zips:
        raise SystemExit("Put the zips you received into the recordings/ folder first.")

    rows, todo, seen = [], [], {}
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            meta_names = [n for n in zf.namelist() if n.endswith("metadata.json")]
            if not meta_names:
                print(f"skip {z.name}: no metadata.json inside")
                continue
            meta_name = meta_names[0]
            root = meta_name[: -len("metadata.json")]
            meta = json.loads(zf.read(meta_name).decode("utf-8"))
            sp = meta.get("speaker", {})
            slug = slugify(sp.get("name_or_code"))
            if slug in seen and seen[slug] != z.name:
                slug = f"{slug}-{len(seen)}"
            seen[slug] = z.name
            dest = DATA / slug
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

            for rec in meta.get("recordings", []):
                m = SAFE_AUDIO.match(rec.get("file", ""))
                if not m:
                    print(f"  skip unexpected file name {rec.get('file')!r}")
                    continue
                clip = m.group(1)
                wav = dest / f"{clip}.wav"
                if args.force or not wav.exists():
                    wav.write_bytes(zf.read(root + rec["file"]))
                rows.append({
                    "speaker": slug, "clip": clip, "type": rec.get("type"), "optional": rec.get("optional", False),
                    "wav": str(wav.relative_to(ROOT)), "duration_s": rec.get("duration_s"),
                    "speaker_note": rec.get("speaker_note", ""), "gender": sp.get("gender", ""),
                    "age_range": sp.get("age_range", ""), "home_language": sp.get("home_language", ""),
                    "background_noise": sp.get("background_noise", ""),
                    "device": (meta.get("device") or {}).get("model_reported", ""), "zip": z.name,
                })
                ref = REFS / slug / f"{clip}.txt"
                if not ref.exists():
                    ref.parent.mkdir(parents=True, exist_ok=True)
                    ref.write_text(reference_stub({**rec, "id": clip}), encoding="utf-8")
                if "# TODO" in ref.read_text(encoding="utf-8"):
                    todo.append(str(ref.relative_to(ROOT)))
            print(f"{z.name}: speaker '{slug}', {len(meta.get('recordings', []))} clips")

    write_csv(DATA / "manifest.csv", rows, FIELDS)
    speakers = sorted({r["speaker"] for r in rows})
    total = sum(float(r["duration_s"] or 0) for r in rows)
    print(f"\n{len(speakers)} speakers, {len(rows)} clips, {total / 60:.1f} min of audio -> data/manifest.csv")
    if todo:
        print(f"\n{len(todo)} reference transcripts still need you (marked # TODO):")
        for t in todo:
            print("  ", t)
        print("Timing runs work without them; accuracy scores skip a clip until its TODO line is gone.")


if __name__ == "__main__":
    main()

"""Step 2. Run whisper.cpp over every clip for each setting in the grid.

    python run_asr.py                         # grid from config.json
    python run_asr.py --models small-q8 --langs ur --threads 2 4
    python run_asr.py --limit 3               # quick smoke test
    python run_asr.py --force                 # re-run clips that already have output

Writes results/asr/<tag>/<speaker>/<clip>.txt and appends timings to results/asr_runs.csv.
Tag = <build>_<model>_<lang>_t<threads>. Re-running skips finished clips, so it can be stopped and resumed.
"""
import argparse
import re
import subprocess
import time
from pathlib import Path

import psutil

from nabzlib import RESULTS, ROOT, append_csv, load_config, read_manifest, resolve_binary, resolve_path

FIELDS = ["tag", "build", "model", "lang", "threads", "speaker", "clip", "type", "audio_s",
          "wall_s", "load_s", "proc_s", "rtf", "peak_rss_mb", "returncode"]


def run_one(cmd, log_path):
    peak = 0
    t0 = time.perf_counter()
    with open(log_path, "w", encoding="utf-8", errors="replace") as log:
        p = psutil.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        while p.poll() is None:
            try:
                rss = p.memory_info().rss
                for c in p.children(recursive=True):
                    rss += c.memory_info().rss
                peak = max(peak, rss)
            except psutil.Error:
                pass
            time.sleep(0.05)
    wall = time.perf_counter() - t0
    text = log_path.read_text(encoding="utf-8", errors="replace")
    load = re.search(r"load time =\s*([\d.]+) ms", text)
    total = re.search(r"total time =\s*([\d.]+) ms", text)
    load_s = float(load.group(1)) / 1000 if load else None
    proc_s = (float(total.group(1)) - float(load.group(1))) / 1000 if (load and total) else None
    return p.returncode, wall, load_s, proc_s, peak / 1048576


def main():
    cfg = load_config()["whisper"]
    g = cfg["grid"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--builds", nargs="+", default=g["builds"])
    ap.add_argument("--models", nargs="+", default=g["models"])
    ap.add_argument("--langs", nargs="+", default=g["langs"])
    ap.add_argument("--threads", nargs="+", type=int, default=g["threads"])
    ap.add_argument("--speakers", nargs="+")
    ap.add_argument("--clips", nargs="+", help="clip ids or prefixes, e.g. dict own_01")
    ap.add_argument("--include-visits", action="store_true", help="also run the long conv_ clips")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--prompt", help="text file passed to whisper --prompt (e.g. prompts/whisper_drugs.txt); tag gets _<file stem>")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    clips = read_manifest()
    if args.speakers:
        clips = [c for c in clips if c["speaker"] in args.speakers]
    if args.clips:
        clips = [c for c in clips if any(c["clip"].startswith(p) for p in args.clips)]
    if not args.include_visits:
        clips = [c for c in clips if not c["clip"].startswith("conv_")]
    if args.limit:
        clips = clips[: args.limit]

    for build in args.builds:
        binary = resolve_binary(cfg["builds"][build])
        if not binary:
            raise SystemExit(f"whisper-cli for build '{build}' not found at {cfg['builds'][build]}. See README step 2.")
        for model in args.models:
            mpath = resolve_path(cfg["models"][model])
            if not mpath.is_file():
                raise SystemExit(f"Model '{model}' not found at {mpath}. See README step 3.")
            for lang in args.langs:
                for th in args.threads:
                    tag = f"{build}_{model}_{lang}_t{th}" + ("_" + Path(args.prompt).stem if args.prompt else "")
                    prompt = ["--prompt", (ROOT / args.prompt).read_text(encoding="utf-8").strip()] if args.prompt else []
                    done = 0
                    for c in clips:
                        out_dir = RESULTS / "asr" / tag / c["speaker"]
                        out_dir.mkdir(parents=True, exist_ok=True)
                        base = out_dir / c["clip"]
                        if base.with_suffix(".txt").exists() and not args.force:
                            continue
                        cmd = [str(binary), "-m", str(mpath), "-f", str(ROOT / c["wav"]), "-t", str(th),
                               "-l", lang, "-nt", "-otxt", "-of", str(base), *prompt, *cfg.get("extra_args", [])]
                        rc, wall, load_s, proc_s, peak = run_one(cmd, base.with_suffix(".log"))
                        audio_s = float(c["duration_s"] or 0)
                        rtf = (proc_s or wall) / audio_s if audio_s else None
                        append_csv(RESULTS / "asr_runs.csv", {
                            "tag": tag, "build": build, "model": model, "lang": lang, "threads": th,
                            "speaker": c["speaker"], "clip": c["clip"], "type": c["type"], "audio_s": audio_s,
                            "wall_s": round(wall, 2), "load_s": None if load_s is None else round(load_s, 2),
                            "proc_s": None if proc_s is None else round(proc_s, 2),
                            "rtf": None if rtf is None else round(rtf, 3), "peak_rss_mb": round(peak),
                            "returncode": rc}, FIELDS)
                        done += 1
                        flag = "" if rc == 0 else f"  FAILED (see {base.with_suffix('.log').name})"
                        print(f"[{tag}] {c['speaker']}/{c['clip']}  audio {audio_s:.0f}s  "
                              f"proc {proc_s if proc_s is not None else wall:.1f}s  RAM {peak:.0f} MB{flag}")
                    print(f"[{tag}] {done} clips run")


if __name__ == "__main__":
    main()

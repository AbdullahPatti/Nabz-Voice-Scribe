"""Driver for the note-writer runs of the rerun (NEXT_STEPS.md, Step 1). One llama-server at a time.

For each job: start llama-server with the model (every layer on the GPU), wait for it, call run_note.py for each
(source, tag), stop the server. run_note.py is unchanged and skips notes already written, so this can be rerun.
A run whose folder already holds all its notes is skipped without loading the model. A source with no transcripts
yet is skipped.

    python rerun_notes.py urdu          # plan.txt steps 4-5: five Q4_K_M models on ref and avx2_base-q8_ur_t4
    python rerun_notes.py phone         # phone-tier models: plain, -dry, -cap, -hints
    python rerun_notes.py e2e-dev       # phone note writer on every hf_* checkpoint's Hadi transcripts
    python rerun_notes.py e2e-test --sources hf_base_ur hf_synth-full-s250_ur   # test speakers, chosen checkpoint
    python rerun_notes.py --list        # print the commands without running

Server:  llama.cpp/build/bin/llama-server -m models/<file> -ngl 99 -c 4096 --jinja --port 8080 [--dry-multiplier 0.8]
Notes:   python run_note.py --source <source> --model-tag <tag> --timeout 300 [--schema ...] [--hints --prompt ...]
"""
import argparse
import subprocess
import sys
import time
import urllib.request

from nabzlib import RESULTS, ROOT, read_manifest, read_reference

SERVER = ROOT / "llama.cpp/build/bin/llama-server.exe"
if not SERVER.is_file():
    SERVER = ROOT / "llama.cpp/build/bin/llama-server"
URL = "http://127.0.0.1:8080/v1/models"

CAP = ["--schema", "note_schema_capped.json"]
HINTS = CAP + ["--hints", "--prompt", "note_system_hints.txt"]
REF, BASE, SMALL = "ref", "avx2_base-q8_ur_t4", "avx2_small-q8_ur_t2"
DEV, TEST = ["hadi"], ["merab-haroon", "nouman-tanveer"]

Q4B = "Qwen_Qwen3.5-4B-Q4_K_M.gguf"
Q2B = "Qwen_Qwen3.5-2B-Q4_K_M.gguf"
Q08B = "Qwen_Qwen3.5-0.8B-Q4_K_M.gguf"
IQ3M = "Qwen_Qwen3.5-4B-IQ3_M.gguf"
ALIF3 = "Alif-1.0-3B-Instruct-Q4_K_M.gguf"
DRY = ["--dry-multiplier", "0.8"]


def runs(tag, sources, extra=(), speakers=None):
    return [(s, tag, list(extra), speakers) for s in sources]


def jobs_for(stage, sources):
    """[(gguf, server_args, [(source, tag, run_note args, speakers)])]"""
    if stage == "urdu":
        return [
            (Q4B, [], runs("qwen35-4b", [BASE])),  # ref__qwen35-4b exists (cloud run)
            ("model-Q4_K_M.gguf", [], runs("alif-8b", [REF, BASE])),
            (ALIF3, [], runs("alif-3b", [REF, BASE])),
            ("Qalb-1.0-8B-Instruct.Q4_K_M.gguf", [], runs("qalb-8b", [REF, BASE])),
            ("shaheen_v1_q4_k_m.gguf", [], runs("shaheen-7b", [REF, BASE])),
        ]
    if stage == "phone":
        return [
            (Q08B, [], runs("qwen35-0.8b", [REF, BASE]) + runs("qwen35-0.8b-cap", [REF, BASE], CAP)),
            (Q08B, DRY, runs("qwen35-0.8b-dry", [REF, BASE])),
            (Q2B, [], runs("qwen35-2b", [REF, BASE]) + runs("qwen35-2b-cap", [REF, BASE], CAP)),
            (Q2B, DRY, runs("qwen35-2b-dry", [REF, BASE])),
            (Q4B, [], runs("qwen35-4b-cap", [REF, BASE, SMALL], CAP) + runs("qwen35-4b-hints", [REF, BASE, SMALL], HINTS)),
            (Q4B, DRY, runs("qwen35-4b-dry", [REF, BASE])),
            (ALIF3, [], runs("alif-3b-cap", [REF, BASE], CAP)),
            (ALIF3, DRY, runs("alif-3b-dry", [REF, BASE])),
            (IQ3M, [], runs("qwen35-4b-iq3m-cap", [REF, BASE, SMALL], CAP)
             + runs("qwen35-4b-iq3m-hints", [REF, BASE, SMALL], HINTS)),
        ]
    if stage in ("e2e-dev", "e2e-test"):
        sp = DEV if stage == "e2e-dev" else TEST
        src = sources or sorted(p.name for p in (RESULTS / "asr").iterdir() if p.name.startswith("hf_")
                                and "_bias" not in p.name and p.name != "hf_small_ur")
        rs = runs("qwen35-4b-iq3m-cap", src, CAP, sp)
        rs += runs("qwen35-4b-iq3m-hints", [s for s in src if s == "hf_base_ur"], HINTS, sp)
        return [(IQ3M, [], rs)]
    if stage == "phone-pair":  # whisper.cpp transcripts of the converted checkpoint, all three speakers
        src = sources or sorted(p.name for p in (RESULTS / "asr").iterdir() if p.name.startswith("avx2_ft-"))
        return [(IQ3M, [], runs("qwen35-4b-iq3m-cap", src, CAP))]
    raise SystemExit(f"unknown stage {stage}")


def wanted(source, speakers):
    """Clips run_note.py would write for this source."""
    out = []
    for c in read_manifest():
        if c["clip"].startswith("conv_") or (speakers and c["speaker"] not in speakers):
            continue
        if source == "ref":
            ok = bool(read_reference(c["speaker"], c["clip"]))
        else:
            p = RESULTS / "asr" / source / c["speaker"] / f"{c['clip']}.txt"
            ok = p.is_file() and bool(p.read_text(encoding="utf-8", errors="replace").strip())
        if ok:
            out.append(c)
    return out


def missing(source, tag, speakers):
    return [c for c in wanted(source, speakers)
            if not (RESULTS / "notes" / f"{source}__{tag}" / c["speaker"] / f"{c['clip']}.json").exists()]


def server_up():
    try:
        urllib.request.urlopen(URL, timeout=3)
        return True
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="*")
    ap.add_argument("--sources", nargs="+")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    for stage in args.stage or ["urdu", "phone"]:
        for gguf, sargs, rs in jobs_for(stage, args.sources):
            todo = [(s, t, x, sp) for s, t, x, sp in rs if missing(s, t, sp)]
            scmd = [str(SERVER), "-m", str(ROOT / "models" / gguf), "-ngl", "99", "-c", "4096", "--jinja", "--port", "8080", *sargs]
            if args.list:
                print(" ".join(scmd[3:]) if False else f"SERVER {gguf} {' '.join(sargs)}")
                for s, t, x, sp in rs:
                    print(f"   run_note.py --source {s} --model-tag {t} --timeout 300 {' '.join(x)}"
                          + (f" --speakers {' '.join(sp)}" if sp else "") + ("" if (s, t, x, sp) in todo else "   [complete]"))
                continue
            if not todo:
                print(f"== {gguf} {' '.join(sargs)}: all runs complete, skipped", flush=True)
                continue
            if not (ROOT / "models" / gguf).is_file():
                print(f"== {gguf}: MODEL FILE MISSING, job skipped", flush=True)
                continue
            if server_up():
                raise SystemExit("port 8080 is already in use; stop that server first")
            tag0 = todo[0][1]
            log = open(ROOT / f"llama-{tag0}.log", "w", encoding="utf-8", errors="replace")
            print(f"== starting {gguf} {' '.join(sargs)}", flush=True)
            srv = subprocess.Popen(scmd, stdout=log, stderr=subprocess.STDOUT)
            try:
                t0 = time.time()
                while not server_up():
                    if srv.poll() is not None or time.time() - t0 > 180:
                        print(f"== {gguf}: SERVER DID NOT START (see llama-{tag0}.log)", flush=True)
                        break
                    time.sleep(2)
                else:
                    for s, t, x, sp in todo:
                        cmd = [sys.executable, "-u", str(ROOT / "run_note.py"), "--source", s, "--model-tag", t,
                               "--timeout", "300", *x, *((["--speakers", *sp]) if sp else [])]
                        print("-- " + " ".join(cmd[2:]), flush=True)
                        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
                        lines = (out.stdout + out.stderr).strip().splitlines()
                        bad = [l for l in lines if "INVALID JSON" in l or "error" in l.lower() or "skipped" in l]
                        print(f"   {lines[-1] if lines else '(no output)'}; {len(bad)} invalid/error lines; "
                              f"{len(missing(s, t, sp))} still missing", flush=True)
                        for l in bad[:3]:
                            print("     " + l[:200], flush=True)
            finally:
                srv.terminate()
                try:
                    srv.wait(30)
                except subprocess.TimeoutExpired:
                    srv.kill()
                log.close()
                t0 = time.time()
                while server_up() and time.time() - t0 < 60:
                    time.sleep(1)


if __name__ == "__main__":
    main()

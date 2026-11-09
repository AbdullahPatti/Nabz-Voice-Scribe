"""Step 4. Turn transcripts into structured notes with a local LLM (llama.cpp server).

Start the server first, in another terminal (4 threads mimics a modest PC):
    llama.cpp/build/bin/llama-server -m models/gemma-4-E2B-it-Q4_0.gguf -t 4 -c 4096 --port 8080

Then:
    python run_note.py --source ref --model-tag gemma4-e2b-q4          # your reference transcripts: the LLM's own errors
    python run_note.py --source avx2_small-q8_ur_t4 --model-tag gemma4-e2b-q4   # real ASR output: whole-pipeline errors

Writes results/notes/<source>__<model-tag>/<speaker>/<clip>.json and appends to results/note_runs.csv.
"""
import argparse
import json
import time
import urllib.error
import urllib.request

import psutil

from nabzlib import RESULTS, ROOT, append_csv, load_config, load_json, read_manifest, read_reference

FIELDS = ["source", "model_tag", "speaker", "clip", "type", "input_chars", "wall_s", "prompt_tokens",
          "gen_tokens", "prompt_ms", "gen_ms", "json_parsed", "server_rss_mb"]


def post(url, payload, timeout=900):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def server_rss_mb():
    total = 0
    for p in psutil.process_iter(["name"]):
        try:
            if p.info["name"] and "llama-server" in p.info["name"]:
                total += p.memory_info().rss
        except psutil.Error:
            pass
    return round(total / 1048576) if total else ""


def main():
    cfg = load_config()["llm"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="'ref' or an ASR tag such as avx2_small-q8_ur_t4")
    ap.add_argument("--model-tag", required=True, help="a short name for the LLM you loaded, for the results table")
    ap.add_argument("--speakers", nargs="+")
    ap.add_argument("--clips", nargs="+")
    ap.add_argument("--include-visits", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--url", help="server to use instead of config, e.g. http://127.0.0.1:11434 for Ollama")
    ap.add_argument("--model", help="model name the server needs (Ollama), e.g. qwen2.5:7b")
    ap.add_argument("--prompt", default="note_system.txt", help="system prompt file under prompts/")
    ap.add_argument("--schema", default="note_schema.json",
                    help="JSON schema the server enforces, e.g. note_schema_capped.json (lists capped at 10 items)")
    ap.add_argument("--timeout", type=int, default=900, help="seconds to wait for one note (raise on slow CPUs)")
    args = ap.parse_args()

    url = (args.url or cfg["server_url"]).rstrip("/")
    try:
        urllib.request.urlopen(url + "/v1/models", timeout=5)
    except (urllib.error.URLError, OSError):
        raise SystemExit(f"No llama-server answering at {url}. Start it first (see the top of this file).")

    system = (ROOT / "prompts" / args.prompt).read_text(encoding="utf-8")
    schema = load_json(ROOT / args.schema)
    clips = read_manifest()
    if args.speakers:
        clips = [c for c in clips if c["speaker"] in args.speakers]
    if args.clips:
        clips = [c for c in clips if any(c["clip"].startswith(p) for p in args.clips)]
    if not args.include_visits:
        clips = [c for c in clips if not c["clip"].startswith("conv_")]
    if args.limit:
        clips = clips[: args.limit]

    out_root = RESULTS / "notes" / f"{args.source}__{args.model_tag}"
    n = 0
    for c in clips:
        if args.source == "ref":
            text = read_reference(c["speaker"], c["clip"])
        else:
            p = RESULTS / "asr" / args.source / c["speaker"] / f"{c['clip']}.txt"
            text = p.read_text(encoding="utf-8", errors="replace").strip() if p.is_file() else None
        if not text:
            continue
        out = out_root / c["speaker"] / f"{c['clip']}.json"
        if out.exists() and not args.force:
            continue
        payload = {
            **({"model": args.model} if args.model else {}),
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": "Transcript:\n" + text}],
            "temperature": cfg.get("temperature", 0),
            "max_tokens": cfg.get("max_tokens", 800),
            "response_format": {"type": "json_schema", "json_schema": {"name": "clinical_note", "schema": schema}},
            "chat_template_kwargs": {"enable_thinking": False},
        }
        t0 = time.perf_counter()
        try:
            resp = post(url + "/v1/chat/completions", payload, timeout=args.timeout)
        except urllib.error.HTTPError as e:
            print(f"{c['speaker']}/{c['clip']}: server error {e.code}: {e.read()[:300]!r}")
            continue
        except (TimeoutError, OSError) as e:
            print(f"{c['speaker']}/{c['clip']}: no answer within {args.timeout}s ({e}); skipped")
            continue
        wall = time.perf_counter() - t0
        content = resp["choices"][0]["message"].get("content") or ""
        try:
            note, parsed = json.loads(content), True
        except json.JSONDecodeError:
            note, parsed = None, False
        timings = resp.get("timings", {})
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"transcript": text, "raw": content, "note": note, "timings": timings},
                                  indent=2, ensure_ascii=False), encoding="utf-8")
        append_csv(RESULTS / "note_runs.csv", {
            "source": args.source, "model_tag": args.model_tag, "speaker": c["speaker"], "clip": c["clip"],
            "type": c["type"], "input_chars": len(text), "wall_s": round(wall, 2),
            "prompt_tokens": timings.get("prompt_n", ""), "gen_tokens": timings.get("predicted_n", ""),
            "prompt_ms": round(timings.get("prompt_ms", 0)), "gen_ms": round(timings.get("predicted_ms", 0)),
            "json_parsed": parsed, "server_rss_mb": server_rss_mb()}, FIELDS)
        n += 1
        print(f"{c['speaker']}/{c['clip']}: {wall:.1f}s  {'ok' if parsed else 'INVALID JSON'}")
    print(f"{n} notes written to {out_root.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

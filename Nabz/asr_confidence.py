"""Whisper's own confidence on every drug name it wrote, to catch drugs the ASR invented.

drug_check.py cannot catch those: a drug the ASR wrote is "said" by construction. Here each transcript is scored
again against its audio by teacher forcing (decoding-agnostic: beam search and temperature fallback don't matter),
and every drug name in it (written out, by nabzlib.written_drug_windows) gets the lowest
probability of its tokens. Clips over 30 s are scored per segment, using Whisper's own long-form segments.

    python asr_confidence.py --model checkpoints/synth-full-s250 --tag hf_synth-full-s250_ur

Writes results/asr_confidence.csv (one row per drug occurrence; no transcript text) with said = whether the
reference contains that drug (the same fuzzy matcher score_asr.py uses).
"""
import argparse

import torch

from nabzlib import RESULTS, ROOT, find_terms, read_csv, read_reference, tokens, write_csv, written_drug_windows
from run_asr_hf import Transcriber, load_audio, select_clips

FIELDS = ["tag", "speaker", "clip", "drug", "min_p", "mean_p", "said"]
SR = 16000


def lexicon():
    return [l.strip() for l in (ROOT / "lexicon.txt").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


@torch.inference_mode()
def word_probs(t, audio, text):
    """[(word, [token probs])] for text spoken in audio (<= 30 s)."""
    tok = t.proc.tokenizer
    feats = t.proc(audio, sampling_rate=SR, return_tensors="pt").input_features.to(t.device, torch.float16)
    prefix = tok.convert_tokens_to_ids(["<|startoftranscript|>", "<|ur|>", "<|transcribe|>", "<|notimestamps|>"])
    ids = tok.encode(" " + text.strip(), add_special_tokens=False)
    dec = torch.tensor([prefix + ids], device=t.device)
    logits = t.model(input_features=feats, decoder_input_ids=dec[:, :-1]).logits.float()
    p = logits.softmax(-1)[0, len(prefix) - 1:, :].gather(1, torch.tensor(ids, device=t.device)[:, None])[:, 0].tolist()
    words = []
    for i, tid in zip(ids, p):
        piece = tok.convert_ids_to_tokens(i)
        if piece.startswith("Ġ") or not words:
            words.append([tok.convert_tokens_to_string([piece]).strip(), [tid]])
        else:
            words[-1][0] += tok.convert_tokens_to_string([piece])
            words[-1][1].append(tid)
    return words


def segments(t, audio):
    """Whisper's own long-form segments [(start_s, end_s, text)] for a clip over 30 s."""
    f = t.proc(audio, sampling_rate=SR, return_tensors="pt", return_attention_mask=True, truncation=False, padding="longest")
    torch.manual_seed(0)  # as run_asr_hf.run, so the text matches the saved transcript
    out = t.model.generate(f.input_features.to(t.device, torch.float16), attention_mask=f.attention_mask.to(t.device),
                           task="transcribe", language="ur", num_beams=5, max_new_tokens=440,
                           temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0), compression_ratio_threshold=1.35,
                           logprob_threshold=-1.0, return_timestamps=True, return_dict_in_generate=True)
    return [(float(s["start"]), float(s["end"]), t.proc.tokenizer.decode(s["tokens"], skip_special_tokens=True))
            for s in out["segments"][0]]


def drug_hits(words, names):
    """[(drug, [token probs])] for every drug name written out in the words (nabzlib.written_drug_windows)."""
    toks, owner = [], []  # text tokens, and the Whisper word each came from
    for k, (w, _) in enumerate(words):
        for t in tokens(w):
            toks.append(t)
            owner.append(k)
    hits = []
    for i, n, name in written_drug_windows(toks, names):
        ks = sorted(set(owner[i:i + n]))
        hits.append((name, [p for k in ks for p in words[k][1]]))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", required=True, help="the ASR tag whose transcripts to score")
    ap.add_argument("--speakers", nargs="+")
    args = ap.parse_args()
    names = lexicon()
    t = Transcriber(args.model, "ur")
    out_path = RESULTS / "asr_confidence.csv"
    rows = [r for r in read_csv(out_path) if r["tag"] != args.tag] if out_path.is_file() else []
    mismatch = 0
    for c in select_clips(args.speakers):
        p = RESULTS / "asr" / args.tag / c["speaker"] / f"{c['clip']}.txt"
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8").strip()
        audio = load_audio(ROOT / c["wav"])
        if len(audio) <= 30 * SR:
            parts = [(audio, text)]
        else:
            segs = segments(t, audio)
            if " ".join(s[2].strip() for s in segs).split() != text.split():
                mismatch += 1  # still usable: the segments are the model's own decoding of this clip
            parts = [(audio[int(a * SR):int(b * SR) + SR // 4], s) for a, b, s in segs if s.strip()]
        said = find_terms(read_reference(c["speaker"], c["clip"]) or "", names)
        for a, s in parts:
            for drug, ps in drug_hits(word_probs(t, a, s), names):
                rows.append({"tag": args.tag, "speaker": c["speaker"], "clip": c["clip"], "drug": drug,
                             "min_p": round(min(ps), 4), "mean_p": round(sum(ps) / len(ps), 4), "said": drug in said})
    write_csv(out_path, rows, FIELDS)
    n = [r for r in rows if r["tag"] == args.tag]
    print(f"[{args.tag}] {len(n)} drug occurrences, {sum(str(r['said']) == 'True' for r in n)} said; "
          f"{mismatch} long clips whose segments differ from the saved text")


if __name__ == "__main__":
    main()

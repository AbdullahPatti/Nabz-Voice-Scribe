"""Speech to text with Hugging Face Whisper on the GPU, for research runs (decoding methods, fine-tuned checkpoints).

whisper.cpp stays the runtime for the phone. This script exists because decoding experiments (contextual biasing)
and fine-tuned checkpoints are much easier to build and test in PyTorch; anything that works is then ported.
Timings from this script are desktop-GPU timings and say nothing about phones.

    python run_asr_hf.py --model openai/whisper-base --lang ur
    python run_asr_hf.py --model openai/whisper-small --lang ur
    python run_asr_hf.py --model checkpoints/xyz --lang ur --tag-suffix ft1

Writes results/asr/hf_<name>_<lang>[_<suffix>]/<speaker>/<clip>.txt and appends to results/asr_runs.csv,
so score_asr.py scores it like any whisper.cpp run.
"""
import argparse
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from nabzlib import RESULTS, ROOT, append_csv, read_manifest

FIELDS = ["tag", "build", "model", "lang", "threads", "speaker", "clip", "type", "audio_s",
          "wall_s", "load_s", "proc_s", "rtf", "peak_rss_mb", "returncode"]


def load_audio(path):
    a, sr = sf.read(path, dtype="float32", always_2d=True)
    a = a.mean(axis=1)
    if sr != 16000:
        import librosa
        a = librosa.resample(a, orig_sr=sr, target_sr=16000)
    return a.astype(np.float32)


class Transcriber:
    def __init__(self, model, lang, device="cuda", logits_processor_factory=None):
        self.proc = WhisperProcessor.from_pretrained(model)
        self.model = WhisperForConditionalGeneration.from_pretrained(model, torch_dtype=torch.float16).to(device).eval()
        self.lang, self.device, self.lpf = lang, device, logits_processor_factory

    @torch.inference_mode()
    def __call__(self, audio):
        # truncation=False: the feature extractor otherwise cuts every clip to 30 s, so the long-form branch
        # below never ran and the end of longer clips was silently dropped (runs before 10 Nov 2026)
        long = len(audio) > 30 * 16000
        feats = self.proc(audio, sampling_rate=16000, return_tensors="pt", return_attention_mask=True,
                          **(dict(truncation=False, padding="longest") if long else {}))
        # like whisper.cpp's defaults: beam 5, and re-decode at higher temperature when the output looks like a
        # repetition loop (compression ratio) or is low-confidence. Plain greedy loops on half the clips.
        kw = dict(task="transcribe", num_beams=5, max_new_tokens=440, temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
                  compression_ratio_threshold=1.35, logprob_threshold=-1.0)
        if self.lang != "auto":
            kw["language"] = self.lang
        if self.lpf:
            kw["logits_processor"] = self.lpf(self.proc.tokenizer)
        inp = feats.input_features.to(self.device, torch.float16)
        if inp.shape[-1] > 3000:  # long-form: the generate() path handles > 30 s with timestamps
            kw.update(return_timestamps=True, attention_mask=feats.attention_mask.to(self.device))
        ids = self.model.generate(inp, **kw)
        return self.proc.batch_decode(ids, skip_special_tokens=True)[0].strip()


def run(transcriber, tag, model_name, lang, clips, force=False):
    done = 0
    for c in clips:
        out = RESULTS / "asr" / tag / c["speaker"] / f"{c['clip']}.txt"
        if out.exists() and not force:
            continue
        audio = load_audio(ROOT / c["wav"])
        torch.manual_seed(0)  # temperature fallback samples; seed it so reruns give the same text
        t0 = time.perf_counter()
        text = transcriber(audio)
        wall = time.perf_counter() - t0
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        audio_s = len(audio) / 16000
        append_csv(RESULTS / "asr_runs.csv", {
            "tag": tag, "build": "hf-gpu", "model": model_name, "lang": lang, "threads": "", "speaker": c["speaker"],
            "clip": c["clip"], "type": c["type"], "audio_s": round(audio_s, 2), "wall_s": round(wall, 2), "load_s": "",
            "proc_s": round(wall, 2), "rtf": round(wall / audio_s, 3) if audio_s else "", "peak_rss_mb": "",
            "returncode": 0}, FIELDS)
        done += 1
    print(f"[{tag}] {done} clips transcribed")


def select_clips(speakers=None, include_visits=False):
    clips = read_manifest()
    if speakers:
        clips = [c for c in clips if c["speaker"] in speakers]
    if not include_visits:
        clips = [c for c in clips if not c["clip"].startswith("conv_")]
    return clips


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/whisper-base")
    ap.add_argument("--lang", default="ur", help="ur, en, or auto")
    ap.add_argument("--tag-suffix", default="")
    ap.add_argument("--bias", type=float, help="lexicon contextual-biasing strength (asr_bias.py), e.g. 2.0")
    ap.add_argument("--speakers", nargs="+")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    name = Path(args.model).name.replace("whisper-", "")
    tag = f"hf_{name}_{args.lang}" + (f"_bias{args.bias:g}" if args.bias else "") + (f"_{args.tag_suffix}" if args.tag_suffix else "")
    lpf = None
    if args.bias:
        from asr_bias import factory
        lpf = factory(args.bias)
    run(Transcriber(args.model, args.lang, logits_processor_factory=lpf), tag, args.model, args.lang,
        select_clips(args.speakers), args.force)


if __name__ == "__main__":
    main()

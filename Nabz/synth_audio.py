"""Render synthetic dictations (synth_dictation.py) to speech with MMS-TTS Urdu (Latin script), on the GPU.

Each item gets a random speaking rate and VITS noise scales, so durations and prosody vary. There is one voice:
speaker variety comes from augmentation at training time (train_whisper.py). Items over 28 s are skipped.

    python synth_audio.py --texts data/synth/texts.jsonl --out data/synth
"""
import argparse
import json
import random

import soundfile as sf
import torch
from transformers import AutoTokenizer, VitsModel

from nabzlib import ROOT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--texts", default="data/synth/texts.jsonl")
    ap.add_argument("--out", default="data/synth")
    ap.add_argument("--model", default="facebook/mms-tts-urd-script_latin")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    tok = AutoTokenizer.from_pretrained(args.model)
    model = VitsModel.from_pretrained(args.model).cuda().eval()
    sr = model.config.sampling_rate
    out = ROOT / args.out
    (out / "wav").mkdir(parents=True, exist_ok=True)
    items = [json.loads(l) for l in (ROOT / args.texts).read_text(encoding="utf-8").splitlines()]
    kept = 0
    with (out / "manifest.jsonl").open("w", encoding="utf-8") as man:
        for i, it in enumerate(items):
            model.speaking_rate = random.uniform(0.85, 1.2)
            model.noise_scale = random.uniform(0.45, 0.9)
            model.noise_scale_duration = random.uniform(0.6, 1.0)
            with torch.no_grad():
                w = model(**tok(it["spoken"], return_tensors="pt").to("cuda")).waveform[0].float().cpu().numpy()
            dur = len(w) / sr
            if dur > 28:
                continue
            path = out / "wav" / f"{i:05d}.wav"
            sf.write(path, w, sr)
            man.write(json.dumps({"audio": str(path.relative_to(ROOT)), "text": it["target"], "duration": round(dur, 2)},
                                 ensure_ascii=False) + "\n")
            kept += 1
    print(f"rendered {kept} of {len(items)} items ({sr} Hz) into {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

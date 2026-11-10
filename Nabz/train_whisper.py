"""Fine-tune Whisper on synthetic Roman-Urdu dictations (synth_audio.py), optionally plus real clips of some speakers.

Goal: the small phone ASR writes Roman Urdu with drug names in Latin script, which the note writer reads well
(85% of medicines on reference text vs 8% on Whisper's Urdu-script output).

Defaults are chosen up front, not tuned on the real clips:
  * decoder-only training (--train-encoder for the full ablation): the task is a new output script and vocabulary,
    not new acoustics, and a frozen encoder cannot overfit to the single TTS voice;
  * on-the-fly augmentation for speaker and room variety: speed 0.85-1.15, additive noise at 5-30 dB SNR,
    random phone-mic band limits, synthetic reverb, random gain;
  * fixed step budget; the only validation is held-out synthetic speech. The real clips are test data.

    python train_whisper.py --name synth-dec                                  # synthetic only
    python train_whisper.py --name loso-hadi --real merab-haroon nouman-tanveer   # + real clips of 2 speakers
"""
import argparse
import json
import math
import random
import time

import numpy as np
import torch
import torchaudio.functional as AF
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from nabzlib import ROOT, read_manifest, read_reference
from run_asr_hf import load_audio

SR = 16000


def augment(w, rng):
    w = torch.from_numpy(w)
    if rng.random() < 0.8:  # speed perturbation (changes tempo and pitch, like a different speaker)
        # source rate rounded to 200 Hz: an arbitrary rate shares a tiny gcd with 16 kHz, which makes torchaudio
        # build a huge polyphase filter (1.8 s per clip vs 1 ms); 200 Hz steps are 1.25% speed steps
        src = round(SR * rng.uniform(0.85, 1.15) / 200) * 200
        w = AF.resample(w, src, SR)
    if rng.random() < 0.5:  # phone microphone band limits
        w = AF.highpass_biquad(w, SR, rng.uniform(80, 400))
        w = AF.lowpass_biquad(w, SR, rng.uniform(3000, 7500))
    if rng.random() < 0.3:  # small-room reverb: exponentially decaying noise as the impulse response
        n = int(SR * rng.uniform(0.08, 0.4))
        ir = torch.randn(n) * torch.exp(-torch.arange(n) / (n / rng.uniform(3, 8)))
        ir[0] = 1.0
        w = AF.fftconvolve(w, ir / ir.abs().sum() * 4)[: len(w)]
    if rng.random() < 0.7:  # background noise at a random SNR, white or brown-ish
        noise = torch.randn_like(w)
        if rng.random() < 0.5:
            noise = torch.cumsum(noise, 0)
            noise = noise - noise.mean()
        snr = rng.uniform(5, 30)
        p_s, p_n = w.pow(2).mean().clamp_min(1e-8), noise.pow(2).mean().clamp_min(1e-8)
        w = w + noise * torch.sqrt(p_s / (p_n * 10 ** (snr / 10)))
    w = w * rng.uniform(0.3, 1.0) / w.abs().max().clamp_min(1e-6)
    return w.numpy().astype(np.float32)


def load_items(real_speakers, real_repeat):
    items = [json.loads(l) for l in (ROOT / "data/synth/manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    synth = [{"audio": ROOT / i["audio"], "text": i["text"]} for i in items]
    real = []
    for c in read_manifest():
        if c["speaker"] in (real_speakers or []) and not c["clip"].startswith("conv_"):
            ref = read_reference(c["speaker"], c["clip"])
            if ref:
                real.append({"audio": ROOT / c["wav"], "text": ref})
    return synth, real * real_repeat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--base", default="openai/whisper-base")
    ap.add_argument("--lang", default="ur")
    ap.add_argument("--real", nargs="*", help="speakers whose real clips join training (never the test speaker)")
    ap.add_argument("--real-repeat", type=int, default=20)
    ap.add_argument("--train-encoder", action="store_true")
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)

    proc = WhisperProcessor.from_pretrained(args.base, language=args.lang, task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(args.base).cuda()
    model.config.forced_decoder_ids = None
    model.generation_config.forced_decoder_ids = None
    if not args.train_encoder:
        for p in model.model.encoder.parameters():
            p.requires_grad = False
    synth, real = load_items(args.real, args.real_repeat)
    rng.shuffle(synth)
    val, train = synth[:200], synth[200:] + real
    print(f"train {len(train)} items ({len(real)} real, repeated), val {len(val)} synthetic; "
          f"{'full' if args.train_encoder else 'decoder-only'}; {args.steps} steps x {args.batch}", flush=True)
    prefix = proc.tokenizer.prefix_tokens  # <|startoftranscript|><|ur|><|transcribe|><|notimestamps|>
    cache = {}

    def batch(items, aug):
        feats, labels = [], []
        for it in items:
            if it["audio"] not in cache:
                cache[it["audio"]] = load_audio(it["audio"])
            w = cache[it["audio"]]
            w = augment(w, rng) if aug else w
            feats.append(proc.feature_extractor(w, sampling_rate=SR, return_tensors="np").input_features[0])
            ids = prefix + proc.tokenizer.encode(" " + it["text"], add_special_tokens=False) + [proc.tokenizer.eos_token_id]
            labels.append(ids[:448])
        L = max(map(len, labels))
        lab = torch.full((len(labels), L), -100, dtype=torch.long)
        for i, l in enumerate(labels):
            lab[i, : len(l)] = torch.tensor(l)
        dec_in = lab[:, :-1].clone()
        dec_in[dec_in == -100] = proc.tokenizer.eos_token_id
        return (torch.tensor(np.stack(feats)).cuda(), dec_in.cuda(), lab[:, 1:].cuda())

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0.01)
    warm = max(1, args.steps // 20)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(1, s / args.steps))))
    scaler = torch.amp.GradScaler()

    def loss_on(x, d, y):
        with torch.autocast("cuda", dtype=torch.float16):
            logits = model(input_features=x, decoder_input_ids=d).logits
        return torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), y.reshape(-1), ignore_index=-100)

    @torch.no_grad()
    def validate():
        model.eval()
        ls = [loss_on(*batch(val[i:i + 32], aug=False)).item() for i in range(0, len(val), 32)]
        model.train()
        return sum(ls) / len(ls)

    model.train()
    t0, log = time.time(), []
    print(f"step 0 val_loss {validate():.3f}", flush=True)
    for step in range(1, args.steps + 1):
        loss = loss_on(*batch(rng.sample(train, args.batch), aug=True))
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(opt)
        scaler.update()
        sched.step()
        if step % 250 == 0 or step == args.steps:
            v = validate()
            log.append({"step": step, "train_loss": round(loss.item(), 4), "val_loss": round(v, 4)})
            print(f"step {step} train_loss {loss.item():.3f} val_loss {v:.3f} ({time.time() - t0:.0f}s)", flush=True)
    out = ROOT / "checkpoints" / args.name
    model.save_pretrained(out)
    proc.save_pretrained(out)
    (out / "train_args.json").write_text(json.dumps({**vars(args), "log": log}, indent=2), encoding="utf-8")
    print(f"saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

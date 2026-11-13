# Nabz Scribe: what to do on the GPU PC

Written 13 November 2026 on the Legion laptop. Claude Code on the PC: read all of this and `results/RUN_NOTES.md`,
then carry it out in order. Work inside the `Nabz` folder. Stop only where a step says STOP.

## What changed

The user has decided that recordings, reference transcripts, per-clip results and the phone model go on GitHub
(the speakers agreed). As of this commit the repository tracks:

- `recordings/*.zip` (the original kit zips), `data/<speaker>/` (unpacked clips and `metadata.json`), `refs/`,
  `results/asr/`, `results/notes/`
- `models/ft-synth-full-s250/ggml-model-q8_0.bin` (once the PC adds it; 77 MB, under GitHub's 100 MB limit)

Still **not** pushed: `checkpoints/`, the Qwen GGUF, `phone_bundle/`, `data/synth/wav/`. They are over GitHub's
100 MB file limit or re-creatable. See Step 4 for the checkpoint.

The laptop only had the older per-clip results (whisper.cpp base/small/turbo runs and the first note runs).
Everything from the A4000 runs (`results/asr/hf_*`, `ft-s250-q8`, the Urdu and phone-tier note runs,
`negation_guard.csv`) exists only on the PC and is what this file asks you to push.

## Step 0. Pull, then see which case this is

`git pull` will now bring in files the PC may already have as untracked copies (`refs/`, `data/<speaker>/`,
`results/asr/`, `results/notes/`). If git refuses because untracked files would be overwritten: copy those four
folders to a backup folder outside the repo, move the colliding files out of the way, pull, then compare the
backup with what was pulled. Copy back anything that exists only in the backup. If a file differs, keep the PC's
version only for files under `results/`; for `refs/` STOP and show the user the difference.

Then:

    ls checkpoints/synth-full-s250  models/ft-synth-full-s250  phone_bundle/nabz  data/synth

- **Case A, the files are there** (the A4000 PC, nothing wiped): skip to Step 3.
- **Case B, they are missing:** do Steps 1 and 2. The clips and references now come with the pull, so nothing has
  to be copied by hand. `data/manifest.csv` is already correct, so `prepare.py` does not need to run.

## Step 1 (Case B only). Retrain the fine-tuned Whisper base

Environment: Python 3.12, then

    python -m venv .venv            # activate it
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu126    # cu128 for RTX 50-series
    pip install -r requirements-research.txt

Train (seeds are fixed at 13 in all three scripts; run one job at a time, the trainer caches ~5 GB of audio in RAM):

    python synth_dictation.py --n 6000 --out data/synth/texts.jsonl
    python synth_audio.py --texts data/synth/texts.jsonl --out data/synth
    python train_whisper.py --name synth-full --train-encoder --save-at 250 500

`data/synth/texts.jsonl` is tracked (generated on the laptop, seed 13). `git diff` after regenerating should show
no change; if it does, say so in RUN_NOTES. The chosen checkpoint is `checkpoints/synth-full-s250`. The training
command is reconstructed from RUN_NOTES (full fine-tune, default 2000-step schedule, checkpoint saved at step 250);
the original command line was not recorded. The run can be stopped once `synth-full-s250` is saved.

Check it before going on. Expected on Merab + Nouman (RUN_NOTES, "The phone pair in whisper.cpp"): sker about 24%,
number_recall about 80%, neg_kept about 90%.

    python run_asr_hf.py --model checkpoints/synth-full-s250 --lang ur
    python run_asr_hf.py --model openai/whisper-base --lang ur
    python score_asr.py

Differences under about 10 points are noise at this sample size. If sker on the test speakers is worse than plain
base (32%), STOP and report: the retrain did not reproduce.

## Step 2 (Case B only). Convert for the phone and rebuild the bundle

1. Convert with whisper.cpp's `models/convert-h5-to-ggml.py` (repo commit d2c6f05; tokenizer files copied from
   `openai/whisper-base`), then quantize with `whisper-quantize ... q8_0`. Result:
   `models/ft-synth-full-s250/ggml-model-q8_0.bin`, about 77 MB (model `ft-s250-q8` in `config.json`).
2. Run it with whisper.cpp b5454, `-t 4 -l ur`, score, and compare with the `whisper.cpp ft-s250-q8` row in RUN_NOTES.
3. Download the note writer: `hf download bartowski/Qwen_Qwen3.5-4B-GGUF Qwen_Qwen3.5-4B-IQ3_M.gguf --local-dir models`
   (set `HF_HUB_DISABLE_XET=1` if the download stalls).
4. Build `phone_bundle/nabz/` containing:
   - `ggml-ft-s250-q8_0.bin` (the file from 1, renamed)
   - `Qwen_Qwen3.5-4B-IQ3_M.gguf`
   - `clips/` with three wavs from `data/`, one of them `merab-haroon/dict_05` (37.6 s, the worst case)
   - `phone/termux_bench.sh`

## Step 3. Phone benchmark (the user does this; full steps in `phone/README.md`)

1. Copy `phone_bundle/nabz/` to the phone's **Download** folder over USB.
2. Install **Termux from F-Droid** (not the Play Store) and run:

       termux-setup-storage
       pkg update -y
       bash ~/storage/downloads/nabz/termux_bench.sh

   Phone plugged in, screen on, other apps closed. 30 to 45 minutes, mostly compiling.
3. Copy `Download/nabz/nabz-phone-results.txt` back into `results/phone/<phone-model>.txt` (numbers only).
   Use a mid-range phone with 6 to 8 GB RAM, not a flagship; more than one phone is better.
4. Add a short section to `results/RUN_NOTES.md`: ASR seconds per dictation (fine-tuned + base), note-writer
   tokens per second, peak RAM, and whether each is within the 30 s budgets in `config.json`.

Do not wait for the phone test before Step 4.

## Step 4. Push the PC-only files

    git add results/ models/ft-synth-full-s250/ggml-model-q8_0.bin data/synth/texts.jsonl data/synth/manifest.jsonl
    git status        # check: no file over 100 MB
    git commit -m "A4000 per-clip results and the fine-tuned phone model"
    git push

Also:

- Write the names of the three clips in `phone_bundle/nabz/clips/` into `phone/README.md` step 1, so the bundle can
  be rebuilt anywhere from the repo plus the Qwen download, and commit that.
- The PyTorch checkpoint (`checkpoints/synth-full-s250`, about 290 MB) is too big for git. Zip it and attach it to
  a GitHub release (`gh release create ft-s250 synth-full-s250.zip --notes "Whisper base, synthetic fine-tune, step 250"`).
  If `gh` is not set up, tell the user to upload the zip by hand on the Releases page.

## After this

- **Record more speakers** with the same recording kit: at least one over 24 and one Punjabi-dominant. Unpack with
  `prepare.py`, then run the ASR and note runs on the new speakers only, as extra test data.
- **Correct the own-words references** (`refs/*/own_*.txt` are drafts): listen, fix, rerun the scorers.
- **Replace `lexicon.txt`** (318-entry placeholder) with the DRAP export and recheck drug hints and the cross-check.
- Then: the Android app around whisper.cpp + llama.cpp, with every medicine a one-tap confirm.

# Nabz Scribe: redo the lost GPU work on the new PC

Written 13 November 2026 on the Legion laptop. Claude Code on the PC: read all of this, `results/RUN_NOTES.md` and
`plan.txt`, then carry it out in order without asking, except where a step says STOP. Work inside the `Nabz` folder.

## Situation

All GPU work from 9 to 11 November was done on an RTX A4000 PC that is no longer reachable. Models, checkpoints,
synthetic audio, the phone bundle and every per-clip transcript and note from those runs are gone. What survives:

- the code, and `results/RUN_NOTES.md` describing each experiment and its numbers
- `results/a4000_snapshot/`: every summary table as it stood after the A4000 runs. **Never edit or regenerate it.**
- from the laptop: the recordings (`recordings/*.zip`, `data/<speaker>/`), `refs/`, and the per-clip files of the
  early runs (whisper.cpp base/small/turbo, the first Gemma/Qwen note runs)

**The user's decision: redo everything that was lost on this PC, and treat this run as the first and only one.**
The numbers from this PC are the ones the paper will report. The A4000 numbers are kept only as a comparison.
No new speakers will be recorded for now: the data is the 3 speakers, 39 scored clips.

## Rules

1. **Same protocol, decided before looking.** Hadi is the dev speaker; Merab and Nouman are test speakers. Choose
   the checkpoint on Hadi by the rule in RUN_NOTES (end-to-end medicines in the note from the phone note writer,
   safety first), then run the test speakers once with that choice. If this run picks a different checkpoint than
   `synth-full-s250`, that is the result: report it, do not steer toward the old one.
2. **Report what comes out.** Where a number differs from the snapshot by more than about 10 points, or a
   conclusion changes, say so plainly in RUN_NOTES. Do not round in the old result's favour.
3. **Same tags as before**, so tables line up with the snapshot. `results/a4000_snapshot/asr_runs.csv` and
   `note_runs.csv` list every run that existed (tag, model, source): that is the list of runs to redo. A run is
   "lost" if its folder is missing from `results/asr/` or `results/notes/`.
4. **Clean the run logs first.** Remove the rows of lost runs from `results/asr_runs.csv` and `results/note_runs.csv`
   (they stay in the snapshot), so old timings are not mixed with new ones. Keep the rows of runs whose per-clip
   files exist.
5. **One GPU job at a time.** The trainer caches about 5 GB of audio in RAM.
6. Commands are in each script's docstring and in `plan.txt`. Where RUN_NOTES does not record an exact command,
   reconstruct it from the description, and write the command you used into RUN_NOTES this time.

## Step 0. Machine and environment

    git pull
    nvidia-smi        # note GPU, driver, CUDA version for RUN_NOTES

Python 3.12, then:

    python -m venv .venv            # activate it
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu126    # cu128 for RTX 50-series
    pip install -r requirements-research.txt

Tools, pinned as before: llama.cpp **b11912** prebuilt CUDA build (`plan.txt` step 3), whisper.cpp **b5454**
prebuilt `whisper-bin-x64` plus the whisper.cpp source at commit **d2c6f05** for `convert-h5-to-ggml.py` and
`whisper-quantize`. Stock `ggml-base-q8_0.bin` and `ggml-small-q8_0.bin` go in `whisper.cpp/models/`
(from `huggingface.co/ggerganov/whisper.cpp`). Set `HF_HUB_DISABLE_XET=1` if a Hugging Face download stalls.

STOP if there is no CUDA GPU, or less than 40 GB free disk.

## Step 1. Redo the experiments, in the order of RUN_NOTES

Each item names the RUN_NOTES section to reproduce. Score after each (`score_asr.py`, `score_note.py`,
`drug_check.py`, `negation_guard.py`, `report.py`) and compare with the snapshot.

1. **"Urdu note writers on the A4000"**: follow `plan.txt` steps 4 to 6 (5 models, `ref` and `avx2_base-q8_ur_t4`).
2. **"Phone-tier note writers, schema cap, negation guard and drug-name hints"**: Qwen3.5 0.8B, 2B, 4B (Q4_K_M),
   4B IQ3_M and Alif 3B; plain, `-dry` and `-cap` variants; then the hints runs. GGUFs: `bartowski/Qwen_Qwen3.5-*-GGUF`
   (check each repo and file name exists before downloading).
3. **PyTorch Whisper parity**: `run_asr_hf.py` for `openai/whisper-base` and `openai/whisper-small`, `--lang ur`.
4. **"Lexicon biasing"** (`asr_bias.py`, Hadi only, the λ grid in the table). It was a negative result; redo it so
   the paper has per-clip evidence, but do not spend time tuning it.
5. **"Whisper base fine-tuned on synthetic Roman-Urdu dictations"**:

       python synth_dictation.py --n 6000 --out data/synth/texts.jsonl     # tracked; git diff should show no change
       python synth_audio.py --texts data/synth/texts.jsonl --out data/synth
       python train_whisper.py --name synth-dec --save-at 250 500
       python train_whisper.py --name synth-full --train-encoder --save-at 250 500

   These two commands are reconstructed (default 2000-step schedule, checkpoints at 250 and 500); the A4000 runs
   also had an interrupted second decoder-only run (`synth-dec-b`), which need not be repeated. Transcribe all
   checkpoints on Hadi with `run_asr_hf.py`.
6. **"End to end"**: phone note writer (Qwen3.5 4B IQ3_M, capped schema) on each checkpoint's Hadi transcripts;
   choose the checkpoint (Rule 1); then the test speakers once.
7. **"Catching drugs the fine-tuned ASR invents"**: `asr_confidence.py`, then the base cross-check.
8. **"The phone pair in whisper.cpp"**: convert the chosen checkpoint, quantize q8_0 to
   `models/ft-synth-full-s250/ggml-model-q8_0.bin` (rename the folder and the `config.json` entry if a different
   checkpoint was chosen), run whisper.cpp `-t 4 -l ur`, and the end-to-end table with the base-q8 witness.

The snapshot's headline to compare against (Merab + Nouman, whisper.cpp pair): 46% of medicines in the note
against 10% for stock base, 0 wrong medicines unflagged after the cross-check.

STOP and report if the fine-tuned model is no better end to end than stock base on Hadi: the central result did
not reproduce and the user must decide what to do.

## Step 2. Write up

In `results/RUN_NOTES.md`:

- Under the first A4000 heading, add one line: the per-clip files of the 9 to 11 November A4000 runs were lost;
  those sections are kept as the earlier run; the numbers of record are in the new sections below.
- Add new sections, one per item above, in the same short factual style: machine, exact commands, tables, findings.
  For each table say whether it agrees with the earlier run.
- Fix the "Gaps" list: no further speakers are planned for now, so 3 speakers (all 18 to 24, one dev speaker) is a
  stated limitation of the study, not a to-do.

## Step 3. Phone bundle and phone benchmark

Build `phone_bundle/nabz/`: the fine-tuned q8 model as `ggml-ft-s250-q8_0.bin`, `Qwen_Qwen3.5-4B-IQ3_M.gguf`,
`clips/` with three wavs from `data/` (one of them `merab-haroon/dict_05`, 37.6 s, the worst case), and
`phone/termux_bench.sh`. Write the three clip names into `phone/README.md` step 1.

Then the user does the phone test (`phone/README.md`):

1. Copy `phone_bundle/nabz/` to the phone's **Download** folder over USB.
2. Install **Termux from F-Droid** (not the Play Store) and run:

       termux-setup-storage
       pkg update -y
       bash ~/storage/downloads/nabz/termux_bench.sh

   Phone plugged in, screen on, other apps closed. 30 to 45 minutes, mostly compiling.
3. Copy `Download/nabz/nabz-phone-results.txt` into `results/phone/<phone-model>.txt` and add a RUN_NOTES section:
   ASR seconds per dictation (fine-tuned + base), note-writer tokens per second, peak RAM, and whether each is
   within the 30 s budgets in `config.json`. A mid-range phone with 6 to 8 GB RAM, not a flagship.

Do not wait for the phone test before Step 4.

## Step 4. Push

    git add results/ models/ft-synth-full-s250/ggml-model-q8_0.bin data/synth/manifest.jsonl phone/README.md
    git status        # check: no file over 100 MB
    git commit        # one commit per experiment is better than one big one
    git push

Per-clip results are tracked now, so push as you go: nothing should again exist on one machine only. The PyTorch
checkpoints (about 290 MB each) are too big for git: zip the chosen one and attach it to a GitHub release
(`gh release create ft-s250 <zip> --notes "Whisper base, synthetic fine-tune"`), or tell the user to upload it by
hand on the Releases page.

## After this

- **Correct the own-words references** (`refs/*/own_*.txt` are drafts): the user listens and fixes them, then
  rerun the scorers. Best done before the paper's final numbers.
- **Replace `lexicon.txt`** (318-entry placeholder) with the DRAP export and recheck drug hints and the cross-check.
- Then: the Android app around whisper.cpp + llama.cpp, with every medicine a one-tap confirm.

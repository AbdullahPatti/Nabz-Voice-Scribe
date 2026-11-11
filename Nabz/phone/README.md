# Measuring Nabz on an Android phone

This measures whether the chosen pipeline fits a phone before any app is built: speed and peak RAM of the three
models, on the phone's CPU, with the same whisper.cpp and llama.cpp versions as the PC runs.

| model | file | size | role |
|---|---|---|---|
| fine-tuned Whisper base, q8_0 | `ggml-ft-s250-q8_0.bin` | 78 MB | writes the transcript |
| stock Whisper base, q8_0 | `ggml-base-q8_0.bin` (the script downloads it) | 78 MB | cross-check witness |
| Qwen3.5 4B IQ3_M | `Qwen_Qwen3.5-4B-IQ3_M.gguf` | 2.48 GB | writes the note |

Use the kind of phone doctors actually carry (a mid-range Android with 6-8 GB RAM), not a flagship. Allow about
5 GB free storage and 30-45 minutes, most of it compiling.

## Steps

1. **On the PC**, the bundle is ready in `phone_bundle/nabz/` (2.4 GB: two models, three test clips, the script).
   If it is gone, ask Claude to re-stage it (it is kept out of git).
2. **Copy it to the phone** over USB: put the whole `nabz` folder in the phone's **Download** folder, so it ends
   up at `Download/nabz/`.
3. **Install Termux** from F-Droid (https://f-droid.org/packages/com.termux/). The Play Store version is outdated.
4. **Open Termux** and run, one line at a time:
   ```
   termux-setup-storage            # tap Allow; gives Termux access to Download/
   pkg update -y
   bash ~/storage/downloads/nabz/termux_bench.sh
   ```
   Keep the screen on and the phone plugged in, and close other apps. Compiling takes 15-30 minutes the first
   time; re-runs skip it.
5. **Send back** `Download/nabz/nabz-phone-results.txt`. It has timings, RAM and the phone model only, no
   transcripts. Transcripts stay in Termux (`~/nabz-bench/out/`).

Optional: run it a second time right after the first, to see whether the phone slows down when hot.

## What the numbers will decide

- **Speech:** both Whisper models run on each dictation, so ASR time per dictation = ft + base. The project budget
  is 30 s per dictation (p90, `config.json`); the 37.6 s clip is the worst case.
- **Note writer:** time per note ≈ 400 / prompt t/s + 360 / generation t/s (cold start, p90 note length). The
  budget is 30 s. Peak RAM must leave room for Android and the app; on a 6 GB phone, much over ~3 GB is a risk.
- If the 4B note writer is too slow, the fallbacks already measured are Qwen3.5 2B (1.4 GB, weaker: RUN_NOTES
  "Phone-tier note writers") or running the note writer only after the doctor stops recording.

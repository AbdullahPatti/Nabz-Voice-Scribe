# Progress of the rerun (NEXT_STEPS.md)

One line per item. `todo`, `done` (date, commit) or `failed` (what, why). The commit named is the one before the
commit that records the line (a commit cannot name itself); `git log -- results/PROGRESS.md` gives the exact one.
At the start of every session: read this and continue from the first item that is not done.

| item | status | notes |
|---|---|---|
| Rule 4. Clean the run logs | done (13 Nov 2026, after 7b1d7af) | rows of lost runs removed from asr_runs.csv (426) and note_runs.csv (1744); 13 ASR runs and 8 note runs with per-clip files kept |
| Step 0. Machine and environment | done (13 Nov 2026, after b66e87b) | RTX A4000 16 GB, driver 596.71 (CUDA 13.2), Windows 11 Pro 10.0.22621, i7-13700, 32 GB RAM. Python 3.12.10, torch 2.14.1+cu126, torchaudio 2.11.0+cu126, transformers 5.23.0. llama.cpp b11912 win-cuda-12.4 (961c376a2), whisper.cpp b5454 whisper-bin-x64, whisper.cpp source at d2c6f05, stock base-q8 and small-q8. All 8 GGUF files downloaded (HF_HUB_DISABLE_XET=1). gh installed but not logged in. |
| Step 1.1 Urdu note writers (plan.txt steps 4 to 6) | todo | |
| Step 1.2 Phone-tier note writers, cap, dry, hints | todo | |
| Step 1.3 PyTorch Whisper parity (hf base, hf small) | done (13 Nov 2026, after b66e87b) | done before 1.1 and 1.2 while the note-writer models downloaded (GPU was free). hf_base_ur and hf_small_ur, 39 clips each. |
| Step 1.4 Lexicon biasing (Hadi, λ grid) | done (13 Nov 2026, after eed52d5) | Hadi only. Guarded λ 1, 2, 3 (run_asr_hf.py --bias λ --tag-suffix cg); unguarded λ 2, 4, 6, 8, 10 (rerun_bias_noguard.py, since asr_bias.py now always applies the guard). Not tuned. |
| Step 1.5 Synthetic fine-tune (texts, audio, synth-dec, synth-full, Hadi transcripts) | todo | |
| Step 1.6 End to end, checkpoint choice, test speakers | todo | |
| Step 1.7 ASR confidence and base cross-check | todo | |
| Step 1.8 Phone pair in whisper.cpp | todo | |
| Step 2. Write up RUN_NOTES | todo | |
| Step 3. Phone bundle | todo | |
| Step 4. Push, release, "Finished" section | todo | |

## Log


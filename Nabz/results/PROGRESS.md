# Progress of the rerun (NEXT_STEPS.md)

One line per item. `todo`, `done` (date, commit) or `failed` (what, why). The commit named is the one before the
commit that records the line (a commit cannot name itself); `git log -- results/PROGRESS.md` gives the exact one.
At the start of every session: read this and continue from the first item that is not done.

| item | status | notes |
|---|---|---|
| Rule 4. Clean the run logs | done (13 Nov 2026, after 7b1d7af) | rows of lost runs removed from asr_runs.csv (426) and note_runs.csv (1744); 13 ASR runs and 8 note runs with per-clip files kept |
| Step 0. Machine and environment | todo | |
| Step 1.1 Urdu note writers (plan.txt steps 4 to 6) | todo | |
| Step 1.2 Phone-tier note writers, cap, dry, hints | todo | |
| Step 1.3 PyTorch Whisper parity (hf base, hf small) | todo | |
| Step 1.4 Lexicon biasing (Hadi, λ grid) | todo | |
| Step 1.5 Synthetic fine-tune (texts, audio, synth-dec, synth-full, Hadi transcripts) | todo | |
| Step 1.6 End to end, checkpoint choice, test speakers | todo | |
| Step 1.7 ASR confidence and base cross-check | todo | |
| Step 1.8 Phone pair in whisper.cpp | todo | |
| Step 2. Write up RUN_NOTES | todo | |
| Step 3. Phone bundle | todo | |
| Step 4. Push, release, "Finished" section | todo | |

## Log


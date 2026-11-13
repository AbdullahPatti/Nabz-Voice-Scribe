# Progress of the rerun (NEXT_STEPS.md)

One line per item. `todo`, `done` (date, commit) or `failed` (what, why). The commit named is the one before the
commit that records the line (a commit cannot name itself); `git log -- results/PROGRESS.md` gives the exact one.
At the start of every session: read this and continue from the first item that is not done.

| item | status | notes |
|---|---|---|
| Rule 4. Clean the run logs | done (13 Nov 2026, after 7b1d7af) | rows of lost runs removed from asr_runs.csv (426) and note_runs.csv (1744); 13 ASR runs and 8 note runs with per-clip files kept |
| Step 0. Machine and environment | done (13 Nov 2026, after b66e87b) | RTX A4000 16 GB, driver 596.71 (CUDA 13.2), Windows 11 Pro 10.0.22621, i7-13700, 32 GB RAM. Python 3.12.10, torch 2.14.1+cu126, torchaudio 2.11.0+cu126, transformers 5.23.0. llama.cpp b11912 win-cuda-12.4 (961c376a2), whisper.cpp b5454 whisper-bin-x64, whisper.cpp source at d2c6f05, stock base-q8 and small-q8. All 8 GGUF files downloaded (HF_HUB_DISABLE_XET=1). gh installed but not logged in. |
| Step 1.1 Urdu note writers (plan.txt steps 4 to 6) | done (13 Nov 2026, after 6443f73) | 9 runs x 39 notes (qwen35-4b on base; alif-8b, alif-3b, qalb-8b, shaheen-7b on ref and base) via rerun_notes.py urdu. Every row of note_summary.csv equals the A4000 snapshot, invalid-note counts included. |
| Step 1.2 Phone-tier note writers, cap, dry, hints | done (13 Nov 2026, after 400c70c) | 30 runs x 39 notes via rerun_notes.py phone: Qwen3.5 0.8B, 2B, 4B Q4_K_M, Alif 3B (plain, -dry, -cap), 4B IQ3_M (-cap), hints for 4B and IQ3_M on ref, base, small. Every row of note_summary.csv equals the A4000 snapshot. negation_guard.csv written: 0 prescribed medicines moved. |
| Step 1.3 PyTorch Whisper parity (hf base, hf small) | done (13 Nov 2026, after b66e87b) | done before 1.1 and 1.2 while the note-writer models downloaded (GPU was free). hf_base_ur and hf_small_ur, 39 clips each. |
| Step 1.4 Lexicon biasing (Hadi, λ grid) | done (13 Nov 2026, after eed52d5) | Hadi only. Guarded λ 1, 2, 3 (run_asr_hf.py --bias λ --tag-suffix cg); unguarded λ 2, 4, 6, 8, 10 (rerun_bias_noguard.py, since asr_bias.py now always applies the guard). Not tuned. |
| Step 1.5 Synthetic fine-tune (texts, audio, synth-dec, synth-full, Hadi transcripts) | done (13 Nov 2026, after 4161b33) | texts.jsonl regenerated with no diff; 5,634 of 6,000 items rendered (5,434 train, 200 val); synth-dec and synth-full trained 2000 steps with checkpoints at 250 and 500 (val loss 3.12 -> 0.012 and 0.003; logs in results/train_logs/); all 6 checkpoints transcribed on Hadi. |
| Step 1.6 End to end, checkpoint choice, test speakers | done (13 Nov 2026, after c816ef3) | Phone note writer (IQ3_M, capped) on all 6 checkpoints' Hadi transcripts (rerun_notes.py e2e-dev). Rule 1 (rerun_tables.py choose) picked synth-full-s250: Hadi med_recall 46% (stock base 12%), 0 avoid violations. Test speakers run once (rerun_notes.py e2e-test): med_recall 44% vs 10% for hf base. |
| Step 1.7 ASR confidence and base cross-check | done (13 Nov 2026, after 47c6154) | asr_confidence.py on hf_synth-full-s250_ur (48 drugs written: 31 said, 17 invented); AUC min_p 0.57 dev / 0.65 test; base cross-check (rerun_tables.py crosscheck, results/crosscheck.csv) flags 7/7 and 10/10 invented drugs; end to end wrong unflagged 7 -> 0 on test. |
| Step 1.8 Phone pair in whisper.cpp | done (13 Nov 2026, after b5edee1) | synth-full-s250 converted (convert-h5-to-ggml.py at d2c6f05) and quantized q8_0 to models/ft-synth-full-s250/ggml-model-q8_0.bin (78 MB; folder and config.json entry unchanged, same checkpoint as before). whisper.cpp b5454 -t 4 -l ur on 39 clips (avx2_ft-s250-q8_ur_t4), notes via rerun_notes.py phone-pair. Test: med_recall 50% vs 10% base-q8, wrong unflagged after cross-check 0; 1 avoid violation (flagged by drug_check). |
| Step 2. Write up RUN_NOTES | todo | |
| Step 3. Phone bundle | todo | |
| Step 4. Push, release, "Finished" section | todo | |

## Log


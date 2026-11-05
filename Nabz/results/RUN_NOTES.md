# Run notes, 5 November 2026

Read this before quoting anything from `decision_table.md`.

## Where this ran

A cloud machine with 2 CPU cores and 7 GB RAM. Every job used 2 threads and ran alone. **The timings and RAM figures are not valid for hardware decisions.** The last line of the decision table says "fast laptop CPU"; that is the generic report text. Rerun the chosen settings on the Legion laptop, an old lab PC and a phone (README step 8).

Accuracy numbers do not depend on the machine, so they stand.

## What ran

- Speakers: hadi (male), merab-haroon (female), nouman-tanveer (male). All 18 to 24.
- Clips scored: 13 per speaker (dict_01 to dict_10, own_01 to own_03). Visits (`conv_`) were skipped: they are 12 to 20 s role-plays, not real consultations.
- Whisper: base-q8 and small-q8 with `-l ur`, `auto`, `en`; large-v3-turbo-q8 with `ur` only, as the ceiling.
- Note writers: Gemma 4 E2B Q4_0 and Qwen3.5 4B Q4_K_M, each on the reference text and on `avx2_small-q8_ur_t2` (best `drug_recall` among non-turbo models).

## References

- dict_ references are the script text. No speaker flagged changed words.
- **own_ references are drafts.** Claude wrote them from the fact card plus the small and turbo transcripts. Each file says DRAFT. Listen and correct, then rerun `score_asr.py` and `score_note.py`. Because the drafts lean on ASR output, `sker` and `neg_kept` on own_ clips are slightly flattering until checked.

## Findings

1. **Forcing Urdu breaks English speech.** Merab and Nouman spoke their own-words clips mostly in English. With `-l ur`, turbo produced hallucinations ("موسیقی" repeated) and small produced loops. `auto` transcribed them correctly. `small-q8 ur` still edges `auto` on drug_recall (72% vs 70%), but `auto` wins neg_kept (87% vs 78%) and sker (19% vs 24%). The app should detect language per clip, not force `ur`.
2. **Turbo is not worth it here.** 73% drug recall vs 72% for small, at 2.5x the time and twice the RAM.
3. **Qwen3.5 4B is the better note writer on clean text:** 85% medicines, 86% strengths, 3 negation flips, no invented drugs, no avoid violations. Gemma 4 E2B: 68%, 57%, 24 flips. Gemma regularly lists a symptom the doctor negated ("bleeding" when the doctor said no bleeding) as a complaint. That alone rules it out without a fix.
4. **The speech step is the bottleneck.** On Urdu-script ASR text, medicine recall falls to 24% (Qwen) and 12% (Gemma), and Qwen invents 23 medicines and lists 4 avoided drugs as prescribed. Whisper writes drug names in garbled Urdu script ("پر اندال" for Panadol), and the LLM cannot recover them. This is the paper's story: drug-name-aware ASR (fine-tuning, a DRAP lexicon, or constrained decoding) before anything else.
5. **Nothing is within the time budget on this machine.** Do not conclude anything from that; see "Where this ran".

## Gaps

- No speaker over 24, and no Punjabi-dominant speaker. Recruit at least one.
- Hadi left home language and phone model blank.
- The pipeline was run on one ASR setting only. Next: rerun Qwen on `avx2_small-q8_auto_t2`.

## Privacy

`data/manifest.csv` in this folder has the device field scrubbed (one speaker typed a phone number there). The original zips in `recordings/` still contain it and the audio. The consent text says recordings will not be published, so this repository should be private.

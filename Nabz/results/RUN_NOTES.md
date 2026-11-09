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

## Drug lexicon experiments, 9 November 2026 (no models run, existing outputs only)

`lexicon.txt` is a **placeholder**: about 300 common Pakistani OPD brands and generics written from memory, one spelling each, no answer-key pronunciation variants. Replace it with the DRAP export and rerun.

**1. Rewriting the transcript does not work.** Snapping Urdu-script spans to the nearest brand by consonant skeleton, before the LLM sees the text, found 57% of the key drugs in `small-q8_ur` but inserted 116 false drugs ("خاتون", woman, became Capoten). Tightening the tolerance and requiring a dose word nearby brought that to 21 false drugs at 32% recall, no better than Qwen's own 23 inventions. Ordinary Urdu words sit too close to brand names in skeleton space. Dropped; not committed.

**2. Checking the LLM output does work.** `drug_check.py` flags any medicine in a note that is not an exact lexicon entry, or that has nothing close to it in the transcript:

| run | right passed | right flagged | wrong flagged | wrong passed | avoid passed | avoid flagged |
|---|---|---|---|---|---|---|
| small-q8_ur → gemma | 4 | 2 | 4 | 0 | 0 | 1 |
| small-q8_ur → qwen | 6 | 6 | 19 | **0** | **3** | 1 |
| ref → gemma | 34 | 3 | 0 | 0 | 0 | 0 |
| ref → qwen | 39 | 3 | 0 | 0 | 0 | 0 |

No invented or swapped drug (e.g. "Ibuprofen" for an unspoken Brufen) reaches the doctor unflagged. The cost is that half of Qwen's correct medicines on ASR text get flagged for review (misspelled real names such as "Zartrak"). The 3 flags on reference text are all "cough syrup", which is not a brand.

The lexicon side must be an **exact** match: with ~72k DRAP brands, almost any invented name is one edit from a real one ("Exomix" vs Xanax).

**3. What remains is a negation problem.** The 3 avoided drugs that pass were said with "nahi", which Whisper dropped (Merab dict_02: "Brufen bilkul nahi leni" became "بروفن نے لینے"). No lexicon can catch that. It needs negation-preserving ASR, or a rule that any drug near a negation in the transcript goes to the avoid list for the doctor to confirm.

## Whisper base with a drug-name prompt, 9 November 2026

Run on the Legion laptop (4 threads, whisper.cpp build b5454). The `_t4` rows in `asr_summary.csv` come from this run; the `_t2` rows are the older cloud run on a different build.

| tag | drug_recall | number_recall | neg_kept | sker |
|---|---|---|---|---|
| base-q8 ur, no prompt | 67% | 30% | 61% | 33% |
| base-q8 ur, `whisper_drugs.txt` | 76% | 38% | **30%** | 36% |
| base-q8 ur, `whisper_drugs_nokey.txt` | 68% | 38% | **39%** | 32% |
| base-q8 auto, no prompt | 58% | 41% | 66% | 29% |
| small-q8 ur (cloud, for reference) | 72% | 55% | 78% | 24% |

1. **The drug prompt's gain is mostly leakage.** `whisper_drugs.txt` lists the answer-key drugs. The control list without them gives 68%, against 67% with no prompt.
2. **Any prompt about halves negation recall** (61% → 30-39%). Whisper drops "nahi", which turns avoided drugs into prescribed ones. Don't use `--prompt`.
3. With no prompt, base trails small by 5 points on drugs, 25 on numbers and 17 on negation. Doses and "nahi" are where base costs most.
4. With base, `ur` beats `auto` on drugs (67% vs 58%), the opposite of small.

## Qwen 2.5 7B notes on base output, 9 November 2026

Ollama `qwen2.5:7b` on `avx2_base-q8_ur_t4`, with `note_system.txt` (tag `qwen25-7b-ollama`) and `note_system_v2.txt` (tag `qwen25-7b-ollama-v2`). 39 notes each, about 4.6 s per note on the Legion laptop.

| run | schema_valid | med_recall | strength_recall | extra_meds | avoid_violations | neg_recall | neg_flips |
|---|---|---|---|---|---|---|---|
| base ur → qwen2.5 7b | 79% | 6% | 12% | 6 | 0 | 38% | 7 |
| base ur → qwen2.5 7b, v2 prompt | 92% | 3% | 5% | 9 | 2 | 31% | 7 |
| ref → qwen2.5 7b | 100% | 60% | 76% | 3 | 0 | 68% | 12 |
| ref → qwen3.5 4b (cloud) | 100% | 85% | 86% | 0 | 0 | 83% | 3 |

1. **The pipeline fails on base output.** About 1 medicine in 20 gets through. Qwen mostly leaves drugs out, and it invents complaints that were never said: Merab dict_01 gained "headache" and "cough".
2. **`drug_check.py` flagged every wrong drug** (6 and 7). With the v2 prompt, 2 avoided drugs were listed as prescribed and passed unflagged. That's the negation gap again.
3. **Qwen 2.5 7B is weaker than Qwen3.5 4B even on clean text** (60% vs 85% of medicines), so it's not the model to build on.
4. **Ollama doesn't fully enforce the JSON schema** (79% and 92% valid). `server_ram_mb` is wrong for Ollama runs, because the script measures the wrong process.
5. Prompting the note writer can't recover drug names from garbled Urdu-script text. The transcript has to improve first.

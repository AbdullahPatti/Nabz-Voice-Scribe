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

- **Limitation of the study, not a to-do (13 November 2026):** 3 speakers, all 18 to 24, one of them the dev speaker; no speaker over 24 and no Punjabi-dominant speaker. No further speakers are planned for now, so every result here rests on 39 clips from these three.
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

## Urdu note writers on the A4000, 9 November 2026

**The per-clip files of the 9 to 11 November A4000 runs were lost. The sections from here to "The phone pair in whisper.cpp, 11 November 2026" are kept as the earlier run (summary tables in `results/a4000_snapshot/`); the numbers of record are in the sections headed "Rerun" below.**

**Machine:** NVIDIA RTX A4000 16 GB, driver 596.86 (nvidia-smi reports CUDA 13.2), Windows 11 Pro 10.0.22621. llama.cpp b11912 prebuilt `win-cuda-12.4-x64` (commit 961c376a2), `-ngl 99 -c 4096 --jinja`, every layer on the GPU. Python 3.12.10. Repo commit before the run: `e94a3bc`. Every model got the same prompt (`note_system.txt`), the same schema, temperature 0 and max_tokens 800. All GGUF files are Q4_K_M.

| run | schema_valid | med_recall | strength_recall | extra_meds | avoid_violations | neg_recall | neg_flips | wrong_passed | avoid_passed | GGUF GB |
|---|---|---|---|---|---|---|---|---|---|---|
| ref → qwen35-4b (cloud, earlier) | 100% | 85% | 86% | 0 | 0 | 83% | 3 | 0 | 0 | 3.01 |
| ref → alif-8b | 100% | 81% | 48% | 3 | 0 | 26% | 9 | 0 | 0 | 4.92 |
| ref → alif-3b | 62% | 88% | 75% | 14 | 6 | 69% | 6 | 0 | 6 | 2.24 |
| ref → qalb-8b | 100% | 15% | 14% | 0 | 0 | 4% | 3 | 0 | 0 | 4.92 |
| ref → shaheen-7b | 85% | 67% | 80% | 0 | 0 | 77% | 15 | 0 | 0 | 4.68 |
| ref → qwen2.5 7b (Ollama, earlier) | 100% | 60% | 76% | 3 | 0 | 68% | 12 | 0 | 0 | not on this machine |
| base ur → qwen35-4b | 97% | 8% | 10% | 19 | 1 | 31% | 8 | 0 | 1 | 3.01 |
| base ur → alif-8b | 92% | 10% | 5% | 35 | 1 | 16% | 12 | 0 | 1 | 4.92 |
| base ur → alif-3b | 44% | 9% | 20% | 15 | 2 | 4% | 6 | 0 | 2 | 2.24 |
| base ur → qalb-8b | 100% | 0% | 0% | 0 | 0 | 1% | 0 | 0 | 0 | 4.92 |
| base ur → shaheen-7b | 49% | 13% | 11% | 12 | 2 | 44% | 5 | 0 | 2 | 4.68 |
| base ur → qwen2.5 7b (Ollama, earlier) | 79% | 6% | 12% | 6 | 0 | 38% | 7 | 0 | 0 | not on this machine |

"base ur" is `avx2_base-q8_ur_t4`. **Read the low schema_valid rows with care:** `score_note.py` leaves unparseable notes out of the recall averages, so alif-3b's recalls come from 24 of 39 notes (ref) and 17 of 39 (base), and shaheen-7b's from 33 and 19. A note that doesn't parse gives the doctor nothing, so these recalls flatter both models.

1. **No Urdu model beat qwen35-4b on base output.** On safety, alif-3b and shaheen-7b each list 2 avoided drugs as prescribed (qwen35-4b: 1). alif-8b ties qwen35-4b on avoid errors but invents 35 medicines (qwen35-4b: 19). qalb-8b's zeros are not a win: it leaves medications, complaints and negatives empty on almost every note, clean text included (medications filled in 6 of 39 ref notes and 0 of 39 base notes). `drug_check.py` flagged every wrong drug in every run (wrong_passed is 0 throughout). All 6 avoid errors on base output are Augmentin in dict_10. For Merab, Whisper garbled the "nahi" ("اگوینٹن نیویںی"). For Hadi, the transcript still says "نہیں دینی", and alif-3b and shaheen-7b listed it as prescribed anyway. That is a model error, not a speech error. Medicine recall stays between 0% and 13% for every model, so the pipeline still fails on base output, whichever note writer is used.
2. **alif-3b is not usable as it stands.** On ref it finds 88% of medicines in the notes that parse, but 15 of 39 notes are cut off at 800 tokens in repetition loops ("ulty nahi hai", "dast nahi", … repeated). It also lists Brufen and Disprin as prescribed on dict_02 for all three speakers (6 avoid violations), and the drug checker cannot catch these because the names were said. alif-8b on the same text: every note valid, 0 avoid violations, but only 48% of strengths and 26% of negatives. On base output, alif-3b parses 44% of notes and keeps 4% of negatives.
3. **The speech step costs nearly everything.** Medicine recall from ref to base: qwen35-4b 85% → 8%, alif-8b 81% → 10%, alif-3b 88% → 9%, shaheen-7b 67% → 13%, qalb-8b 15% → 0%. Invented medicines rise for every model except qalb-8b (alif-8b 3 → 35, qwen35-4b 0 → 19).
4. **Nothing failed in step 5.** Every server started with `--jinja` and returned no errors, and all 9 runs wrote 39 notes. Every invalid note (qwen35-4b 1, alif-8b 3, alif-3b 15 + 22, shaheen-7b 6 + 20) stopped at exactly 800 generated tokens, inside a repetition loop. These are kept as results. The first model download stalled on Hugging Face's Xet transfer; it worked with `HF_HUB_DISABLE_XET=1`.

The timing and RAM columns in `note_summary.csv` and `decision_table.md` come from a desktop GPU. They say nothing about phones, and `within_budget` does not apply. `server_ram_mb` is the server's CPU RAM, not GPU memory.

## Phone-tier note writers, schema cap, negation guard and drug-name hints, 9 November 2026

Same A4000 machine and llama.cpp b11912 as above. The app is phone-only, so the question is now which note writer fits a phone (under the 2.5 GB file budget in the project doc) and what can be done without a better speech model. Timings below are desktop-GPU timings and say nothing about phones.

**1. Repetition loops, not knowledge, break the small models.** Every invalid note in every run stopped at exactly 800 tokens, repeating a list item ("nasal polyps", "no vaginal discharge", ...). llama.cpp's DRY sampler (`--dry-multiplier 0.8`) changed nothing for Qwen and little for Alif: its default sequence breakers include `"` and newline, so it never sees one JSON list item repeating the last. **Capping every list at 10 items in the schema** (`note_schema_capped.json`; real notes never exceeded 7) makes the grammar close the list. Invalid notes fell to 0 or 1 per run for Qwen3.5 0.8B, 2B and 4B. Alif 3B still had 3 on ref and 12 on base output (it loops inside strings). The cap also exposes what truncation hid. `score_note.py` leaves unparseable notes out of the recall averages, so previously truncated notes now count, with their errors.

| run (capped schema) | schema_valid | med_recall | strength_recall | extra_meds | avoid_violations | neg_recall | neg_flips | GGUF GB |
|---|---|---|---|---|---|---|---|---|
| ref → qwen3.5 4b Q4_K_M | 100% | 88% | 86% | 0 | 0 | 83% | 3 | 3.01 |
| ref → qwen3.5 4b IQ3_M | 100% | 85% | 71% | 0 | 0 | 88% | 0 | **2.48** |
| ref → qwen3.5 2b Q4_K_M | 100% | 78% | 57% | 3 | 0 | 64% | 9 | 1.40 |
| ref → qwen3.5 0.8b Q4_K_M | 100% | 28% | 29% | 21 | 9 | 47% | 34 | 0.58 |
| ref → alif 3b Q4_K_M | 92% | 86% | 71% | 11 | 3 | 65% | 6 | 2.24 |
| base ur → qwen3.5 4b Q4_K_M | 100% | 8% | 10% | 19 | 1 | 33% | 8 | 3.01 |
| base ur → qwen3.5 4b IQ3_M | 100% | 9% | 10% | 14 | 1 | 16% | 13 | 2.48 |
| base ur → qwen3.5 2b Q4_K_M | 100% | 8% | 5% | 23 | 3 | 36% | 14 | 1.40 |
| base ur → alif 3b Q4_K_M | 69% | 7% | 21% | 34 | 3 | 5% | 8 | 2.24 |

**Phone note writer: Qwen3.5 4B at IQ3_M.** It is the only model under 2.5 GB with no invented or avoided drugs on clean text, and it gives up 3 points of medicines and 15 of strengths against Q4_K_M. Qwen3.5 2B costs 10 points of medicines and adds 9 negation flips. 0.8B is unsafe: 9 avoided drugs listed as prescribed. Alif 3B invents 11 medicines on clean text. Measure IQ3_M's RAM and speed on a real phone before committing.

**2. Negation guard** (`negation_guard.py`, no model). Any medicine in a note that the transcript follows with a negation word in the same clause ("Augmentin nahi deni", "منتن نہیں دینی") is moved to "avoid, doctor confirms". On all runs so far it moved **no correctly prescribed medicine**. It caught every avoid error on reference text (6 of 6 for alif-3b, 9 of 9 for qwen3.5 0.8b). On Whisper output it caught about half: every miss is a clip where Whisper garbled the "nahi" itself (Merab dict_10 "اگوینٹن نیویںی", dict_02 "بروفن نے لینے"). No text rule can fix that; it needs the speech step.

**3. Drug-name hints** (`drug_hints.py`, `run_note.py --hints --prompt note_system_hints.txt`). The transcript stays unchanged. Up to 10 cross-script sound-alike matches from the lexicon are appended ("پروفین" may be Brufen), and the LLM keeps the ones used as a medicine. Matcher tolerances are nabzlib's existing ones, untuned; only `lexicon.txt` is used. The hints contain 44% of the key drugs on base output, alongside 134 false candidates.

| run (capped schema) | med_recall | strength_recall | extra_meds | avoid_violations | right suggested | wrong suggested | wrong_passed |
|---|---|---|---|---|---|---|---|
| base ur → 4b Q4_K_M | 8% | 10% | 19 | 1 | 4 | 18 | 0 |
| base ur → 4b Q4_K_M + hints | **23%** | **29%** | 17 | 2 | 12 | 15 | **8** |
| base ur → 4b IQ3_M | 9% | 10% | 14 | 1 | 4 | 13 | 0 |
| base ur → 4b IQ3_M + hints | 17% | 14% | **5** | 1 | 7 | **4** | **3** |
| small ur → 4b IQ3_M | 23% | 14% | 11 | 2 | 11 | 9 | 0 |
| small ur → 4b IQ3_M + hints | 21% | 10% | 7 | 0 | 9 | 7 | 4 |
| ref → 4b IQ3_M + hints | 77% | 71% | 0 | 0 | 42 | 0 | 0 |

"Right/wrong suggested" counts medicines in the notes from `drug_check.csv`, flagged or not.

- On base output, hints roughly double to triple the medicines that reach the note. With the phone model, wrong medicines fall from 13 to 4.
- **They also blind `drug_check.py`.** It passes a drug that is in the lexicon and sounds like something said, which is exactly how a hint is made. Wrong drugs that reach the doctor unflagged go from 0 to 8 (Q4_K_M) and 0 to 3 (IQ3_M). They are sound-alike swaps: Vastarel for Norvasc, Ponstan for Zyrtec. A generator and a verifier that share the same evidence give no independent check.
- **Rule for the app:** on Urdu-script ASR text, never auto-accept a medicine. Every one is a suggestion the doctor confirms with one tap. Under that rule `wrong_passed` is 0 by construction, and what matters is suggestion precision: 64% with hints (7 of 11) against 24% without (4 of 17) for the phone model.
- Hints cost a little on clean text (85% → 77% medicines), so use them only on Urdu-script ASR output.
- The lexicon is a 318-entry placeholder. With the ~72k-entry DRAP list, hints will be noisier; test that before trusting these gains.

**4. PyTorch Whisper matches whisper.cpp** once decoding matches (beam 5 plus temperature fallback; plain greedy loops on half the clips). hf base ur: drug 69%, numbers 33%, neg 61%, sker 29%; whisper.cpp base-q8 ur: 67%, 30%, 61%, 33%. hf small ur: 72%, 50%, 76%, 25%; whisper.cpp small-q8: 72%, 55%, 78%, 24%. Decoding experiments in PyTorch (`run_asr_hf.py`) are therefore a fair proxy for the phone build.

**5. Lexicon biasing in Whisper decoding does not help** (`asr_bias.py`, negative result). It uses trie shallow fusion over the lexicon's Latin token sequences, with the bonus taken back when a partial name is abandoned (Zhao et al. 2019), on HF whisper-base `ur`. Strength was tuned on Hadi only, and the other two speakers were kept for testing; since nothing beat the baseline on Hadi, they were never used.

| Hadi, 13 clips | drug_recall | number_recall | neg_kept | sker | Latin words | inserted drugs |
|---|---|---|---|---|---|---|
| no bias | 67% | 37% | 87% | 22% | 0 | 0 |
| λ=1 | 59% | 29% | 79% | 26% | 1 | 0 |
| λ=2 | 67% | 28% | 83% | 26% | 4 | 0 |
| λ=3 | 72% | 25% | 90% | 22% | 16 | 1 |
| λ=2, no chain guard | 74% | 37% | 83% | 23% | 28 | 0 |
| λ=4, no chain guard | 53% | 17% | 52% | 204% | 209 | 2 |
| λ≥6, no chain guard | 0-3% | 0-8% | 0% | >500% | 102-378 | 12-22 |

In Urdu mode, whisper-base gives Latin tokens so little probability that a bonus small enough to stay stable rarely switches script. A larger one collapses into chained drug names ("gavisconlactuloseursofalk..."). Blocking a new name straight after a finished one stops the chaining, but at λ ≤ 3 the gains are within run-to-run noise: temperature fallback samples, now seeded in `run_asr_hf.py`. Dropped in favour of teaching the model the output script (next section).

## Whisper base fine-tuned on synthetic Roman-Urdu dictations, 10 November 2026

A4000, PyTorch (`train_whisper.py`, `run_asr_hf.py`). Training data: 5,434 synthetic dictations (`synth_dictation.py` grammar, MMS-TTS Latin-script Urdu voice, `synth_audio.py`), 200 held out for validation, speed/band-limit/reverb/noise augmentation. lr 2e-5 cosine over 2000 steps, batch 16. No real clip was used for training. Hadi is the dev speaker (as for biasing); Merab and Nouman stay held out.

`score_asr.py` gained two columns, because drug_recall and neg_kept only reward recall: `neg_extra` (negation words beyond the reference) and `drugs_inserted` (a lexicon drug written exactly, by consonant skeleton, that the reference does not contain). On Urdu-script output `drugs_inserted` is mostly noise (short names like Avil, Diovan, Ativan collide with ordinary Urdu words); on Latin output it counts real invented drugs.

All 39 clips, the first full run (decoder-only, 2000 steps):

| run | drug_recall | number_recall | neg_kept | neg_extra | drugs_inserted | sker |
|---|---|---|---|---|---|---|
| hf whisper-base ur | 69% | 33% | 61% | 1 | 49 (noise) | 29% |
| synth-dec, 2000 steps | 52% | 83% | 94% | 41 | 88 | 45% |

Hadi only (13 clips), by training length:

| run | drug_recall | number_recall | neg_kept | neg_extra | drugs_inserted | sker |
|---|---|---|---|---|---|---|
| hf whisper-base ur | 67% | 37% | 87% | 1 | 13 (noise) | **22%** |
| hf whisper-small ur (reference) | 83% | 60% | 87% | 0 | 7 | 16% |
| decoder-only, 250 steps | 55% | 76% | 92% | 3 | 13 | 30% |
| decoder-only, 500 steps | 59% | 74% | 90% | 8 | 24 | 38% |
| decoder-only, 2000 steps | 56% | 90% | 96% | 13 | 31 | 42% |
| full (encoder too), 250 steps | 58% | 73% | 100% | 9 | 12 | 30% |
| full (encoder too), 500 steps | 69% | 68% | 97% | 7 | 16 | 32% |

1. **The output script changes as intended.** Transcripts come out in Roman Urdu with Latin drug names and digits ("Azomax 500", "Platelets 95 hazaar", "Brufen bilkul nahi lena"). Numbers roughly double (37% → 68-90%).
2. **But the model hallucinates in the shape of its training dictations.** Where the audio is unclear it writes template text: invented drugs (Haldol, Telfast, Warfarin, Viagra), lab values that were never said ("HB 5", "BP 111 by 10"), and extra negations. "Kamzori bhi hai" became "Kamzori bhi nahi hai", which flips a symptom. The 94% neg_kept of the 2000-step run is inflated by 41 extra negation words. Substitutions are confident Latin names: "Augmentin 625" → "Paracetamol 625".
3. **More training means more hallucination.** sker rises with steps in both variants (30% → 38% → 42%). No checkpoint reaches base's 22% on Hadi, so the selection rule (lowest Hadi sker) picks none of them over base, and nothing was run on the two held-out speakers.
4. **ASR drug_recall is lenient to Urdu script:** the fuzzy cross-script matcher counts garbled spellings as found, while the note writer gets only 8-9% of medicines from that same text. So the deciding metric is end to end: the phone note writer's notes on each checkpoint's output (next section), fixed before those notes were run.
5. The training data is one TTS voice reading grammar text with drugs drawn uniformly from the lexicon, so the decoder learns a strong "dictation template" prior with a flat prior over drugs. Fixes to try: real speech in training (fair only if split by dictation script, since every speaker read the same dict_01-10), more voices, or fewer steps / lower lr with the encoder trained.

Speed fix: speed perturbation resampled from an arbitrary rate, which made torchaudio build a huge filter (1.8 s per clip, ~12 h per run); the source rate is now rounded to 200 Hz (1 ms). A run takes ~20 min alone on the A4000.

**Interrupted:** the 1000- and 2000-step checkpoints of the second decoder-only and full runs were stopped when the PC ran low on RAM. Two trainers each cache all 5,434 waveforms in RAM (~5 GB each), alongside the transcription job and llama-server; run them one at a time.

## End to end: fine-tuned Whisper base → phone note writer, 10 November 2026

Note writer: Qwen3.5 4B IQ3_M, capped schema, `note_system.txt` (hints runs: `note_system_hints.txt --hints`), temperature 0, A4000. "right / wrong" are medicines in the notes judged by `drug_check.csv` (precision in brackets); "unflagged" are wrong medicines `drug_check.py` passed.

**Dev, Hadi (13 clips).** Chosen on these numbers:

| ASR source | med_recall | strength | neg_recall | neg_flips | avoid_violations | right / wrong | unflagged |
|---|---|---|---|---|---|---|---|
| hf whisper-base ur | 12% | 0% | 27% | 4 | 0 | 2 / 3 | 0 |
| hf whisper-base ur + hints | 12% | 0% | 31% | 3 | 0 | 2 / 2 | 1 |
| decoder-only, 250 steps | 35% | 29% | 37% | 3 | 0 | 7 / 9 | 4 |
| decoder-only, 500 steps | 35% | 29% | 49% | 3 | 0 | 5 / 14 | 9 |
| decoder-only, 2000 steps | 31% | 29% | 45% | 3 | 0 | 5 / 16 | 13 |
| **full, 250 steps** | **46%** | 14% | **60%** | **1** | 0 | 8 / 12 | 3 |
| full, 500 steps | 35% | 0% | 49% | 2 | 0 | 6 / 11 | 5 |
| reference text | 85% | 71% | 86% | 0 | 0 | 15 / 0 | 0 |

**Test, Merab + Nouman (26 clips), run once with the chosen checkpoint `synth-full-s250`:**

| ASR source | sker | number_recall | neg_kept | med_recall | strength | neg_recall | neg_flips | avoid_violations | right / wrong | unflagged |
|---|---|---|---|---|---|---|---|---|---|---|
| hf whisper-base ur | 32% | 31% | 48% | 12% | 14% | 12% | 10 | 1 | 4 / 17 (19%) | 0 |
| hf whisper-base ur + hints | | | | 13% | 21% | 20% | 11 | 1 | 4 / 14 (22%) | 4 |
| hf whisper-small ur (reference) | 29% | 45% | 70% | | | | | | | |
| **synth-full-s250** | **24%** | **79%** | **86%** | **42%** | 14% | **67%** | **5** | **0** | **15 / 26 (37%)** | 8 |
| reference text | | | | 85% | 71% | 90% | 0 | 0 | 30 / 0 | 0 |

1. **The synthetic fine-tune is the first change that moves the whole pipeline.** On unseen speakers, medicines reaching the note go 12% → 42% and negatives 12% → 67%. Negation flips halve and no avoided drug is listed as prescribed. Suggestion precision doubles (19% → 37%), so under the confirm-every-medicine rule the doctor sees almost 4x the correct suggestions with a higher share of right ones. ASR sker beats whisper-small too (24% vs 29%) at base's size.
2. **The ASR now invents drugs, and that blinds `drug_check.py`.** A drug the ASR wrote is "said" by construction, so 8 wrong medicines pass unflagged (base: 0). Auto-accept stays off. An independent check is needed, e.g. Whisper's own token confidence on drug names.
3. **Strengths don't improve (14%).** Doses come out as numbers, but the note writer often drops them or pairs them with the wrong drug when the drug name is wrong.
4. **Less training is better** (sker and invented drugs rise with steps in both variants), and training the encoder helps end to end at 250 steps. 250 steps is the earliest checkpoint tried; shorter runs and lower lr are untested.
5. Caveats: 3 speakers, 39 clips, one dev speaker; every speaker read the same dict_01-10 scripts. The synthetic grammar excluded the test scripts' 5-grams, but its vocabulary was written with this OPD domain in mind. The phone runtime is whisper.cpp; this checkpoint still has to be converted and checked for parity there.

## Catching drugs the fine-tuned ASR invents, 10 November 2026

**Fix first: `run_asr_hf.py` cut every clip at 30 s.** Whisper's feature extractor truncates by default, so the long-form branch never ran. 5 of 39 clips are longer (30.3-37.6 s); only Merab dict_05 (37.6 s) lost speech (its last ~7 s, a sugar test and "pairon mein sun hona nahi hai"). Fixed with `truncation=False`; `hf_base_ur` and `hf_synth-full-s250_ur` were re-run on those 5 clips and their notes regenerated. whisper.cpp runs were never affected. Corrected test numbers are below; the table in the previous section is from before the fix (medicines 42% → 40%).

**Stricter "drug written" matcher** (`nabzlib.written_drugs`): the consonant skeleton is too lossy for short names (Cac-1000 → "k" = "ke", Diovan → "dn" = "din", Avil → "l"), which is where most of base's `drugs_inserted` noise came from. Latin windows must now spell the name exactly; Urdu-script windows need an identical skeleton of at least 3 consonants. `drugs_inserted` on the test speakers: base 5, fine-tuned 11.

**1. Whisper's own confidence is a weak check** (`asr_confidence.py`). Each transcript is re-scored against its audio by teacher forcing, and each written drug gets the lowest probability of its tokens. The fine-tuned model writes 52 drug names, 33 said and 19 invented. AUC for said vs invented is 0.57 (Hadi) and 0.71 (test), or 0.67/0.78 with the mean token probability. At the cut-off fixed on Hadi (flag at most 1 in 5 said drugs), it catches 1 of 11 invented drugs on the test speakers. Invented drugs come from the learned dictation template and are written with confidence.

**2. Cross-checking against plain whisper-base works.** The base model never saw the template. A drug the fine-tuned model writes is flagged when base's Urdu-script transcript has nothing that sounds like it (the fuzzy cross-script `find_terms`):

| written by synth-full-s250 | invented drugs flagged | said drugs flagged |
|---|---|---|
| Hadi (dev) | 8 / 8 | 3 / 11 |
| Merab + Nouman (test) | **11 / 11** | 5 / 22 |

**3. End to end** (Qwen3.5 4B IQ3_M, capped schema; a note medicine is flagged if `drug_check.py` flags it or base's transcript has no sound-alike):

| Merab + Nouman (test) | med_recall | strength | neg_recall | neg_flips | avoid_violations | right / wrong | wrong unflagged | right flagged for review |
|---|---|---|---|---|---|---|---|---|
| hf whisper-base ur | 12% | 14% | 16% | 10 | 1 | 4 / 18 | 0 | |
| hf whisper-base ur + hints | 15% | 29% | 20% | 12 | 1 | 5 / 13 | 3 | |
| synth-full-s250 | 40% | 14% | 63% | 5 | 0 | 14 / 28 | 10 | |
| **synth-full-s250 + base cross-check** | 40% | 14% | 63% | 5 | 0 | 14 / 28 | **0** | 4 / 14 |

On Hadi the same gate takes wrong-unflagged from 3 to 0 and flags 2 of 8 right medicines.

- **Proposed pipeline:** fine-tuned base writes the transcript the note writer reads, and plain base runs on the same audio as an independent witness. Every medicine is still a one-tap confirm; the flag marks "the ASR may have invented this". On these 26 test clips, 10 of 14 correct medicines arrive unflagged and every wrong one is flagged.
- **Cost on the phone:** a second base-size ASR pass (both models are base size), so ASR time roughly doubles. The two can share audio preprocessing.
- **Not checked yet:** both models in whisper.cpp q8 (conversion is blocked on running freshly downloaded code here), and sound-alike collisions once the lexicon becomes the ~72k-entry DRAP list.

## The phone pair in whisper.cpp, 11 November 2026

`synth-full-s250` converted with whisper.cpp's `models/convert-h5-to-ggml.py` (repo HEAD d2c6f05, tokenizer files copied from openai/whisper-base, which fine-tuning doesn't change) and quantized with `whisper-quantize` q8_0: **77 MB**, the same size as stock base-q8. Runs use the prebuilt whisper.cpp b5454 `whisper-bin-x64` (the build of the laptop baseline), `-t 4 -l ur`, as config model `ft-s250-q8`. The baseline `avx2_base-q8_ur_t4` rows are from the Legion laptop with the same build. Desktop CPU timings (0.8 s per clip, ~235 MB RAM) say nothing about phones.

ASR, whisper.cpp vs PyTorch:

| | Hadi sker | Hadi numbers | test drug_recall | test number_recall | test neg_kept | test neg_extra | test drugs_inserted | test sker |
|---|---|---|---|---|---|---|---|---|
| hf whisper-base ur | 22% | 37% | 68% | 31% | 48% | 0 | 5 | 32% |
| whisper.cpp base-q8 | 27% | 32% | 68% | 29% | 52% | 0 | 3 | 35% |
| hf synth-full-s250 | 30% | 73% | 67% | 80% | 90% | 7 | 11 | 24% |
| **whisper.cpp ft-s250-q8** | 30% | 78% | 63% | 84% | 91% | 5 | 10 | **24%** |

Aggregates carry over. Word for word they don't (1 of 39 transcripts identical; 17 below 0.8 word overlap): q8 weights plus a different decoder and temperature fallback, as for stock base.

End to end, the phone pair: whisper.cpp ft-s250-q8 writes the transcript, and whisper.cpp base-q8 is the cross-check witness (a note medicine is flagged if `drug_check.py` flags it or the base transcript has no sound-alike):

| Merab + Nouman (test) | med_recall | strength | neg_recall | neg_flips | avoid_violations | right / wrong | wrong unflagged | + cross-check: wrong unflagged | right flagged |
|---|---|---|---|---|---|---|---|---|---|
| whisper.cpp base-q8 | 10% | 14% | 13% | 10 | 1 | 3 / 11 | 0 | | |
| whisper.cpp base-q8 + hints | 19% | 21% | 19% | 9 | 1 | 5 / 3 | 2 | | |
| hf synth-full-s250 (+ hf base witness) | 40% | 14% | 63% | 5 | 0 | 14 / 28 | 10 | 0 | 4 / 14 |
| **whisper.cpp ft-s250-q8 (+ base-q8 witness)** | **46%** | **36%** | **61%** | **4** | **0** | 16 / 27 | 4 | **0** | 7 / 16 |

Hadi (dev), same pair: med_recall 31% (PyTorch 46%, base-q8 8%), neg_recall 47%, neg_flips 5, wrong unflagged after cross-check 0, right flagged 3 of 5.

1. **The fine-tune survives conversion to the phone runtime.** On held-out speakers, whisper.cpp q8 gives 46% of medicines in the note (base-q8: 10%), and no wrong medicine passes unflagged once base-q8 cross-checks.
2. **The whisper.cpp witness flags more correct medicines** (7 of 16, vs 4 of 14 with the PyTorch witness), so the doctor confirms more by hand. Precision is still twice base's.
3. **Clip-level variance between runtimes is large** (Hadi: 31% vs 46% of medicines), with only 13 clips per speaker. Treat differences under ~10 points as noise until more speakers are recorded.

# Rerun on the new PC, 13 November 2026 (the run of record)

Everything from "Urdu note writers on the A4000" onward was redone from scratch on this PC, following `NEXT_STEPS.md`. Progress and commits are in `results/PROGRESS.md`. "Earlier run" below means the A4000 run of 9 to 11 November, whose summary tables are in `results/a4000_snapshot/`.

**Machine:** NVIDIA RTX A4000 16 GB, driver 596.71 (nvidia-smi reports CUDA 13.2), Windows 11 Pro 10.0.22621, Intel i7-13700, 32 GB RAM. Python 3.12.10, torch 2.14.1+cu126, torchaudio 2.11.0+cu126, transformers 5.23.0. llama.cpp b11912 prebuilt `win-cuda-12.4-x64` (commit 961c376a2). whisper.cpp b5454 prebuilt `whisper-bin-x64`; whisper.cpp source at d2c6f05 for conversion. Repo commit before the run: `7b1d7af`. The GPU is the same model as the earlier run's; the Python packages were installed fresh and their versions on the earlier machine were not recorded.

**Protocol, fixed before any result:** Hadi is the dev speaker, Merab and Nouman the test speakers. The checkpoint rule was written into `rerun_tables.py` before any model was trained (fewest avoid violations, then most medicines in the note from the phone note writer on Hadi, ties by fewer wrong medicines unflagged). The test speakers were run once.

**New helper scripts** (no scoring script, prompt, reference or answer key was changed): `rerun_notes.py` (starts llama-server per model and calls `run_note.py`), `rerun_bias_noguard.py`, `rerun_tables.py` (per-speaker-group tables, checkpoint choice, cross-check). `rerun_tables.py` was checked against the snapshot: it gives the earlier run's published numbers for the runs the snapshot contains.

**Summary of agreement with the earlier run**

| item | agrees? |
|---|---|
| Urdu note writers | identical, every row |
| Phone-tier note writers, cap, DRY, hints, negation guard | identical, every row |
| PyTorch Whisper parity | small agrees; base is 4 to 7 points lower here |
| Lexicon biasing | **differs:** the unbiased Hadi baseline is 16 points lower here, so λ=2 and 3 now beat it on drug_recall |
| Synthetic fine-tune, ASR metrics | same pattern; several single cells differ by more than 10 points |
| End to end, checkpoint choice | same checkpoint (`synth-full-s250`); test medicines 44% vs 40% |
| Confidence and cross-check | agrees: confidence weak, cross-check flags every invented drug |
| Phone pair in whisper.cpp | headline agrees (50% vs 46% of medicines, 0 wrong unflagged); **one avoid violation here (0 before)**; Hadi 54% vs 31% |

## Rerun: Urdu note writers, 13 November 2026

Commands (`rerun_notes.py urdu`), for each model in turn:

    llama.cpp/build/bin/llama-server -m models/<file> -ngl 99 -c 4096 --jinja --port 8080
    python run_note.py --source ref                --model-tag <tag> --timeout 300
    python run_note.py --source avx2_base-q8_ur_t4 --model-tag <tag> --timeout 300

Models and files as in `plan.txt` (all Q4_K_M), downloaded with `hf download <repo> <file> --local-dir models` under `HF_HUB_DISABLE_XET=1`. `ref__qwen35-4b` is the earlier cloud run, not redone. Then `score_note.py`, `drug_check.py`, `report.py`.

| run | schema_valid | med_recall | strength_recall | extra_meds | avoid_violations | neg_recall | neg_flips | wrong_passed | avoid_passed | GGUF GB |
|---|---|---|---|---|---|---|---|---|---|---|
| ref → qwen35-4b (cloud, earlier) | 100% | 85% | 86% | 0 | 0 | 83% | 3 | 0 | 0 | 3.01 |
| ref → alif-8b | 100% | 81% | 48% | 3 | 0 | 26% | 9 | 0 | 0 | 4.92 |
| ref → alif-3b | 62% | 88% | 75% | 14 | 6 | 69% | 6 | 0 | 6 | 2.24 |
| ref → qalb-8b | 100% | 15% | 14% | 0 | 0 | 4% | 3 | 0 | 0 | 4.92 |
| ref → shaheen-7b | 85% | 67% | 80% | 0 | 0 | 77% | 15 | 0 | 0 | 4.68 |
| base ur → qwen35-4b | 97% | 8% | 10% | 19 | 1 | 31% | 8 | 0 | 1 | 3.01 |
| base ur → alif-8b | 92% | 10% | 5% | 35 | 1 | 16% | 12 | 0 | 1 | 4.92 |
| base ur → alif-3b | 44% | 9% | 20% | 15 | 2 | 4% | 6 | 0 | 2 | 2.24 |
| base ur → qalb-8b | 100% | 0% | 0% | 0 | 0 | 1% | 0 | 0 | 0 | 4.92 |
| base ur → shaheen-7b | 49% | 13% | 11% | 12 | 2 | 44% | 5 | 0 | 2 | 4.68 |

**Agrees with the earlier run: every cell is identical**, including the number of invalid notes per run (qwen35-4b 1, alif-8b 3, alif-3b 15 + 22, shaheen-7b 6 + 20). Same GPU model, same llama.cpp build, temperature 0. The earlier findings stand unchanged: no Urdu model beat qwen35-4b on base output; alif-3b is not usable as it stands; the speech step costs nearly everything. Nothing failed: every server started with `--jinja` and all 9 runs wrote 39 notes. Timings and RAM in `note_summary.csv` are desktop-GPU figures and say nothing about phones.

## Rerun: phone-tier note writers, schema cap, negation guard and drug-name hints, 13 November 2026

Commands (`rerun_notes.py phone`). Server as above; `-dry` runs add `--dry-multiplier 0.8` to the server. GGUFs: `bartowski/Qwen_Qwen3.5-{0.8B,2B,4B}-GGUF` (`Qwen_Qwen3.5-<size>-Q4_K_M.gguf`, and `Qwen_Qwen3.5-4B-IQ3_M.gguf`), each checked to exist before download.

    python run_note.py --source <src> --model-tag <tag>       --timeout 300                                   # plain and -dry
    python run_note.py --source <src> --model-tag <tag>-cap   --timeout 300 --schema note_schema_capped.json
    python run_note.py --source <src> --model-tag <tag>-hints --timeout 300 --schema note_schema_capped.json --hints --prompt note_system_hints.txt

Sources: `ref` and `avx2_base-q8_ur_t4` for every model; also `avx2_small-q8_ur_t2` for the 4B `-cap` and `-hints` runs. 30 runs of 39 notes. Then `score_note.py`, `drug_check.py`, `negation_guard.py`, `drug_hints.py`, `report.py`.

| run (capped schema) | schema_valid | med_recall | strength_recall | extra_meds | avoid_violations | neg_recall | neg_flips | GGUF GB |
|---|---|---|---|---|---|---|---|---|
| ref → qwen3.5 4b Q4_K_M | 100% | 88% | 86% | 0 | 0 | 83% | 3 | 3.01 |
| ref → qwen3.5 4b IQ3_M | 100% | 85% | 71% | 0 | 0 | 88% | 0 | 2.48 |
| ref → qwen3.5 2b Q4_K_M | 100% | 78% | 57% | 3 | 0 | 64% | 9 | 1.40 |
| ref → qwen3.5 0.8b Q4_K_M | 100% | 28% | 29% | 21 | 9 | 47% | 34 | 0.58 |
| ref → alif 3b Q4_K_M | 92% | 86% | 71% | 11 | 3 | 65% | 6 | 2.24 |
| base ur → qwen3.5 4b Q4_K_M | 100% | 8% | 10% | 19 | 1 | 33% | 8 | 3.01 |
| base ur → qwen3.5 4b IQ3_M | 100% | 9% | 10% | 14 | 1 | 16% | 13 | 2.48 |
| base ur → qwen3.5 2b Q4_K_M | 100% | 8% | 5% | 23 | 3 | 36% | 14 | 1.40 |
| base ur → qwen3.5 0.8b Q4_K_M | 97% | 1% | 5% | 22 | 3 | 30% | 16 | 0.58 |
| base ur → alif 3b Q4_K_M | 69% | 7% | 21% | 34 | 3 | 5% | 8 | 2.24 |

| run (capped schema) | med_recall | strength_recall | extra_meds | avoid_violations | right suggested | wrong suggested | wrong_passed |
|---|---|---|---|---|---|---|---|
| base ur → 4b Q4_K_M | 8% | 10% | 19 | 1 | 4 | 18 | 0 |
| base ur → 4b Q4_K_M + hints | 23% | 29% | 17 | 2 | 12 | 15 | 8 |
| base ur → 4b IQ3_M | 9% | 10% | 14 | 1 | 4 | 13 | 0 |
| base ur → 4b IQ3_M + hints | 17% | 14% | 5 | 1 | 7 | 4 | 3 |
| small ur → 4b IQ3_M | 23% | 14% | 11 | 2 | 11 | 9 | 0 |
| small ur → 4b IQ3_M + hints | 21% | 10% | 7 | 0 | 9 | 7 | 4 |
| ref → 4b IQ3_M + hints | 77% | 71% | 0 | 0 | 42 | 0 | 0 |

**Agrees with the earlier run: all 30 runs are identical row for row in `note_summary.csv`** (plain, `-dry`, `-cap` and `-hints`), and the `drug_check.py` counts in the hints table are the same.

- Invalid notes per run, plain → capped: 0.8b 18 → 0 (ref) and 34 → 1 (base); 2b 6 → 0 and 24 → 0; 4b 0 → 0 and 1 → 0; alif-3b 15 → 3 and 22 → 12. DRY changed nothing for Qwen (0.8b 18 and 34, 2b 6 and 23, 4b 0 and 1) and little for Alif (7 and 20).
- **Negation guard** (`results/negation_guard.csv`, now tracked): it moved no correctly prescribed medicine in any run (`prescribed_moved` 0 throughout). On reference text it caught every avoid error (alif-3b 6 of 6, alif-3b-cap 3 of 3, qwen3.5 0.8b 3 of 3, 0.8b-cap 9 of 9). On Whisper output it caught 0 to 2 per run and left 1 or 2, as before.
- **Hints quality** (`drug_hints.py`): the hints contain 44% of the key drugs on base output with 134 false candidates, 48% and 122 on small.
- The earlier conclusions stand: the phone note writer is Qwen3.5 4B IQ3_M with the capped schema; hints raise medicines on base output but blind `drug_check.py` (wrong_passed 0 → 8 and 0 → 3), so no medicine is auto-accepted.

## Rerun: PyTorch Whisper parity, 13 November 2026

    python run_asr_hf.py --model openai/whisper-base  --lang ur
    python run_asr_hf.py --model openai/whisper-small --lang ur
    python score_asr.py

All 39 clips:

| | drug_recall | number_recall | neg_kept | sker |
|---|---|---|---|---|
| hf whisper-base ur | 61% | 26% | 59% | 32% |
| whisper.cpp base-q8 ur (laptop) | 67% | 30% | 61% | 33% |
| hf whisper-small ur | 71% | 48% | 79% | 25% |
| whisper.cpp small-q8 ur (cloud) | 72% | 55% | 78% | 24% |

**Partly agrees.** Small matches the earlier run (72%, 50%, 76%, 25%). Base is lower here than in the earlier run (68%, 33%, 61%, 28%): drugs 7 points, numbers 7, sker 4 worse. The gap is concentrated on Hadi, where hf base finds 51% of drugs against 67% in the earlier run and 64% for whisper.cpp base-q8; on the test speakers hf base and whisper.cpp base-q8 are level (66% vs 68% drugs, 36% vs 35% sker). The code and seed are the same; the installed transformers and torch versions are the likely cause, but the earlier versions were not recorded, so that is not verified. PyTorch base is still a usable proxy for the phone build, with this caveat: differences under about 10 points between the two runtimes on 13 clips are noise.

## Rerun: lexicon biasing, 13 November 2026

Hadi only, HF whisper-base `ur`. Not tuned.

    python run_asr_hf.py --model openai/whisper-base --lang ur --bias <1|2|3> --tag-suffix cg --speakers hadi
    python rerun_bias_noguard.py 2 4 6 8 10

`asr_bias.py` as committed always applies the chain guard, so the "no chain guard" rows use `rerun_bias_noguard.py`: the same trie bias with the root bonus paid at every step, reconstructed from the description of the earlier run.

| Hadi, 13 clips | drug_recall | number_recall | neg_kept | sker | Latin words | inserted drugs |
|---|---|---|---|---|---|---|
| no bias | 51% | 27% | 79% | 25% | 0 | 2 |
| λ=1 | 51% | 27% | 79% | 25% | 0 | 2 |
| λ=2 | 67% | 28% | 83% | 26% | 5 | 1 |
| λ=3 | 69% | 31% | 83% | 28% | 13 | 1 |
| λ=2, no chain guard | 67% | 28% | 83% | 26% | 5 | 1 |
| λ=4, no chain guard | 60% | 23% | 60% | 168% | 385 | 2 |
| λ=6, no chain guard | 0% | 0% | 0% | 546% | 212 | 3 |
| λ=8, no chain guard | 0% | 0% | 0% | 621% | 597 | 14 |
| λ=10, no chain guard | 0% | 0% | 0% | 615% | 629 | 25 |

"Inserted drugs" is `drugs_inserted` from `score_asr.py` with the stricter matcher adopted on 10 November, so it is not comparable with the earlier table's column.

**Does not agree with the earlier run on one point, and the conclusion is weaker.** Earlier, no setting beat the unbiased baseline (67% drugs), and biasing was called a negative result. Here the unbiased baseline on Hadi is 51% (see the parity section), and λ=2 and λ=3 give 67% and 69%: 16 to 18 points more drug names, with numbers, negation and sker within 3 points of the baseline. The biased numbers themselves are close to the earlier ones (λ=2: 67% both times; λ=3: 69% vs 72%); what moved is the baseline. So on this run biasing at λ=2 to 3 does help ASR drug_recall on the dev speaker. Three cautions: it is 13 clips of one speaker; the gain only brings PyTorch base up to what whisper.cpp base-q8 gets on Hadi with no bias (64%); and ASR drug_recall is lenient to Urdu script, while the note writer gets 8 to 12% of medicines from such text whichever way it is decoded. The rest agrees: λ=1 changes nothing, λ=4 without the guard starts chaining names, λ≥6 collapses. Biasing was not run on the test speakers or end to end, as instructed, and the pipeline continues with the fine-tune. If biasing is revisited, the fair test is end to end on Hadi against whisper.cpp base-q8.

## Rerun: Whisper base fine-tuned on synthetic Roman-Urdu dictations, 13 November 2026

    python synth_dictation.py --n 6000 --out data/synth/texts.jsonl      # git diff: no change
    python synth_audio.py --texts data/synth/texts.jsonl --out data/synth
    python train_whisper.py --name synth-dec --save-at 250 500
    python train_whisper.py --name synth-full --train-encoder --save-at 250 500
    python run_asr_hf.py --model checkpoints/<ckpt> --lang ur --speakers hadi       # for each of the 6 checkpoints

5,634 of 6,000 items were rendered (366 over 28 s skipped): 5,434 for training and 200 held out, the same counts as the earlier run. Defaults: lr 2e-5 cosine, 2000 steps, batch 16, seed 13. One run at a time: decoder-only took 20 min, full 24 min. Validation loss (held-out synthetic speech) fell from 3.12 to 0.076 / 0.032 / 0.012 at 250 / 500 / 2000 steps (decoder-only) and to 0.030 / 0.013 / 0.003 (full). Logs: `results/train_logs/`. The earlier run's interrupted second decoder-only run (`synth-dec-b`) was not repeated, so the 250- and 500-step decoder-only checkpoints are now tagged `hf_synth-dec-s250_ur` and `hf_synth-dec-s500_ur` (earlier: `hf_synth-dec-b-s250_ur`, `-s500_ur`). The full run completed to 2000 steps this time (`hf_synth-full_ur`), which the earlier run did not have.

Hadi only (13 clips):

| run | drug_recall | number_recall | neg_kept | neg_extra | drugs_inserted | sker |
|---|---|---|---|---|---|---|
| hf whisper-base ur | 51% | 27% | 79% | 1 | 2 | 25% |
| hf whisper-small ur (reference) | 83% | 60% | 87% | 0 | 1 | 16% |
| decoder-only, 250 steps | 67% | 71% | 77% | 6 | 9 | 32% |
| decoder-only, 500 steps | 71% | 83% | 96% | 8 | 15 | 39% |
| decoder-only, 2000 steps | 55% | 92% | 91% | 12 | 22 | 46% |
| full, 250 steps | 71% | 76% | 96% | 5 | 7 | 28% |
| full, 500 steps | 60% | 74% | 92% | 5 | 10 | 35% |
| full, 2000 steps | 67% | 70% | 100% | 7 | 19 | 39% |

`synth-full-s250` on all 39 clips (after the choice below): drugs 73%, numbers 79%, neg_kept 89%, neg_extra 8, drugs_inserted 17, sker 25% (earlier: 64%, 78%, 93%, 16, 19, 26%).

**Agrees with the earlier run in every finding; single cells differ.**

1. The output script changes as intended: Roman Urdu with Latin drug names and digits (about 500 Latin words on Hadi's 13 clips against 0 for base). Numbers go from 27% to 70-92%.
2. The model still writes template text where the audio is unclear. Invented drugs (`drugs_inserted`) are 7 to 22 on Hadi against 2 for base, and extra negations 5 to 12 against 1.
3. More training still means more hallucination: sker and invented drugs rise with steps in both variants (decoder-only 32% → 39% → 46%, 9 → 15 → 22; full 28% → 35% → 39%, 7 → 10 → 19). No checkpoint reaches base's sker on Hadi (25%); `synth-full-s250` is closest at 28%.
4. Cells that differ from the earlier table by more than 10 points: base drug_recall (51% vs 67%, see parity); decoder-only 250 steps drug_recall 67% vs 55% and neg_kept 77% vs 92%; decoder-only 500 steps drug_recall 71% vs 59%; full 250 steps drug_recall 71% vs 58%. `drugs_inserted` is lower throughout here (for example full 250: 7 vs 12). The training commands are reconstructions and the audio was re-rendered, so the checkpoints are not the same weights; with 13 clips these are the size of differences to expect between two trainings.

Sanity: the synthetic clips are 16 kHz, 4.9 to 28.0 s each, 28.6 hours in all (nobody listened to them in this unattended run; that the models learned Roman Urdu from them is the evidence that they are speech), validation loss fell, and transcripts are Roman Urdu, e.g. Hadi dict_10 from `synth-full-s250`: "Penicillin se allergy hai. Is lioxoquantin nahi deni. Zyrtec aadhi goli raat ko."

## Rerun: end to end, fine-tuned Whisper base → phone note writer, 13 November 2026

Note writer: Qwen3.5 4B IQ3_M, capped schema, `note_system.txt`, temperature 0 (`-hints`: `note_system_hints.txt --hints`).

    python rerun_notes.py e2e-dev                                               # every hf_* source, --speakers hadi
    python score_note.py ; python drug_check.py ; python rerun_tables.py choose
    python run_asr_hf.py --model checkpoints/synth-full-s250 --lang ur          # the 26 test clips
    python rerun_notes.py e2e-test --sources hf_base_ur hf_synth-full-s250_ur   # --speakers merab-haroon nouman-tanveer

**Dev, Hadi (13 clips).** In the order the rule ranks them:

| ASR source | med_recall | strength | neg_recall | neg_flips | avoid_violations | right / wrong | unflagged |
|---|---|---|---|---|---|---|---|
| **full, 250 steps** | **46%** | 29% | 49% | 3 | 0 | 9 / 16 | 4 |
| decoder-only, 250 steps | 42% | 29% | 56% | 1 | 0 | 7 / 17 | 7 |
| decoder-only, 500 steps | 35% | 43% | 49% | 2 | 0 | 7 / 13 | 10 |
| full, 500 steps | 31% | 14% | 51% | 2 | 0 | 6 / 15 | 7 |
| full, 2000 steps | 31% | 14% | 44% | 1 | 0 | 7 / 13 | 9 |
| decoder-only, 2000 steps | 23% | 29% | 41% | 1 | 0 | 4 / 17 | 15 |
| hf whisper-base ur | 12% | 0% | 27% | 3 | 0 | 2 / 2 | 0 |
| hf whisper-base ur + hints | 12% | 0% | 23% | 3 | 0 | 2 / 2 | 1 |
| reference text | 85% | 71% | 86% | 0 | 0 | 15 / 0 | 0 |

**Chosen: `synth-full-s250`,** the same checkpoint as the earlier run. No checkpoint has an avoid violation, and it has the most medicines in the note (46%, the same figure as before) and the fewest wrong medicines unflagged among the fine-tuned ones. It beats stock base end to end on Hadi (46% vs 12%), so the "did not reproduce" branch of NEXT_STEPS does not apply.

**Test, Merab + Nouman (26 clips), run once with `synth-full-s250`:**

| ASR source | sker | number_recall | neg_kept | med_recall | strength | neg_recall | neg_flips | avoid_violations | right / wrong | unflagged |
|---|---|---|---|---|---|---|---|---|---|---|
| hf whisper-base ur | 36% | 25% | 50% | 10% | 7% | 14% | 10 | 1 | 3 / 10 (23%) | 0 |
| hf whisper-base ur + hints | | | | 17% | 21% | 17% | 10 | 1 | 5 / 2 (71%) | 2 |
| hf whisper-small ur (reference) | 30% | 42% | 76% | | | | | | | |
| **synth-full-s250** | **24%** | **80%** | **85%** | **44%** | 7% | **50%** | **7** | **0** | **15 / 30 (33%)** | 7 |
| reference text | | | | 85% | 71% | 90% | 0 | 0 | 30 / 0 | 0 |

**Agrees with the earlier run** (its corrected test row: medicines 40%, strength 14%, neg_recall 63%, flips 5, avoid 0, 14 / 28, 10 unflagged; base 12%, 14%, 16%, 10, 1, 4 / 18, 0).

1. On unseen speakers, medicines reaching the note go 10% → 44% (earlier 12% → 40%), and no avoided drug is listed as prescribed.
2. **Negatives improve less than before:** neg_recall 14% → 50% (earlier 16% → 63%, a 13-point smaller result), and flips fall from 10 to 7 (earlier 10 to 5).
3. Suggestion precision is 33% against 23% for base (earlier 37% vs 19%). The earlier "doubles" is now "rises by about half".
4. **Strengths do not improve, and are lower here: 7% (earlier 14%), the same as base.**
5. The ASR invents drugs and that blinds `drug_check.py`: 7 wrong medicines pass unflagged (earlier 10; base 0). Auto-accept stays off.
6. Less training is still better: medicines in the note fall with steps in both variants, and wrong medicines unflagged rise.
7. A different point from before: hints on plain base give 17% of medicines at 71% precision (5 right, 2 wrong) on the test speakers. That is far fewer medicines than the fine-tune but a much higher share of right ones; 2 of its wrong ones pass unflagged.

## Rerun: catching drugs the fine-tuned ASR invents, 13 November 2026

    python asr_confidence.py --model checkpoints/synth-full-s250 --tag hf_synth-full-s250_ur
    python rerun_tables.py confidence --tag hf_synth-full-s250_ur
    python rerun_tables.py crosscheck --tag hf_synth-full-s250_ur --witness hf_base_ur      # writes results/crosscheck.csv
    python rerun_tables.py e2e --group test --witness hf_base_ur --runs ...

The 30 s fix (`truncation=False`) was already in `run_asr_hf.py` for this run, so no clip was cut; `asr_confidence.py` reported 0 long clips whose segments differ from the saved text.

**1. Whisper's own confidence is a weak check.** The fine-tuned model writes 48 drug names, 31 said and 17 invented (earlier 52, 33, 19). AUC for said vs invented with the lowest token probability is 0.57 (Hadi) and 0.65 (test); with the mean token probability 0.66 and 0.81 (earlier 0.57 / 0.71 and 0.67 / 0.78). At the cut-off fixed on Hadi (flag at most 1 in 5 said drugs: min_p < 0.189, which flags 2 of 11 said and 1 of 7 invented on Hadi), it catches 2 of 10 invented drugs on the test speakers and flags 3 of 20 said ones (earlier 1 of 11). Agrees.

**2. Cross-checking against plain whisper-base works.** A drug the fine-tuned model writes is flagged when base's transcript of the same audio has nothing that sounds like it:

| written by synth-full-s250 | invented drugs flagged | said drugs flagged |
|---|---|---|
| Hadi (dev) | 7 / 7 | 4 / 11 |
| Merab + Nouman (test) | **10 / 10** | 5 / 20 |

Agrees (earlier 8 / 8 and 3 / 11; 11 / 11 and 5 / 22).

**3. End to end** (Qwen3.5 4B IQ3_M, capped schema; a note medicine is flagged if `drug_check.py` flags it or base's transcript has no sound-alike):

| Merab + Nouman (test) | med_recall | strength | neg_recall | neg_flips | avoid_violations | right / wrong | wrong unflagged | right flagged for review |
|---|---|---|---|---|---|---|---|---|
| hf whisper-base ur | 10% | 7% | 14% | 10 | 1 | 3 / 10 | 0 | |
| hf whisper-base ur + hints | 17% | 21% | 17% | 10 | 1 | 5 / 2 | 2 | |
| synth-full-s250 | 44% | 7% | 50% | 7 | 0 | 15 / 30 | 7 | |
| **synth-full-s250 + base cross-check** | 44% | 7% | 50% | 7 | 0 | 15 / 30 | **0** | 6 / 15 |

On Hadi the same gate takes wrong-unflagged from 4 to 0 and flags 3 of 9 right medicines. **Agrees with the earlier run** (10 → 0 on test, 4 of 14 right flagged; Hadi 3 → 0, 2 of 8). On these 26 test clips, 9 of 15 correct medicines arrive unflagged and every wrong one is flagged. The proposed pipeline stands: fine-tuned base writes the transcript, plain base is the independent witness, every medicine is a one-tap confirm.

## Rerun: the phone pair in whisper.cpp, 13 November 2026

    # vocab.json and added_tokens.json from openai/whisper-base copied next to the checkpoint; mel filters from github.com/openai/whisper
    python whisper.cpp/src/models/convert-h5-to-ggml.py <checkpoint copy> <openai-whisper clone> <out dir>
    whisper.cpp/build/bin/whisper-quantize <out dir>/ggml-model.bin models/ft-synth-full-s250/ggml-model-q8_0.bin q8_0
    python run_asr.py --models ft-s250-q8 --langs ur --threads 4          # tag avx2_ft-s250-q8_ur_t4
    python rerun_notes.py phone-pair                                      # IQ3_M, capped schema, 39 clips
    python rerun_tables.py e2e --group test --witness avx2_base-q8_ur_t4 --runs ...

The chosen checkpoint is the same as before, so the folder name and the `config.json` entry are unchanged. The q8_0 file is 78 MB (81,768,602 bytes), tracked in git. whisper.cpp b5454 `whisper-bin-x64`, `-t 4 -l ur`; the witness `avx2_base-q8_ur_t4` is the laptop run with the same build. On this desktop CPU: about 0.8 s per clip, 280 MB peak RAM, which says nothing about phones.

ASR, whisper.cpp vs PyTorch:

| | Hadi sker | Hadi numbers | test drug_recall | test number_recall | test neg_kept | test neg_extra | test drugs_inserted | test sker |
|---|---|---|---|---|---|---|---|---|
| hf whisper-base ur | 25% | 27% | 66% | 25% | 50% | 0 | 3 | 36% |
| whisper.cpp base-q8 | 27% | 32% | 68% | 29% | 52% | 0 | 3 | 35% |
| hf synth-full-s250 | 28% | 76% | 74% | 80% | 85% | 3 | 10 | 24% |
| **whisper.cpp ft-s250-q8** | 29% | 71% | 80% | 80% | 86% | 4 | 8 | **23%** |

Aggregates carry over, as before. Word for word they do not: 4 of 39 transcripts are identical between the two runtimes.

End to end, the phone pair (whisper.cpp ft-s250-q8 writes the transcript, whisper.cpp base-q8 is the witness):

| Merab + Nouman (test) | med_recall | strength | neg_recall | neg_flips | avoid_violations | right / wrong | wrong unflagged | + cross-check: wrong unflagged | right flagged |
|---|---|---|---|---|---|---|---|---|---|
| whisper.cpp base-q8 | 10% | 14% | 13% | 10 | 1 | 3 / 11 | 0 | | |
| whisper.cpp base-q8 + hints | 19% | 21% | 19% | 9 | 1 | 5 / 3 | 2 | | |
| hf synth-full-s250 (+ hf base witness) | 44% | 7% | 50% | 7 | 0 | 15 / 30 | 7 | 0 | 6 / 15 |
| **whisper.cpp ft-s250-q8 (+ base-q8 witness)** | **50%** | 21% | **47%** | **5** | **1** | 18 / 26 | 5 | **0** | 9 / 18 |

Hadi (dev), same pair: med_recall 54% (PyTorch 46%, base-q8 8%), strength 43%, neg_recall 49%, neg_flips 1, avoid_violations 0, right / wrong 10 / 9, wrong unflagged 3 and 0 after the cross-check, right flagged 5 of 10.

**The headline agrees with the earlier run: 50% of medicines in the note against 10% for stock base-q8 (earlier 46% against 10%), and 0 wrong medicines unflagged after the cross-check (earlier 0).** Differences, stated plainly:

1. **One avoid violation here; the earlier run had none.** Merab dict_02: the fine-tuned model wrote "Brufolone lena" for "Brufen bilkul nahi leni", losing the "nahi", and the note lists "Brufolone" as prescribed. `drug_check.py` flags it (not a lexicon name), so it does not reach the doctor unflagged (`avoid_passed` 0), and the negation guard cannot catch it because the transcript has no negation. Stock base-q8 has the same count (1 avoid violation, on Augmentin, which passes unflagged). So the fine-tune no longer shows an advantage on avoided drugs in the phone runtime; the earlier "no avoided drug is listed as prescribed" does not hold for whisper.cpp here.
2. **Negatives are lower:** neg_recall 47% (earlier 61%), a 14-point difference. Strength is 21% (earlier 36%), 15 points lower.
3. **The witness flags half the correct medicines** (9 of 18; earlier 7 of 16), so the doctor confirms more by hand.
4. **Hadi is 54% here against 31% before** (23 points). The earlier note about clip-level variance between runtimes applies in both directions: on 13 clips, treat differences under about 10 points as noise and larger single-speaker swings with caution.
5. The fine-tune survives conversion to the phone runtime: precision is 41% (18 of 44) against 21% for base-q8 (3 of 14), and ASR sker on the test speakers is 23% against 35%.

**Caveats, unchanged:** 3 speakers, 39 clips, one dev speaker, all 18 to 24; every speaker read the same dict_01-10 scripts; `lexicon.txt` is a 318-entry placeholder; own-words references are drafts. The phone timings and RAM are not measured yet (`phone/README.md`).

## Phone test: Google Pixel 8 Pro, 14 November 2026

    # in Termux (F-Droid), after pkg upgrade -y; models downloaded on the phone with wget
    bash ~/storage/downloads/nabz/termux_bench.sh        # results/phone/google-pixel-8-pro.txt

Google Pixel 8 Pro, Tensor G3, Android 17, 11.3 GB RAM, CPU only, 4 threads. whisper.cpp b5454 and llama.cpp b11912
(961c376) compiled on the phone, the same versions as the PC runs. One run; battery level and temperature were not
recorded. The Qwen file is the PC's file (2,483,333,088 bytes); llama-bench labels it "IQ3_S mix, 3.66 bpw".

Speech to text (`whisper-cli -l ur -t 4`, beam 5), wall seconds:

| clip | audio | ft-s250-q8 | base-q8 (witness) | both | peak RAM |
|---|---|---|---|---|---|
| hadi dict_01 | 20.6 s | 7.5 | 10.2 | 17.8 | 221 MB |
| merab-haroon dict_05 (longest) | 37.6 s | 11.6 | 12.7 | 24.2 | 260 MB |
| nouman-tanveer own_01 (shortest) | 12.1 s | 6.2 | 8.0 | 14.2 | 220 MB |

Note writer (Qwen3.5 4B IQ3_M, `llama-bench -p 400 -n 360 -t 4`): prompt 3.98 tokens/s, generation 2.32 tokens/s,
peak RAM 3,519 MB. A cold-start p90 note is 400 / 3.98 + 360 / 2.32 = 101 + 155 = **256 s, about 4 minutes 16 seconds**.

Against the budgets in `config.json` (30 s each, p90):

1. **Speech fits.** Both models on the worst-case clip take 24.2 s. The two models run one after the other here; the
   margin on the 37.6 s clip is 6 s.
2. **The note writer does not fit: 256 s against 30 s, about 8.5 times over.** Generation alone (155 s) is 5 times
   the budget, so caching the system prompt does not rescue it.
3. **RAM: 3.5 GB for the note writer.** Fine on this phone; over the "much over ~3 GB is a risk" line of
   `phone/README.md` for a 6 GB phone.

**This phone is a flagship with 11.3 GB RAM, not the mid-range 6-8 GB phone `phone/README.md` asks for.** A mid-range
phone will be slower, so the speech margin may not hold there and the note writer will be further over. Not measured:
a mid-range phone, a second run when hot, Qwen3.5 2B on a phone, GPU or NPU back ends.

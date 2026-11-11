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

## Urdu note writers on the A4000, 9 November 2026

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

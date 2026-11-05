# Nabz Scribe spike results (2026-11-05)

Speakers scored: 3 (hadi, merab-haroon, nouman-tanveer)

## Speech to text

| tag | clips | rtf_median | dict_proc_p90_s | peak_ram_mb | drug_recall | number_recall | neg_kept | sker | within_budget |
|---|---|---|---|---|---|---|---|---|---|
| avx2_turbo-q8_ur_t2 | 39 | 2.28 | 72.5 | 1141 | 73% | 57% | 75% | 23% | no |
| avx2_small-q8_ur_t2 | 39 | 0.9 | 31.1 | 592 | 72% | 55% | 78% | 24% | no |
| avx2_small-q8_auto_t2 | 39 | 1.06 | 41.3 | 592 | 70% | 61% | 87% | 19% | no |
| avx2_base-q8_ur_t2 | 39 | 0.36 | 11.7 | 271 | 61% | 23% | 60% | 32% | yes |
| avx2_base-q8_auto_t2 | 39 | 0.43 | 15.9 | 263 | 56% | 35% | 62% | 30% | yes |
| avx2_base-q8_en_t2 | 39 | 0.26 | 26.4 | 261 | 35% | 36% | 56% | 68% | yes |
| avx2_small-q8_en_t2 | 39 | 0.58 | 18.8 | 557 | 32% | 46% | 48% | 63% | yes |

SkER is a rough, script-independent error rate on consonant skeletons. Compare it between rows, not against published WER numbers.

## Note writer

| run | notes | schema_valid | wall_median_s | wall_p90_s | server_ram_mb | med_recall | strength_recall | extra_meds | avoid_violations | neg_recall | neg_flips | within_budget |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| avx2_small-q8_ur_t2__gemma4-e2b | 39 | 100% | 50.5 | 67.4 | 4664 | 12% | 0% | 5 | 1 | 36% | 29 | no |
| avx2_small-q8_ur_t2__qwen35-4b | 39 | 97% | 68.2 | 207.8 | 5937 | 24% | 14% | 23 | 4 | 46% | 5 | no |
| ref__gemma4-e2b | 39 | 100% | 57.8 | 75.7 | 4225 | 68% | 57% | 0 | 0 | 64% | 24 | no |
| ref__qwen35-4b | 39 | 100% | 78.1 | 100.6 | 5816 | 85% | 86% | 0 | 0 | 83% | 3 | no |

Rows with source `ref` show the LLM's own errors on clean text. Rows with an ASR tag show the whole pipeline. The gap between them is what speech recognition costs.

## Decision rules

- Keep the smallest speech model that is within budget and finds most drug names.
- If none is within budget, drop to the next smaller model or fewer beams before touching the LLM.
- Any avoid violation or negation flip on reference text is a prompt or model problem: fix it before the pilot.
- Timings come from a fast laptop CPU. Rerun the chosen setting on a real old lab PC before trusting them.

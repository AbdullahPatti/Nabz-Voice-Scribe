# Nabz Scribe spike results (2026-11-13)

Speakers scored: 3 (hadi, merab-haroon, nouman-tanveer)

## Speech to text

| tag | clips | rtf_median | dict_proc_p90_s | peak_ram_mb | drug_recall | number_recall | neg_kept | sker | within_budget |
|---|---|---|---|---|---|---|---|---|---|
| avx2_base-q8_ur_t4_whisper_drugs | 39 | 0.19 | 9.6 | 334 | 76% | 38% | 30% | 36% | yes |
| avx2_turbo-q8_ur_t2 | 39 | 2.28 | 72.5 | 1141 | 73% | 57% | 75% | 23% | no |
| avx2_small-q8_ur_t2 | 39 | 0.9 | 31.1 | 592 | 72% | 55% | 78% | 24% | no |
| hf_small_ur | 39 | 0.07 | 1.7 |  | 71% | 48% | 79% | 25% | yes |
| avx2_small-q8_auto_t2 | 39 | 1.06 | 41.3 | 592 | 70% | 61% | 87% | 19% | no |
| hf_base_ur_bias3_cg | 13 | 0.06 | 1.9 |  | 69% | 31% | 83% | 28% | yes |
| avx2_base-q8_auto_t4_whisper_drugs | 39 | 0.25 | 16.6 | 343 | 68% | 37% | 29% | 38% | yes |
| avx2_base-q8_ur_t4_whisper_drugs_nokey | 39 | 0.18 | 12.5 | 330 | 68% | 38% | 39% | 32% | yes |
| avx2_base-q8_ur_t4 | 39 | 0.14 | 6.1 | 272 | 67% | 30% | 61% | 33% | yes |
| hf_base_ur_bias2 | 13 | 0.06 | 3.6 |  | 67% | 28% | 83% | 26% | yes |
| hf_base_ur_bias2_cg | 13 | 0.06 | 3.5 |  | 67% | 28% | 83% | 26% | yes |
| avx2_base-q8_ur_t2 | 39 | 0.36 | 11.7 | 271 | 61% | 23% | 60% | 32% | yes |
| hf_base_ur | 39 | 0.04 | 3.2 |  | 61% | 26% | 59% | 32% | yes |
| hf_base_ur_bias4 | 13 | 0.06 | 11.9 |  | 60% | 23% | 60% | 168% | yes |
| avx2_base-q8_auto_t4 | 39 | 0.19 | 8.0 | 263 | 58% | 41% | 66% | 29% | yes |
| avx2_base-q8_auto_t2 | 39 | 0.43 | 15.9 | 263 | 56% | 35% | 62% | 30% | yes |
| avx2_base-q8_auto_t4_whisper_drugs_nokey | 39 | 0.22 | 14.7 | 335 | 56% | 32% | 35% | 36% | yes |
| hf_base_ur_bias1_cg | 13 | 0.06 | 3.3 |  | 51% | 27% | 79% | 25% | yes |
| avx2_base-q8_en_t2 | 39 | 0.26 | 26.4 | 261 | 35% | 36% | 56% | 68% | yes |
| avx2_small-q8_en_t2 | 39 | 0.58 | 18.8 | 557 | 32% | 46% | 48% | 63% | yes |
| hf_base_ur_bias10 | 13 | 0.94 | 15.4 |  | 0% | 0% | 0% | 615% | yes |
| hf_base_ur_bias6 | 13 | 0.91 | 14.0 |  | 0% | 0% | 0% | 546% | yes |
| hf_base_ur_bias8 | 13 | 0.9 | 15.2 |  | 0% | 0% | 0% | 621% | yes |

SkER is a rough, script-independent error rate on consonant skeletons. Compare it between rows, not against published WER numbers.

## Note writer

| run | notes | schema_valid | wall_median_s | wall_p90_s | server_ram_mb | med_recall | strength_recall | extra_meds | avoid_violations | neg_recall | neg_flips | within_budget |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| avx2_base-q8_ur_t4__alif-3b | 39 | 44% | 6.1 | 6.3 | 7269 | 9% | 20% | 15 | 2 | 4% | 6 | yes |
| avx2_base-q8_ur_t4__alif-3b-cap | 39 | 69% | 4.3 | 6.3 | 6511 | 7% | 21% | 34 | 3 | 5% | 8 | yes |
| avx2_base-q8_ur_t4__alif-3b-dry | 39 | 49% | 6.0 | 6.6 | 6718 | 13% | 27% | 16 | 2 | 4% | 6 | yes |
| avx2_base-q8_ur_t4__alif-8b | 39 | 92% | 4.2 | 5.3 | 8045 | 10% | 5% | 35 | 1 | 16% | 12 | yes |
| avx2_base-q8_ur_t4__qalb-8b | 39 | 100% | 2.1 | 2.1 | 6613 | 0% | 0% | 0 | 0 | 1% | 0 | yes |
| avx2_base-q8_ur_t4__qwen25-7b-ollama | 39 | 79% | 4.6 | 13.2 | 1868 | 6% | 12% | 6 | 0 | 38% | 7 | yes |
| avx2_base-q8_ur_t4__qwen25-7b-ollama-v2 | 39 | 92% | 5.7 | 8.6 | 2385 | 3% | 5% | 9 | 2 | 31% | 7 | yes |
| avx2_base-q8_ur_t4__qwen35-0.8b | 39 | 13% | 3.1 | 3.1 | 4631 | 0% | 0% | 2 | 0 | 40% | 2 | yes |
| avx2_base-q8_ur_t4__qwen35-0.8b-cap | 39 | 97% | 2.7 | 3.1 | 5103 | 1% | 5% | 22 | 3 | 30% | 16 | yes |
| avx2_base-q8_ur_t4__qwen35-0.8b-dry | 39 | 13% | 3.1 | 3.1 | 4634 | 0% | 0% | 2 | 0 | 40% | 2 | yes |
| avx2_base-q8_ur_t4__qwen35-2b | 39 | 38% | 4.7 | 4.8 | 5027 | 7% | 20% | 4 | 0 | 42% | 4 | yes |
| avx2_base-q8_ur_t4__qwen35-2b-cap | 39 | 100% | 2.3 | 4.0 | 6479 | 8% | 5% | 23 | 3 | 36% | 14 | yes |
| avx2_base-q8_ur_t4__qwen35-2b-dry | 39 | 41% | 4.8 | 4.9 | 5025 | 6% | 17% | 5 | 0 | 42% | 5 | yes |
| avx2_base-q8_ur_t4__qwen35-4b | 39 | 97% | 2.8 | 4.9 | 7251 | 8% | 10% | 19 | 1 | 31% | 8 | yes |
| avx2_base-q8_ur_t4__qwen35-4b-cap | 39 | 100% | 2.7 | 3.6 | 9081 | 8% | 10% | 19 | 1 | 33% | 8 | yes |
| avx2_base-q8_ur_t4__qwen35-4b-dry | 39 | 97% | 2.8 | 4.7 | 9283 | 8% | 10% | 19 | 1 | 31% | 8 | yes |
| avx2_base-q8_ur_t4__qwen35-4b-hints | 39 | 100% | 3.0 | 4.4 | 11757 | 23% | 29% | 17 | 2 | 31% | 8 | yes |
| avx2_base-q8_ur_t4__qwen35-4b-iq3m-cap | 39 | 100% | 2.8 | 3.5 | 8573 | 9% | 10% | 14 | 1 | 16% | 13 | yes |
| avx2_base-q8_ur_t4__qwen35-4b-iq3m-hints | 39 | 100% | 2.6 | 3.4 | 11239 | 17% | 14% | 5 | 1 | 20% | 10 | yes |
| avx2_base-q8_ur_t4__shaheen-7b | 39 | 49% | 10.9 | 11.1 | 6681 | 13% | 11% | 12 | 2 | 44% | 5 | yes |
| avx2_small-q8_ur_t2__gemma4-e2b | 39 | 100% | 50.5 | 67.4 | 4664 | 12% | 0% | 5 | 1 | 36% | 29 | no |
| avx2_small-q8_ur_t2__qwen25-7b-ollama | 14 | 93% | 4.5 | 8.9 | 1467 | 4% | 0% | 2 | 0 | 58% | 0 | yes |
| avx2_small-q8_ur_t2__qwen35-4b | 39 | 97% | 68.2 | 207.8 | 5937 | 24% | 14% | 23 | 4 | 46% | 5 | no |
| avx2_small-q8_ur_t2__qwen35-4b-cap | 39 | 100% | 3.3 | 4.4 | 10977 | 28% | 24% | 25 | 4 | 52% | 6 | yes |
| avx2_small-q8_ur_t2__qwen35-4b-hints | 39 | 100% | 3.2 | 3.7 | 11746 | 31% | 33% | 13 | 2 | 49% | 10 | yes |
| avx2_small-q8_ur_t2__qwen35-4b-iq3m-cap | 39 | 100% | 3.0 | 3.3 | 11113 | 23% | 14% | 11 | 2 | 31% | 7 | yes |
| avx2_small-q8_ur_t2__qwen35-4b-iq3m-hints | 39 | 100% | 2.6 | 3.6 | 11229 | 21% | 10% | 7 | 0 | 38% | 10 | yes |
| ref__alif-3b | 39 | 62% | 3.8 | 6.2 | 3816 | 88% | 75% | 14 | 6 | 69% | 6 | yes |
| ref__alif-3b-cap | 39 | 92% | 2.8 | 4.7 | 3429 | 86% | 71% | 11 | 3 | 65% | 6 | yes |
| ref__alif-3b-dry | 39 | 82% | 2.3 | 6.1 | 3393 | 80% | 60% | 16 | 6 | 67% | 8 | yes |
| ref__alif-8b | 39 | 100% | 4.2 | 5.1 | 5720 | 81% | 48% | 3 | 0 | 26% | 9 | yes |
| ref__gemma4-e2b | 39 | 100% | 57.8 | 75.7 | 4225 | 68% | 57% | 0 | 0 | 64% | 24 | no |
| ref__qalb-8b | 39 | 100% | 2.0 | 2.8 | 5101 | 15% | 14% | 0 | 0 | 4% | 3 | yes |
| ref__qwen25-7b-ollama | 39 | 100% | 5.8 | 7.1 | 1113 | 60% | 76% | 3 | 0 | 68% | 12 | yes |
| ref__qwen35-0.8b | 39 | 54% | 2.4 | 3.0 | 2137 | 17% | 33% | 3 | 3 | 52% | 22 | yes |
| ref__qwen35-0.8b-cap | 39 | 100% | 2.4 | 2.7 | 4694 | 28% | 29% | 21 | 9 | 47% | 34 | yes |
| ref__qwen35-0.8b-dry | 39 | 54% | 2.4 | 3.1 | 2137 | 17% | 33% | 3 | 3 | 52% | 22 | yes |
| ref__qwen35-2b | 39 | 85% | 2.5 | 4.6 | 2730 | 74% | 67% | 3 | 0 | 71% | 3 | yes |
| ref__qwen35-2b-cap | 39 | 100% | 2.4 | 2.6 | 5163 | 78% | 57% | 3 | 0 | 64% | 9 | yes |
| ref__qwen35-2b-dry | 39 | 85% | 2.5 | 4.7 | 2733 | 74% | 67% | 3 | 0 | 71% | 3 | yes |
| ref__qwen35-4b | 39 | 100% | 78.1 | 100.6 | 5816 | 85% | 86% | 0 | 0 | 83% | 3 | no |
| ref__qwen35-4b-cap | 39 | 100% | 3.2 | 4.0 | 5352 | 88% | 86% | 0 | 0 | 83% | 3 | yes |
| ref__qwen35-4b-dry | 39 | 100% | 3.2 | 4.0 | 5345 | 88% | 86% | 0 | 0 | 83% | 3 | yes |
| ref__qwen35-4b-hints | 39 | 100% | 3.4 | 4.5 | 11716 | 81% | 71% | 0 | 0 | 85% | 3 | yes |
| ref__qwen35-4b-iq3m-cap | 39 | 100% | 3.4 | 4.0 | 4685 | 85% | 71% | 0 | 0 | 88% | 0 | yes |
| ref__qwen35-4b-iq3m-hints | 39 | 100% | 3.2 | 3.9 | 11233 | 77% | 71% | 0 | 0 | 88% | 6 | yes |
| ref__shaheen-7b | 39 | 85% | 4.0 | 10.9 | 5015 | 67% | 80% | 0 | 0 | 77% | 15 | yes |

Rows with source `ref` show the LLM's own errors on clean text. Rows with an ASR tag show the whole pipeline. The gap between them is what speech recognition costs.

## Decision rules

- Keep the smallest speech model that is within budget and finds most drug names.
- If none is within budget, drop to the next smaller model or fewer beams before touching the LLM.
- Any avoid violation or negation flip on reference text is a prompt or model problem: fix it before the pilot.
- Timings come from a fast laptop CPU. Rerun the chosen setting on a real old lab PC before trusting them.

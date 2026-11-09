# Nabz Scribe feasibility spike

This toolkit answers one question: **which speech model and which LLM can turn a doctor's 30-second dictation into a correct note within 60 seconds on weak hardware?**

It takes the zips from the recording kit, runs whisper.cpp and a llama.cpp model over every clip, scores what came out against a fixed answer key, and writes one decision table.

```
recordings/       put the zips you receive here
data/             unpacked audio + manifest.csv          (prepare.py)
refs/             reference transcripts you check         (prepare.py, then you)
results/          transcripts, notes, scores, decision_table.md
answer_key.json   drugs, doses, numbers and negations each clip must contain
note_schema.json  the JSON note the LLM must fill
prompts/          the note-writer system prompt
```

Setup takes about 45 minutes once. A full run on 5 speakers takes an evening.

---

## 1. Set up Ubuntu on your laptop (WSL)

The builds and scripts are simplest on Linux. On Windows, use WSL.

In PowerShell as administrator:

```powershell
wsl --install -d Ubuntu
```

Restart, open **Ubuntu** from the Start menu, then:

```bash
sudo apt update
sudo apt install -y build-essential cmake git python3-pip python3-venv unzip libcurl4-openssl-dev
```

Unzip this toolkit inside Ubuntu's home folder, not on C: (files on C: are much slower from WSL). In Windows Explorer, Ubuntu's home is at `\\wsl$\Ubuntu\home\<your-name>\`.

```bash
cd ~/nabz-spike
python3 -m venv .venv
source .venv/bin/activate          # run this line every time you open a new terminal
pip install -r requirements.txt
```

## 2. Build whisper.cpp

```bash
cd ~/nabz-spike
git clone https://github.com/ggml-org/whisper.cpp
cd whisper.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF \
      -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_AVX512=OFF
cmake --build build -j --config Release
```

This build uses only the instructions a 4th-gen or newer Core i3/i5 has, so it runs on an OPD PC. (Earlier I suggested turning AVX2 off. That was too pessimistic: every Core i3/i5 from 4th gen onward has AVX2. Turning it off only models Pentium and Celeron machines.)

Optional worst case, for Pentium/Celeron PCs:

```bash
cmake -B build-noavx2 -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF \
      -DGGML_AVX=ON -DGGML_AVX2=OFF -DGGML_FMA=OFF -DGGML_F16C=OFF -DGGML_AVX512=OFF
cmake --build build-noavx2 -j --config Release
```

## 3. Download the speech models

Still inside `whisper.cpp/`:

```bash
bash ./models/download-ggml-model.sh base-q8_0
bash ./models/download-ggml-model.sh small-q8_0
bash ./models/download-ggml-model.sh large-v3-turbo-q8_0     # optional: the accuracy ceiling
cd ..
```

These are already quantized to INT8, so there is no separate quantize step.

## 4. Unpack the recordings

Put every zip you receive into `recordings/`, then:

```bash
python prepare.py
```

It prints each speaker and lists the reference transcripts that still need you.

**About references.** For the 10 read notes, the reference is the script text. If the speaker wrote that they changed words, that file starts with `# TODO`: listen, fix the text to match the audio, delete the TODO line. For the 3 own-words notes, listen and type what was said in Roman Urdu, then delete the TODO line. A clip with a TODO still gets timed, but it gets no accuracy score until you finish its reference.

Run `prepare.py` again whenever new zips arrive. It never overwrites references you already edited.

## 5. Run speech to text

Smoke test first:

```bash
python run_asr.py --limit 2 --langs ur
```

Then the full grid (base and small, languages `ur`, `auto`, `en`, 4 threads):

```bash
python run_asr.py
python score_asr.py
```

You can stop it at any time; running it again carries on where it stopped. Useful variations:

```bash
python run_asr.py --threads 2                 # a weaker PC
python run_asr.py --models turbo-q8 --langs ur   # the ceiling (slow on CPU)
python run_asr.py --builds noavx2 --models base-q8 --langs ur
```

## 6. Run the note writer

Build llama.cpp once:

```bash
cd ~/nabz-spike
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_AVX512=OFF
cmake --build build -j --config Release --target llama-server
cd ..
```

Start a model in a **second terminal** and leave it running. The first start downloads the model.

```bash
# phone-tier candidate (file is about 2.8 GB)
~/nabz-spike/llama.cpp/build/bin/llama-server -hf ggml-org/gemma-4-E2B-it-GGUF:Q4_0 -t 4 -c 4096 --port 8080

# PC-tier candidate (about 3.0 GB), run later in place of the one above
~/nabz-spike/llama.cpp/build/bin/llama-server -hf bartowski/Qwen_Qwen3.5-4B-GGUF:Q4_K_M -t 4 -c 4096 --port 8080
```

Back in the first terminal, run each model twice: once on your references and once on the best ASR setting from step 5.

```bash
python run_note.py --source ref --model-tag gemma4-e2b
python run_note.py --source avx2_small-q8_ur_t4 --model-tag gemma4-e2b
python score_note.py
```

Then stop the server (Ctrl+C), start the Qwen model, and repeat with `--model-tag qwen35-4b`.

The `ref` run shows the LLM's own mistakes on clean text. The ASR run shows the whole pipeline. **The gap between them is what speech recognition costs you, and it is a result for the paper.**

## 6b. Check medicines against the drug list

```bash
python drug_check.py
```

Flags every note medicine that is not in `lexicon.txt` (placeholder; swap in the DRAP export) or was not said in the transcript. `wrong_passed` and `avoid_passed` are safety errors.

## 7. The decision table

```bash
python report.py
```

Open `results/decision_table.md`.

### What the columns mean

| Column | Meaning |
|---|---|
| `dict_proc_p90_s` | 9 in 10 dictations are transcribed within this many seconds, with the model already loaded |
| `peak_ram_mb` | Highest memory whisper used, including loading the model |
| `drug_recall` | Share of drug names (prescribed, avoided, allergies) that appear in the transcript, in either script |
| `number_recall` | Share of ages, strengths and readings (500, 160, 95...) that appear, as digits or words |
| `neg_kept` | Share of "nahi" negations that survived transcription |
| `sker` | Rough error rate on consonant skeletons. Works across Urdu and Roman script. Compare rows; don't quote it as WER |
| `med_recall`, `strength_recall` | Prescribed medicines and their strengths that reached the note |
| `extra_meds` | Medicines in the note that were never prescribed (misheard or invented) |
| `avoid_violations` | A medicine the doctor said not to give was listed as prescribed |
| `neg_flips` | Something the doctor said was absent ("ulti nahi") was listed as a complaint |

`extra_meds`, `avoid_violations` and `neg_flips` are safety errors. Open those notes in `results/notes/` and read them yourself.

### Decision rules

1. Keep the smallest speech model that is within budget and finds most drug names. Pick the language flag that wins on `drug_recall` and `neg_kept`, not on `sker`.
2. If nothing is within budget, go one model smaller before you touch the LLM.
3. Any avoid violation or negation flip on the `ref` run is a prompt or model problem. Fix it before going near a doctor.
4. If drug names are the main failure, that is the paper's story: fine-tuning plus the DRAP lookup.

## 8. Check the timings on real hardware

Your i7-14700HX is roughly 2 to 3 times faster per core than a 4th-gen Core i3, so every time here is optimistic.

- **Old PC:** copy the whole `nabz-spike` folder to an old lab PC at FAST (Ubuntu or WSL), and run the chosen setting with `--threads 2` and `--threads 4`.
- **Phone:** install Termux from F-Droid on an Android phone with 4 to 6 GB of RAM, then:

```bash
pkg install clang cmake git
git clone https://github.com/ggml-org/whisper.cpp && cd whisper.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
bash ./models/download-ggml-model.sh small-q8_0
./build/bin/whisper-cli -m models/ggml-small-q8_0.bin -f dict_01.wav -t 4 -l ur -nt
```

Copy 3 or 4 dictation WAVs to the phone and note the `total time` and `load time` it prints.

Put these numbers into the experiment tracker beside the laptop numbers. The laptop table picks the model; the old-PC and phone numbers decide whether it ships.

## Notes

- Speech-to-text timings exclude model loading (`proc_s` = total minus load), because the app keeps the model loaded. Load time is still logged in `results/asr_runs.csv`.
- With `-l ur`, Whisper usually writes Urdu script, while references are Roman Urdu. All scoring is script-independent, so this is expected.
- Gemma 4 E2B at Q4_0 is about 2.8 GB on disk, above the 2.5 GB phone budget in the project doc. Measure its real RAM here before deciding; if it's too heavy, a smaller Qwen3.5 model is the fallback for phones.
- Visit recordings (`conv_`) are skipped unless you add `--include-visits`. They have no answer key yet; they're for timing long audio.

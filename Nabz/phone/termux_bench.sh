#!/data/data/com.termux/files/usr/bin/bash
# Nabz phone benchmark. Run inside Termux on the Android phone (see phone/README.md).
#
# Builds the same whisper.cpp (b5454) and llama.cpp (b11912) used on the PC, then measures on this phone:
#   * the fine-tuned speech model (ggml-ft-s250-q8_0.bin) and stock base-q8 (the cross-check) on 3 real clips
#   * the note writer (Qwen3.5 4B IQ3_M): prompt and generation speed at note size, and peak RAM
# Everything stays on the phone except nabz-phone-results.txt, which has numbers only (no transcripts).
#
#   bash ~/storage/downloads/nabz/termux_bench.sh
set -euo pipefail

B=~/storage/downloads/nabz          # the copied phone_bundle folder
W=~/nabz-bench                      # build + work folder inside Termux
T=${THREADS:-4}                     # most phones have 4 fast cores
OUT=$B/nabz-phone-results.txt
TIME=$PREFIX/bin/time

[ -d "$B" ] || { echo "Bundle not found at $B. Run termux-setup-storage and copy the nabz folder to Download/."; exit 1; }
pkg install -y clang cmake git make time wget >/dev/null
mkdir -p "$W" && cd "$W"

if [ ! -x whisper.cpp/build/bin/whisper-cli ]; then
  [ -d whisper.cpp ] || git clone --depth 1 --branch b5454 https://github.com/ggml-org/whisper.cpp
  cmake -S whisper.cpp -B whisper.cpp/build -DCMAKE_BUILD_TYPE=Release >/dev/null
  cmake --build whisper.cpp/build -j"$T" --target whisper-cli
fi
if [ ! -x llama.cpp/build/bin/llama-bench ]; then
  [ -d llama.cpp ] || git clone --depth 1 --branch b11912 https://github.com/ggml-org/llama.cpp
  cmake -S llama.cpp -B llama.cpp/build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF >/dev/null
  cmake --build llama.cpp/build -j"$T" --target llama-bench
fi
BASE=$B/ggml-base-q8_0.bin
if [ ! -f "$BASE" ]; then  # stock base-q8, the cross-check model (the same file the laptop used)
  wget -q -O "$BASE" https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q8_0.bin
fi

{
  echo "# Nabz phone benchmark $(date '+%Y-%m-%d %H:%M')"
  echo "device: $(getprop ro.product.manufacturer) $(getprop ro.product.model)  soc: $(getprop ro.soc.model) $(getprop ro.board.platform)"
  echo "android: $(getprop ro.build.version.release)  ram: $(awk '/MemTotal/ {printf "%.1f GB", $2/1048576}' /proc/meminfo)  threads: $T"
  echo "battery: $(cat /sys/class/power_supply/battery/capacity 2>/dev/null || echo ?)%  $(cat /sys/class/power_supply/battery/status 2>/dev/null || true)"
  echo
  echo "## speech to text (whisper-cli -l ur, default beam 5): wall seconds, peak RAM MB"
  echo "model clip audio_s wall_s peak_ram_mb"
} > "$OUT"

mkdir -p out
for m in ft-s250 base; do
  model=$B/ggml-ft-s250-q8_0.bin; [ $m = base ] && model=$BASE
  # one warm-up so the first timed run doesn't include reading the model from flash
  whisper.cpp/build/bin/whisper-cli -m "$model" -f "$(ls "$B"/clips/*.wav | head -1)" -t "$T" -l ur -nt >/dev/null 2>&1
  for wav in "$B"/clips/*.wav; do
    clip=$(basename "$wav" .wav)
    audio=$(( ($(stat -c %s "$wav") - 44) / 32000 ))  # 16 kHz mono 16-bit
    $TIME -f "%e %M" -o out/t.txt whisper.cpp/build/bin/whisper-cli -m "$model" -f "$wav" -t "$T" -l ur -nt \
      > "out/${m}_$clip.txt" 2>/dev/null
    read -r wall kb < out/t.txt
    echo "$m $clip $audio $wall $((kb / 1024))" | tee -a "$OUT"
  done
done

# note size from the PC runs: ~400 prompt tokens on a cold start (system prompt + transcript), p90 360 generated
{
  echo
  echo "## note writer (llama-bench, Qwen3.5 4B IQ3_M): tokens per second; peak RAM MB"
} >> "$OUT"
$TIME -f "%M" -o out/t.txt llama.cpp/build/bin/llama-bench -m "$B"/Qwen_Qwen3.5-4B-IQ3_M.gguf -p 400 -n 360 -t "$T" -r 2 -o md \
  | tee -a "$OUT"
echo "peak_ram_mb $(( $(cat out/t.txt) / 1024 ))" | tee -a "$OUT"

echo
echo "Done. Send me this file: $OUT  (Download/nabz/nabz-phone-results.txt)"

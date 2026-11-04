#!/bin/bash
# usage: stage_llm.sh <gguf> <model-tag> <source> [<source> ...]   (source = ref | best | an ASR tag)
cd /home/claude/run
MODEL=$1; TAG=$2; shift 2
llama.cpp/build/bin/llama-server -m "$MODEL" -t 2 -c 4096 -np 1 --port 8080 > "llm_$TAG.log" 2>&1 &
SRV=$!
until curl -s http://127.0.0.1:8080/health | grep -q ok; do sleep 3; done
for SRC in "$@"; do
  if [ "$SRC" = best ]; then
    SRC=$(python3 -c "
import csv
rows=[r for r in csv.DictReader(open('results/asr_summary.csv')) if 'turbo' not in r['tag']]
f=lambda v: float(v.rstrip('%') or 0)
rows.sort(key=lambda r:(f(r['drug_recall']), f(r['neg_kept']), -f(r['sker'])), reverse=True)
print(rows[0]['tag'])")
  fi
  echo "== $TAG on $SRC $(date +%T)" >> "note_$TAG.log"
  python3 -u run_note.py --source "$SRC" --model-tag "$TAG" --timeout 2400 >> "note_$TAG.log" 2>&1
done
kill $SRV; wait $SRV 2>/dev/null
echo "STAGE_DONE $TAG $(date +%T)" >> "note_$TAG.log"

#!/bin/bash
cd /home/claude/run
while pgrep -f "models base-q8" >/dev/null; do sleep 20; done
python3 -u run_asr.py --models small-q8 --threads 2 >> asr_small.log 2>&1
python3 -u run_asr.py --models turbo-q8 --langs ur --threads 2 >> asr_turbo.log 2>&1
python3 -u score_asr.py > asr_score.log 2>&1
echo STAGE_ASR_DONE >> asr_score.log

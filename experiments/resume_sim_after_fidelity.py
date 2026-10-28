#!/usr/bin/env python3
"""Wait for validated input campaign completion, then exec the checkpointed sim lane."""
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    while True:
        state=json.loads((ROOT/'results/fidelity-2026-10-27/campaign.json').read_text())
        if state['status']=='complete':break
        if state['status'] in ['interrupted','failed','paused']:
            raise SystemExit('Fidelity campaign stopped; simulator was not started')
        time.sleep(20)
    command=[str(ROOT/'.venv/bin/python'),str(ROOT/'experiments/revalidation_campaign.py'),'sim',
             '--checkpoint-storage','/mnt/research/memory-tiering/simulator-checkpoints',
             '--checkpoint-validation','/mnt/research/memory-tiering/checkpoint-validation/full-system-1/validation.json']
    os.chdir(ROOT)
    os.execv(command[0],command)

if __name__=='__main__':main()

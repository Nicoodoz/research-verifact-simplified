"""Read-only progress monitor; never sends API requests or reads ground-truth labels."""
from pathlib import Path
from collections import Counter
import json
import time

root = Path(__file__).resolve().parents[2]
path = root / 'outputs/019_support_boundary_screen/live_ledger.json'
last = -1
while True:
    time.sleep(15)
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        continue
    phase = state['phases'].get('validation', state['phases']['selection'])
    counts = Counter(job['status'] for job in phase['jobs'].values())
    received = counts['received']
    total = len(phase['jobs'])
    if received // 100 != last or state.get('pause_reason') or received == total:
        print(json.dumps(dict(received=received, total=total, statuses=dict(counts), used_or_reserved=state['used_or_reserved_cny'], provider=state['provider'], pause=state.get('pause_reason'))), flush=True)
        last = received // 100
    if received == total or state.get('pause_reason'):
        break

"""014 frozen input, shared evaluator/parser, Qwen-only accounting. No API on import."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/014_qwen27b_baseline_comparison'
OLD = ROOT / 'outputs/010_verifact_baseline_alignment'
MODEL = 'Qwen/Qwen3.8-27B'
V4 = 'deepseek-ai/DeepSeek-V4-Flash'
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tasks/004_event_alignment_pilot'))
import pilot
import siliconflow as sf
from verifact_research.evaluation import evaluate, paired_compare, LABELS
from verifact_research.inference.siliconflow_pool import (
    canonical, fingerprint, file_hash, require, save, load_accounts, HttpClient, balance_exhausted)

def now():
    return datetime.now(timezone.utc).isoformat()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def csvrows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def jsonlines(path):
    with Path(path).open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def write_lines(path, rows):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        for row in rows:
            f.write(canonical(row) + '\n')

def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with Path(path).open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def check_hashes(mapping):
    for name, digest in mapping.items():
        require(file_hash(ROOT / name) == digest, 'Frozen file changed: ' + name)

def bound(job):
    # Byte bound + template/schema allowance, not an exact tokenizer measurement.
    return ((len(canonical(job['body']).encode('utf-8')) + 2000) * 3 + 2048 * 12) / 1e6

def cost(job, tr):
    if balance_exhausted(tr):
        return 0.0, 'unanswered_balance_error'
    try:
        data = pilot.strict_json(tr['body_text'])
        u = data['usage']
        p, c = u['prompt_tokens'], u['completion_tokens']
        require(all(type(n) is int and n >= 0 for n in (p,c)), 'Bad usage')
        require(u['total_tokens'] == p+c, 'Bad usage total')
        return (p*3+c*12)/1e6, 'public_Qwen_3_12_usage_not_invoice'
    except (ValueError, TypeError, KeyError, IndexError):
        return bound(job), 'unknown_usage_byte_reservation_not_invoice'

def normalize(job, receipt, model=MODEL):
    tr = receipt['transport']
    result = dict(request_id=job['request_id'], proposition_id=job['proposition_id'],
                  status='failed', verdict=None, structural_errors=[], adherence_errors=[])
    try:
        require(tr['http_status'] == 200, 'No successful response')
        data = pilot.strict_json(tr['body_text'])
        require(data.get('model') == model, 'Unexpected returned model')
        require(len(data['choices']) == 1, 'Unexpected choices')
        choice = data['choices'][0]
        result.update(output_text=choice['message'].get('content'), finish_reason=choice['finish_reason'],
                      model_returned=data.get('model'), system_fingerprint=data.get('system_fingerprint'),
                      provider_id=data.get('id'), raw_usage=data.get('usage'))
        require(choice['finish_reason'] == 'stop', 'Truncated/filtered/nonfinal generation')
        answer = pilot.strict_json(choice['message']['content'])
        require(isinstance(answer,dict) and answer.get('verdict') in LABELS, 'Invalid final label')
        usage = sf.normalize_usage(data)
        require(usage['total_tokens'] == usage['input_tokens']+usage['output_tokens'], 'Bad total usage')
        require(usage['reasoning_tokens']==0 and not choice['message'].get('reasoning_content'), 'Thinking enabled')
        require(usage['output_tokens'] <= job['body']['max_tokens'], 'Output limit exceeded')
        result.update(status='success', verdict=answer['verdict'], usage=usage,
                      latency_seconds=(datetime.fromisoformat(tr['ended_utc'])-datetime.fromisoformat(tr['started_utc'])).total_seconds())
        reference = pilot.strict_json(job['body']['messages'][1]['content'])['reference']
        try:
            pilot.parse_answer(choice['message']['content'], 'structured', reference, 200)
        except (ValueError, TypeError, KeyError) as exc:
            result['adherence_errors'].append(str(exc))
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        result['structural_errors'].append(str(exc))
    return result

def verify_preparation():
    m = read(OUT/'preparation_001/manifest.json')
    check_hashes(m['files'])
    check_hashes(m['dependencies'])
    check_hashes(m['execution_code'])
    require(read(OUT/'authority_001.json')['task_cap_cny']==40, 'Wrong cap')
    require(file_hash(OUT/'authority_001.json') == m['authority_sha256'], 'Authority changed')
    require(file_hash(OUT/'protocol_001.md') == m['protocol_sha256'], 'Protocol changed')
    return m

"""019 fixed-input scoring experiment. Importing this module never calls an API."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import copy, csv, hashlib, json, math, sys
ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/019_support_boundary_screen'
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tasks/016_disagreement_triggered_review_validation'))
import common016 as old
from verifact_research.evaluation import evaluate, paired_compare
from verifact_research.inference.siliconflow_pool import canonical, fingerprint, file_hash, require, save, load_accounts, balance_exhausted, HttpClient
from verifact_research.inference.aliyun import load_config, AliyunClient
LABELS = ('Supported', 'Not Supported', 'Not Addressed')
GRID = (0, 0.5, 1, 1.5, 2, 3, 4)
MODEL = 'deepseek-ai/DeepSeek-V4-Flash'
ALI_MODEL = 'deepseek-v4-flash-0731'
CAP = 80.0
PROMPTS = ROOT / 'outputs/009_retrieval_baselines/confirmation_001/preparation/judge_prompts.json'
MATERIALS = ROOT / 'outputs/018_verifact_gap_attribution/preparation_001/materials.jsonl'
GLOBAL_ROUTE = ROOT / 'outputs/service_tools/provider_routing/current.json'

def now():
    return datetime.now(timezone.utc).isoformat()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def jsonlines(path):
    with Path(path).open(encoding='utf-8-sig') as f:
        return [json.loads(line) for line in f if line.strip()]

def write_json(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    save(path, obj, new=True)

def write_lines(path, rows):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        for row in rows: f.write(canonical(row) + '\n')

def write_csv(path, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

def rank(text):
    return hashlib.sha256(('019/v1:' + text).encode()).hexdigest()

def body(text, reference, scored=False):
    result = copy.deepcopy(old.judge_body({'text': text}, reference, read(PROMPTS), 'v4_first'))
    if scored:
        s = result['messages'][0]['content']
        needle = 'exactly three keys: "verdict", "reason", "checks".'
        require(s.count(needle) == 1, 'Original prompt schema changed')
        s = s.replace(needle, 'exactly four keys: "verdict", "reason", "checks", "label_scores".')
        s += ('\nIn addition to the ordinary verdict, reason, and checks, return label_scores '
              'for all three existing labels. Use integer scores from 0 to 100 summing to 100. '
              'These are your relative confidence scores for which existing label applies to the '
              'complete proposition using only the supplied reference. They are not percentages '
              'of the proposition that are supported. Do not change the label definitions or '
              'infer missing patient facts. Keep the ordinary evidence-based explanation and '
              'its existing length allowance.\n')
        result['messages'][0]['content'] = s
        schema = result['response_format']['json_schema']['schema']
        schema['required'].append('label_scores')
        schema['properties']['label_scores'] = dict(type='object', additionalProperties=False,
            required=list(LABELS), properties={k: dict(type='integer', minimum=0, maximum=100) for k in LABELS})
    payload = json.loads(result['messages'][1]['content'])
    require(payload == {'proposition': text, 'reference': reference}, 'Whitelist violation')
    return result

def strict_json(text):
    def pairs(items):
        obj = {}
        for k, v in items:
            require(k not in obj, 'Duplicate JSON key'); obj[k] = v
        return obj
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))

def parse(transport, scored):
    r = dict(status='invalid', verdict=None, scores=None, errors=[], adherence=[])
    if transport.get('http_status') != 200:
        r['errors'] = ['no_http_200']; return r
    try:
        native = strict_json(transport['body_text']); choice = native['choices'][0]
        r.update(output_text=choice['message'].get('content'), finish_reason=choice.get('finish_reason'),
                 model_returned=native.get('model'), usage=native.get('usage'), response_id=native.get('id'))
        require(choice.get('finish_reason') == 'stop', 'truncated_or_other_finish')
        require(not choice['message'].get('reasoning_content'), 'unexpected_thinking')
        o = strict_json(r['output_text'])
        require(o.get('verdict') in LABELS, 'invalid_verdict')
        require(isinstance(o.get('reason'), str) and isinstance(o.get('checks'), list), 'missing_explanation')
        r.update(verdict=o['verdict'], parsed=o, status='success')
        aspects = ['claim_summary','relevant_evidence','supporting_case','opposing_case','overall_assessment']
        if [v.get('aspect') if isinstance(v,dict) else None for v in o['checks']] != aspects:
            r['adherence'].append('check_names_or_count')
        if scored:
            q = o.get('label_scores')
            require(isinstance(q,dict) and set(q)==set(LABELS), 'missing_score_labels')
            require(all(type(v) is int and 0 <= v <= 100 for v in q.values()), 'invalid_score_type_or_range')
            require(sum(q.values()) == 100, 'score_sum_not_100')
            r['scores'] = q
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        r['status'] = 'invalid'; r['errors'].append(str(exc)[:120])
    return r

def decision(scores, lam):
    require(lam in GRID, 'Unregistered lambda')
    require(set(scores)==set(LABELS) and all(type(v) is int and 0 <= v <= 100 for v in scores.values()) and sum(scores.values())==100, 'Bad scores')
    # Ordering implements the prespecified NS, NA, S tie break.
    return max((LABELS[1],LABELS[2],LABELS[0]), key=lambda k: math.log(max(scores[k]/100,1e-6)) + (lam if k==LABELS[0] else 0))

def bound(body):
    return ((len(canonical(body).encode('utf-8'))+2000)*3 + body['max_tokens']*9)/1e6

def charge(body, transport):
    if balance_exhausted(transport): return 0., 'explicit_unanswered_balance_error'
    try:
        u = strict_json(transport['body_text'])['usage']
        i, o = u['prompt_tokens'], u['completion_tokens']
        require(type(i) is int and type(o) is int and i>=0 and o>=0, 'Invalid usage')
        require(u.get('total_tokens',i+o)==i+o, 'Inconsistent usage')
        return (i*3+o*9)/1e6, 'peak_no_cache_usage_estimate'
    except (KeyError, TypeError, ValueError):
        return bound(body), 'unknown_usage_reservation'

def check_manifest(path):
    m = read(path)
    for k,v in m['sha256'].items(): require(file_hash(ROOT/k)==v,'Frozen file changed: '+k)
    return m

def totals(rows, predictions):
    require(len(rows)==len(predictions), 'Alignment mismatch')
    return dict(n=len(rows), correct=sum(r['human_gt']==p for r,p in zip(rows,predictions)),
        false_s=sum(r['human_gt']!=LABELS[0] and p==LABELS[0] for r,p in zip(rows,predictions)),
        tp={k:sum(r['human_gt']==p==k for r,p in zip(rows,predictions)) for k in LABELS},
        support=dict(Counter(r['human_gt'] for r in rows)))

def prediction_rows(rows, labels):
    return [dict(proposition_id=r['proposition_id'], verdict=p) for r,p in zip(rows,labels)]

"""Separate mutable navigation from frozen history; never relax experiment manifests.

Only check_history uses this policy. common014/common015.check_hashes and their
input, execution-code, receipt, metric and report bindings remain unchanged.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS = (
    '001_dataset_audit', '002_reproduce_paper_results', '003_error_analysis',
    '004_event_alignment_pilot', '005_pilot_effect_analysis',
    '006_source_context_feasibility', '007_context_retrieval',
    '008_retrieval_planning', '009_retrieval_baselines',
    '010_verifact_baseline_alignment', '011_evidence_integrity_packaging',
    '012_comparative_error_diagnosis', '013_multi_mechanism_screen',
    '014_qwen27b_baseline_comparison', '015_disagreement_adjudication',
)
# Explicit top-level entries only. Nested run/source READMEs, audit artifacts,
# protocols and main reports are not made mutable by their extension or name.
MUTABLE_HISTORY_PATHS = frozenset(
    ['README.md', 'AGENTS.md', '.gitattributes', 'reviews/README.md',
     'docs/siliconflow_pool/README.md'] +
    [f'{parent}/{task}/README.md' for parent in ('tasks', 'outputs') for task in TASKS] +
    [f'reviews/{task}.md' for task in TASKS]
)
VERIFIER = 'tasks/014_qwen27b_baseline_comparison/verify014.py'
ORIGINAL = 'outputs/014_qwen27b_baseline_comparison/revision_001/original/' + VERIFIER
BINDINGS = 'tasks/014_qwen27b_baseline_comparison/replay_bindings.json'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check_history(history, root=ROOT, bindings=None):
    """Return visible drift diagnostics; fail on every unregistered frozen change."""
    root=Path(root)
    if bindings is None:
        bindings=json.loads((root/BINDINGS).read_text(encoding='utf-8'))['historical_verifier_revisions']
    if set(bindings)-{VERIFIER}:
        raise ValueError('Only the registered historical 014 verifier may be rebound')
    strict=0;mutable=[];revisions=[]
    for name,expected in history.items():
        path=root/name
        if name in MUTABLE_HISTORY_PATHS:
            actual=digest(path) if path.is_file() else None
            mutable.append(dict(path=name,historical_sha256=expected,current_sha256=actual,
                changed=actual!=expected,role='navigation_or_audit_status_not_computation'))
        elif name in bindings:
            binding=bindings[name]
            if binding['original_path']!=ORIGINAL or binding['original_sha256']!=expected:
                raise ValueError('Historical verifier provenance mismatch: '+name)
            if digest(root/ORIGINAL)!=expected or digest(path)!=binding['current_sha256']:
                raise ValueError('Registered verifier or original snapshot changed: '+name)
            revisions.append(dict(path=name,**binding,role='explicit_replay_only_revision'))
        else:
            if digest(path)!=expected:
                raise ValueError('Frozen file changed: '+name)
            strict+=1
    return dict(total_historical_entries=len(history),strict_unchanged_files=strict,
        mutable_entries=mutable,registered_verifier_revisions=revisions,
        policy='exact top-level navigation/status allowlist; all other history strict; experiment manifests always strict')

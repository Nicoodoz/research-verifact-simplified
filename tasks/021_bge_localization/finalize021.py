"""Create final task021 manifest and audit handoff; offline only."""
from pathlib import Path
import json, subprocess
import common021 as c

NAV=[c.ROOT/'README.md',c.ROOT/'AGENTS.md',c.ROOT/'docs/API_POLICY.md',c.ROOT/'docs/PROJECT_STATUS.md']
KEY=[
    c.OUT/'protocol_001.md',
    c.OUT/'registration_001.json',
    c.OUT/'report.md',
    c.OUT/'comparison_summary.json',
    c.OUT/'claim_comparison.csv',
    c.OUT/'precision_diagnostic_001.json',
    c.OUT/'verification_001.json',
    c.OUT/'test_summary.json',
    c.OUT/'CURRENT.md',
    c.OUT/'CURRENT.md.json',
    c.OUT/'run_summary.json',
    c.OUT/'execution_closure.json',
    c.OUT/'audit_handoff.md',
    c.TASK/'README.md',
]

def rel(p): return p.relative_to(c.ROOT).as_posix()

def main():
    # Refresh documentation-sync hashes to the actual final navigation bytes.
    changes={}
    back=c.OUT/'documentation_sync_001'
    for p in NAV:
        r=p.relative_to(c.ROOT)
        bp=back/r
        changes[r.as_posix()]={
            'before_sha256':c.sha256(bp),
            'after_sha256':c.sha256(p),
            'changed':bp.read_bytes()!=p.read_bytes(),
        }
    c.save(back/'changes.json',changes)

    # All task/output content except caches and the manifest/handoff that are created here.
    files={}
    for root in (c.TASK,c.OUT):
        for p in sorted(root.rglob('*')):
            if not p.is_file(): continue
            if '__pycache__' in p.parts or p.suffix in {'.pyc','.pyo'}: continue
            if p.name in {'manifest.json','handoff_001.json'}: continue
            files[rel(p)]=c.sha256(p)

    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip()
    manifest={
        'schema_version':1,
        'task':'021_bge_localization',
        'status':'completed_pending_independent_audit',
        'source_git_head':head,
        'files':files,
        'navigation_docs':{rel(p):c.sha256(p) for p in NAV},
        'model_bindings':{
            'embedding':{
                'repo':'BAAI/bge-m3',
                'revision':'5617a9f61b028005a4858fdac845db406aefb181',
                'weights_sha256':c.EMBED_LFS_SHA,
                'weights_committed':False,
            },
            'reranker':{
                'repo':'BAAI/bge-reranker-v2-m3',
                'revision':'953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e',
                'weights_sha256':c.RERANK_LFS_SHA,
                'weights_committed':False,
            },
        },
        'scope':{
            'claims':879,
            'embedding_vectors':2057,
            'rerank_pairs':49246,
            'new_paid_api_calls':0,
            'reserved_test_used':False,
            'gt_or_judge_performance_read':False,
        },
        'result':{
            'strict_frozen_equivalence_pass':False,
            'api_c48_local_reranker_reference_exact':594,
            'full_local_reference_exact':565,
        },
        'tests':{
            'repository_unittest':'223/223 PASS',
            'task_python_compile':True,
            'verification_001':'PASS',
        },
    }
    c.save(c.OUT/'manifest.json',manifest)

    key_hashes={rel(p):c.sha256(p) for p in KEY}
    key_hashes[rel(c.OUT/'manifest.json')]=c.sha256(c.OUT/'manifest.json')
    handoff={
        'status':'completed_pending_independent_audit',
        'task':'021_bge_localization',
        'git_head':head,
        'commit_or_push_performed':False,
        'scientific_result':{
            'strict_frozen_equivalence_pass':False,
            'api_c48_local_reranker_reference_exact':594,
            'full_local_reference_exact':565,
            'interpretation':'Local BGE is operational and highly similar, but is not a strict frozen-equivalent replacement for the 020 API-BGE implementation.',
        },
        'execution_guards':{
            'new_paid_api_calls':0,
            'reserved_test_used':False,
            'gt_or_judge_performance_read':False,
            'source_020_hashes_unchanged':True,
            'project_gitignore_unchanged':True,
            'model_weights_git_ignored_locally':True,
        },
        'tests':{
            'repository_tests_run':223,
            'repository_tests_passed':223,
            'task_python_compile':'PASS',
            'verification_001':'PASS',
        },
        'key_sha256':key_hashes,
        'navigation_sha256':{rel(p):c.sha256(p) for p in NAV},
        'independent_audit':False,
    }
    c.save(c.OUT/'handoff_001.json',handoff)
    print(json.dumps({
        'manifest_files':len(files),
        'manifest_sha256':c.sha256(c.OUT/'manifest.json'),
        'handoff_sha256':c.sha256(c.OUT/'handoff_001.json'),
        'report_sha256':c.sha256(c.OUT/'report.md'),
        'comparison_sha256':c.sha256(c.OUT/'comparison_summary.json'),
    },ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()

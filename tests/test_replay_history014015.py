"""Regression tests for audit-index drift, source provenance and frozen-file rejection."""
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tasks/014_qwen27b_baseline_comparison'))
import replay_history as h
import common014 as c

class HistoryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='verifact-history-test-')
        self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def put(self,name,data=b'original\n'):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def test_navigation_drift_is_visible(self):
        names=['reviews/README.md','reviews/014_qwen27b_baseline_comparison.md',
            'tasks/014_qwen27b_baseline_comparison/README.md','outputs/014_qwen27b_baseline_comparison/README.md','.gitattributes']
        history={n:self.put(n) for n in names}
        for n in names:self.put(n,b'updated status\n')
        result=h.check_history(history,self.root,{})
        self.assertEqual(len(result['mutable_entries']),len(names))
        self.assertTrue(all(r['changed'] for r in result['mutable_entries']))
        self.assertEqual(result['strict_unchanged_files'],0)

    def test_not_all_markdown_or_audits_are_exempt(self):
        for name in ['outputs/014_qwen27b_baseline_comparison/report.md',
            'outputs/014_qwen27b_baseline_comparison/protocol_001.md',
            'outputs/009_retrieval_baselines/run_001/README.md',
            'docs/sources/007_context_retrieval/services/embed/README.md',
            'reviews/artifacts/014_015_audit_20260916/evidence.json']:
            with self.subTest(name=name):
                old=self.put(name);self.put(name,b'tampered\n')
                with self.assertRaisesRegex(ValueError,'Frozen file changed'):h.check_history({name:old},self.root,{})

    def test_computation_and_payloads_stay_strict(self):
        for name in ['tasks/014_qwen27b_baseline_comparison/common014.py',
            'tasks/015_disagreement_adjudication/common015.py','src/verifact_research/evaluation/metrics.py',
            'outputs/014_qwen27b_baseline_comparison/live/receipt_000001_01.json',
            'outputs/015_disagreement_adjudication/preparation_001/jobs.jsonl',
            'outputs/015_disagreement_adjudication/analysis_001/metrics.json','config.json']:
            with self.subTest(name=name):
                old=self.put(name);self.put(name,b'tampered\n')
                with self.assertRaises(ValueError):h.check_history({name:old},self.root,{})

    def test_explicit_old_verifier_binding(self):
        old=self.put(h.ORIGINAL);current=self.put(h.VERIFIER,b'revised verifier\n')
        binding={h.VERIFIER:dict(original_path=h.ORIGINAL,original_sha256=old,current_sha256=current)}
        result=h.check_history({h.VERIFIER:old},self.root,binding)
        self.assertEqual(len(result['registered_verifier_revisions']),1)
        self.put(h.ORIGINAL,b'changed original\n')
        with self.assertRaisesRegex(ValueError,'snapshot changed'):h.check_history({h.VERIFIER:old},self.root,binding)

    def test_current_verifier_tampering_rejected(self):
        old=self.put(h.ORIGINAL);current=self.put(h.VERIFIER,b'revised verifier\n')
        binding={h.VERIFIER:dict(original_path=h.ORIGINAL,original_sha256=old,current_sha256=current)}
        self.put(h.VERIFIER,b'unknown revision\n')
        with self.assertRaises(ValueError):h.check_history({h.VERIFIER:old},self.root,binding)

    def test_cannot_rebind_model_code(self):
        name='tasks/014_qwen27b_baseline_comparison/common014.py';old=self.put(name)
        with self.assertRaisesRegex(ValueError,'Only the registered'):h.check_history({name:old},self.root,{name:{}})

    def test_manifest_hash_checker_is_still_strict_for_navigation(self):
        name='reviews/README.md';old=self.put(name);self.put(name,b'new\n')
        with patch.object(c,'ROOT',self.root):
            with self.assertRaises(ValueError):c.check_hashes({name:old})

if __name__=='__main__':unittest.main()

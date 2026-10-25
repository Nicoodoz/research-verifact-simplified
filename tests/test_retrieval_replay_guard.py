"""009 audit-index regression and isolation tests; no real files are mutated."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tasks/009_retrieval_baselines'))
import study009 as s
import verify009 as replay


class ReplayGuardTests(unittest.TestCase):
    def test_unrelated_workspace_changes_are_recorded_not_rejected(self):
        with patch.object(replay.subprocess,'check_output',side_effect=['HEAD\n','reviews/README.md\nreviews/009_retrieval_baselines.md\nsrc/unrelated.py\n']):
            info=replay.workspace_snapshot()
        self.assertEqual(info['tracked_changes'],['reviews/README.md','reviews/009_retrieval_baselines.md','src/unrelated.py'])
        self.assertIn('informational_only',info['workspace_changes_policy'])

    def fixture(self,root,self_check=True):
        out=root/'results'
        out.mkdir()
        verifier=root/'tasks/009_retrieval_baselines/verify009.py'
        verifier.parent.mkdir(parents=True)
        verifier.write_text('old verifier',encoding='utf-8')
        computation=root/'compute.py'
        computation.write_text('frozen computation',encoding='utf-8')
        config=root/'config.json'
        config.write_text('{"frozen":true}',encoding='utf-8')
        for name in ('input.json','receipt.json','predictions.csv'):
            (out/name).write_text('original '+name,encoding='utf-8')
        if self_check:
            s.pilot.write_json(out/'verification.json',dict(self_check_not_independent_audit=True))
        s.seal(out,[config],[verifier,computation])
        return out,verifier,computation,config

    def test_verifier_update_preserves_frozen_data_code_and_dependency_guards(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(s,'ROOT',Path(tmp)):
            out,verifier,computation,config=self.fixture(Path(tmp))
            verifier.write_text('revised verifier',encoding='utf-8')
            info=replay.check_frozen_manifest(out/'manifest.json')
            self.assertFalse(info[0]['matches'])
            for target in (out/'input.json',out/'receipt.json',out/'predictions.csv',computation,config,out/'verification.json'):
                with self.subTest(target=target.name):
                    original=target.read_bytes()
                    target.write_bytes(original+b' tampered')
                    with self.assertRaises((ValueError,AssertionError)):
                        replay.check_frozen_manifest(out/'manifest.json')
                    target.write_bytes(original)
            self.assertFalse(replay.check_frozen_manifest(out/'manifest.json')[0]['matches'])

    def test_verifier_binding_in_experiment_manifest_is_still_strict(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(s,'ROOT',Path(tmp)):
            out,verifier,_,_=self.fixture(Path(tmp),self_check=False)
            verifier.write_text('tampered',encoding='utf-8')
            with self.assertRaises(AssertionError):
                replay.check_frozen_manifest(out/'manifest.json')


if __name__=='__main__':
    unittest.main()

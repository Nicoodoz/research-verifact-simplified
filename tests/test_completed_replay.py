"""Safety checks for the read-only completed-task replay entry."""
from pathlib import Path
from unittest.mock import patch
import importlib.util,json,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('completed_replay',ROOT/'scripts/replay_completed_research.py')
replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)
class CompletedReplayTests(unittest.TestCase):
 def test_existing_output_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):replay.safe_destination('021',Path(d))
 def test_frozen_workspace_destination_is_rejected(self):
  with self.assertRaises(ValueError):replay.safe_destination('019',ROOT/'outputs/020_lambda2_patient_validation/new_fake_audit')
 def test_new_named_replay_is_allowed_without_creation(self):
  with tempfile.TemporaryDirectory() as d,patch.object(replay,'ROOT',Path(d)):
   p=Path(d)/'outputs/replays/example'
   self.assertEqual(replay.safe_destination('021',p),p.resolve());self.assertFalse(p.exists())
 def test_source_tamper_rejected(self):
  with tempfile.TemporaryDirectory() as d,patch.object(replay,'ROOT',Path(d)):
   root=Path(d);f=root/'tasks/019_support_boundary_screen/frozen.py';f.parent.mkdir(parents=True);f.write_text('changed')
   b=root/'reviews/artifacts/019_021_audit_20260919/audited_files_sha256.json';b.parent.mkdir(parents=True);b.write_text(json.dumps({f.relative_to(root).as_posix():'0'*64}))
   with self.assertRaises(ValueError):replay.check_bindings('019')
if __name__=='__main__':unittest.main()


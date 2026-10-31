"""Small stdlib-only check of serialized paths and an unresettable deadline."""
from pathlib import Path, PurePosixPath, PureWindowsPath
from tempfile import TemporaryDirectory
import json
import unittest

from worker144 import compute_deadline, resolve_bundle_path


class WorkerMetadataTests(unittest.TestCase):
    def test_windows_serialization_reads_same_posix_relative_file(self):
        with TemporaryDirectory() as folder:
            bundle = Path(folder) / 'bundle'
            target = bundle / 'reuse' / 'claim_repeat136' / 'example.json'
            target.parent.mkdir(parents=True)
            target.write_text('{"retained":true}', encoding='utf-8')
            windows = str(PureWindowsPath('reuse', 'claim_repeat136', 'example.json'))
            recorded = json.loads(json.dumps({'copied_path': windows}))['copied_path']
            self.assertIn('\\', recorded)
            linux_path = PurePosixPath('/bundle') / recorded.replace('\\', '/')
            self.assertEqual(linux_path.as_posix(), '/bundle/reuse/claim_repeat136/example.json')
            self.assertEqual(resolve_bundle_path(bundle, recorded), target.resolve())
            self.assertEqual(resolve_bundle_path(bundle, target.relative_to(bundle).as_posix()), target.resolve())
            self.assertEqual(json.loads(resolve_bundle_path(bundle, recorded).read_text()), {'retained': True})

    def test_absolute_and_parent_paths_are_rejected(self):
        with TemporaryDirectory() as folder:
            for value in ('../outside.json', '..\\outside.json', '/outside.json',
                          '\\outside.json', 'C:\\outside.json', 'C:outside.json',
                          '\\\\server\\share\\outside.json'):
                with self.subTest(path=value), self.assertRaises(ValueError):
                    resolve_bundle_path(folder, value)

    def test_restart_keeps_original_absolute_compute_deadline(self):
        job = {'absolute_compute_deadline': 1800}
        self.assertEqual(compute_deadline(1000, 1200, 4000, 180, job), 1800)
        self.assertEqual(compute_deadline(1600, 1200, 4000, 180, job), 1800)
        self.assertEqual(compute_deadline(1900, 1200, 4000, 180, job), 1800)
        self.assertEqual(compute_deadline(1000, 1200, 4000, 180, {}), 2200)
        self.assertEqual(compute_deadline(1000, 1200, 1800, 180, job), 1620)


if __name__ == '__main__':
    unittest.main()

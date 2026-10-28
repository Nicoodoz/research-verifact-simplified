"""Small regression for the actual AutoDL shebang-less shutdown script issue."""
from pathlib import Path
import tempfile,unittest
import budget105 as budget

class NoCardChecks(unittest.TestCase):
    def test_shutdown_file_dispatch_does_not_execute(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'shutdown'
            for content,prefix in [(b'curl platform-stop\n',['/bin/bash']),
                                   (b'#!/bin/bash\nexit 0\n',[]),(b'\x7fELFrest',[])]:
                path.write_bytes(content)
                self.assertEqual(budget.shutdown_command(path),prefix+[str(path),'-h','now'])

if __name__=='__main__':unittest.main(verbosity=2)

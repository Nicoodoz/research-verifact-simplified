import sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'tasks/029_semantic_information_gate'))
import run029
out=root/'outputs/replays/audit029_20260920_conda'
out.mkdir(parents=True,exist_ok=False)
run029.execute(out)

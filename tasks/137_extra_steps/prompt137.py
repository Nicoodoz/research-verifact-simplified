"""Same136 input contract, with137's model identity kept separate."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'))
from prompt136 import prompt_ids
RESPONSE_PREFIX=''
def configure(variant):
 assert variant=='extra_steps'
 return RESPONSE_PREFIX

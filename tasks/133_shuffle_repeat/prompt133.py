"""The two unchanged inputs being compared on the new fixed-seed model."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/104_supervision_evidence'))
from training104 import prompt_ids as plain_ids
sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'))
from prompt136 import prompt_ids as repeat_ids
def prompt_ids(tokenizer,row,arm):
 if arm=='plain104':return plain_ids(tokenizer,row)
 if arm=='claim_repeat':return repeat_ids(tokenizer,row)
 raise ValueError(arm)

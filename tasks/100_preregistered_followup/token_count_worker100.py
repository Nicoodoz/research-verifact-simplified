"""Existing tokenizer-only helper; reads JSON lines on stdin, emits token counts only."""
from pathlib import Path
import json,sys
from tokenizers import Tokenizer
root=Path(__file__).resolve().parents[2]
tok=Tokenizer.from_file(str(root/'.local_models/100_preregistered_followup/sources/tokenizer.json'))
tok.no_truncation();tok.no_padding()
if '--probe' in sys.argv:
 import tokenizers
 print(json.dumps(dict(tokenizers_version=tokenizers.__version__,python=sys.version.split()[0],probe_tokens=len(tok.encode('A short synthetic token-count probe.',add_special_tokens=False).ids))))
else:
 for line in sys.stdin:
  req=json.loads(line)
  texts=req['texts']
  counts=[len(x.ids) for x in tok.encode_batch(texts,add_special_tokens=False)]
  print(json.dumps(counts),flush=True)

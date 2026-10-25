"""074 shared IO; importing does not load credentials or call any API."""
import csv,datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/074_anchor_dynamic_examples'
TASK=Path(__file__).parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def text_hash(s):return hashlib.sha256(s.encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def jl(p,rows):
 with Path(p).open('x',encoding='utf-8',newline='\n') as f:
  for x in rows:f.write(canonical(x)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def annotations():return {x['proposition_id']:x for x in csv.DictReader((ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv').open(encoding='utf-8-sig'))}

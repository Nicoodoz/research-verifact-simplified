"""Training-only source-unit selection; AI never changes physician GT."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import sys,json,time
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/147_fixed_reason'))
from api_budget147 import send
P=R/'.local_models/162_train_demo_pool'
PROMPT='''You are selecting a transparent few-shot demonstration from an original training patient. The physician verdict is fixed and must not be changed. Read the entire supplied reference, which is divided into exact numbered source units. Decide whether this record can clearly illustrate that verdict. Supported means fully supported; Not Supported includes contradicted or only partially supported assertions; Not Addressed means the specific assertion is not addressed, not that the patient lacks the fact. Do not manufacture a link or use the fixed verdict to override missing evidence. If the supplied reference does not convincingly illustrate that fixed verdict, return suitable=false and explain the limitation; do not propose a new label. For a suitable demonstration choose at most four COMPLETE numbered source units, with their combined text at most 2200 characters, retaining decisive evidence and any material caveat. Return unit numbers, never rewritten text. For Not Addressed inspect the FULL reference; never delete supporting/contradicting information to make an assertion seem unaddressed. If complete units cannot preserve a clear distinction within the size limit, mark unsuitable. Return only JSON {"suitable":true,"source_units":[1,2],"basis":"at most 70 words describing the actual distinction"} or {"suitable":false,"source_units":[],"basis":"limitation"}.'''

def one(r):
    folder=P/'review'/r['id'];done=folder/'result.json'
    if done.exists():return json.loads(done.read_text())
    # Training GT only. No model error, score, patient identity or evaluation data is sent.
    payload=dict(assertion=r['claim'],fixed_training_physician_verdict=r['GT'],reference_prefix=r['prefix'],full_reference_units=r['units'])
    folder.mkdir(parents=True,exist_ok=True);trials=[];value=None;error=None
    for attempt in range(2):
        native,transport,elapsed=send([dict(role='system',content=PROMPT),dict(role='user',content=json.dumps(payload,ensure_ascii=False))],folder/('attempt'+str(attempt)),max_tokens=8192,task='162_train_demo_pool')
        trials.append(dict(http_status=transport['http_status'],seconds=elapsed,usage=native.get('usage')))
        if transport['http_status']==200:
            try:
                assert native['choices'][0]['finish_reason']=='stop'
                value=json.loads(native['choices'][0]['message']['content']);assert type(value['suitable']) is bool and isinstance(value['basis'],str)
                selected=value['source_units'];available={u['number']:u['text'] for u in r['units']}
                assert isinstance(selected,list) and len(selected)==len(set(selected)) and all(type(i) is int and i in available for i in selected)
                assert not value['suitable'] or 0<len(selected)<=4
                excerpt=r['prefix']+'\n'.join(available[i].rstrip() for i in sorted(selected))
                if value['suitable'] and len(excerpt)>2200:error='complete selected units exceed2200 characters'
            except (ValueError,KeyError,IndexError,TypeError,AssertionError) as e:value=None;error='invalid core response: '+type(e).__name__
            break
        if transport['http_status'] not in (0,429,500,502,503,504):break
        if attempt==0:time.sleep(3)
    result=dict(id=r['id'],GT=r['GT'],GT_changed=False,parsed=value,usable=bool(value and value['suitable'] and not error),validation_error=error,trials=trials)
    done.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return result

def main():
    data=[json.loads(s) for s in (P/'candidates.jsonl').read_text(encoding='utf-8').splitlines()];assert len(data)==6 and all(r['role']=='original120_train32' for r in data)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for f in as_completed([pool.submit(one,r) for r in data]):
            r=f.result();print(json.dumps(dict(id=r['id'],usable=r['usable'],validation_error=r['validation_error'])),flush=True)
    print('Six training candidates assessed; no classification efficacy inferred.',flush=True)

if __name__=='__main__':main()

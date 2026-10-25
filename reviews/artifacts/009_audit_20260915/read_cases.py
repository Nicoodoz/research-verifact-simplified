from pathlib import Path
import json,sys
root=Path('D:/Research-VeriFact/outputs/009_retrieval_baselines')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def lines(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
mode=sys.argv[1]
if mode=='notes':
    for folder,review in [('development_001','review_001'),('confirmation_001','review_002')]:
        for n in read(root/folder/review/'semantic_001/notes_snapshot.json')['cases']:
            print(n['case_id'], '\n'+n['observation'], '\n'+n['interpretation'], '\nLIMIT '+n['uncertainty'])
elif mode=='interventions':
    for c in read(root/'interventions_001/preparation/cases.json'):
        if c['spec']['case_id'] not in sys.argv[2:]:continue
        print('CASE',c['spec']['case_id'],c['claim'])
        for role in ('keys','addition_control_ids','donor_removal_control_ids','recipient_replaced_ids'):
            print(role)
            for k in c[role]:
                p=c['evidence'][k];print('NOTE',p['note_id'],p['start'],p['date'],p['text'])
elif mode=='case':
    folder=root/sys.argv[2]
    items={i['case_id']:i for i in lines(folder/'judge_preparation/inputs.jsonl')}
    responses={r['request_id']:r for r in lines(folder/'analysis_001/normalized_responses.jsonl')}
    pp={p['passage_id']:p for p in lines(folder/'preparation/corpus.jsonl')}
    for cid in sys.argv[3:]:
        i=items[cid]; print('CASE',cid,i['text']); seen=set()
        for m in ('A48','B48','C48'):
            r=i['retrieval'][m];print('ARM',m,'BODY',r['body_sha256'])
            for k in r['selected_ids']:
                if k not in seen:
                    p=pp[k]; print('NOTE',p['note_id'],p['start'],p['date'],p['text']);seen.add(k)
            print('FULL OUTPUT', responses[r['request_id']]['output_text'])
elif mode=='summary':
    p=Path(__file__).parent
    v=read(p/'replay/verification.json')
    print('TESTS',v['tests']); print('REPLAY FILES',{k:len(vv) for k,vv in v['byte_identical_replays'].items()})
    print('MANIFESTS',len(v['frozen_manifests']))
    e=read(p/'independent_results.json')
    print('ACCOUNTING',json.dumps(e['receipt_accounting'],ensure_ascii=False))
    print('INTERVENTIONS',json.dumps(e['intervention_transformations'],ensure_ascii=False))

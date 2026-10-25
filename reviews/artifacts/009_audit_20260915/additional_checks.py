"""Independent anchor, sampling and isolated corruption probes."""
from pathlib import Path
from collections import Counter,defaultdict
from unittest.mock import patch
from contextlib import ExitStack
import json,hashlib,csv,sys,shutil
ROOT=Path('D:/Research-VeriFact'); OUT=ROOT/'outputs/009_retrieval_baselines'; TMP=Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def rows(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def digest(t):return hashlib.sha256(t.encode()).hexdigest()
def save(x): (TMP/'additional_results.json').write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
sys.path.insert(0,str(ROOT/'tasks/009_retrieval_baselines'))
import study009 as s
import io009
import retrieval_baseline as rb
ev={}
with ExitStack() as stack:
    for name in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
        stack.enter_context(patch(name,side_effect=AssertionError('No audit network')))
    for name,review in [('development_001','review_001'),('confirmation_001','review_002')]:
        folder=OUT/name
        items={i['case_id']:i for i in lines(folder/'judge_preparation/inputs.jsonl')}
        ps={p['passage_id']:p for p in lines(folder/'preparation/corpus.jsonl')}
        normalized={r['request_id']:r for r in lines(folder/'analysis_001/normalized_responses.jsonl')}
        anchors=read(folder/review/'semantic_001/anchors.json')
        for a in anchors:
            item=items[a['case_id']]
            if a['kind']=='ehr':
                p=ps[a['passage_id']]; text=p['text']
                assert p['subject_id']==item['subject_id'] and p['note_id']==a['note_id'] and p['start']==a['start']
                for route in ('dense','bm25','hybrid'):
                    ids=item['rankings'][route] if route=='hybrid' else [r[0] for r in item['rankings'][route]]
                    rank=ids.index(a['passage_id'])+1 if a['passage_id'] in ids else None
                    assert a['route_rank_positions'][route]==rank
                for arm,gate in a['branch_gates'].items():
                    r=item['retrieval'][arm]
                    k=a['passage_id']
                    assert gate['candidate_eligible']==(k in r['candidate_ids'])
                    assert gate['selected']==(k in r['selected_ids'])
                    scored=sorted(r['candidate_ids'],key=lambda k:(-item['scores'][k],k))
                    assert gate['exact_rerank_position']==(scored.index(k)+1 if k in scored else None)
            else:
                r=item['retrieval'][a['method']]
                assert r['request_id']==a['request_id']
                text=normalized[a['request_id']]['output_text']
            assert digest(text)==a['text_sha256']
            assert a['positions'] and all(text[start:end]==a['quote'] for start,end in a['positions'])
        ev[name+'_anchors']=dict(count=len(anchors),kinds=dict(Counter(a['kind'] for a in anchors)))
    # Independently reproduce the confirmation review rule and all NS additions.
    folder=OUT/'confirmation_001'; changes=rows(folder/'analysis_001/transitions.csv'); items={i['proposition_id']:i for i in lines(folder/'judge_preparation/inputs.jsonl')}
    def key(r):return digest('009/review/v1:'+r['proposition_id'])
    chosen=set()
    for author in ('llm','human'):
        for status in ('improved','worsened','changed_wrong'):
            for contrast in ('B_minus_A','C_minus_A'):
                chosen.update(r['proposition_id'] for r in sorted((r for r in changes if r['author_type']==author and r[contrast]==status),key=key)[:2])
        for status in ('stable_correct','stable_wrong'):
            pool=[r for r in changes if r['author_type']==author and r['B_minus_A']==r['C_minus_A']==status and any(items[r['proposition_id']]['retrieval'][m]['body_sha256']!=items[r['proposition_id']]['retrieval']['A48']['body_sha256'] for m in ('B48','C48'))]
            chosen.update(r['proposition_id'] for r in sorted(pool,key=key)[:2])
    assert chosen=={r['proposition_id'] for r in rows(folder/'review_001/index.csv')}
    before=len(chosen)
    chosen.update(r['proposition_id'] for r in changes if r['human_gt']=='Not Supported' and (r['A48']!=r['B48'] or r['A48']!=r['C48']))
    assert chosen=={r['row']['proposition_id'] for r in lines(folder/'review_002/packets.jsonl')}
    ev['review_sample']={'first_rule_cases':before,'all_NS_changes_added':len(chosen)-before,'final':len(chosen)}
    # A small frozen stage copied to the isolated audit directory. Successful
    # reads precede mutations, avoiding a test that merely fails for bad setup.
    mirror=TMP/'corruption_probes'; destination=mirror/'live/dev_rerank'
    shutil.copytree(OUT/'live/dev_rerank',destination)
    state=read(destination/'state.json'); rid=next(iter(state['jobs'])); ptr=state['jobs'][rid]['receipts'][0]
    recpath=destination/ptr['file']; original=recpath.read_bytes()
    def rejects(call):
        try:call()
        except (AssertionError,ValueError):return True
        raise AssertionError('Corruption was accepted')
    with patch.object(s,'OUT',mirror),patch.object(s,'ROOT',TMP):
        assert len(io009.stage('dev_rerank')[0])==110
        recpath.write_bytes(original+b' ')
        assert rejects(lambda:io009.stage('dev_rerank'))
        recpath.write_bytes(original)
        mpath=destination/'manifest.json'; mbytes=mpath.read_bytes(); m=read(mpath)
        m['jobs'][0]['body']['query']+=' altered'
        mpath.write_text(json.dumps(m),encoding='utf-8')
        assert rejects(lambda:io009.stage('dev_rerank'))
        mpath.write_bytes(mbytes)
        assert len(io009.stage('dev_rerank')[0])==110
    item=next(iter(items.values())); ps={p['passage_id']:p for p in lines(folder/'preparation/corpus.jsonl')}
    ids=item['retrieval']['A48']['candidate_ids']; scores=dict(item['scores']); scores.pop(ids[0])
    assert rejects(lambda:rb.pack(ids,scores,ps,item['admission']))
    other=next(k for k,p in ps.items() if p['subject_id']!=item['subject_id'])
    assert rejects(lambda:rb.pack([ids[0],other],{ids[0]:1,other:1},ps,item['admission']))
    ev['isolated_negative_controls']=['receipt byte tamper rejected','frozen request changed rejected','missing real score rejected','mixed-patient evidence rejected']
    ev['network_disabled']=True
save(ev)
print(json.dumps(ev,ensure_ascii=False,indent=2))

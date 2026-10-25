"""Auditor-written direct-source checks; no 012 computation modules imported."""
from pathlib import Path
from collections import Counter,defaultdict
from contextlib import ExitStack
from unittest.mock import patch
import csv,json,re,hashlib,sys
import duckdb,pandas as pd
from sklearn.metrics import matthews_corrcoef,confusion_matrix
R=Path('D:/Research-VeriFact');O=R/'outputs/012_comparative_error_diagnosis';TEN=R/'outputs/010_verifact_baseline_alignment';NINE=R/'outputs/009_retrieval_baselines/confirmation_001';RAW=R/'data/00_raw/verifact-bhc/1.1.0';T=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(t):return hashlib.sha256(t.encode()).hexdigest()
def fp(x):return digest(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False))
def save(): (T/'independent_results.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
e={'no_012_implementation_imported':True,'network_disabled':True}
with ExitStack() as st:
    for name in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):st.enter_context(patch(name,side_effect=AssertionError('No network')))
    aligned={r['row']['proposition_id']:r for r in jl(O/'alignment_002/aligned_materials.jsonl')}
    ledger=jl(O/'diagnosis_001/ledger.jsonl');cohort=rows(TEN/'preparation_001/cohort.csv');ids={r['proposition_id'] for r in cohort}
    assert ids==set(aligned)=={r['proposition_id'] for r in ledger} and len(ids)==len(ledger)==650
    bypid={r['proposition_id']:r for r in ledger}
    cfg=[r for r in rows(RAW/'verifact/rater_configurations.csv') if r['rater_alias']=='v1.1.0-rater-121'];assert len(cfg)==1
    assert all(cfg[0][k]==v for k,v in dict(model='R1-70B',fact_type='sentence',top_n='100',retrieval_method='rerank',reference_format='absolute_time',reference_only_admission='True',deduplicate_text='True').items())
    with duckdb.connect() as db:
        db.register('selected',pd.DataFrame({'proposition_id':sorted(ids)}))
        original=db.execute('SELECT proposition_id, reference_id, verdict, reason, reasoning_chain, reasoning_final_answer FROM read_parquet(?) JOIN selected USING(proposition_id) WHERE rater_alias=?',[str(RAW/'verifact/verdicts.parquet'),'v1.1.0-rater-121']).fetchall()
        db.register('wanted',pd.DataFrame({'reference_id':sorted({r[1] for r in original})}))
        references=dict(db.execute('SELECT reference_id, reference FROM read_parquet(?) JOIN wanted USING(reference_id)',[str(RAW/'verifact/reference_payloads.parquet')]).fetchall())
    assert len(original)==650
    final_positions=[]
    for pid,rid,label,reason,chain,final in original:
        p=aligned[pid];assert all(p['original'][key]==v for key,v in dict(reference_id=rid,verdict=label,reason=reason,reasoning_chain=chain,reasoning_final_answer=final).items())
        assert p['input']['references']['verifact_reference']==references[rid] and digest(references[rid])==rid and bypid[pid]['O']==label
        found=[]
        for m in re.finditer('{',final):
            try:value,size=json.JSONDecoder().raw_decode(final[m.start():])
            except ValueError:continue
            if isinstance(value,dict) and 'verdict' in value and 'reason' in value:found.append((m.start(),size,value['verdict']))
        assert len(found)==1 and found[0][2]==label
        final_positions.append({'proposition_id':pid,'offset':found[0][0],'verdict':label})
    prep_jobs={j['request_id']:j for j in jl(TEN/'preparation_001/jobs.jsonl')}
    state=read(TEN/'live/judge/state.json'); manifest=read(TEN/'live/judge/manifest.json');assert fp(manifest)==state['run_id']
    assignments=rows(TEN/'preparation_001/assignments.csv');assert len(assignments)==1300
    for a in assignments:
        pid,rid,arm=a['proposition_id'],a['request_id'],a['arm'];p=aligned[pid];job=prep_jobs[rid]
        assert job['body']==p['current_bodies'][arm] and fp(job['body'])==a['body_sha256']
        received=[]
        for ptr in state['jobs'][rid]['receipts']:
            path=TEN/'live/judge'/ptr['file'];r=read(path);assert sha(path)==ptr['sha256'] and r['request_id']==rid and r['run_id']==state['run_id'] and r['job_sha256']==fp(job)
            if r['transport']['http_status']==200:received.append(json.loads(r['transport']['body_text']))
        assert len(received)==1;raw=received[0]['choices'][0]['message']['content']
        assert raw==p['current_outputs'][arm]['output_text']
        value=json.loads(raw);assert value['verdict']==bypid[pid]['V' if arm=='verifact_reference' else 'C']
        assert json.loads(job['body']['messages'][1]['content'])=={'proposition':p['input']['text'],'reference':p['input']['references'][arm]}
    metrics={};counts={}
    for author in ('llm','human'):
        own=[r for r in ledger if r['author_type']==author];metrics[author]={};counts[author]={}
        for system in ('O','V','C'):
            gt=[r['human_gt'] for r in own];pred=[r[system] for r in own]
            metrics[author][system]={'n':len(own),'pa':sum(a==b for a,b in zip(gt,pred))/len(own),'mcc':matthews_corrcoef(gt,pred),'confusion_S_NS_NA':confusion_matrix(gt,pred,labels=['Supported','Not Supported','Not Addressed']).tolist()}
        for a,b in [('O','V'),('O','C'),('V','C')]:
            c=Counter()
            for r in own:
                x,y=r[a]==r['human_gt'],r[b]==r['human_gt'];c['both_correct' if x and y else 'both_wrong' if not x and not y else 'improved' if y else 'worsened']+=1
            counts[author][a+'->'+b]=dict(c)
    union=[r for r in ledger if any(r[k]!=r['human_gt'] for k in ('O','V','C'))];commonwrong=sum(all(r[k]!=r['human_gt'] for k in ('O','V','C')) for r in ledger)
    assert len(union)==195 and commonwrong==51
    assert {r['proposition_id'] for r in union}=={r['proposition_id'] for r in jl(O/'diagnosis_001/error_union.jsonl')}
    selected=read(O/'alignment_002/selection.json'); assert len(selected)==24
    reviewed={r['proposition_id'] for r in ledger if r['semantic_review_status']=='deep_read_complete_executor'};assert reviewed==set(selected)
    assert sum(r['proposition_id'] not in reviewed for r in union)==176
    e.update(source_binding={'claims':650,'current_raw_outputs':1300,'original_final_labels_match':650},metrics=metrics,transitions=counts,error_union=195,all_wrong=51,all_correct=455,not_deep_read_errors=176);save();print('Direct release/native receipt mapping and independent metrics passed',flush=True)
    # Independent deterministic selection, including reconstruction of prior membership.
    prior=set()
    for path in [NINE/'review_002/packets.jsonl',TEN/'review_002/packets.jsonl',R/'outputs/011_evidence_integrity_packaging/pilot_review_001/packets.jsonl']:
        for p in jl(path):prior.add(p.get('input',{}).get('proposition_id',p.get('row',{}).get('proposition_id')))
    choose=[];pat=Counter();vcounts=Counter();gcounts=Counter()
    def take(pool):
        pool=[r for r in pool if r['proposition_id'] not in choose]
        if not pool:return
        r=min(pool,key=lambda r:(r['proposition_id'] in prior,pat[r['subject_id']],vcounts[(r['author_type'],r['V']==r['human_gt'])],gcounts[(r['author_type'],r['human_gt'])],digest('012/deep/v1:'+r['proposition_id'])))
        choose.append(r['proposition_id']);pat[r['subject_id']]+=1;vcounts[(r['author_type'],r['V']==r['human_gt'])]+=1;gcounts[(r['author_type'],r['human_gt'])]+=1
    def direction(r,a,b):return (r[a]==r['human_gt'],r[b]==r['human_gt'])
    for author in ('llm','human'):
        for pair in [(False,True),(True,False),(False,False),(True,True)]:
            pool=[r for r in ledger if r['author_type']==author and direction(r,'O','C')==pair]
            for _ in range(min(3,len(pool))):take(pool)
    for author in ('llm','human'):
        for pair in [(False,True),(True,False),(False,False),(True,True)]:
            pool=[r for r in ledger if r['author_type']==author and direction(r,'O','V')==pair]
            if not any(r['proposition_id'] in choose for r in pool):take(pool)
    for sid in sorted({r['subject_id'] for r in ledger}):
        for author in ('llm','human'):
            pool=[r for r in ledger if r['subject_id']==sid and r['author_type']==author]
            if not any(r['proposition_id'] in choose for r in pool):take(pool)
    assert set(choose)==set(selected) and sum(pid not in prior for pid in choose)==22
    e['selection']={'reconstructed':24,'outside_prior_009_011_case_packets':22,'authors_by_O_C_cells':dict(Counter(r['author_type']+'/'+str(direction(r,'O','C')) for r in ledger if r['proposition_id'] in choose))};save()
    # Scan exact 010 reference source ranges, independent of 012 trace/selector code.
    notes={n['ROW_ID']:n for n in jl(O/'materials_001/ehr_notes.jsonl')};risks=[];blocks_total=0
    for pid,p in aligned.items():
        ref=p['input']['references']['c48_reference']
        starts=list(re.finditer(r'(?m)^\d+\. Date: ',ref))
        for i,m in enumerate(starts):
            block=ref[m.start():starts[i+1].start() if i+1<len(starts) else len(ref)]
            head=re.match(r'\d+\. Date: .*?, Time: .*?, Note Category: .*?, Note ID: (\d+), Raw characters: \[(\d+),(\d+)\) \| Text: ',block);assert head
            nid,lo,hi=head.group(1),int(head.group(2)),int(head.group(3));n=notes[nid]
            assert n['SUBJECT_ID']==p['row']['subject_id'] and block[head.end():].rstrip()==n['TEXT'][lo:hi].rstrip();blocks_total+=1
            prefix=n['TEXT'][:lo];match=re.search(r'(?i)\b(?:no|not|without|denies)\s*$',prefix)
            if match:risks.append((p['row']['case_id'],nid,lo,match.start()))
    savedrisks=read(O/'pipeline_001/boundary_candidates.json'); assert len(risks)==40 and len({(notes[n]['SUBJECT_ID'],n,lo) for cid,n,lo,_ in risks})==11
    assert {(cid,n,neglo) for cid,n,lo,neglo in risks}=={(r['case_id'],r['trace']['note_id'],r['trace']['start']) for r in savedrisks}
    e['boundary_scan']={'all_C_reference_blocks':blocks_total,'occurrences':len(risks),'claims':len({r[0] for r in risks}),'unique_note_boundaries':11,'not_medical_error_prevalence':True};save()
    # Every reported literal anchor independently resolves to the bound source.
    packets={p['row']['case_id']:p for p in jl(O/'materials_001/packets.jsonl')};anchorcount=0
    for d in read(O/'diagnosis_001/diagnoses.json'):
        p=packets[d['case_id']]
        for a in d['anchors']:
            if a['kind']=='parent':txt=p['proposition']['parent_text_chunk']
            elif a['kind']=='human':txt=p['human'][a['field']]
            elif a['kind']=='reference':txt=p['input']['references']['verifact_reference' if a['system']=='V' else 'c48_reference']
            elif a['system']=='O':txt=p['original'][a.get('field','reasoning_final_answer')]
            else:txt=p['current_outputs']['verifact_reference' if a['system']=='V' else 'c48_reference']['output_text']
            assert digest(txt)==a['source_text_sha256'] and a['positions'] and all(txt[start:end]==a['quote'] for start,end in a['positions']);anchorcount+=1
    e['literal_anchors_validated']=anchorcount
    h=read(O/'handoff_snapshot.json');assert all(sha(R/p)==v for p,v in h['files'].items());e['handoff_unchanged_after']=True;save()
print(json.dumps({k:v for k,v in e.items() if k not in ('metrics','transitions')},ensure_ascii=False,indent=2),flush=True)

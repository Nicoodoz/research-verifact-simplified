"""Post-evaluation fixed case selection and traceability diagnosis; never alters inputs."""
from collections import Counter,defaultdict
import common028 as c
def run():
    out=c.OUT/'diagnosis_001';out.mkdir(exist_ok=False);a=c.OUT/'analysis_001';norm=c.lines(a/'normalized.jsonl');nn={(r['proposition_id'],r['arm']):r for r in norm};cs=c.csvread(a/'candidates.csv');byid={r['proposition_id']:r for r in cs};materials={r['proposition_id']:r for r in c.lines(c.OUT/'preparation_001/materials.jsonl')};fixed=[]
    for key in ('C06','C16','C14','C29'):
        pid=c.read(c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/case_material_001'/(key+'.json'))['proposition_id'];fixed.append((pid,'027_'+key))
    strata=defaultdict(list)
    for r in cs:
        if r['trace']==r['repeat']:continue
        tag=('recovered_R' if r['trace']=='Supported' else 'lost_R') if r['RHW']=='R' else ('new_risk' if r['trace']=='Supported' else 'blocked_risk');strata[r['group']+'/'+tag].append(r)
    extras=[(min(v,key=lambda r:c.fingerprint('028/review/'+r['proposition_id']))['proposition_id'],k) for k,v in sorted(strata.items())][:8];selected=[];seen=set()
    for pid,why in fixed+extras:
        if pid not in seen:selected.append((pid,why));seen.add(pid)
    for i,(pid,why) in enumerate(selected,1):
        row=byid[pid];m=materials[pid];c.put(out/f'K{i:02}.json',dict(case_id=f'K{i:02}',selection=why,row=row,claim=m['text'],reference=m['reference'],repeat=nn[pid,'repeat'],trace=nn[pid,'trace']))
    selection=[dict(case_id=f'K{i:02}',proposition_id=pid,selection=why,**{k:byid[pid][k] for k in ('group','subject_id','author_type','GT','RHW','SD','repeat','trace')}) for i,(pid,why) in enumerate(selected,1)];c.put(out/'case_selection.json',selection)
    # Additional source is historical released retrieval reference, NOT entire EHR.
    wanted={p for p,_ in fixed};source=c.ROOT/'outputs/018_verifact_gap_attribution/preparation_001/materials.jsonl';old=[r for r in c.lines(source) if r['row']['proposition_id'] in wanted]
    for r in old:c.put(out/('extra_'+r['row']['proposition_id']+'.json'),dict(proposition_id=r['row']['proposition_id'],claim=r['row']['text'],reference=r['references']['O'],source='018 frozen original VeriFact released reference; not full EHR',not_in_028_API=True))
    tr=[r for r in norm if r['arm']=='trace'];veto=[dict(proposition_id=r['proposition_id'],group=r['group'],RHW=byid[r['proposition_id']]['RHW'],diagnostics=r['adherence']) for r in tr if r['relation_only_keep'] and not r['keep']]
    traceability=dict(rows_distribution=dict(Counter(len(r['rows']) for r in tr)),total_requirements=sum(len(r['rows']) for r in tr),relation_counts=dict(Counter(row['relation'] for r in tr for row in r['rows'])),citation_failures=[dict(proposition_id=r['proposition_id'],row=row['index'],reference_id=e['reference_id'],quote=e['quote']) for r in tr for row in r['rows'] for e in row['evidence'] if not e['valid']],veto=veto,veto_RHW=dict(Counter(r['RHW'] for r in veto)),mean_output_tokens_by_arm={arm:sum(r['usage']['completion_tokens'] for r in norm if r['arm']==arm)/155 for arm in ('trace','repeat')})
    conflicts=c.read(c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/analysis_002/conflicts.json');diversity={}
    for group in ('025','026'):
        gs=[]
        for g in conflicts[group]['mixed_groups']:
            profiles=[];actions=[]
            for pid in g['ids']:
                r=nn[pid,'trace'];counts=Counter(v['relation'] for v in r['rows']);profiles.append(tuple(counts[k] for k in ('supported','contradicted','unaddressed','uncertain')));actions.append(r['keep'])
            gs.append(dict(ids=g['ids'],distinct_relation_count_profiles=len(set(profiles)),distinct_keep_actions=len(set(actions))))
        diversity[group]=gs
    c.put(out/'traceability.json',traceability);c.put(out/'conflict_representation.json',diversity)
    deps=[source,a/'manifest.json',c.TASK/'diagnose028.py',c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/analysis_002/conflicts.json']+[c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/case_material_001'/(k+'.json') for k in ('C06','C16','C14','C29')]
    c.put(out/'manifest.json',dict(inputs={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in deps},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print(c.canonical(dict(cases=selection,traceability=traceability)))
if __name__=='__main__':run()

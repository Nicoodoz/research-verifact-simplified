"""Assemble fixed 31-case reading packets, no external data or model calls."""
import common027 as x
c=x.c
def run():
    x.offline();out=x.OUT/'case_material_001';out.mkdir(exist_ok=False)
    selection=x.read(x.OUT/'analysis_001/case_selection.json');items={r['proposition_id']:r for r in x.read(x.OUT/'analysis_001/candidates.json') if r['group']=='026'}
    source=x.ROOT/'outputs/026_frozen_sd_patient_transfer';materials={r['proposition_id']:r for r in c.jl(source/'preparation_001/inputs.jsonl')};nn={(r['proposition_id'],r['model_key']):r for r in c.jl(source/'analysis_001/normalized.jsonl') if r['arm']=='S'}
    index=[]
    for i,s in enumerate(selection,1):
        pid=s['proposition_id'];r=items[pid];mat=materials[pid];case=dict(case_id=f'C{i:02}',**s,features=r,D_scores=r['D_scores'],Q_scores=r['Q_scores'],gate_probability=r['SD'],claim=mat['text'],reference=mat['reference'],DeepSeek_output=nn[pid,'deepseek']['output_text'],Qwen_output=nn[pid,'qwen']['output_text'])
        x.put(out/(case['case_id']+'.json'),case)
        text=f"# {case['case_id']} {s['role']} {r['kind']} keep={r['keep']} patient={r['subject_id']} {r['author_type']}\n\nID {pid}\nGT {r['GT']}; D {list(r['D_scores'].values())}; Q {list(r['Q_scores'].values())}; gate {r['SD']:.6f}\n\nCLAIM: {mat['text']}\n\nREFERENCE (complete):\n{mat['reference']}\n\nDEEPSEEK OUTPUT:\n{case['DeepSeek_output']}\n\nQWEN OUTPUT:\n{case['Qwen_output']}\n"
        (out/(case['case_id']+'.md')).write_text(text,encoding='utf-8',newline='\n')
        index.append(dict(case_id=case['case_id'],**s,claim=mat['text'],D_scores=r['D_scores'],Q_scores=r['Q_scores'],prob=r['SD'],reference_chars=len(mat['reference'])))
    x.put(out/'index.json',index);x.put(out/'manifest.json',dict(inputs={p.relative_to(x.ROOT).as_posix():x.sha(p) for p in [x.TASK/'cases027.py',x.OUT/'analysis_001/manifest.json',source/'preparation_001/inputs.jsonl',source/'analysis_001/normalized.jsonl']},outputs={p.name:x.sha(p) for p in out.iterdir() if p.is_file()}))
    print(*[f"{r['case_id']} {r['kind']} keep={r['keep']} {r['subject_id']} {r['claim']} | D={r['D_scores']} Q={r['Q_scores']} p={r['prob']:.4f}" for r in index],sep='\n')
if __name__=='__main__':run()

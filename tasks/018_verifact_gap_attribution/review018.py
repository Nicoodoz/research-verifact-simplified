"""Deterministic coverage priorities and complete, nontruncated reading pages."""
from collections import defaultdict,Counter
import argparse
import common018 as c

def prepare():
    root=c.OUT/'review_001';c.require(not root.exists(),'Review preparation exists')
    mats=c.jsonlines(c.OUT/'preparation_001/materials.jsonl');rows=[m['row'] for m in mats]
    sources=[('009',c.ROOT/'outputs/009_retrieval_baselines/confirmation_001/review_002/semantic_001/notes_snapshot.json'),
        ('010',c.TEN/'review_002/semantic_001/notes_snapshot.json'),('012',c.ROOT/'outputs/012_comparative_error_diagnosis/diagnosis_001/diagnoses.json')]
    prior=defaultdict(list)
    for task,path in sources:
        value=c.read(path)
        for n in value['cases'] if isinstance(value,dict) else value:
            cid='010_old6_'+n['case_id']
            if any(r['case_id']==cid for r in rows):prior[cid].append(dict(task=task,path=path.relative_to(c.ROOT).as_posix(),note=n))
    chosen={};reason=defaultdict(list)
    def add(r,why):chosen[r['case_id']]=r;reason[r['case_id']].append(why)
    directional=[r for r in rows if r['bucket'] in ('O_only','C_only')]
    # Prior complete diagnoses are reused rather than silently redone or inflated.
    for r in directional:
        if any(n['task'] in ('010','012') for n in prior[r['case_id']]):add(r,'existing010_or012_directional_diagnosis')
    for keys in (('subject_id','author_type','bucket'),('cohort','author_type','bucket','human_gt')):
        for vals in sorted({tuple(r[k] for k in keys) for r in directional}):
            group=[r for r in directional if tuple(r[k] for k in keys)==vals]
            if not any(r['case_id'] in chosen for r in group):add(min(group,key=lambda r:c.fingerprint('018/full-read/v1:'+r['proposition_id'])),'coverage/'+str(keys)+'/'+str(vals))
    selected=c.read(c.OUT/'preparation_001/reading_selection.json')
    for sid in sorted({r['subject_id'] for r in rows}):
        for bucket in ('both_wrong','both_correct'):
            group=[r for r in rows if r['subject_id']==sid and r['bucket']==bucket and r['proposition_id'] in selected]
            if group:add(min(group,key=lambda r:c.fingerprint('018/control/v1:'+r['proposition_id'])),'control/'+bucket)
    root.mkdir();(root/'pages').mkdir();(root/'briefs').mkdir()
    c.write_json(root/'prior_diagnoses.json',dict(prior));c.write_json(root/'deep_priority.json',dict(reasons=dict(reason),cases=sorted(chosen)))
    # Full material pages preserve every character; only identical block text+metadata is shared.
    catalog={b['block_id']:b for b in c.jsonlines(c.OUT/'preparation_001/blocks.jsonl')}
    bindings=defaultdict(list)
    for b in c.csvrows(c.OUT/'preparation_001/block_bindings.csv'):bindings[(b['case_id'],b['arm'])].append(b)
    display={k:f'B{i+1:05d}' for i,k in enumerate(catalog)};seen={};page_index=[];case_index=[]
    for mat in sorted(mats,key=lambda m:(m['row']['cohort'],m['row']['subject_id'],m['row']['case_id'])):
        r=mat['row'];cid=r['case_id'];pid=r['proposition_id']
        if r['bucket'] in ('O_only','C_only'):
            brief=dict(row=r,original_final=mat['outputs']['O']['reasoning_final_answer'],current_final={s:mat['outputs'][s]['output_text'] for s in ('C','V','Q') if s in mat['outputs']},
                role='Final-output screening only; cannot establish evidence absence or internal mechanism')
            with (root/'briefs'/f'{r["cohort"]}_{r["subject_id"]}.jsonl').open('a',encoding='utf-8',newline='\n') as f:f.write(c.canonical(brief)+'\n')
        if cid not in chosen:continue
        text=f"CASE {cid} {r['author_type']} patient={r['subject_id']} GT={r['human_gt']} O={r['O']} C={r['C']} V={r.get('V','not_run')} bucket={r['bucket']}\nCLAIM: {r['text']}\n"
        text+='\nPRIOR DIAGNOSES\n'+c.canonical(prior[cid])+'\nFULL OUTPUTS\n'+c.canonical(mat['outputs'])+'\nFULL REFERENCES (exact block dedup with metadata)\n'
        newblocks=[]
        for arm in ('O','C'):
            bb=bindings[(cid,arm)];text+='\n'+arm+' HEADER '+mat['references'][arm][:int(bb[0]['start'])]
            text+='\n'+arm+' ORDER '+','.join(b['number']+'='+display[b['block_id']] for b in bb)+'\n'
            for b in bb:
                key=b['block_id']
                if key in seen:continue
                z=catalog[key];text+=f"\n{display[key]} date={z['date']} time={z['time']} category={z['category']} description={z['description']} note={z['note_id']}\n{z['text']}\n"
                seen[key]=cid;newblocks.append(key)
        chunks=[text[i:i+26000] for i in range(0,len(text),26000)]
        names=[]
        for i,chunk in enumerate(chunks):
            name=f'{len(page_index)+1:04d}_{cid}_p{i+1}.txt';(root/'pages'/name).write_text(chunk,encoding='utf-8',newline='\n');names.append(name)
            page_index.append(dict(page=len(page_index)+1,case_id=cid,part=i+1,parts=len(chunks),file='pages/'+name,characters=len(chunk),sha256=c.file_hash(root/'pages'/name)))
        case_index.append(dict(case_id=cid,proposition_id=pid,bucket=r['bucket'],cohort=r['cohort'],subject_id=r['subject_id'],author_type=r['author_type'],pages=names,
            reused_block_cases=sorted({seen[b['block_id']] for arm in ('O','C') for b in bindings[(cid,arm)] if seen[b['block_id']]!=cid}),
            full_material_characters=len(text),prior_sources=[n['path'] for n in prior[cid]]))
    c.write_json(root/'page_index.json',page_index);c.write_json(root/'case_index.json',case_index);c.write_json(root/'block_display.json',display)
    c.write_json(root/'summary.json',dict(priority_cases=len(chosen),buckets=dict(Counter(r['bucket'] for r in chosen.values())),cohorts=dict(Counter(r['cohort'] for r in chosen.values())),
        pages=len(page_index),characters=sum(p['characters'] for p in page_index),directional_screening=len(directional),not_yet_read=True,
        unprioritized_directional=len(directional)-sum(r['bucket'] in ('O_only','C_only') for r in chosen.values())))
    c.seal(root,[c.OUT/'preparation_001/manifest.json']+[p for _,p in sources],[c.TASK/'review018.py'])
    print(c.canonical(c.read(root/'summary.json')))

if __name__=='__main__':prepare()

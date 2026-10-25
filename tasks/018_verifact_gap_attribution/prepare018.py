"""Bind only the two exposed cohorts, complete outputs, exact references and saved pipelines."""
from collections import Counter
import subprocess
import duckdb
import pandas as pd
import common018 as c

def prepare():
    out=c.OUT/'preparation_001';c.require(not out.exists(),'Do not overwrite preparation')
    c.twelve.check(c.ROOT/'outputs/012_comparative_error_diagnosis/alignment_002')
    for p in (c.SIXTEEN/'stage1/preparation_002',c.SIXTEEN/'stage1/base_preparation_001',c.SIXTEEN/'completion_002/analysis_001'):c.prior.old.check_manifest(p)
    src,passages,paths=c.prior.sources();source={r['proposition_id']:r for r in src}
    cohorts={q:c.csvrows(p) for q,p in [('010',c.TEN/'preparation_001/cohort.csv'),('016',c.SIXTEEN/'stage1/preparation_002/cohort.csv')]}
    order=c.prior.old.baseline.patient_order()
    for q,expected in [('010',order[18:24]),('016',order[24:30])]:c.require({r['subject_id'] for r in cohorts[q]}==set(expected),'Patient isolation')
    c.require(len(cohorts['010'])==650 and len(cohorts['016'])==601,'Cohort size')
    ids={r['proposition_id'] for rows in cohorts.values() for r in rows};c.require(len(ids)==1251,'Duplicate claims')
    rawfiles=[c.RAW/'verifact'/n for n in ('verdicts.parquet','reference_payloads.parquet','rater_configurations.csv')]
    release_manifest=c.read(c.ROOT/'outputs/002_reproduce_paper_results/run_003/manifest.json')
    for p in rawfiles:c.require(c.file_hash(p)==release_manifest['input_sha256'][p.relative_to(c.RAW).as_posix()],'Raw release changed')
    with duckdb.connect() as db:
        db.register('wanted',pd.DataFrame({'proposition_id':sorted(ids)}))
        df=db.execute('SELECT v.* FROM read_parquet(?) v JOIN wanted USING(proposition_id) WHERE rater_alias=?',[str(rawfiles[0]),'v1.1.0-rater-121']).fetchdf()
        originals={r['proposition_id']:r for r in df.where(pd.notna(df),None).to_dict('records')}
        db.register('refs',pd.DataFrame({'reference_id':sorted({r['reference_id'] for r in originals.values()})}))
        ref=dict(db.execute('SELECT reference_id,reference FROM read_parquet(?) JOIN refs USING(reference_id)',[str(rawfiles[1])]).fetchall())
    c.require(len(originals)==1251,'Original predictions incomplete')
    norm16={(r['proposition_id'],r['role']):r for r in c.jsonlines(c.SIXTEEN/'completion_002/analysis_001/normalized_responses.jsonl')}
    old12={r['row']['proposition_id']:r for r in c.jsonlines(c.ROOT/'outputs/012_comparative_error_diagnosis/alignment_002/aligned_materials.jsonl')}
    preds={q:{s:{r['proposition_id']:r['verdict'] for r in c.csvrows(p)} for s,p in files.items()} for q,files in {
        '010':{'O':c.TEN/'preparation_001/released_predictions.csv','V':c.TEN/'analysis_001/predictions_verifact_reference.csv','C':c.TEN/'analysis_001/predictions_c48_reference.csv'},
        '016':{'O':c.SIXTEEN/'completion_002/analysis_001/predictions_released.csv','C':c.SIXTEEN/'completion_002/analysis_001/predictions_v4_first.csv','Q':c.SIXTEEN/'completion_002/analysis_001/predictions_qwen.csv'}}.items()}
    records=[];materials=[];block_catalog={};bindings=[]
    for q,rows in cohorts.items():
        for r in rows:
            pid=r['proposition_id'];item=source[pid];o=originals[pid]
            c.require(r['invalid']=='False' and r['proposition_type']=='claim','Expected valid claims')
            values={s:p[pid] for s,p in preds[q].items()};c.require(values['O']==o['verdict'] and o['model']=='R1-70B','Original binding mismatch')
            refs={'O':ref[o['reference_id']],'C':item['baseline']['reference']}
            c.require(c.prior.old.pilot.digest_text(refs['O'])==o['reference_id'],'Released reference digest mismatch')
            outputs={'O':{k:o[k] for k in ('reason','reasoning_chain','reasoning_final_answer')}}
            if q=='010':
                packet=old12[pid]
                c.require(refs['O']==packet['input']['references']['verifact_reference'] and refs['C']==packet['input']['references']['c48_reference'],'010 reference binding')
                outputs.update({s:packet['current_outputs'][arm] for s,arm in [('V','verifact_reference'),('C','c48_reference')]})
            else:outputs.update({s:norm16[(pid,role)] for s,role in [('C','v4_first'),('Q','qwen')]})
            for s in values:
                if s!='O':c.require(outputs[s]['verdict']==values[s] and outputs[s]['status']=='success','Current prediction binding')
            row=dict(r,cohort=q,case_id=q+'_'+item['case_id'],text=item['text'],**values,bucket=c.bucket(values['O'],values['C'],r['human_gt']),
                correctness_pattern=''.join('1' if values[s]==r['human_gt'] else '0' for s in ('O','V','C')) if q=='010' else '',
                reference_id=o['reference_id'],semantic_status='not_reviewed',mechanism='unknown')
            records.append(row)
            materials.append(dict(row=row,outputs=outputs,references=refs,pipeline=item))
            for arm,text in refs.items():
                for b in c.blocks(text):
                    # Exact clinical text AND metadata; no normalization of clinical content.
                    identity={k:b[k] for k in ('date','time','category','description','note_id','text')}
                    key=c.fingerprint(dict(subject_id=r['subject_id'],**identity))
                    block_catalog.setdefault(key,dict(block_id=key,subject_id=r['subject_id'],**identity))
                    bindings.append(dict(proposition_id=pid,case_id=row['case_id'],arm=arm,number=b['number'],block_id=key,start=b['start'],end_exclusive=b['end_exclusive']))
    selected={r['proposition_id']:'directional' for r in records if r['bucket'] in ('O_only','C_only')}
    for sid in order[18:30]:
        for bucket in ('both_wrong','both_correct'):
            rr=sorted([r for r in records if r['subject_id']==sid and r['bucket']==bucket],key=lambda r:c.fingerprint('018/control/v1:'+r['proposition_id']))[:2]
            selected.update({r['proposition_id']:'control/'+bucket for r in rr})
    out.mkdir(parents=True);c.write_lines(out/'ledger.jsonl',records);c.write_csv(out/'ledger.csv',records,sorted(set().union(*(r.keys() for r in records))))
    c.write_lines(out/'materials.jsonl',materials);c.write_lines(out/'blocks.jsonl',list(block_catalog.values()));c.write_csv(out/'block_bindings.csv',bindings)
    c.write_json(out/'reading_selection.json',selected)
    c.write_csv(out/'cohort.csv',[dict(r,cohort=q) for q,rows in cohorts.items() for r in rows])
    selected_blocks={b['block_id'] for b in bindings if b['proposition_id'] in selected}
    summary=dict(claims=len(records),cohorts={q:dict(Counter(r['bucket'] for r in records if r['cohort']==q)) for q in cohorts},
        selected=len(selected),directional=sum(v=='directional' for v in selected.values()),controls=sum(v!='directional' for v in selected.values()),
        selected_unique_blocks=len(selected_blocks),selected_unique_block_characters=sum(len(block_catalog[k]['text']) for k in selected_blocks),
        selected_full_outputs_characters=sum(len(c.canonical(m['outputs'])) for m in materials if m['row']['proposition_id'] in selected),API_calls=0,cost_cny=0)
    c.write_json(out/'summary.json',summary)
    deps=paths+rawfiles+[c.OUT/'protocol_001.md',c.TEN/'analysis_001/manifest.json',c.ROOT/'outputs/012_comparative_error_diagnosis/alignment_002/manifest.json',c.SIXTEEN/'completion_002/analysis_001/manifest.json']
    c.seal(out,deps,[c.TASK/'common018.py',c.TASK/'prepare018.py'])
    c.write_json(c.OUT/'history_before.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),files={p:c.file_hash(c.ROOT/p) for p in subprocess.check_output(['git','ls-files','-z'],cwd=c.ROOT).decode().split('\0') if p and (c.ROOT/p).is_file()}))
    print(c.canonical(summary))

if __name__=='__main__':prepare()

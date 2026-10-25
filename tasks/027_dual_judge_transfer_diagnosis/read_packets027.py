"""Lossless chunk-deduplicated reading view; all selected references retained."""
import re,collections
import common027 as x
def run():
    root=x.OUT/'case_material_001';out=x.OUT/'reading_view_001';out.mkdir(exist_ok=False);by_patient=collections.defaultdict(list)
    for r in x.read(root/'index.json'):by_patient[r['subject_id']].append(x.read(root/(r['case_id']+'.json')))
    mapping={}
    for sid,rows in by_patient.items():
        seen={};chunks=[];outputs=[]
        for r in rows:
            parts=re.split(r'(?m)^\d+\. ',r['reference']);mapping[r['case_id']]=[]
            for part in parts[1:]:
                if part not in seen:seen[part]=f'P{sid}_{len(chunks)+1:02}';chunks.append((seen[part],part))
                mapping[r['case_id']].append(seen[part])
            ds=re.sub(r'\s+',' ',r['DeepSeek_output']);qs=re.sub(r'\s+',' ',r['Qwen_output'])
            outputs.append(f"## {r['case_id']} {r['role']} {r['kind']} keep={r['keep']}\nCLAIM {r['claim']}\nReference blocks {mapping[r['case_id']]}\nDeepSeek full: {ds}\nQwen full: {qs}\n")
        (out/(sid+'_references.txt')).write_text('\n\n'.join(key+' '+re.sub(r'\s+',' ',value) for key,value in chunks),encoding='utf-8')
        (out/(sid+'_outputs.txt')).write_text('\n'.join(outputs),encoding='utf-8')
    x.put(out/'case_block_mapping.json',mapping)
    x.put(out/'manifest.json',dict(inputs={p.relative_to(x.ROOT).as_posix():x.sha(p) for p in [x.TASK/'read_packets027.py',root/'manifest.json']},outputs={p.name:x.sha(p) for p in out.iterdir() if p.is_file()}))
    print({sid:len(rows) for sid,rows in by_patient.items()})
if __name__=='__main__':run()

"""Small, zero-API cohort overlap map; no re-evaluation or pooled score."""
from itertools import combinations
from common090 import *

def main():
    paths={
        '084':'outputs/084_f4_coverage_validation/sample_blind.jsonl',
        '086_E':'outputs/086_global_demonstration_selection/E_cases_blind.jsonl',
        '087':'outputs/087_f4_evidence_intervention/sample_blind.jsonl',
        '089':'outputs/089_source_audited_demo_compression/sample_blind.jsonl',
        '090':'outputs/090_demo_constructor_repair_validation/cohort_manifest.jsonl'}
    cohorts={};sources={}
    for name,rel in paths.items():
        rows=lines(ROOT/rel);sources[rel]=sha(ROOT/rel)
        panels=sorted({r.get('panel','all') for r in rows})
        for panel in panels:
            z=[r for r in rows if r.get('panel','all')==panel]
            key=name if panel=='all' else name+'_'+panel
            cohorts[key]=(set(r['id'] for r in z),set(str(r['sid']) for r in z))
            assert len(cohorts[key][0])==len(z)
    pairs=[dict(a=a,b=b,shared_ids=len(cohorts[a][0]&cohorts[b][0]),shared_patients=len(cohorts[a][1]&cohorts[b][1])) for a,b in combinations(cohorts,2)]
    put(PUB/'cohort_overlap_map.json',dict(sources=sources,cohorts={k:dict(n=len(v[0]),patients=len(v[1])) for k,v in cohorts.items()},pairs=pairs,
        scope='Only listed formal panels; no claim that absence here means absence from all prior development. 088 has no target evaluation; 085 pending. No pooled performance.'))
    out=['# 084—090正式面板重叠','','ID重叠/患者重叠由各冻结样本文件直接计算；未扫描所有历史任务。0个共同ID不等于新患者或无开发暴露。088没有目标评价，085尚无正式R1结果，不强造评价行。','',
        '|面板A|面板B|共同命题ID|共同患者|','|---|---|---:|---:|']
    for p in pairs:out.append(f"|{p['a']}|{p['b']}|{p['shared_ids']}|{p['shared_patients']}|")
    text(PUB/'cohort_overlap_map.md','\n'.join(out)+'\n')
    print(canonical(dict(cohorts={k:dict(n=len(v[0]),patients=len(v[1])) for k,v in cohorts.items()},pairs=pairs)))

if __name__=='__main__':main()

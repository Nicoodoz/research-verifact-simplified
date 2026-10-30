"""Additional panel split of the already returned160; no new inference."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/120_full_pool_sft'))
from final_compare120 import metrics,paired,LABELS


def main():
    out=ROOT/'outputs/132_midpoint_update'
    rows=[json.loads(s) for s in (out/'screen160_predictions_sanitized.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows)==160 and all(r['midpoint_valid'] for r in rows)
    result={};lines=['# 132：已完成160条的自然／压力分报','',
        '只拆分已返回的同一批160条，不调整扩展规则，不新增推理。两个分面板均是旧500的嵌套子集。','',
        '|面板／模型|N|MCC|PA|正确|false-S/真实非S|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
    for name in ('natural','pressure'):
        subset=[r for r in rows if r['old_panel']==name]
        scores={label:metrics(subset,{r['id']:r[key] for r in subset}) for label,key in
            [('paper_r1','paper_r1'),('107','baseline107'),('120','baseline120'),('132','midpoint132')]}
        old={r['id']:dict(verdict=r['baseline107']) for r in subset};new={r['id']:dict(verdict=r['midpoint132']) for r in subset}
        parent={r['id']:dict(verdict=r['baseline120']) for r in subset}
        result[name]=dict(N=len(subset),scores=scores,vs107=paired(subset,old,new,'107'),vs120=paired(subset,parent,new,'120'))
        for label,m in scores.items():
            recall='/'.join(f"{m['per_class'][g]['recall']*100:.2f}%" if any(r['GT']==g for r in subset) else '—' for g in LABELS)
            lines.append(f"|{name}/{label}|{len(subset)}|{m['mcc']:.4f}|{m['percent_agreement']*100:.2f}%|{m['correct']}|{m['false_S']}/{m['non_S']}|{recall}|")
    (out/'screen160_panels.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'screen160_panels.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({p:{k:{f:v[f] for f in ('mcc','correct','false_S','non_S')} for k,v in r['scores'].items()} for p,r in result.items()}))


if __name__=='__main__':main()

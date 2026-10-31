"""Patient composition intervals conditional on already frozen144 review flags."""
from pathlib import Path
import argparse
import json
import sys

import numpy as np

R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/143_selective_verification'))
from analyze143 import c, load, EXPECTED_SHA, LABELS
sys.path.insert(0,str(R/'src'))
from verifact_research.evaluation.metrics import interval

O=R/'outputs/144_native_confidence'
ITERATIONS=1000
MARKER='## 固定送审标记的患者配对区间'


def summarize(counts):
    """Counts are N, original nonS, residual FS107/FSmargin, automatic N107/Nmargin."""
    n,non_s,fs107,fs_margin,auto107,auto_margin=map(int,counts)
    return dict(N=n,original_non_S=non_s,residual_FS_disagreement107=fs107,
        residual_FS_native_margin=fs_margin,
        residual_FS_rate_disagreement107=fs107/non_s if non_s else None,
        residual_FS_rate_native_margin=fs_margin/non_s if non_s else None,
        delta_residual_FS_rate=(fs_margin-fs107)/non_s if non_s else None,
        automatic_N_disagreement107=auto107,automatic_N_native_margin=auto_margin,
        delta_automatic_coverage=(auto_margin-auto107)/n)


def compute(source):
    frozen=c.read(source);keys,_,predictions=load()
    if (frozen.get('scope')!='full1817' or frozen.get('N')!=len(keys)
            or frozen.get('kind')!='fixed_equal_workload_retrospective'
            or frozen.get('native_labels_unchanged') is not True
            or frozen.get('source107_sha256')!=EXPECTED_SHA['label_only107']):
        raise ValueError('Require the existing full1817 fixed equal-workload analysis')
    patients=sorted({str(row['sid']) for row in keys.values()})
    if len(patients)!=20 or len(keys)!=1817:
        raise ValueError('Expected the original1817 propositions and20 patients')
    result=dict(task=144,scope='full1817',N=len(keys),patients=len(patients),
        source_equal_workload_sha256=c.sha(source),source_keys_sha256=EXPECTED_SHA['keys'],
        iterations=ITERATIONS,seeds='numpy RandomState(seed), seed=0..999',
        resampling='20 lexically sorted patient IDs with replacement; retain whole clusters with multiplicity; paired draws',
        direction='native_margin minus disagreement107',
        estimand='Residual false-S count difference divided by the same original non-S count in each sampled cohort',
        selection='Existing full-cohort review flags fixed; no score sorting, threshold fitting or flag changes inside bootstrap',
        limitations='Conditional patient-composition uncertainty only; excludes historical selection, refitting, new hospitals and CP guarantees. An interval crossing zero proves neither equivalence nor absence of useful ranking.',
        no_automatic_subset_MCC_comparison=True,no_native_label_changes=True,
        new_GPU_calls=0,new_API_calls=0,variants={})
    for variant,name in [('native120','full_pool120'),('claim_repeat136','claim_repeat136')]:
        part=frozen['variants'][variant];labels=predictions[name]
        if frozen['native_sources'][variant]['sha256']!=EXPECTED_SHA[name]:
            raise ValueError('Native source differs from the frozen equal-workload input')
        flags={s:set(part[s+'_review_ids']) for s in ('disagreement','margin')}
        if any(len(values)!=part['k'] or len(part[s+'_review_ids'])!=part['k']
               or not values<=keys.keys() or any(labels[i]!=LABELS[0] for i in values)
               for s,values in flags.items()):
            raise ValueError('Review flags must be unique fixed original-S IDs')
        expected={i for i in keys if labels[i]==LABELS[0] and predictions['label_only107'][i]!=LABELS[0]}
        if flags['disagreement']!=expected:
            raise ValueError('The original107 disagreement flags changed')
        patient_counts=[]
        for sid in patients:
            ids=[i for i,row in keys.items() if str(row['sid'])==sid]
            non_s={i for i in ids if keys[i]['GT']!=LABELS[0]}
            original_fs={i for i in non_s if labels[i]==LABELS[0]}
            patient_counts.append([len(ids),len(non_s),
                len(original_fs-flags['disagreement']),len(original_fs-flags['margin']),
                len(set(ids)-flags['disagreement']),len(set(ids)-flags['margin'])])
        counts=np.asarray(patient_counts,dtype=np.int64)
        point=summarize(counts.sum(axis=0))
        for strategy,key in [('disagreement107','residual_FS_disagreement107'),('native_margin','residual_FS_native_margin')]:
            if (point[key]!=part[strategy]['remaining_automatic_false_S']
                    or point['original_non_S']!=part[strategy]['original_non_S']):
                raise ValueError('Counts differ from original equal-workload metrics')
        risk_draws=[];coverage_draws=[]
        for seed in range(ITERATIONS):
            sample=np.random.RandomState(seed).choice(len(patients),len(patients),replace=True)
            draw=summarize(counts[sample].sum(axis=0))
            if draw['delta_residual_FS_rate'] is not None:
                risk_draws.append(draw['delta_residual_FS_rate'])
            coverage_draws.append(draw['delta_automatic_coverage'])
        result['variants'][variant]=dict(k=part['k'],point=point,
            residual_FS_rate_difference=dict(delta=point['delta_residual_FS_rate'],
                ci95=interval(np.asarray(risk_draws)) if risk_draws else None,
                valid_draws=len(risk_draws),undefined_denominator_draws=ITERATIONS-len(risk_draws)),
            automatic_coverage_difference=dict(delta=point['delta_automatic_coverage'],
                ci95=interval(np.asarray(coverage_draws)),valid_draws=len(coverage_draws)),
            patient_counts=[dict(sid=sid,**summarize(row)) for sid,row in zip(patients,counts)])
    return result


def appendix(result,filename):
    lines=[MARKER,'',
        '固定已有全批送审标记，20名患者整簇有放回抽样1000次（RandomState种子0—999），每次两策略共用同一原非S分母；未重新排序或拟合阈值。差值方向为原生margin减107分歧。','',
        '|主模型/k|残留FS（margin/107）|FS率差（百分点）|配对95%区间（百分点）|自动覆盖差95%区间（百分点）|',
        '|---|---:|---:|---:|---:|']
    for name,v in result['variants'].items():
        p=v['point'];risk=v['residual_FS_rate_difference'];lo,hi=risk['ci95']
        clo,chi=v['automatic_coverage_difference']['ci95']
        lines.append(f"|{name}/{v['k']}|{p['residual_FS_native_margin']}/{p['residual_FS_disagreement107']}（原非S={p['original_non_S']}）|{100*risk['delta']:+.3f}|[{100*lo:+.3f}, {100*hi:+.3f}]|[{100*clo:+.3f}, {100*chi:+.3f}]|")
    lines += ['',
        '两策略全队列自动覆盖差均为0；抽样患者组成变化时可不为0。以上仅刻画条件于当前全批排序/选择的患者混合不确定性，不包含历史选型、重新拟合或跨医院泛化，也不是CP保证。区间跨0不证明等效，也不单独否定风险排序路线；不比较不同自动子集的MCC。', '',
        f'[计算与逐患者计数]({filename})']
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=O/'full1817_equal_workload.json')
    parser.add_argument('--out',type=Path,default=O/'full1817_equal_workload_bootstrap.json')
    parser.add_argument('--report',type=Path,default=O/'full1817_equal_workload.md')
    args=parser.parse_args();source_before=args.source.read_bytes();report_before=args.report.read_bytes()
    if args.out.exists() or MARKER.encode('utf-8') in report_before:
        raise FileExistsError('Preserve the existing bootstrap output/appendix')
    result=compute(args.source)
    args.out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    newline='\r\n' if report_before.count(b'\r\n')==report_before.count(b'\n') else '\n'
    suffix=appendix(result,args.out.name).replace('\n',newline).encode('utf-8')
    args.report.write_bytes(report_before+newline.encode('utf-8')+suffix)
    assert args.source.read_bytes()==source_before and args.report.read_bytes().startswith(report_before)
    print(c.canonical({name:v['residual_FS_rate_difference'] for name,v in result['variants'].items()}))


if __name__=='__main__':main()

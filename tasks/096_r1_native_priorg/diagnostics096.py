"""Frozen-output diagnosis, no parameter search or new inference."""
import sys,collections,math
import common096 as c
import marlin096 as m
from calibration096 import decode
sys.path.insert(0,str(c.ROOT/'src'));sys.path.insert(0,str(c.ROOT/'tasks/095_anchored_minimal_contrast'))
from metrics095 import score,paired,transition
O=m.O
def shape(rows,key):
    valid=[r for r in rows if r.get(key) is not None];h=collections.Counter(tuple(r[key][k] for k in c.LABELS) for r in valid)
    return dict(N=len(valid),one_hot=sum(max(r[key].values())==100 for r in valid),max_at_least95=sum(max(r[key].values())>=95 for r in valid),any_zero=sum(0 in r[key].values() for r in valid),GT_score_zero=sum(r[key][r['GT']]==0 for r in valid),unique_vectors=len(h),vectors=[dict(S=v[0],NS=v[1],NA=v[2],N=n) for v,n in h.most_common()],by_GT={g:dict(N=sum(r['GT']==g for r in valid),GT_score_zero=sum(r['GT']==g and r[key][g]==0 for r in valid),one_hot=sum(r['GT']==g and max(r[key].values())==100 for r in valid)) for g in c.LABELS})
def main():
    model=c.read(O/'R1_calibration_model.json');rows=c.lines(O/'unified_predictions.jsonl');native=c.lines(O/'R1_parsed_predictions.jsonl');truth={r['id']:r for r in c.lines(c.PRIVATE/'calibration_supervision.jsonl')};cal=[dict(id=r['id'],GT=truth[r['id']]['GT'],R1_scores=r['label_scores'],V4_scores=truth[r['id']]['scores']) for r in native if r['stage']=='calibration' and r['core_valid']]
    shapes={};identities={};components={};matched={};reps=[];pairlist=[('Original','R1_raw'),('V4_raw','R1_raw'),('R1_raw','R1_adapted_PriorG'),('R1_V4_PriorG','R1_adapted_PriorG')]
    for panel,rr in [('calibration',cal),('natural',[r for r in rows if r['panel']=='natural']),('diagnostic',[r for r in rows if r['panel']=='diagnostic'])]:
        shapes[panel]={k:shape(rr,k) for k in ['R1_scores','V4_scores']}
        if panel=='calibration':continue
        identities[panel]={a+'__'+b:sum(r['predictions'][a]!=r['predictions'][b] for r in rr) for a,b in [('R1_raw','R1_U0'),('R1_prior_only','R1_V4_PriorG'),('R1_raw','R1_adapted_PriorG'),('R1_G_only','R1_adapted_PriorG')]}
        components[panel]=dict(metrics=score(rr,['R1_raw','R1_U0','R1_G_only','R1_prior_only','R1_V4_PriorG','R1_adapted_PriorG']),pairs={b+'_vs_'+a:paired(rr,a,b) for a,b in [('R1_raw','R1_V4_PriorG'),('R1_G_only','R1_adapted_PriorG')]})
        vv=[]
        for r in rr:
            if not r['B_core_valid']:continue
            x=dict(r,predictions=dict(r['predictions']));x['predictions']['V4_matched_PriorG']=decode(r['V4_scores'],model['V4_matched_model']['theta'][0],model['reference_counts'],model['counts']);vv.append(x)
        matched[panel]=dict(metrics=score(vv,['V4_PriorG','V4_matched_PriorG']),changed=sum(r['predictions']['V4_PriorG']!=r['predictions']['V4_matched_PriorG'] for r in vv),paired=paired(vv,'V4_PriorG','V4_matched_PriorG'))
        for a,b in pairlist:
            for gt in c.LABELS:
                for kind in ['rescue','harm','wrong_to_wrong']:
                    bag=[r for r in rr if r['GT']==gt and r['predictions'][a]!=r['predictions'][b] and ('rescue' if r['predictions'][b]==gt else 'harm' if r['predictions'][a]==gt else 'wrong_to_wrong')==kind]
                    if bag:
                        r=min(bag,key=lambda r:c.key('096/representative/v1/',r['id']));reps.append(dict(panel=panel,comparison=b+'_vs_'+a,kind=kind,id=r['id'],sid=r['sid'],GT=gt,author=r['author'],base=r['predictions'][a],candidate=r['predictions'][b],R1_scores=r['R1_scores'],V4_scores=r['V4_scores'],selection='post-analysis illustrative hash pick within GT/transition; not new confirmation evidence'))
    c.put(O/'score_diagnostics.json',shapes);c.put(O/'component_label_identity.json',identities);c.put(O/'PriorG_component_ablation.json',components);c.put(O/'matched_supervision_V4.json',matched);c.putl(O/'representative_cases.jsonl',reps)
    # Public mechanism notes contain IDs/labels/scores, never clinical quotations.
    lines=['# 可核查的代表性转移','', '按面板、GT、转移类型固定hash选择。仅说明观测预测/边界变化，不从reason推断内部机制，不作为新增确认样本。临床原文不写入公开工件。','', '|面板|比较|类型|ID|患者|GT|原→新|R1分数(S/NS/NA)|','|---|---|---|---|---|---|---|---|']
    for r in reps:
        s='/'.join(str(r['R1_scores'][k]) for k in c.LABELS);lines.append(f"|{r['panel']}|{r['comparison']}|{r['kind']}|{r['id']}|{r['sid']}|{r['GT']}|{r['base']}→{r['candidate']}|{s}|")
    c.write(O/'representative_cases.md','\n'.join(lines));print('DIAGNOSTICS_COMPLETE',identities)
    for panel,v in shapes.items():print(panel,{k:{a:d[a] for a in ['N','one_hot','GT_score_zero','unique_vectors']} for k,d in v.items()})
    print('MATCHED_V4_CHANGED',{k:v['changed'] for k,v in matched.items()})
if __name__=='__main__':
    import socket
    from unittest.mock import patch
    with patch.object(socket.socket,'connect',side_effect=AssertionError('offline diagnosis')):main()

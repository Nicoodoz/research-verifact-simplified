"""Current navigation, readable ranking and executor handoff. No additional training."""
import subprocess
import common033 as s

def main():
    out=s.OUT/'handoff_001';s.require(not out.exists(),'Handoff exists');out.mkdir();rank=s.read(s.OUT/'historical_001/ranking.json');byid={r['model_id']:dict(r,origin='030_saved_model') for r in rank};direct=s.csvread(s.OUT/'search_001/directed_ranking.csv')
    for r in direct:
        if r['model_id'] not in byid:
            model=s.read(s.OUT/'models'/(r['model_id']+'.json'));z={k:v for k,v in r.items()};z.update(origin='033_directed',k=int(r['k']),eligible_retention80=r['eligible_retention80']=='True',robust_gain_per100R=float(r['robust_gain_per100R']),MCC=float(r['MCC']),correct=int(r['correct']),risk=int(r['risk']),train_patients=model['final_fit']['training_patients']);byid[r['model_id']]=z
    result=[]
    for method in ('A','B','D'):
        for i,r in enumerate(sorted([r for r in byid.values() if r['method']==method],key=s.sort_key),1):result.append(dict(rank_within_method=i,**r))
    s.csvwrite(s.OUT/'training_subset_ranking.csv',result)
    paragraph='**033当前（2026-09-20）：** Gate训练subset研究完成执行及自检，待独立审计。复用030全部4356模型/1452集合，23个定向集合仅新增36个最终拟合；含必要OOF基线共178个新最终模型。A3核查较全训练多4正确但多1 false-S，同风险−1.20R；D5同风险仅+0.40R且rescue保留76.1%。未找到稳定更优subset，建议A保留全development40人训练覆盖，A3仅作小幅工作点收益备选。0 API、未用reserved40、不commit/push或自动后续。旧033 reserved准备已撤回改名归档，本033不沿用其任务。'
    nav=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md']
    for rel in nav:
        p=s.ROOT/rel;data=p.read_bytes();s.require(b'**033' not in data,'033 current block already exists');backup=out/'navigation_before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(data);nl=b'\r\n' if b'\r\n' in data else b'\n';prefix='../' if rel.startswith('docs/') else '';links=f' [主报告]({prefix}outputs/033_gate_training_subset/report.md) · [推荐名单]({prefix}outputs/033_gate_training_subset/recommendation_001/training_patients.csv) · [交审]({prefix}outputs/033_gate_training_subset/audit_handoff.md)。';pos=data.index(b'\n')+1;p.write_bytes(data[:pos]+nl+(paragraph+links).encode('utf-8')+nl+data[pos:])
    s.status('completed',state='completed',API_cost_cny=0,independent_audit='pending',new_final_models=178)
    for record in ('preparation_001/manifest.json','search_001/selection_freeze.json'):
        value=s.read(s.OUT/record)
        for p,h in value.get('sources',{}).items():s.require(s.sha(s.ROOT/p)==h,'Source changed '+p)
    for p,h in s.read(s.OUT/'search_001/selection_freeze.json')['code'].items():s.require(s.sha(s.TASK/p)==h,'Scientific code changed '+p)
    changed=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=s.ROOT,text=True).splitlines();s.require(set(changed)<=set(nav),'Historical tracked file modified')
    files=sorted(p for root in (s.TASK,s.OUT) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts);s.put(out/'manifest.json',dict(created_utc=s.now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),files={p.relative_to(s.ROOT).as_posix():s.sha(p) for p in files},navigation={p:s.sha(s.ROOT/p) for p in nav},tracked_changes=changed,independent_audit=False,API_calls=0,reserved_used=False,obsolete_preparation_archive=['tasks/withdrawn_reserved_preparation_20260920','outputs/withdrawn_reserved_preparation_20260920'],archive_not_used_as_input=True,delete_rejected_by_automatic_policy=True,archive_rename_succeeded=True,no_commit_or_push=True));print('Handoff sealed',len(files),'files',flush=True)

if __name__=='__main__':main()

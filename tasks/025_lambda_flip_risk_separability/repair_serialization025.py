"""Create a distinct replay entry with JSON bool casts only; retain first partial run."""
import common025 as c
def run():
    original=c.TASK/'analyze025.py';target=c.TASK/'analyze025_fixed.py';s=original.read_text(encoding='utf-8')
    needle='        decisions[method]=dict(checks=checks,worth_further_development=all(checks.values()))'
    c.require(s.count(needle)==1,'Repair target differs')
    s=s.replace(needle,'        checks={k:bool(v) for k,v in checks.items()}\n'+needle)
    s=s.replace("worth_further_development=v['R_gain_vs_mixture']>=3 and v['mixture_gain_ci95'][0]>0","worth_further_development=bool(v['R_gain_vs_mixture']>=3 and v['mixture_gain_ci95'][0]>0)")
    s=s.replace("c.OUT/'analysis_001'","c.OUT/'analysis_002'")
    with target.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
    c.write(c.OUT/'serialization_repair_001.json',dict(reason='numpy.bool_ not JSON serializable in final decision only',old_code_sha256=c.sha(original),new_code_sha256=c.sha(target),original_partial_run='analysis_001',formal_run='analysis_002',model_feature_threshold_frontier_changes=False,first_partial_outputs={p.name:c.sha(p) for p in (c.OUT/'analysis_001').iterdir() if p.is_file()}))
if __name__=='__main__':run()

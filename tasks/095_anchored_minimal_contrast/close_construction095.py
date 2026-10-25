"""Freeze operation failure without post-hoc per-case human deployment choices."""
from collections import Counter
import common095 as c
import state095 as s
import method095 as old
import sourcefix095 as fixed

def main():
    checked=c.lines(c.PRIVATE/'checked.jsonl');sample=c.lines(c.OUT/'screen_sample.jsonl');meta={r['id']:r for r in sample};inputs={r['id']:r for r in c.lines(c.PRIVATE/'screen_inputs.jsonl')};success=s.success_index();changes=[]
    for r in checked:
        tr=s.receipt(success[r['constructor_request_id']]);a=old.parse_builder(tr,inputs[r['id']]);b=fixed.parse_builder(tr,inputs[r['id']])
        if a['valid']:assert a==b
        if a!=b:changes.append(dict(id=r['id'],before=a.get('error'),after_valid=b['valid'],only_whitespace=True))
    eligible=[r for r in checked if r['operated']];counts=Counter(meta[r['id']]['panel'] for r in eligible);numeric=len(eligible)>=60 and len({meta[r['id']]['sid'] for r in eligible})>=10 and counts['natural']>=20 and counts['mechanism']>=20
    c.put(c.OUT/'sourcefix_effect.json',dict(N=len(checked),offline_recovered=len(changes),changes=changes,old_successful_constructions_reused=True,no_prompt_change=True))
    c.put(c.OUT/'operation_gate.json',dict(pass_gate=False,numeric_coverage_gate=numeric,N=len(checked),program_valid=sum(r['valid'] for r in checked),automated_eligible=len(eligible),automated_eligible_patients=len({meta[r['id']]['sid'] for r in eligible}),automated_eligible_panels=dict(counts),operated=0,patients=0,panels={'natural':0,'mechanism':0},clinical_Judge_calls=0,reason='GT-blind pilot source review: two definite time/scope violations and one same-event unknown among three automatic passes; whitespace repair does not fix semantic deployability',no_manual_per_case_filter=True,automatic_flag_meaning='construction_audit.operated means would-trigger under automatic checker, NOT actual final-Judge deployment after global semantic gate closed'))
    audit_rows=c.lines(c.OUT/'construction_audit.jsonl')
    c.putl(c.OUT/'construction_deployment_status.jsonl',[dict(id=r['id'],program_valid=r['program_valid'],automated_eligible=r['operated'],final_Judge_deployed=False,stop_scope='global_semantic_implementation_failure',source_audit_sha256=c.h(c.canonical(r))) for r in audit_rows])
    audit_sample=[];pilot=set(c.read(c.OUT/'experiment_freeze.json')['pilot_ids'])
    for panel in ['natural','mechanism']:
        rr=sorted([r for r in eligible if r['id'] not in pilot and meta[r['id']]['panel']==panel],key=lambda r:c.h('095/quality/'+r['id']))[:12]
        for i,r in enumerate(rr):audit_sample.append(dict(id=r['id'],panel=panel,reviewer='root' if i%2==0 else 'independent_source_reviewer'))
    c.putl(c.OUT/'construction_quality_sample.jsonl',audit_sample)
    c.put(c.OUT/'construction_stop.json',dict(utc=c.now(),decision='STOP_C_FINAL_JUDGE_CONTINUE_A_F',N_constructed=len(checked),no_final_classification_claim=True,reason='The predefined operation has not been implemented with reliable temporal/conjunctive context preservation; do not turn invalid contrasts into a test of semantic benefit.',remaining_actions=['Finish baseline under same150 budget','Source-quality and cache/decision analysis','Independent final review','Chinese report and manuscript','Commit/push']))
    print('Construction',len(checked),'program-valid',sum(r['valid'] for r in checked),'automatic checker eligible',len(eligible),'numeric gate',numeric,'ACTUAL DEPLOYMENT0: semantic gate failed','quality sample',len(audit_sample))
if __name__=='__main__':main()

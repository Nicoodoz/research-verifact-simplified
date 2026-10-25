"""Mechanism tests on existing probes, never a generalization score."""
import argparse
import study013 as s
import mechanisms013 as m
from prepare013 import source_data,ANCHORS,CONTRACT_CASES,AUX_CASES
from io013 import stage,normalize,rerank_scores

def run():
    items,pp,notes,prompts=source_data();bycase={x['case_id']:x for x in items}
    values,attempts=stage('unit_aux');judges,ja=stage('unit_judge')
    assignments=s.pilot.read_csv(s.OUT/'unit_judge_preparation_001/assignments.csv')[1]
    outputs=[]
    for a in assignments:
        value=judges[a['request_id']];r=normalize(value['job'],value['receipt'],a['proposition_id'])
        outputs.append(dict(a,result=r))
    retrieval=[]
    for cid in AUX_CASES:
        x=bycase[cid];rid=x['proposition_id'];r=values['rerank:'+rid]
        try:
            scores=rerank_scores(r);pool=m.wide_pool(x)
            wide=s.core.select_evidence(pool,scores,pp,x['admission'])
            refresh=s.core.select_evidence(x['retrieval']['C48']['candidate_ids'],scores,pp,x['admission'])
            score_diag=dict(status='valid',pool=pool,scores=scores,wide=wide,refresh48=refresh,
                old_new_max_abs_diff=max(abs(scores[k]-x['scores'][k]) for k in x['retrieval']['C48']['candidate_ids']),
                refresh_reference_changed=refresh['reference']!=x['retrieval']['C48']['reference'])
        except (AssertionError,KeyError,TypeError,ValueError) as e:score_diag=dict(status='failed',error=str(e))
        sel=values['selector:'+rid]
        selected=m.selected_evidence(x,pp,sel['job'],sel['native'])
        retrieval.append(dict(case_id=cid,proposition_id=rid,baseline=x['retrieval']['C48'],rerank=score_diag,selector=selected,
            selector_raw=sel['native'],selector_input=sel['job']['body']))
    rr={r['case_id']:r for r in retrieval};contract=[o for o in outputs if o['arm']=='contract']
    target_copies=[]
    for o in contract:
        result=o['result'];checks=result.get('checks',[])
        if not checks and result.get('output_text'):
            try:checks=s.pilot.strict_json(result['output_text']).get('checks',[])
            except (ValueError,TypeError):pass
        summary=next((c.get('assessment','') for c in checks if c.get('aspect')=='claim_summary'),'')
        target_copies.append(dict(case_id=o['case_id'],copied=bycase[o['case_id']]['text'] in summary,status=result['status']))
    n264=next(o for o in contract if o['case_id']=='N264')['result']
    contract_machine=all(o['result']['status']=='success' for o in contract) and sum(x['copied'] for x in target_copies)>=6 and n264.get('verdict')!='Supported'
    restored={cid:bool(set(ANCHORS[cid])&set(rr[cid]['selector']['selected_ids'])) and not bool(set(ANCHORS[cid])&set(rr[cid]['baseline']['selected_ids'])) for cid in ('N071','N395','N561')}
    selector_ok=all(r['selector']['selector_status']=='valid' for r in retrieval) and sum(restored.values())>=2
    wide_ok=all(r['rerank']['status']=='valid' for r in retrieval) and set(ANCHORS['N526'])<=set(rr['N526']['rerank'].get('scores',{}))
    offline=s.read_json(s.OUT/'preparation_001/offline_checks.json')
    out=s.OUT/'unit_analysis_001';out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/'judge_outputs.jsonl',outputs);s.pilot.write_jsonl(out/'retrieval_tests.jsonl',retrieval)
    s.pilot.write_json(out/'mechanical_gate.json',dict(contract_machine=contract_machine,contract_copies=target_copies,
        selector=selector_ok,selector_anchor_restoration=restored,wide_candidates=wide_ok,text_guard=offline['text_guard_probe'],
        semantic_contract_review_required=True,new_optimization_rules_permitted=False))
    s.pilot.write_csv(out/'attempts.csv',attempts+ja)
    # Seal once the required semantic probe review and final gate are appended.
    print(s.pilot.canonical(s.read_json(out/'mechanical_gate.json')))

if __name__=='__main__':run()

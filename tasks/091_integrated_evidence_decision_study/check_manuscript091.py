"""Independent aggregate checks for the final-system model-swap table."""
from common091 import *
from verify091 import independent
def main():
    p=ROOT/'outputs/085_r1_70b_valdemardi/final_system_comparison.json';d=read(p);rows=[]
    expect={'Original-VeriFact':(156,8,.5670),'V4-B-PriorG':(155,6,.5881),'V4-F4-PriorG':(161,8,.6433),'R1-B-PriorG':(146,10,.4024),'R1-F4-PriorG':(156,11,.5423)}
    for k,(correct,fs,mcc) in expect.items():
        v=d['summary'][k];ys=[];ps=[]
        for i,r in enumerate(v['confusion_matrix']):
            for j,n in enumerate(r):ys.extend([LABELS[i]]*n);ps.extend([LABELS[j]]*n)
        m=independent(ys,ps);assert m['correct']==correct and m['false_S']==fs and round(m['MCC'],4)==mcc
        for f in ('PA','MCC','AC1'):assert abs(m[f]-v[f])<1e-12
        rows.append(dict(config=k,**m))
    text_file=OUT/'manuscript_zh.md';body=text_file.read_text(encoding='utf-8')
    assert all(f'## {i} ' in body for i in range(1,9));assert '【' not in body and 'TODO' not in body
    rels=['outputs/036_final_validation/report.md','outputs/078_component_ablation/report.md','outputs/079_f4_priorg_adaptation/report.md','outputs/080_final_decision_adaptation/report.md','outputs/081_gt_blind_evidence_selection/report.md','outputs/082_anchor_configuration_adaptation/report.md','outputs/083_native_rationale_information/report.md','outputs/084_f4_coverage_validation/report.md','outputs/085_r1_70b_valdemardi/report_formal.md','outputs/087_f4_evidence_intervention/report.md','outputs/090_demo_constructor_repair_validation/report.md','docs/VeriFact_论文草稿_v1_036已回填.md','outputs/090_demo_constructor_repair_validation/paper_draft.md','tasks/019_support_boundary_screen/common019.py','tasks/078_component_ablation/analyze078.py','tasks/085_r1_70b_valdemardi/analyze_final_system.py']
    value=dict(status='PASS',independent_audit=False,additional_aggregate_rows=rows,manuscript_sha256=sha(text_file),source_sha256=bind([p]+[ROOT/r for r in rels]),no_reserved_individual_data=True)
    put(OUT/'manuscript_anchor_checks.json',value);print(canonical(dict(status='PASS',model_swap_rows=len(rows),manuscript_chars=len(body))))
if __name__=='__main__':main()

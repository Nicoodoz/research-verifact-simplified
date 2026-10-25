"""Finalize the conditional B decision without constructing a posthoc method."""
import common097 as c

def main():
    a=c.read(c.OUT/'a_analysis.json');src=c.read(c.OUT/'b_source_parent_summary.json');probe=c.read(c.OUT/'b_line_probe_summary.json');panel=c.read(c.OUT/'b_prospective_freeze.json')
    charged=a['new_busy_price_or_reserved_cny'];remaining=20-charged;operating_remaining=18-charged
    # Favor B in this forecast: S0 assumed free from existing 095 B cache, and
    # W/F/H each cost only the CHEAPEST actually observed A arm on average.
    per={arm:a['cost_by_arm'][arm]/a['usage_by_arm'][arm]['N'] for arm in ('C48_native','published_native','published_B')}
    optimistic=panel['N']*3*min(per.values())
    out=dict(status='B_NOT_EXECUTED_GATE_FAIL',prospective_N=panel['N'],A_disjoint=True,B_S0_W_F_H_HTTP200=0,B_new_paid_calls=0,matched_ablation_available=False,not_a_negative_method_score=True,
        historical_difference='013 cut-prefix, 046 same-note adjacent paragraph and 049 quote-index already tested; a new operation would require actual source dependency binding with F/H same text, not only a larger source window.',
        source_audit=dict(cases=src['N_cases'],entries=src['entries'],mapped_raw_slices=src['entries'],cut_parent=src['cut_parent'],cross_item_risk=src['cross_item_risk'],line_probe_trigger_cases=probe['trigger_cases'],line_probe_over_cap_cases=probe['cases_exceeding_8000_if_all_applied']),
        construction_gate='FAIL: the only coded line probe proves exact raw spans but does not establish clinical event/list-item dependency; applying all triggers exceeds original reference size on 37/40 cases. No defensible automatic H/F representation frozen.',
        budget_gate=dict(hard_cap=20,operating_cap=18,A_busy_price_or_reserved=charged,hard_remaining=remaining,operating_remaining=operating_remaining,observed_A_mean_busy_per_new_arm=per,optimistic_900_call_estimate_cny=optimistic,full_four_arm_new_calls_at_least=900,pass_estimate=optimistic<=operating_remaining),
        decision='Do not issue B classification requests; no matched W/F/H score exists. Later resumption needs new explicit task/budget and a frozen source-dependency construction that passes blinded quality checks.')
    c.write_json(c.OUT/'b_gate.json',out)
    print('B gate',out['construction_gate'],'optimistic_cost',optimistic,'available',operating_remaining)
if __name__=='__main__':main()

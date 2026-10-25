"""Copy proven transport/metrics into 074, preserving historic 073 sources."""
from common074 import *
def main():
 s=(ROOT/'tasks/073_clinical_example_matching/run073.py').read_text(encoding='utf-8-sig')
 s=s.replace('bounded 073 executor','bounded 074 executor').replace('outputs/073_clinical_example_matching','outputs/074_anchor_dynamic_examples').replace('FROZEN_BEFORE_073_API','FROZEN_BEFORE_074_API')
 s=s.replace('workers=3','workers=6').replace('workers <= 3','workers <= 6').replace('default=3','default=6')
 s=s.replace('completed_new, failure_streak = 0, 0','completed_new, failure_streak, success_streak = 0, 0, 0')
 s=s.replace('                        failure_streak = 0','                        failure_streak = 0\n                        success_streak += 1\n                        if success_streak >= 6:\n                            current_workers = min(workers, current_workers + 1)\n                            success_streak = 0')
 s=s.replace('                        failure_streak += 1','                        failure_streak += 1\n                        success_streak = 0')
 assert 'deepseek-v4-flash-0731' in s
 with (TASK/'run074.py').open('x',encoding='utf-8',newline='\n') as f:f.write(s)
 s=(ROOT/'tasks/073_clinical_example_matching/analyze073.py').read_text(encoding='utf-8-sig')
 s=s.replace('frozen 073 stages','frozen 074 stages').replace('run073','run074').replace('outputs/073_clinical_example_matching','outputs/074_anchor_dynamic_examples')
 marker='    cost_by_arm = defaultdict(float)'
 extra='''    final_pairs["H6_minus_F6"] = compare(rows, maps["F6"], maps["H6"])
    if common_raw:
        raw_pairs["H6_minus_F6"] = compare(common_raw, raw["F6"], raw["H6"])
    core_valid = [x for x in rows if all(x["id"] not in invalid[arm] for arm in arms)]
    core_metrics = {arm: metric(core_valid, maps[arm]) for arm in arms}
    core_pairs = {arm+"_minus_"+base: compare(core_valid, maps[base], maps[arm]) for arm,base in [("F4","B"),("F6","F4"),("H6","B"),("H6","F4"),("H6","F6")]}
'''
 s=s.replace(marker,extra+marker).replace('"final_metrics": metrics, "raw_metrics": raw_metrics,','"final_metrics": metrics, "raw_metrics": raw_metrics,\n              "core_valid_n": len(core_valid), "core_valid_final_metrics": core_metrics, "core_valid_final_pairs": core_pairs,')
 with (TASK/'analyze074.py').open('x',encoding='utf-8',newline='\n') as f:f.write(s)
 t=(ROOT/'tasks/073_clinical_example_matching/test_transport073.py').read_text(encoding='utf-8-sig').replace('run073','run074').replace('outputs/073_clinical_example_matching','outputs/074_anchor_dynamic_examples').replace("prefix='073_transport_'","prefix='074_transport_'")
 with (TASK/'test_transport074.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
 print('074 executor and unified evaluator prepared; no API calls')
if __name__=='__main__':main()

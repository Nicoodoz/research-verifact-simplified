"""Engineering pairing only: no GT, classification metric or best-case selection."""
from pathlib import Path
import argparse
import json
import statistics


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--results',type=Path,required=True);parser.add_argument('--out',type=Path)
    args=parser.parse_args();job=json.loads((args.bundle/'data/job.json').read_text());pairs=[];missing=[]
    keys=sorted({(r['variant'],r['id']) for r in job['calls']})
    for variant,i in keys:
        values={}
        for mode in ('control','capture'):
            path=args.results/variant/mode/(i+'.json')
            if path.exists():values[mode]=json.loads(path.read_text())
            else:missing.append(dict(id=i,variant=variant,mode=mode))
        if len(values)!=2:continue
        a,b=values['control'],values['capture']
        pairs.append(dict(id=i,variant=variant,control_seconds=a['generation_seconds'],capture_seconds=b['generation_seconds'],
            delta_seconds=b['generation_seconds']-a['generation_seconds'],
            identical_content=a['content_sha256']==b['content_sha256'],identical_tokens=a['generated_token_sha256']==b['generated_token_sha256'],
            identical_verdict=a['parsed'].get('verdict')==b['parsed'].get('verdict'),
            both_valid=a['parsed']['valid'] and b['parsed']['valid'],capture_status=b['capture']['status'],
            processor_vs_raw_max_abs_difference=b['processor_vs_raw_max_abs_difference'],
            both_match_cached_label=a['matches_original_cached_label'] and b['matches_original_cached_label'],
            both_match_cached_content=a['matches_original_cached_content'] and b['matches_original_cached_content']))
    report=dict(purpose='paired engineering only; no classification-effect claim',expected_pairs=12,complete_pairs=len(pairs),
        missing=missing,pairs=pairs,raw_logits_audit_enabled_in_both_arms=True,
        mean_delta_seconds=statistics.mean(p['delta_seconds'] for p in pairs) if len(pairs)==12 else None,
        median_delta_seconds=statistics.median(p['delta_seconds'] for p in pairs) if len(pairs)==12 else None,
        no_repeat_after_bad_results=True,no_GT_used=True)
    if args.out:args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report))


if __name__=='__main__':main()

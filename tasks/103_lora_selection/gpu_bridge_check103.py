"""Compare prospective bridge IDs without treating API as local training baseline."""
import argparse,json
from pathlib import Path
from gpu_worker103 import rows,read,write
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);a=p.parse_args();plan=read(a.bundle/'gpu_plan.json');api={(r['id'],r['model'],r['mode']):r for r in rows(a.bundle/'api_bridge.jsonl')};report=[]
 for m in plan['candidates']:
  for arm,mode in [('native_base','native'),('label_base','label')]:
   local=rows(a.out/m/'eval'/(arm+'_speed.jsonl'))
   for r in local:
    cloud=api.get((r['id'],m,mode));report.append(dict(id=r['id'],model=m,arm=arm,local_verdict=r['parsed']['verdict'],api_verdict=cloud['verdict'] if cloud else None,local_input_tokens=r['input_tokens'],api_input_tokens=cloud['prompt_tokens'] if cloud else None,local_finish=r['parsed'].get('finish_reason'),local_forced_think_boundary=r['forced_thinking_boundary'],same_label=None if cloud is None else r['parsed']['verdict']==cloud['verdict']))
 write(a.out/'bridge_check.json',dict(rows=report,api_revision_precision_unknown=True,not_training_increment=True))
 assert all(r['local_finish']=='stop' and r['local_verdict'] is not None for r in report),'Inspect format/truncation before full evaluation'
 print('Bridge inputs and format checked; inspect label/template differences in bridge_check.json')
if __name__=='__main__':main()

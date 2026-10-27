"""Freeze stage-one handoff; no API or GPU side effects."""
import ast,json
from decimal import Decimal
import common103 as c
from parse_label103 import parse_label
def main():
 assert parse_label('Not Addressed','stop')['verdict']=='Not Addressed'
 assert not parse_label('Not Addressed because no mention','stop')['valid']
 checks=2
 for name in ['data_freeze.json','api_execution_freeze.json','gpu_preparation_freeze.json']:
  for rel,h in c.read(c.OUT/name)['files'].items():assert c.sha(c.ROOT/rel)==h,rel;checks+=1
 for p in c.TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'));checks+=1
 for name,manifest in [('gpu_bundle.tar.gz','gpu_bundle_manifest.json'),('gpu_bundle_a800.tar.gz','a800_fallback_manifest.json')]:assert c.sha(c.PRIVATE/name)==c.read(c.OUT/manifest)['sha256'];checks+=1
 cost=sum((Decimal(str(r['uncached_cny'])) for r in c.lines(c.OUT/'usage.jsonl')),Decimal(0));assert abs(cost-Decimal(str(c.read(c.OUT/'api_cost_ledger.json')['uncached_budget_used_cny'])))<Decimal('.0000001') and cost<=30;checks+=1
 c.put(c.OUT/'gpu_cost_ledger.json',dict(status='NOT_STARTED_WAITING_FOR_USER_INSTANCE',actual_gpu_cny=0,actual_storage_cny=0,elapsed_GPU_seconds=0,cap_GPU_storage_cny=60,max_GPU_seconds=28800,reference_hourly_cny=6.98,actual_instance_price=None,instances_purchased=0))
 c.put(c.OUT/'stage1_check.json',dict(utc=c.utc(),status='PASS',checks=checks,independent_audit=False,real_GPU_validation_pending=True,primary_API_results_preserved=True,exact_literal_parser_tested=True,both_private_bundles_verified=True))
 files=['report.md','recommendation.json','analysis.json','label_format_sensitivity.json','api_cost_ledger.json','gpu_cost_ledger.json','stage1_check.json','gpu_plan.json','a800_fallback_manifest.json']
 c.put(c.OUT/'stage1_complete.json',dict(utc=c.utc(),status='READY_FOR_GPU',API_done=True,GPU_done=False,GPU_instance_connection_required=True,second_stage_not_started=True,full_training_authorized=False,next_task_started=False,API_cost_uncached_cny=float(cost),GPU_cost_cny=0,files={p:c.sha(c.OUT/p) for p in files}))
 print('READY_FOR_GPU; stage1 checks',checks,'API',cost)
if __name__=='__main__':main()

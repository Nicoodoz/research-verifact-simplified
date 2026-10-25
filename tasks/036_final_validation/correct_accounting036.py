"""Correct BGE token export from provider meta; all original fees and receipts stay frozen."""
import argparse,copy,json,shutil
from collections import Counter
import common036 as c
def main(verify=False):
    old=c.OUT/'accounting_001';out=c.OUT/'accounting_002';summary=c.read(old/'summary.json');correct=copy.deepcopy(summary);totals={k:0 for k in ('embedding','rerank')};sources={k:Counter() for k in totals};checked=0
    for r in c.csvread(old/'ledger.csv'):
        if r['role'] not in totals:continue
        rp=c.ROOT/r['path'];receipt=c.read(rp.parent/'receipt.json');assert receipt['request_sha256']==c.sha(rp);value=json.loads(receipt['transport']['body_text']);usage=value.get('usage',{})
        counted=usage.get('prompt_tokens',usage.get('total_tokens'));source='usage.prompt_tokens_or_total_tokens'
        if counted is None:counted=value.get('meta',{}).get('billed_units',{}).get('input_tokens');source='meta.billed_units.input_tokens'
        if counted is None:counted=value.get('meta',{}).get('tokens',{}).get('input_tokens');source='meta.tokens.input_tokens'
        assert type(counted) is int and counted>0;assert abs(float(r['charge_cny'])-counted*.07/1e6)<1e-10
        totals[r['role']]+=counted;sources[r['role']][source]+=1;checked+=1
    for role,n in totals.items():correct['role_summary']['shared/'+role]['prompt_tokens']=n;correct['role_summary']['shared/'+role]['input_token_sources']=dict(sources[role])
    correct['created_utc']=c.now();correct['correction']=dict(reason='accounting001 exported BGE tokens from usage only. Rerank replies report billed input tokens in provider meta, so the exported rerank token total was incorrectly zero. Runtime/native cost accounting already used meta and ALL FEES WERE CORRECT.',previous_manifest_sha256=c.sha(old/'manifest.json'),raw_BGE_receipts_checked=checked,scientific_predictions_changed=False,fees_changed=False)
    if verify:
        recorded=c.read(out/'summary.json')
        assert recorded['total_used_or_reserved_cny']==summary['total_used_or_reserved_cny']
        for role,n in totals.items():assert recorded['role_summary']['shared/'+role]['prompt_tokens']==n
        print('Accounting correction replay PASS',checked,totals);return
    assert not out.exists();out.mkdir();shutil.copyfile(old/'ledger.csv',out/'ledger.csv');shutil.copyfile(old/'standalone_costs.csv',out/'standalone_costs.csv')
    c.put(out/'summary.json',correct);c.csvwrite(out/'roles.csv',[dict(role=k,**v) for k,v in correct['role_summary'].items()]);c.put(out/'verification.json',dict(status='PASS',BGE_receipts_checked=checked,tokens=totals,total_cny_unchanged=correct['total_used_or_reserved_cny'],old_export_preserved=True,API_calls=0))
    c.put(out/'manifest.json',{p.name:c.sha(p) for p in out.iterdir() if p.is_file()})
    c.write_text(c.OUT/'accounting_CURRENT.md','# 036 当前费用入口\n\n正式入口为[accounting_002](accounting_002/summary.json)。accounting_001费用和原始账本始终正确，但rerank token统计列未读取供应商meta而错误显示0；002逐条从4228份BGE回执重建输入token并核对费用。原001/回执不改，总费用和预测/评价完全不变。\n\n零API复查：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/036_final_validation/correct_accounting036.py --verify`。\n')
    print('Corrected token export; same total CNY',correct['total_used_or_reserved_cny'],totals)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');main(p.parse_args().verify)

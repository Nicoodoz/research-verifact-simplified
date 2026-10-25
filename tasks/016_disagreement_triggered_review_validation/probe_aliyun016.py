"""One explicitly authorized authentic request, separate provider provenance, no GT evaluation."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime
import math
import common016 as c
from finish_io016 import ORIGINAL, collect, base_labels
from verifact_research.inference.aliyun import load_config, call_once

OUT = ORIGINAL/'aliyun_real_request_check_001'


def main():
    c.require(not OUT.exists(), 'Probe already prepared/sent; do not repeat')
    config = load_config(c.ROOT/'.env.aliyun')
    c.require(config.api_key and config.model == 'qwen3.8-27b', 'Missing key or unexpected Alibaba model')
    values, attempts, total = collect()
    labels, _ = base_labels(values)
    c.require(abs(total-c.read(ORIGINAL/'current_checkpoint_004.json')['whole_task_used_or_reserved_cny'])<1e-8, 'Prior cost drift')
    attempted = {a['request_id'] for a in attempts}
    jobs = c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl')
    source = next(j for j in jobs if j['role']=='qwen' and j['request_id'] not in attempted and j['request_id'] not in values)
    body = deepcopy(source['body']);body['model'] = config.model
    c.require({k:v for k,v in body.items() if k!='model'}=={k:v for k,v in source['body'].items() if k!='model'}, 'Frozen settings drift')
    c.require(set(c.pilot.strict_json(body['messages'][1]['content']))=={'proposition','reference'}, 'Hidden metadata in body')
    reserve = ((len(c.canonical(body).encode('utf-8'))+2000)*3+body['max_tokens']*12)/1e6
    cal = c.read(ORIGINAL/'token_calibration_001.json')['models']['qwen']
    inp = math.ceil(sum(len(m['content']) for m in body['messages'])*cal['input_factor']+200)
    estimate = (inp*3+cal['output_allowance']*12)/1e6
    c.require(total+reserve<=40, '016 total cap exceeded')
    job = dict(source, request_id='016:aliyun_probe:'+c.fingerprint(body), body=body)
    OUT.mkdir()
    c.write_json(OUT/'source_job.json',source);c.write_json(OUT/'job.json',job)
    c.write_json(OUT/'authorization.json',dict(created_utc=c.now(),user_scope='One real experimental request to test Alibaba; no bulk continuation',
        source_request_id=source['request_id'],selection='First never-attempted Qwen job in frozen original order, no GT used',
        endpoint=config.endpoint,model=config.model,only_body_change='model identifier; same claim/reference/prompt/generation settings',
        prices_source='https://help.aliyun.com/zh/model-studio/qwen3-8-27b',prices_checked_date='2026-09-16',
        input_output_CNY_per_million=[3,12],cache_discount_not_assumed=True,input_tokens_estimate=inp,
        output_allowance=cal['output_allowance'],estimated_cost_cny=estimate,estimate_uses_prior_supplier_empirical_calibration_not_exact_tokenizer=True,
        max_reservation_cny=reserve,prior_task_cny=total,task_cap_cny=40,projected_task_after_this_test_cny=total+reserve,
        prior_checkpoint_sha256=c.file_hash(ORIGINAL/'current_checkpoint_004.json'),
        retain_answer_never_regenerate=True,formal_provider_switch_not_implemented=True,
        successful_probe_is_separately_retained_for_future_integration_not_silently_mixed=True,
        script_sha256=c.file_hash(Path(__file__)),client_sha256=c.file_hash(c.ROOT/'src/verifact_research/inference/aliyun.py')))
    print(c.canonical(dict(action='single_real_request',estimated_cny=estimate,reservation_cny=reserve,prior_task_cny=total,max_task_after_probe_cny=total+reserve)),flush=True)
    call_once(config,body,OUT/'attempt_001',max_cost_cny=reserve,task_used_cny=total,task_cap_cny=40)
    receipt = c.read(OUT/'attempt_001/receipt.json');tr=receipt['transport']
    normalized = c.old14.normalize(job,receipt,model=config.model)
    c.write_json(OUT/'normalized_response.json',normalized)
    charge = reserve;basis='unknown_usage_reservation'
    try:
        native=c.pilot.strict_json(tr['body_text']);u=native['usage'];p=u['prompt_tokens'];o=u['completion_tokens']
        c.require(all(type(x)is int and x>=0 for x in (p,o)) and u['total_tokens']==p+o,'Usage invalid')
        charge=(p*3+o*12)/1e6;basis='Alibaba_Beijing_public_price_no_cache_discount_not_invoice'
    except (ValueError,KeyError,TypeError):pass
    latency=(datetime.fromisoformat(tr['ended_utc'])-datetime.fromisoformat(tr['started_utc'])).total_seconds()
    summary=dict(created_utc=c.now(),http_status=tr['http_status'],latency_seconds=latency,provider='aliyun_model_studio',
        valid_prediction=normalized['status']=='success',structural_errors=normalized['structural_errors'],
        adherence_errors=normalized['adherence_errors'],usage=normalized.get('usage'),model_returned=normalized.get('model_returned'),
        additional_cost_or_reserved_cny=charge,charge_basis=basis,whole_task_used_or_reserved_cny=total+charge,cap_cny=40,
        SiliconFlow_V4_valid=601,SiliconFlow_Qwen_valid=sum('qwen' in r for r in labels.values()),
        Alibaba_Qwen_separately_retained=int(normalized['status']=='success'),
        original_request_id=source['request_id'],proposition_id=source['proposition_id'],GT_effects_evaluated=False,
        repeat_or_review_started=False,bulk_continuation=False,all_previous_results_unchanged=True)
    c.write_json(OUT/'summary.json',summary)
    c.write_json(ORIGINAL/'current_checkpoint_005.json',dict(summary,previous_checkpoint_sha256=c.file_hash(ORIGINAL/'current_checkpoint_004.json'),
        latest_probe='aliyun_real_request_check_001/summary.json',
        accounting_warning='Legacy collect() stops at finalization001; future execution must additionally carry this Alibaba attempt fee/reservation and retain this successful answer if valid'))
    report=f'''# 阿里云真实实验请求测试

- 范围：016原冻结队列第一条从未发送的Qwen请求，只改阿里云模型标识，原claim、C48、prompt和生成参数不变。
- HTTP状态：{tr['http_status']}；耗时：{latency:.2f}秒；有效结构化预测：{summary['valid_prediction']}。
- 本次usage估算／预留：¥{charge:.8f}；016累计：¥{total+charge:.8f}/¥40（非账单，旧未知预留保持）。
- 请求、回执、usage及完整回答分别保存在source_job.json、job.json、attempt_001/和normalized_response.json；密钥不落盘。
- 没有GT效果评价、批量续跑或分歧复核。成功回答单独保留，未来登记供应商切换时应复用，不得再生成；单次成功不能证明批量稳定或跨供应商结果等价。
- [发送前登记](authorization.json) · [结果汇总](summary.json)。计价依据：[阿里云北京模型价格](https://help.aliyun.com/zh/model-studio/qwen3-8-27b)。
'''
    (OUT/'report.md').write_text(report,encoding='utf-8',newline='\n')
    c.seal(OUT,[ORIGINAL/'current_checkpoint_004.json',ORIGINAL/'stage1/base_preparation_001/manifest.json'],[Path(__file__),c.ROOT/'src/verifact_research/inference/aliyun.py'])
    print(c.canonical(summary))


if __name__=='__main__':main()

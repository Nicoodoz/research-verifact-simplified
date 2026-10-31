"""CPU-only coverage/cost or complete fixed-grid selective analysis of144.

Pilot/partial receipts never produce performance estimates. No score is imputed.
Future effect jobs must freeze native_prediction_sources and all evaluation IDs.
"""
from collections import Counter
from pathlib import Path
import argparse
import math
import statistics
import sys

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'tasks/143_selective_verification'))
from analyze143 import c, LABELS, ratio, score, summarize, metric_table, metric_details, number

PERCENTAGES = (0, 5, 10, 20, 30)
VARIANTS = ('native120', 'claim_repeat136', 'relevance_order142')
KEYS = R / '.local_models/134_author_baselines/keys.jsonl'


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def rows_if(path):
    return c.rows(path) if path.exists() else []


def resolve(base, value):
    path = Path(value)
    return path if path.is_absolute() else base / path


def checked_index(rows, fields):
    result = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key in result:
            raise ValueError('Duplicate frozen record: ' + str(key))
        result[key] = row
    return result


def read_job(bundle):
    data = bundle / 'data' if (bundle / 'data/job.json').exists() else bundle
    job = c.read(data / 'job.json')
    if job.get('scope') not in ('pilot', 'screen160', 'old500', 'full1817'):
        raise ValueError('Unknown144 scope')
    variants = job['variants']
    if not variants or not set(variants) <= set(VARIANTS):
        raise ValueError('Unknown or empty variant list')
    targets = job['score_ids_by_variant']
    if set(targets) != set(variants) or any(len(ids) != len(set(ids)) for ids in targets.values()):
        raise ValueError('Frozen per-variant score IDs differ')
    expected = {(variant, i) for variant in variants for i in targets[variant]}
    if len(expected) != job['expected_N']:
        raise ValueError('Wrong expected score count')
    inputs = checked_index(c.rows(data / 'inputs.jsonl'), ('variant', 'id'))
    if set(inputs) != expected:
        raise ValueError('Frozen inputs do not match prescribed score targets')
    if job.get('fixed_referral_percent') != list(PERCENTAGES):
        raise ValueError('The fixed review grid changed')
    if job['scope']=='pilot' and (set(variants)!=set(VARIANTS) or any(len(ids)!=9 for ids in targets.values())):
        raise ValueError('The formal pilot must be the frozen nine IDs by three variants')
    return job, inputs, data


def collect(results, expected, inputs, job):
    found, locations, manifests, extra = {}, {}, {}, []
    for root in results:
        for item in rows_if(root / 'encoded_manifest.jsonl'):
            key = (item['variant'], item['id'])
            if key in manifests and manifests[key] != item:
                raise ValueError('Conflicting encoded manifest: ' + str(key))
            manifests[key] = item
        for variant in job['variants']:
            for path in (root / variant).glob('*.json'):
                row = c.read(path)
                if 'id' not in row:
                    continue
                key = (row.get('variant'), row['id'])
                if key not in expected:
                    extra.append(dict(path=str(path), variant=key[0], id=key[1]))
                    continue
                if key in found and found[key] != row:
                    raise ValueError('Conflicting successful144 receipt: ' + str(key))
                found[key] = row
                locations.setdefault(key, []).append(str(path))
    valid, invalid = {}, {}
    for key, row in found.items():
        expected_input = inputs[key]
        encoded = manifests.get(key)
        issues = []
        for field in ('logit_S_minus_Not', 'seconds'):
            if not finite(row.get(field)):
                issues.append('missing_or_nonfinite_' + field)
        logits = row.get('branch_logits', {})
        if not all(finite(logits.get(label)) for label in ('S', 'Not')):
            issues.append('missing_or_nonfinite_branch_logits')
        elif finite(row.get('logit_S_minus_Not')) and not math.isclose(
                logits['S']-logits['Not'], row['logit_S_minus_Not'], rel_tol=1e-7, abs_tol=1e-6):
            issues.append('margin_does_not_match_logits')
        if (row.get('adapter_sha256') != job['adapter_sha256']
                or row.get('prompt_token_sha256') != expected_input['expected_prompt_token_sha256']
                or row.get('original_prompt_tokens') != expected_input['expected_prompt_tokens']):
            issues.append('source_or_original_prompt_mismatch')
        if (encoded is None or any(row.get(k) != encoded.get(k) for k in
                ('prompt_token_sha256', 'scoring_input_token_sha256', 'original_prompt_tokens', 'prefix_token_ids'))
                or not row.get('scoring_input_token_sha256') or not row.get('prefix_token_ids')):
            issues.append('scoring_input_manifest_missing_or_mismatch')
        if row.get('prefix_token_ids') != job['prefix_token_ids']:
            issues.append('fixed_scoring_prefix_mismatch')
        if row.get('batch_size') != 1 or row.get('max_seq_length') != 16384 or row.get('dtype')!='bfloat16':
            issues.append('runtime_configuration_mismatch')
        if issues:
            invalid[key] = issues
        else:
            valid[key] = row
    missing = sorted(expected - found.keys())
    return valid, invalid, missing, found, extra, locations


def numeric_summary(values):
    values = [value for value in values if finite(value)]
    return dict(recorded_N=len(values), total=sum(values) if values else None,
                mean=statistics.mean(values) if values else None,
                median=statistics.median(values) if values else None,
                minimum=min(values) if values else None, maximum=max(values) if values else None)


def interval_union(intervals):
    """Merge overlapping/nested wall-clock spans; retain disjoint runs separately."""
    spans=[]
    for row in intervals:
        start,end=row['started_epoch'],row['completed_epoch']
        if not finite(start) or not finite(end) or end<start:
            raise ValueError('Invalid recorded wall-clock interval')
        spans.append((start,end))
    merged=[]
    for start,end in sorted(spans):
        if merged and start<=merged[-1][1]:
            merged[-1][1]=max(merged[-1][1],end)
        else:
            merged.append([start,end])
    return [dict(started_epoch=start,completed_epoch=end,seconds=end-start) for start,end in merged]


def cost_summary(results, found):
    events, seen_events, runtime, workers, controllers = [], set(), [], {}, []
    for root in results:
        for row in rows_if(root / 'attempts.jsonl'):
            marker = c.canonical(row)
            if marker not in seen_events:
                events.append(row)
                seen_events.add(marker)
        for name in ('runtime.json', 'complete.json', 'run_exit.json', 'failure.json', 'inflight.json'):
            path = root / name
            if path.exists():
                record=c.read(path)
                runtime.append(dict(path=str(path), sha256=c.sha(path), record=record))
                if all(finite(record.get(k)) for k in ('worker_started_epoch','worker_completed_epoch','worker_wall_seconds')):
                    interval=(record['worker_started_epoch'],record['worker_completed_epoch'])
                    if not math.isclose(interval[1]-interval[0],record['worker_wall_seconds'],rel_tol=1e-8,abs_tol=1e-5):
                        raise ValueError('Worker wall interval and duration disagree')
                    workers[interval]=dict(started_epoch=interval[0],completed_epoch=interval[1],
                        seconds=record['worker_wall_seconds'],status=record.get('status','complete'))
        controller_path=root.parent/'controller_done.json'
        if controller_path.exists():
            controller=c.read(controller_path)
            controllers.append(dict(path=str(controller_path),sha256=c.sha(controller_path),record=controller))
    pending, paired_attempts, unpaired_completions = {}, [], []
    for event in sorted(events, key=lambda row: row.get('epoch', 0)):
        key=(event.get('variant'),event.get('id'))
        if event.get('event')=='started':
            pending.setdefault(key,[]).append(event)
        elif event.get('event')=='completed':
            if pending.get(key):
                start=pending[key].pop(0)
                paired_attempts.append(dict(variant=key[0],id=key[1],
                    observed_wall_seconds=event['epoch']-start['epoch'],forward_seconds=event.get('seconds')))
            else:
                unpaired_completions.append(event)
    epochs=[row['epoch'] for row in events if finite(row.get('epoch'))]
    safe_keys = ('event', 'status', 'attempt_id', 'variant', 'id', 'epoch', 'started', 'ended',
                 'seconds', 'forward_seconds', 'elapsed_seconds', 'input_tokens',
                 'original_prompt_tokens', 'prompt_tokens', 'scoring_tokens', 'batch_size', 'error_type')
    union=interval_union(workers.values())
    controller_union=interval_union(dict(started_epoch=row['record']['started'],completed_epoch=row['record']['ended'])
        for row in controllers if finite(row['record'].get('started')) and finite(row['record'].get('ended')))
    return dict(successful_unique_records=len(found),
                successful_forward_seconds=numeric_summary([row.get('seconds') for row in found.values()]),
                original_prompt_tokens=numeric_summary([row.get('original_prompt_tokens') for row in found.values()]),
                prefix_tokens=numeric_summary([len(row['prefix_token_ids']) for row in found.values() if isinstance(row.get('prefix_token_ids'), list)]),
                batch_size_counts=dict(Counter(str(row.get('batch_size', 'missing')) for row in found.values())),
                peak_allocated_bytes=numeric_summary([row.get('peak_allocated_bytes') for row in found.values()]),
                attempt_event_counts=dict(Counter(str(row.get('event', row.get('status', 'unknown'))) for row in events)),
                attempt_events=[{k: row[k] for k in safe_keys if k in row} for row in events],
                completed_attempts=paired_attempts,
                pending_attempts=[{k: row[k] for k in safe_keys if k in row} for queue in pending.values() for row in queue],
                unpaired_completed_attempts=len(unpaired_completions),
                recorded_completed_forward_seconds=numeric_summary([row.get('seconds') for row in events if row.get('event')=='completed']),
                recorded_attempt_wall_seconds=numeric_summary([row['observed_wall_seconds'] for row in paired_attempts]),
                attempt_observation_span_seconds=max(epochs)-min(epochs) if epochs else None,
                recorded_worker_intervals=list(workers.values()),
                worker_interval_union=union,
                worker_wall_seconds=numeric_summary([row['seconds'] for row in union]),
                worker_wall_aggregation='Union of all recorded time intervals; nested/overlapping complete/run_exit spans count once, disjoint spans add.',
                controller_records=controllers,
                controller_wall_seconds=numeric_summary([row['seconds'] for row in controller_union]),
                controller_interval_union=controller_union,
                model_load_seconds=numeric_summary([row['record'].get('model_load_seconds') for row in runtime]),
                preparation_seconds=numeric_summary([row['record'].get('preparation_seconds') for row in runtime]),
                runtime_records=runtime,
                attempts_accounting_note='All recorded attempt events retained; successful forward sum excludes failed/unfinished attempts and loading/waiting. Missing cost is unknown, never zero.',
                deployment_note='Simultaneous logit capture during original generation could avoid a second prefill; not implemented or benchmarked here. This144 scoring pass has real loading/prefill/forward cost.')


def ranked_points(rows, native, scores):
    supported = [row['id'] for row in rows if native[row['id']] == 'Supported']
    if any(i not in scores or not finite(scores[i]) for i in supported):
        raise ValueError('Missing/nonfinite score in original native Supported pool')
    ordered = sorted(supported, key=lambda i: (scores[i], i))
    points = []
    for percent in PERCENTAGES:
        count = len(ordered) * percent // 100
        reviewed = set(ordered[:count])
        value = selective_summary(rows, native, reviewed)
        value.update(review_percent_of_original_S=percent,
                     actual_review_fraction_of_original_S=ratio(count, len(ordered)),
                     native_S_pool_N=len(ordered), review_ids=ordered[:count],
                     score_boundary=scores[ordered[count-1]] if count else None,
                     boundary_id=ordered[count-1] if count else None)
        points.append(value)
    return points


def selective_summary(rows, native, reviewed):
    value = summarize(rows, native, reviewed)
    #143's route conditionally invokes107;144 ranks this model's own score.
    value.pop('logical_inference_calls')
    value['additional107_calls'] = 0
    return value


def native_branch_consistency(native, margins):
    """Prediction/score comparison only; never reads GT or filters a score."""
    selected = sorted(i for i in margins if i in native and native[i]=='Supported')
    if any(not finite(margins[i]) for i in selected):
        raise ValueError('Consistency diagnostic requires valid finite margins')
    negative = [dict(id=i, margin=margins[i]) for i in selected if margins[i] < 0]
    zero = [dict(id=i, margin=margins[i]) for i in selected if margins[i] == 0]
    return dict(scored_native_S_N=len(selected),
                negative_N=len(negative), zero_N=len(zero),
                minimum_margin=min((margins[i] for i in selected),default=None),
                negative_records=negative, zero_records=zero,
                action='Diagnostic only: preserve all original predictions and scores; no removal or resend.',
                interpretation='Negative margin ranks Not above S under this fixed canonical prefix. Batch1 score extraction versus original batch2 generation may affect near-zero values; numerous materially negative margins require configuration/prefix/runtime review.')


def load_native(job, data_folder, keys):
    specs = job.get('native_prediction_sources')
    if not isinstance(specs, dict) or set(specs) != set(job['variants']):
        raise ValueError('Effect job must freeze native_prediction_sources for every variant')
    wanted = set(job['evaluation_ids'])
    native, provenance, missing = {}, {}, {}
    for variant, spec in specs.items():
        path = resolve(R, spec['path'])
        if c.sha(path) != spec['sha256']:
            raise ValueError('Native prediction source fingerprint differs: ' + variant)
        raw = checked_index(c.rows(path), ('id',))
        labels, problems = {}, []
        for i in wanted:
            row = raw.get((i,))
            if row is None:
                problems.append(dict(id=i, issue='missing_native_prediction'))
                continue
            if 'claim' in row or 'reference' in row:
                raise ValueError('Native sources must be sanitized')
            for field in ('GT', 'sid', 'claim_sha256', 'reference_sha256'):
                if field in row and str(row[field]) != str(keys[i][field]):
                    raise ValueError('Native source identity mismatch: ' + variant + '/' + i)
            field = spec['field']
            valid_field = spec.get('validity_field')
            if (row.get(field) not in LABELS or (valid_field and row.get(valid_field) is not True)
                    or row.get('valid', True) is not True or row.get('primary_joint_valid', True) is not True
                    or row.get('receipt_status') in ('invalid', 'missing')):
                problems.append(dict(id=i, issue='invalid_native_prediction'))
            else:
                labels[i] = row[field]
        native[variant] = labels
        missing[variant] = problems
        provenance[variant] = dict(path=str(path), sha256=spec['sha256'],
                                  reason_present=sum(isinstance(row.get('reason'), str) and bool(row['reason'].strip()) for row in raw.values()))
    return native, provenance, missing


def analyze(bundle, results):
    job, inputs, data_folder = read_job(bundle)
    expected = set(inputs)
    valid, invalid, missing, found, extra, locations = collect(results, expected, inputs, job)
    coverage = dict(expected_N=len(expected), received_N=len(found), valid_score_N=len(valid),
                    missing=[dict(variant=v, id=i) for v,i in missing],
                    invalid=[dict(variant=v, id=i, issues=issues) for (v,i),issues in sorted(invalid.items())],
                    ignored_outside_target=extra,
                    by_variant={v: dict(expected_N=len(job['score_ids_by_variant'][v]),
                        received_N=sum(key[0]==v for key in found), valid_N=sum(key[0]==v for key in valid)) for v in job['variants']})
    output = dict(task=144, scope=job['scope'], evaluation_scope=job['evaluation_scope'],
                  status='COVERAGE_ONLY', effect_metrics_generated=False,
                  job_sha256=c.sha(data_folder/'job.json'), inputs_sha256=c.sha(data_folder/'inputs.jsonl'),
                  coverage=coverage, cost=cost_summary(results, found), review_percent_grid=list(PERCENTAGES),
                  score_diagnostics=dict(actual_zero_margin_N=sum(row['logit_S_minus_Not']==0 for row in valid.values()),
                      branch_probability_mass=numeric_summary([row.get('branch_probability_mass') for row in valid.values()]),
                      other_token_mass=numeric_summary([row.get('other_token_mass') for row in valid.values()]),
                      conditional_S_given_S_or_Not=numeric_summary([row.get('conditional_S_given_S_or_Not') for row in valid.values()])),
                  score_definition='logit(S) - logit(Not); first label branch, not a calibrated three-class probability',
                  native_labels_unchanged=True, no_reason_generation_or_borrowing=True,
                  no_GT_threshold_selection=True, CP_guarantee=False)
    if missing or invalid:
        output['stop_reason'] = 'Prescribed scoring target incomplete/invalid; no performance on the scored subset.'
        return output
    if job['scope'] == 'pilot' or job.get('evaluation_metrics_allowed') is not True:
        output['status'] = 'PILOT_COMPLETE_NO_PERFORMANCE' if job['scope']=='pilot' else 'COMPLETE_COVERAGE_ONLY'
        output['stop_reason'] = 'Pilot/coverage-only job: receipt completeness does not authorize performance conclusions.'
        return output
    key_rows = c.rows(KEYS)
    keys = {row['id']: row for row in key_rows}
    evaluation_ids = job['evaluation_ids']
    if len(evaluation_ids) != len(set(evaluation_ids)) or not set(evaluation_ids) <= keys.keys():
        raise ValueError('Invalid frozen evaluation IDs')
    scopes = dict(screen160=160, old500=500, full1817=1817)
    if job['evaluation_scope'] not in scopes or len(evaluation_ids) != scopes[job['evaluation_scope']]:
        raise ValueError('Wrong evaluation target size')
    fixed = (set(c.read(R/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
             if job['evaluation_scope']=='screen160' else
             {i for i,row in keys.items() if job['evaluation_scope']=='full1817' or row['old_panel'] in ('natural','pressure')})
    if set(evaluation_ids) != fixed:
        raise ValueError('Evaluation IDs differ from the frozen134 scope')
    native, provenance, native_missing = load_native(job, data_folder, keys)
    if any(native_missing.values()):
        output['native_coverage_issues'] = native_missing
        output['stop_reason'] = 'Native target not completely valid; no performance output or imputation.'
        return output
    rows = [keys[i] for i in sorted(evaluation_ids)]
    effects = {}
    for variant in job['variants']:
        labels = native[variant]
        supported = {i for i in evaluation_ids if labels[i]=='Supported'}
        if not supported <= set(job['score_ids_by_variant'][variant]):
            output['stop_reason'] = 'Frozen score target does not cover every native Supported prediction.'
            return output
        scores = {i: valid[(variant,i)]['logit_S_minus_Not'] for i in supported}
        consistency = native_branch_consistency(labels, scores)
        points = ranked_points(rows, labels, scores)
        for point in points:
            flags = set(point['review_ids'])
            groups = dict(natural=[r for r in rows if r['old_panel']=='natural'],
                          pressure=[r for r in rows if r['old_panel']=='pressure'],
                          new1317=[r for r in rows if r['subset']=='new'],
                          history103_180=[r for r in rows if r['history103_panel'] in ('natural','pressure')])
            point['panels'] = {name: selective_summary(group,labels,flags) for name,group in groups.items() if group}
            point['authors'] = {name: selective_summary([r for r in rows if r['author']==name],labels,flags) for name in sorted({r['author'] for r in rows})}
            point['patients'] = {str(sid): selective_summary([r for r in rows if r['sid']==sid],labels,flags) for sid in sorted({r['sid'] for r in rows})}
        effects[variant] = dict(native=score(rows,labels), points=points,
                               native_branch_consistency=consistency,
                               score_zero_N=sum(value==0 for value in scores.values()))
    output.update(status='COMPLETE_EFFECT_GRID', effect_metrics_generated=True,
                  evaluation_N=len(rows), evaluation_patients=len({r['sid'] for r in rows}),
                  native_sources=provenance, effects=effects,
                  note='All fixed grid points retained. Automatic-set metrics are not native full-population improvements; human review outcomes not assumed.')
    return output


def render(result):
    cov=result['coverage'];cost=result['cost']
    lines=['# 144原生分支置信度：'+result['scope'], '',
           f"状态：{result['status']}；规定评分{cov['expected_N']}、收到{cov['received_N']}、有效{cov['valid_score_N']}、缺失{len(cov['missing'])}、无效{len(cov['invalid'])}。", '',
           '分数为logit(S)−logit(Not)，是首标签分支分数，不是已校准三分类概率。实际零分数保留，缺失或无效分数不填0。']
    if not result['effect_metrics_generated']:
        lines += ['', result['stop_reason'], '未生成分类效果、送审曲线或按部分数据挑选的点。']
    else:
        lines += ['', '## 全部原生结果', '']+metric_table((name,value['native']) for name,value in result['effects'].items())
        lines += ['', '## 原生S与固定前缀分支的一致性诊断', '',
                  '|输入形式|有分数的原生S|margin<0|margin=0|最小margin|', '|---|---:|---:|---:|---:|']
        for variant,effect in result['effects'].items():
            check=effect['native_branch_consistency']
            lines.append(f"|{variant}|{check['scored_native_S_N']}|{check['negative_N']}|{check['zero_N']}|{number(check['minimum_margin'])}|")
        lines += ['', '负值表示当前canonical前缀下Not分支高于S，与既有原生S输出的分支排序不同；零值只记并列。'
                  '全部对应ID和原margin保留在JSON，不改分数、标签、不剔除、不重发。batch1评分与原batch2生成的数值差可能影响接近0的项；'
                  '若负值很多且明显远离0，应先核对模型、前缀、输入与运行设置，不能直接解释为已校准不确定性。']
        lines += ['', '## 固定送审网格', '', '|模型/原S池送审%|送审n|自动N/覆盖|自动MCC|自动PA|残留FS/原非S|残留FS/自动非S|自动S FDR|送审正确S|拦截FS|随机期望[参考区间]|',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
        for variant,effect in result['effects'].items():
            for point in effect['points']:
                metric=point['automatic'];random=point['random_review'];lo,hi=random['central95_reference_interval']
                lines.append(f"|{variant}/{point['review_percent_of_original_S']}%|{point['review']['N']}|{point['automatic_N']}/{number(point['automatic_coverage'],True)}|{number(metric['mcc_display_value'] if metric else None)}|{number(metric['percent_agreement'] if metric else None,True)}|{point['remaining_automatic_false_S']}/{point['original_non_S']}|{point['remaining_automatic_false_S']}/{point['automatic_non_S']}|{number(point['automatic_predicted_S_FDR'],True)}|{point['review']['deferred_correct_S']}|{point['review']['intercepted_false_S']}|{random['expected_intercepted_false_S']:.2f} [{lo},{hi}]|")
        lines += ['', '只在原生判S池按分数升序、ID平分，送审数floor(比例×原S池N)；所有五点保留，不由GT选择阈值。随机区间为固定队列等量随机送审的精确超几何参考，不是临床安全CI。']
        for variant,effect in result['effects'].items():
            lines += ['', '## '+variant+'完整分类矩阵']+metric_details('原生',effect['native'])
            for point in effect['points']:
                lines += metric_details(str(point['review_percent_of_original_S'])+'%送审后的自动集',point['automatic'])
        lines += ['', '所有点的患者、作者、自然/压力/新增/原180分组及其三类和分母见同名JSON；此路线不追加107判断。送审只加标记，原标签与原reason不改，也不假设人工送审后判对。']
    forward=cost['successful_forward_seconds'];tokens=cost['original_prompt_tokens']
    lines += ['', '## 评分资源与尝试', '',
              f"成功记录forward秒数：已记录{forward['recorded_N']}项，总计{forward['total']}；原prompt tokens记录{tokens['recorded_N']}项，总计{tokens['total']}。", '',
              f"worker墙钟按时间区间并集汇总：{cost['worker_wall_seconds']['recorded_N']}段，总计{number(cost['worker_wall_seconds']['total'])}秒；模型加载{number(cost['model_load_seconds']['total'])}秒，准备{number(cost['preparation_seconds']['total'])}秒。内外层完成/退出记录即使端点不同，嵌套或重叠也只计一次，不重叠运行相加；原记录保留在JSON。", '',
              f"controller墙钟单列：{number(cost['controller_wall_seconds']['total'])}秒。控制器包含worker运行区间，不能与worker墙钟再次相加。", '',
              '实际batch分布：'+str(cost['batch_size_counts'])+'；尝试事件：'+str(cost['attempt_event_counts'])+'。', '',
              f"未配到完成事件的前向尝试{len(cost['pending_attempts'])}次；其forward成本未知时不填零，退出墙钟仍单列。", '',
              '成功forward总和不是完整成本：加载、token编码、等待、失败/在途尝试及进程墙钟按runtime/attempt原始记录另列；字段缺失为未知，不能当作零。'
              '理论上未来可在原生生成同一prefill同步捕获分支logits，但本项目尚未实现或测定该部署成本；当前额外评分需要实际前向。', '',
              '这是既有开发患者上的固定回顾，不是独立测试或CP/风险保证。当前分析新增GPU/API调用为0，已有评分任务的GPU成本须按全尝试账本计入。']
    return '\n'.join(lines).rstrip()+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--results',type=Path,nargs='+',required=True)
    parser.add_argument('--out',type=Path,default=R/'outputs/144_native_confidence')
    args=parser.parse_args()
    result=analyze(args.bundle,args.results)
    prefix=result['scope']
    c.put(args.out/(prefix+'_analysis.json'),result)
    (args.out/(prefix+'_analysis.md')).write_bytes(render(result).encode('utf-8'))
    print(c.canonical(dict(status=result['status'],coverage=result['coverage'],effect_metrics_generated=result['effect_metrics_generated'])))


if __name__=='__main__':
    main()

"""Export observed inference costs only; no model, tokenizer, SHA or evaluator."""
from collections import Counter
from pathlib import Path
import argparse,json,math,statistics,subprocess

R=Path(__file__).resolve().parents[2]
P=R/'.local_models'
SCOPES=('screen160','old500','full1817')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def phases():
    return {
        'claim_repeat136':[(P/'136_claim_repeat_transfer/evidence'/s,'claim_repeat',16384,False) for s in SCOPES],
        'full_repeat139':[(P/'139_full_repeat/evidence'/s,'full_repeat',32768,False) for s in SCOPES],
        'claim_control139':[(P/'139_full_repeat/claim_control160/evidence','claim_control',32768,False)],
        'kl_anchor140':[(P/'140_kl_anchor/evidence','predictions',16384,True)]+[(P/'140_kl_anchor/extension'/s/'evidence','kl_anchor',16384,False) for s in ('old500','full1817')],
        'two_demos141':[(P/'141_two_demos'/s/'evidence','two_demos',32768,False) for s in SCOPES],
    }


def collect_phase(folder,arm,capacity,after_training):
    records={}
    for file in sorted((folder/arm).glob('*.json')):
        raw=read(file)
        if 'id' not in raw:continue
        # Only timing/tokens/validity metadata are retained; content is never exported.
        row={k:raw.get(k) for k in ('id','input_tokens','output_tokens','seconds','batch_seconds','batch_size','finish_reason')}
        row['valid']=raw.get('parsed',{}).get('valid') is True and raw.get('finish_reason')=='stop'
        row['capacity']=capacity
        if row['batch_size'] is None and after_training:
            row['batch_size']=2;row['batch_size_source']='frozen worker140 loop (160 items, batches of2)'
        else:row['batch_size_source']='receipt'
        if row['seconds'] is not None and row['batch_seconds'] is not None:
            assert math.isclose(row['seconds']*row['batch_size'],row['batch_seconds'],rel_tol=1e-9,abs_tol=1e-8)
        assert row['id'] not in records;records[row['id']]=row
    wall=None
    complete=folder/'complete.json';progress=folder/'progress.json';pid=folder/'pid.json';done=folder/'controller_done.json'
    if after_training and complete.exists() and (folder/'training_done.json').exists():
        wall=dict(seconds=read(complete)['epoch']-read(folder/'training_done.json')['epoch'],
            kind='post_training_evaluation_interval',basis='complete.epoch - training_done.epoch; includes eval setup, excludes training and backbone loading')
    elif pid.exists() and done.exists():
        start=read(pid).get('started')
        if start is not None:wall=dict(seconds=read(done)['epoch']-start,
            kind='process_wall' if read(done).get('exit_code')==0 else 'stopped_process_wall',
            basis='controller_done.epoch - pid.started')
    if wall is None and complete.exists() and progress.exists():
        value=read(progress)
        if value.get('stage')=='complete' and value.get('elapsed_seconds') is not None:
            wall=dict(seconds=value['elapsed_seconds'],kind='worker_wall',basis='completed progress.elapsed_seconds')
    return dict(folder=str(folder.relative_to(R)).replace('\\','/'),records=records,wall=wall,complete_file=complete.exists())


def summarize(target,phase_data):
    selected={};walls=[]
    for phase in phase_data:
        subset=target&phase['records'].keys()
        for i in subset:
            assert i not in selected,'Duplicate first receipt '+i
            selected[i]=phase['records'][i]
        if subset:
            walls.append(dict(source=phase['folder'],received_N=len(subset),whole_phase=(subset==phase['records'].keys()),
                recorded_wall=phase['wall'] if subset==phase['records'].keys() else None))
    values=list(selected.values());n=len(values)
    def field(name):
        v=[r[name] for r in values if r[name] is not None]
        return dict(recorded_N=len(v),missing_N=n-len(v),sum=sum(v) if v else None,
            mean=statistics.mean(v) if v else None,median=statistics.median(v) if v else None)
    seconds=field('seconds')
    return dict(expected_N=len(target),received_N=n,valid_N=sum(r['valid'] for r in values),
        invalid_N=sum(not r['valid'] for r in values),missing_N=len(target)-n,
        generation_seconds=dict(complete_total=seconds['sum'] if seconds['recorded_N']==n and n else None,
            recorded_partial_total=seconds['sum'],recorded_N=seconds['recorded_N'],missing_N=seconds['missing_N'],
            mean_per_recorded_item=seconds['mean'],median_per_recorded_item=seconds['median']),
        input_tokens=field('input_tokens'),output_tokens=field('output_tokens'),
        batch_size_items=dict(Counter(str(r['batch_size']) for r in values)),
        inferred_batch_size_items=sum(r['batch_size_source']!='receipt' for r in values),
        context_capacity_items=dict(Counter(str(r['capacity']) for r in values)),phase_walls=walls,
        timing_rule='Sum per-item seconds; batch_seconds is validation only, never summed per item.')


def cell(value,digits=2):
    return '未记录' if value is None else f'{value:.{digits}f}'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=R/'outputs/141_two_demos');args=parser.parse_args()
    keys={r['id']:r for r in (json.loads(x) for x in (P/'134_author_baselines/keys.jsonl').read_text(encoding='utf-8').splitlines())}
    targets=dict(screen160=set(read(P/'134_author_baselines/job.json')['phases'][0]['ids']),
        old500={i for i,r in keys.items() if r['old_panel'] in ('natural','pressure')},full1817=set(keys))
    assert tuple(len(targets[s]) for s in SCOPES)==(160,500,1817)
    source={name:[collect_phase(*phase) for phase in spec] for name,spec in phases().items()}
    tables={s:{} for s in SCOPES};excluded={};stopped=[]
    for name,data in source.items():
        for scope in SCOPES:
            result=summarize(targets[scope],data)
            if scope=='full1817' and result['received_N']!=1817:
                excluded[name]=dict(received_N=result['received_N'],missing_N=result['missing_N'])
            elif scope=='old500' and name=='claim_control139':continue
            else:tables[scope][name]=result
        # A partial final extension is separate from completed160/500 cost tables.
        if name=='two_demos141':
            partial=summarize(targets['full1817']-targets['old500'],data)
            if 0<partial['received_N']<1317:
                partial['scope']='stopped/partial additional1317; excluded from normal old500 costs'
                final_folder=P/'141_two_demos/full1817/evidence'
                if (final_folder/'failure.json').exists():partial['failure']=read(final_folder/'failure.json')
                stopped.append(partial)
    previous={}
    for path in (R/'outputs/139_full_repeat/runtime_cost160.json',R/'outputs/141_two_demos/runtime_cost160.json'):
        if path.exists():previous[str(path.relative_to(R)).replace('\\','/')]=read(path)
    for name,key,path in [('full_repeat139','full_repeat','outputs/139_full_repeat/runtime_cost160.json'),
        ('two_demos141','two_demos','outputs/141_two_demos/runtime_cost160.json'),
        ('claim_control139','claim_control','outputs/141_two_demos/runtime_cost160.json')]:
        old=previous.get(path,{}).get(key)
        if old:
            row=tables['screen160'][name]
            assert old['N']==row['received_N'] and math.isclose(old['generation_seconds_sum'],row['generation_seconds']['complete_total'],rel_tol=1e-10)
            row['previous_cost160_generation_verified']=True
            row['previous_artifact_wall_seconds']=old['process_wall_seconds']
            if name=='two_demos141':
                row['previous_artifact_wall_correction']='Previous828.91 labeled process wall matches worker elapsed828.9078; actual pid-to-controller832.2226 used consistently here. Original artifact retained.'
    result=dict(main_HEAD=subprocess.check_output(['git','rev-parse','main'],cwd=R,text=True).strip(),
        scope_rule='Fixed identical IDs per table; full1817 contains only configurations with1817 actual first receipts.',
        seconds_audit={'136':'worker136: seconds=elapsed/len(identifiers)',
            '139':'worker139: seconds=batch_seconds=elapsed; batch1',
            '140_screen160':'worker140 has no seconds/output_tokens; missing retained. Batch2 from frozen loop.',
            '140_extensions':'worker_eval140: seconds=elapsed/len(identifiers)',
            '141':'worker141: seconds=batch_seconds=elapsed; batch1'},
        common_settings='BF16 native9B; greedy; max_new_tokens384; no thinking. Batch/context differences are explicit, not treated as controlled speed tests.',
        call_count_rule='Received_N counts actual proposition-level Judge decisions. Local batched generation, zero API requests; batch sizes are separate from decision counts.',
        wall_rule='Actual recorded process/worker intervals only; stage sums have repeated loading. Missing values stay null. Post-training140 interval is not a standalone inference process or pure generation time.',
        billing='No CNY inferred from generation times. Shared GPU20 CNY window starts2026-10-31 09:36:01+08:00 at1.58 CNY/hour; includes preparation, loading, compilation, waiting and return. These timings are not that total bill. API0.',
        unrecorded_historical_cost={'paper_r1':'Not recorded: historical author predictions have no matching local runtime receipts; never shown as zero.'},
        tables=tables,not_complete_for_full1817=excluded,separate_stopped_attempts=stopped,
        no_model_or_tokenizer_loaded=True,no_reinference=True,no_full_SHA_scan=True)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'inference_cost.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 实际推理成本（同ID）','',
        '只统计原首答回执，无重推。136及140扩评的 `seconds` 已按batch均摊，汇总只加 `seconds`，不重复加每条的 `batch_seconds`。无效回答仍计入成本。计时包含首次generate可能发生的编译；不同加载、编译与batch条件使其不是严格速度基准。',
        '收到数为实际命题级Judge判定次数；这些均为本地批量生成，新增API请求为0。batch列单列实际批量，不把命题次数冒充批调用次数。','']
    for scope in SCOPES:
        lines+=['## '+scope+'（'+str(len(targets[scope]))+'条）','',
            '|配置|收到/有效/无效/缺失|生成秒数（计时N）|每条均摊秒（计时N）|平均输入token（N）|平均输出token（N）|batch：条数；context|记录墙钟秒|',
            '|---|---|---:|---:|---:|---:|---|---|']
        for name,row in tables[scope].items():
            t=row['generation_seconds'];n=t['recorded_N']
            timing=cell(t['complete_total']) if t['complete_total'] is not None else ('部分 '+cell(t['recorded_partial_total']) if n else '未记录')
            walls=[]
            for phase in row['phase_walls']:
                w=phase['recorded_wall'];label={'process_wall':'进程','stopped_process_wall':'停止进程','worker_wall':'worker','post_training_evaluation_interval':'训练后评价段'}
                walls.append(cell(w['seconds'])+'（'+label[w['kind']]+'）' if w else '未记录')
            batch='/'.join(k+'：'+str(v) for k,v in sorted(row['batch_size_items'].items()))
            cap='/'.join(row['context_capacity_items'])
            tok=lambda key:cell(row[key]['mean'])+'（'+str(row[key]['recorded_N'])+'）'
            lines.append('|'+name+'|'+str(row['received_N'])+'/'+str(row['valid_N'])+'/'+str(row['invalid_N'])+'/'+str(row['missing_N'])+'|'+timing+'（'+str(n)+'）|'+cell(t['mean_per_recorded_item'])+'（'+str(n)+'）|'+tok('input_tokens')+'|'+tok('output_tokens')+'|'+batch+'；'+cap+'|'+' + '.join(walls)+'|')
        lines.append('')
    lines+=['140最初160条未保存生成秒数和输出token，不能补造；500/1817相应均值及部分秒数只来自后续340/1657条，不是完整总耗时。其初筛batch2由冻结worker循环确认，307秒左右的训练后评价段不含训练或模型初次加载，不能与独立推理进程总账直接等同。','',
        '各阶段墙钟包括该进程实际加载、编码、编译及推理（训练后评价段例外），不含准备/上传/回传/阶段间等待；没有将其差额当成纯加载时间。跨阶段相加会包含重复加载。完整1817表排除未齐全的配置，明细见JSON。旧runtime_cost160中141的828.91秒对应worker elapsed而非完整进程；本表统一采用pid.started至controller_done的832.22秒，旧文件保留。','',
        'paper_r1等没有对应本地运行回执的历史预测，其推理成本为“未记录”，不是0，也不为补成本新增调用。','',
        '## 独立停止尝试','']
    if stopped:
        for row in stopped:
            t=row['generation_seconds']
            wall=row['phase_walls'][0]['recorded_wall'] if row['phase_walls'] else None
            lines.append('141额外1317阶段已收到 '+str(row['received_N'])+' 条（有效'+str(row['valid_N'])+'、无效'+str(row['invalid_N'])+'），已记录生成 '+cell(t['recorded_partial_total'])+' 秒，停止进程墙钟 '+cell(wall['seconds'] if wall else None)+' 秒，平均输入/输出 '+cell(row['input_tokens']['mean'])+'/'+cell(row['output_tokens']['mean'])+' tokens；仅为停止前尝试，**不并入原500正常成本**，也不列完整1817成本。')
    else:lines.append('本次快照未发现不足1317的额外141首答；不制造停止尝试数。')
    lines+=['','人民币未由生成秒数推定；实际GPU总账仍按09:36:01起1.58元/小时的共享20元窗口累计，包含准备、等待、加载、编译和回传，API为0。运行成本不含额外训练成本；本表不是完整方案总费用。','']
    (args.out/'inference_cost.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(scopes={s:list(v) for s,v in tables.items()},stopped_N=[x['received_N'] for x in stopped],output=str(args.out)),ensure_ascii=False))


if __name__=='__main__':main()

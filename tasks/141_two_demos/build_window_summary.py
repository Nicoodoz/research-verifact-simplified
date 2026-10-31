"""Read existing metrics only; write a new private snapshot with a supplied conclusion."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,json,os

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'docs/PROJECT_STATUS.md').is_file())
LABELS=('Supported','Not Supported','Not Addressed')
SCOPES={'full1817':1817,'old500':500,'screen160':160}
ORDER=('paper_r1','author_base9b','author_lora9b','base104_9b','label_only107','full_pool120','midpoint132',
       'claim_repeat136','extra_steps137','rationale_tasks138','label_replay138','full_repeat139','kl_anchor140','two_demos141')
SPECS={
    'claim_repeat136':('136_claim_repeat_transfer','{scope}.json'),
    'extra_steps137':('137_extra_steps','{scope}.json'),
    'rationale_tasks138':('138_rationale_tasks','rationale_tasks_{scope}.json'),
    'label_replay138':('138_rationale_tasks','label_replay_{scope}.json'),
    'full_repeat139':('139_full_repeat','{scope}.json'),
    'kl_anchor140':('140_kl_anchor','kl_anchor_{scope}.json'),
    'two_demos141':('141_two_demos','two_demos_{scope}.json'),
}
ALIASES={'candidate':None,'claim_repeat':'claim_repeat136','claim_repeat136':'claim_repeat136',
         'extra_steps':'extra_steps137','extra_steps137':'extra_steps137',
         'rationale_tasks':'rationale_tasks138','label_replay':'label_replay138',
         'kl_anchor':'kl_anchor140','two_demos':'two_demos141',
         'full_repeat':'full_repeat139',
         '107_label_only':'label_only107','120_step369':'full_pool120'}


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def lines(path):return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def lookup(value,*keys):
    for key in keys:
        if not isinstance(value,dict):return None
        value=value.get(key)
    return value
def count(metric):
    return metric.get('n',metric.get('N',sum(sum(r) for r in metric.get('confusion_matrix',[]))))
def label(name,owner):return owner if name=='candidate' else ALIASES.get(name,name)
REPORT_DIR=None
def link(path,title='明细'):
    target=path.resolve().as_posix() if REPORT_DIR is None else os.path.relpath(path.resolve(),REPORT_DIR.resolve()).replace('\\','/')
    return f'[{title}]({target})'


def coverage(doc,expected):
    cov=doc.get('coverage',{})
    if 'candidate' in cov:cov=cov['candidate']
    missing=cov.get('missing_ids',[]);invalid=cov.get('invalid_ids',[])
    valid=doc.get('valid_N',doc.get('joint_valid_N',expected-len(missing)-len(invalid)))
    return dict(expected_N=expected,received_N=cov.get('received_N',expected-len(missing)),
        valid_N=cov.get('valid_N',valid),missing_N=len(missing),invalid_N=len(invalid))


def compact_row(name,metric,path,metric_path,source_scope):
    if not isinstance(metric,dict) or 'mcc' not in metric:return None
    return dict(config=name,N=count(metric),MCC=metric['mcc'],PA=metric['percent_agreement'],
        correct=metric['correct'],false_S=metric['false_S'],non_S=metric['non_S'],
        recall={g:metric['per_class'][g]['recall'] for g in LABELS},
        macro_F1=metric.get('macro_F1'),source=path.relative_to(ROOT).as_posix(),
        metric_path=metric_path,source_scope=source_scope)


def scores_into(target,scores,path,metric_path,scope,owner,required_N=None):
    for original_name,metric in (scores or {}).items():
        name=label(original_name,owner)
        if name not in ORDER:continue
        row=compact_row(name,metric,path,metric_path+'.'+str(original_name),scope)
        if row and (required_N is None or row['N']==required_N):target.setdefault(name,row)


def main_table(docs,scope,expected,expected_ids):
    result={};covrows=[];notes=[]
    for owner,(doc,path) in docs.items():
        cov=coverage(doc,expected);covrows.append(dict(config=owner,**cov,source=path.relative_to(ROOT).as_posix()))
        complete=cov['valid_N']==expected and cov['missing_N']==0 and cov['invalid_N']==0
        receipt=path.with_name(path.stem+'_receipt_status_sanitized.jsonl')
        if receipt.exists():
            status=lines(receipt);valid_ids={r['id'] for r in status if r.get('valid') is True}
            complete=complete and valid_ids==expected_ids
        if not complete:
            notes.append(f'{owner}已有分析但未覆盖完整同ID分母（有效{cov["valid_N"]}/{expected}）；仅列覆盖和明细。')
            continue
        primary=lookup(doc,'primary','scores') or {}
        scores_into(result,primary,path,'primary.scores',scope,owner,expected)
        for key in ('historical_on_primary_IDs','historical_on_same_IDs'):
            scores_into(result,doc.get(key),path,key,scope,owner,expected)
        part=doc.get('historical_common',{})
        if part.get('N')==expected:scores_into(result,part.get('scores'),path,'historical_common.scores',scope,owner,expected)
    return result,covrows,notes


def panel_rows(all_docs,extra_docs,panel,wanted):
    result={}
    #A complete1817 source is preferred;500 may supply exactly400/100.
    aliases={'natural':('natural','natural400'),'pressure':('pressure','pressure100'),
             'new1317':('new1317',),'history103_180':('history103_180',)}
    for scope in SCOPES:
        for owner,(doc,path) in all_docs[scope].items():
            for key in aliases[panel]:
                scores=lookup(doc,'panels',key,'scores')
                scores_into(result,scores,path,'panels.'+key+'.scores',scope,owner,wanted)
    midpoint=extra_docs.get('132')
    if midpoint:
        doc,path=midpoint
        scores_into(result,lookup(doc,'panels',panel,'scores'),path,'panels.'+panel+'.scores','full1817','midpoint132',wanted)
    return result


def render_table(rows, costs=None):
    extra=costs is not None
    output=['|配置|N|MCC|PA|正确|FS/非S|S/NS/NA召回|'+('平均入/出token（记录N）|均摊生成秒（计时N）|' if extra else '')+'来源|',
            '|---|---:|---:|---:|---:|---:|---|'+('---|---|' if extra else '')+'---|']
    for name in ORDER:
        if name not in rows:continue
        r=rows[name];rec='/'.join('—' if r['recall'][g] is None else f"{r['recall'][g]:.2%}" for g in LABELS)
        cost_cells=''
        if extra:
            cost=costs.get(name)
            def mean_cell(key):
                if cost is None:return '本表未整理'
                item=cost.get(key,{})
                return '未记录' if item.get('mean') is None else f"{item['mean']:.2f}（{item['recorded_N']}）"
            t=cost.get('generation_seconds',{}) if cost is not None else {}
            seconds=('本表未整理' if cost is None else '未记录') if t.get('mean_per_recorded_item') is None else f"{t['mean_per_recorded_item']:.2f}（{t['recorded_N']}）"
            cost_cells=mean_cell('input_tokens')+'/'+mean_cell('output_tokens')+'|'+seconds+'|'
        output.append(f"|{name}|{r['N']}|{r['MCC']:.4f}|{r['PA']:.2%}|{r['correct']}|{r['false_S']}/{r['non_S']}|{rec}|{cost_cells}{link(ROOT/r['source'],r['source_scope'])}|")
    return output


def build(conclusion,as_of):
    cost_path=ROOT/'outputs/141_two_demos/inference_cost.json'
    inference_cost=read(cost_path) if cost_path.exists() else {}
    keys=lines(ROOT/'.local_models/134_author_baselines/keys.jsonl')
    screen=set(read(ROOT/'.local_models/134_author_baselines/job.json')['phases'][0]['ids'])
    ids={'full1817':{r['id'] for r in keys},'old500':{r['id'] for r in keys if r['old_panel'] in ('natural','pressure')},'screen160':screen}
    assert {k:len(v) for k,v in ids.items()}==SCOPES
    docs={};missing_sources={};sources=set()
    for scope in SCOPES:
        docs[scope]={};missing_sources[scope]=[]
        for name,(folder,template) in SPECS.items():
            path=ROOT/'outputs'/folder/template.format(scope=scope)
            if path.exists():docs[scope][name]=(read(path),path);sources.add(path)
            else:missing_sources[scope].append(name)
    mains={};covs={};notes={}
    for scope,N in SCOPES.items():mains[scope],covs[scope],notes[scope]=main_table(docs[scope],scope,N,ids[scope])
    #Base134 has its own common-ID cohort: keep that separate from1817.
    authors={};author_cov={};author_N=None
    path134=ROOT/'outputs/134_author_baselines/full1817.json'
    if path134.exists():
        d134=read(path134);part=lookup(d134,'panels','all') or {}
        author_N=part.get('N');author_cov=d134.get('coverage',{});sources.add(path134)
        if author_N:scores_into(authors,part.get('scores'),path134,'panels.all.scores','134共同子集',None,author_N)
    for owner,(doc,path) in docs['full1817'].items():
        if 'three_baseline_common_scores' in doc:
            n=doc.get('three_baseline_common_N');scores=doc['three_baseline_common_scores'];metric_path='three_baseline_common_scores'
        else:
            part=doc.get('author_baseline_common',{});n=part.get('N');scores=part.get('scores',{});metric_path='author_baseline_common.scores'
        if n==author_N:scores_into(authors,scores,path,metric_path,'134共同子集',owner,author_N)
    #104 base is a different prompt/budget from author_base9b. Its original
    #partial coverage must remain a separate explicitly common subset.
    base104_rows={};base104_N=0;base104_source=None
    for owner in ('two_demos141','kl_anchor140','rationale_tasks138'):
        for scope in SCOPES:
            if owner not in docs[scope]:continue
            doc,path=docs[scope][owner];part=doc.get('same_prompt_unfinetuned_overlap',{})
            if not part.get('N') or 'base104_9b' not in part.get('scores',{}):continue
            base104_N=part['N'];base104_source=path.relative_to(ROOT).as_posix()
            scores_into(base104_rows,part['scores'],path,'same_prompt_unfinetuned_overlap.scores',scope,owner,base104_N)
            break
        if base104_N:break
    extra={};p132=ROOT/'outputs/132_midpoint_update/selection1817.json'
    if p132.exists():extra['132']=(read(p132),p132);sources.add(p132)
    panels={name:panel_rows(docs,extra,name,N) for name,N in [('natural',400),('pressure',100),('new1317',1317),('history103_180',180)]}
    start=datetime(2026,10,31,9,36,1,tzinfo=timezone(timedelta(hours=8)))
    session_path=ROOT/'.local_models/140_kl_anchor/bundle/data/session.json'
    old_window_cost=read(session_path).get('prior_GPU_to_new_authorization_CNY') if session_path.exists() else None
    wall=max(0,(as_of-start).total_seconds());cost=wall*1.58/3600
    report=dict(created_at=as_of.isoformat(timespec='seconds'),conclusion=conclusion,
        tables=mains,coverage=covs,scope_notes=notes,missing_analysis_sources=missing_sources,
        author_common_N=author_N,author_common=authors,author_raw_coverage=author_cov,
        base104_common_N=base104_N,base104_common=base104_rows,base104_source=base104_source,panels=panels,
        budget=dict(start=start.isoformat(),as_of=as_of.isoformat(),elapsed_seconds=wall,
                    estimated_GPU_CNY=cost,GPU_cap_CNY=20,API_used_CNY=0,API_cap_CNY=80,
                    includes_preparation_loading_compiling_waiting_return=True,no_shutdown=True,
                    prior16_window_estimate_CNY=old_window_cost),
        methodology='Only copy existing metric fields; never evaluate predictions, average MCC, merge matrices, or impute missing labels.',
        inference_cost_source=cost_path.relative_to(ROOT).as_posix() if inference_cost else None,
        sources=[p.relative_to(ROOT).as_posix() for p in sorted(sources)])
    out=['# 当前窗口集中比较','',conclusion,'',
         '仅复用既有分析JSON。1817、500、160各自是固定同ID范围，禁止跨表直接相减；未完成/覆盖不同的候选不填0、不进入完整分母表。',
         '评价仍是原20名历史暴露的选型患者；100名患者都有研究暴露，不称全新holdout，也没有自动使用确认40人重新选型。当前训练维持原32人、内部验证8人的边界。','']
    titles={'full1817':'完整1817','old500':'原500','screen160':'初筛160'}
    for scope,N in SCOPES.items():
        out+=['## '+titles[scope]+'：固定'+str(N)+'条','']+render_table(mains[scope],inference_cost.get('tables',{}).get(scope,{}))+['']
        out+=['成本括号为实际计时或token记录条数，部分记录不是全范围总成本；其他历史配置的“本表未整理”不表示原日志没有记录。'+link(ROOT/'outputs/141_two_demos/inference_cost.md','生成总时长、batch、墙钟及停止尝试明细')+'。' if inference_cost else '尚未找到该快照的推理成本汇总，不补0。','']
        for note in notes[scope]:out += [note]
        if missing_sources[scope]:out += ['尚无该范围分析文件：'+', '.join(missing_sources[scope])+'；不列成绩。']
        out+=['','|实际候选|收到|有效|缺失|无效|详表|','|---|---:|---:|---:|---:|---|']
        for cov in covs[scope]:
            out.append(f"|{cov['config']}|{cov['received_N']}|{cov['valid_N']}|{cov['missing_N']}|{cov['invalid_N']}|{link(ROOT/cov['source'])}|")
        out.append('')
    if author_N:
        out+=['## 原作者提示两9B：134固定共同'+str(author_N)+'条','',
              '这是独立共同子集，不与1817主表直接相减。作者提示两9B使用768输出上限。','']+render_table(authors)+['']
        for name,cov in author_cov.items():
            missing=cov.get('missing_ids',[]);invalid=cov.get('invalid_ids',[])
            out.append(f"{name}原始覆盖/invalid详见{link(path134)}；缺失{len(missing)}，无效{len(invalid)}。")
    if base104_N:
        out+=['','## 104未微调9B的实际共同'+str(base104_N)+'条','',
              '此未调基线与107/120原104输入匹配；136/140另有claim_repeat，141再加固定示例。它不是原作者prompt基线，也没有1817条完整覆盖。','']+render_table(base104_rows)+['']
    out+=['','## 固定来源分组','',
          '只列已保存且N恰好对应固定组的指标。自然400/压力100可来自500分析；新增1317/103原180须有对应完整覆盖。来源列保留其原scope，不拼接或平均不同子组。','']
    for panel,title,N in [('natural','自然',400),('pressure','压力',100),('new1317','新增',1317),('history103_180','103原面板',180)]:
        out+=['### '+title+str(N),'']+render_table(panels[panel])+['']
    out+=['## 配置与监督边界','',
        '|配置|模型、输入与监督差别|','|---|---|',
        '|paper_r1|作者历史R1系统，不是本轮同模型对照。|',
        '|author_base9b / author_lora9b|同9B原作者式prompt；前者未微调，后者120权重，768输出。|',
        '|107 / 120|同Qwen3.5-9B；107原196条监督，120再用2945条标签训练369步；104接口。|',
        '|132 / 136|132为107与120的固定权重中点；136为120权重、原136 claim_repeat输入。|',
        '|137 / 138|137固定追加149步；138固定48步，主臂含36条旧理由辅助位置，对照为同位置标签回放。|',
        '|139|完整用户输入重复，120权重、batch1/32768；仅列其实际160/500，不外推1817。|',
        '|140|同138回放数据/顺序/48步，加固定0.5×KL；不使用新增理由数据。|',
        '|141|120权重，仅加固定S→NS两条完整标签演示；batch1/32768/greedy384，无新训练。|','',
        '127的67条理由（训练63、内部验证4）是数据准备成果，不能算作这67条已带来训练收益；138只用了更早36条，140不加理由，141只把其中两例的原标签用于in-context输入。133在16步安全暂停，未产生可列的评价成绩。','',
        '当前以标签性能为先，尚未证明同次生成reason与标签的语义自洽；不得给改变后的标签沿用旧reason。','',
        '各原分析JSON保留完整三类precision/recall/F1、混淆矩阵、false-S率和预测S假发现率、救回误伤、患者与作者变化及已有区间；上表来源链接即详细入口。不因这里只摘主列而改变原口径。','',
        '## 费用与状态','',
        f"从{start.isoformat(timespec='seconds')}起到{as_of.isoformat(timespec='seconds')}，按1.58元/小时估算GPU累计¥{cost:.3f}/20。所有准备、加载、编译、等待与回传均计入；这不是平台精确账单，也不因任务切换重置。API仍¥0/80。",
        '不自动关机或释放。默认系统未因该汇总升级；这里的结论由调用者明确传入，脚本不替未完成结果编造结论。','']
    if old_window_cost is not None:
        out += [f'上一16元窗口至本次新增授权前另估约¥{old_window_cost:.3f}，单独记录；旧余额未借用、API额度未重置。','']
    return report,'\n'.join(out)


def main():
    global REPORT_DIR
    parser=argparse.ArgumentParser();parser.add_argument('--conclusion',required=True)
    parser.add_argument('--out',type=Path);parser.add_argument('--as-of',help='Optional timezone-aware ISO timestamp for an explicit snapshot')
    args=parser.parse_args()
    if not args.conclusion.strip():parser.error('--conclusion cannot be empty')
    now=datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone(timedelta(hours=8)))
    if now.tzinfo is None:parser.error('--as-of requires an explicit timezone')
    target=args.out or ROOT/'.local_models/141_two_demos/draft'/now.strftime('%Y%m%d_%H%M%S')
    REPORT_DIR=target
    md=target/'window_summary.md';js=target/'window_summary.json'
    if md.exists() or js.exists():raise FileExistsError('Snapshot exists; choose a new output directory')
    data,text=build(args.conclusion,now);target.mkdir(parents=True,exist_ok=True)
    md.write_bytes(text.encode('utf-8'));js.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(markdown=str(md),json=str(js),scope_rows={k:len(v) for k,v in data['tables'].items()},
                         author_common_N=data['author_common_N'],no_new_evaluation=True),ensure_ascii=False))


if __name__=='__main__':main()

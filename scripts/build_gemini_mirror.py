"""Create an information-rich, local reading mirror; never commits or pushes."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tokenize

ROOT=Path(__file__).resolve().parents[1]
BYTE_LIMIT=95_000_000
FILE_LIMIT=4800
SECRET=re.compile(r'\bsk-(?:ws-)?[A-Za-z0-9._-]{24,}|\bAKIA[A-Z0-9]{16}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
CLINICAL=re.compile(r'\[\*\*[^\]\r\n]{3,}\*\*\]|\b21\d{2}[-/]\d{1,2}[-/]\d{1,2}\b')
UUID=re.compile(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b',re.I)
CASE_HEADING=re.compile(r'病例|逐例|案例|case\s*(?:study|analysis|ledger|book)|representative\s+cases|原始.*(?:EHR|病历)|(?:EHR|病历|原文).*示例',re.I)
CASE_TABLE=re.compile(r'(?:^|\|)\s*(?:claim(?: text)?|proposition(?: text)?|命题(?:原文|文本)?|原句|原文(?:内容|片段|引句)?|EHR(?:证据|文本)?|reference(?: text)?|引文)\s*(?:\||$)',re.I)
SKIP_PART=re.compile(r'^(?:attempts?(?:_\d+)?|requests?|responses?|receipts?|replays|synthetic_transport_tests|__pycache__|\.git|\.local_models|data)$',re.I)
AGG_NAME=re.compile(r'metric|analys|result|summary|paired|performance|evaluat|confusion|bootstrap|sensitiv|strat|cost|ledger|freez|protocol|selfcheck|verif|coverage|manifest|checks|diagnos|profile|group|calibr|compos|decision|comparison|inventory|sources|parameter|model|config|sample|overlap|audit|bound|fit|aggregate',re.I)
CSV_NAME=re.compile(r'table|metric|summary|curve|performance|bootstrap|strat|compar|paired|coverage|count|cost|auc|grid|risk|calibr|patient',re.I)
FIG_NAME=re.compile(r'figure|confusion|matrix|risk_rescue|stage_decomposition|decision_paths|calibration|performance|distribution|ablation|frontier|auc|roc|score|cost|tradeoff',re.I)
BLOCK_CONTENT={'text','claim','proposition','reference','ehr','claim_text','proposition_text','reference_text','ehr_text','prompt','system_prompt','user_prompt','messages','body','request_body','response_body','raw_response','reason','reasoning','reasoning_content','evidence_text','quotation','quote','quotes','rationale','patient_text','medical_text','raw_text','raw_content','content'}
LABELS={'Supported','Not Supported','Not Addressed','S','NS','NA'}
EXTRAS={'docs/reports/导师汇报_F4_raw复核.json','docs/sharing/GEMINI_READING_PACK.md','scripts/build_gemini_reading_pack.py','scripts/build_gemini_mirror.py'}


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8')
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')
def omitted(kind,value):return {'reading_export_omitted':kind,'count':len(value) if hasattr(value,'__len__') else None,'source_value_sha256':sha(encoded(value))}


def markdown(text):
    out=[];blocked=None;table_block=False;removed=0
    for line in text.splitlines():
        h=re.match(r'^(#{1,6})\s+(.+)',line)
        if h:
            depth=len(h[1])
            if blocked is not None and depth<=blocked:blocked=None
            if CASE_HEADING.search(h[2]):blocked=depth
        if blocked is not None:
            removed+=1;continue
        if line.lstrip().startswith('|'):
            if not out or not out[-1].lstrip().startswith('|'):
                table_block=bool(CASE_TABLE.search(line))
            if table_block:
                removed+=1;continue
        else:table_block=False
        if CLINICAL.search(line) or UUID.search(line):
            removed+=1;continue
        out.append(line)
    if removed:out.insert(0,f'> 阅读镜像：已省略{removed}行病例原文／标识；原始文件SHA见MIRROR_MANIFEST.json。\n')
    return '\n'.join(out).rstrip()+'\n',removed


def python_text(text):
    if not CLINICAL.search(text):return text,0
    tokens=[];changed=0
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type in (tokenize.STRING,tokenize.COMMENT) and CLINICAL.search(token.string):
            token=token._replace(string=CLINICAL.sub('[CLINICAL_LITERAL_REMOVED]',token.string));changed+=1
        tokens.append(token)
    result=tokenize.untokenize(tokens)
    if CLINICAL.search(result):raise ValueError('clinical marker outside replaceable literal')
    ast.parse(result)
    return result,changed


def per_case(value):
    return isinstance(value,dict) and bool(set(value)&{'id','proposition_id','case_id','request_id'}) and bool(set(value)&{'GT','raw','verdict','claim','reference','prediction','label_scores'})


def clean_json(value,key='',counter=None):
    counter=counter if counter is not None else Counter()
    lk=key.lower()
    if re.search(r'api[_-]?key|password|secret|authorization|access[_-]?token|refresh[_-]?token',lk):
        counter['credential_field']+=1;return omitted('credential field',value)
    if lk in BLOCK_CONTENT and not (isinstance(value,str) and value in LABELS):
        counter['content_field']+=1;return omitted('patient/prompt/narrative content',value)
    if isinstance(value,str):
        if SECRET.search(value) or CLINICAL.search(value):
            counter['blocked_string']+=1;return omitted('blocked string',value)
        if len(value)>2000:
            counter['long_string']+=1;return omitted('long non-numeric string',value)
        return value
    if isinstance(value,list):
        if value and (per_case(value[0]) or ('ids' in lk and all(isinstance(x,(str,int)) for x in value))):
            counter['record_or_identifier_list']+=1;return omitted('per-case records or identifier list',value)
        if len(value)>10000:
            counter['large_list']+=1;return omitted('list over 10000 elements',value)
        return [clean_json(v,key,counter) for v in value]
    if isinstance(value,dict):
        if per_case(value):
            counter['case_record']+=1;return omitted('per-case record',value)
        if len(value)>20 and sum(bool(UUID.fullmatch(str(k))) for k in value)>len(value)//2:
            counter['case_map']+=1;return omitted('per-case identifier map',value)
        return {str(k):clean_json(v,str(k),counter) for k,v in value.items()}
    return value


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',required=True)
    args=parser.parse_args()
    dest=Path(args.destination).resolve()
    parent=(ROOT/'outputs/replays/gemini_publish_2026-10-25').resolve()
    if not dest.is_relative_to(parent) or dest==parent:raise ValueError('Wrong mirror target')
    if not (dest/'.git').is_dir():raise ValueError('Clone destination first')
    if any(p.name!='.git' for p in dest.iterdir()):raise ValueError('Refuse to overwrite a nonempty mirror')
    head=git('rev-parse','HEAD').strip()
    status=git('status','--porcelain','-z').split('\0')
    tree=[]
    for row in git('ls-tree','-r','-l','-z','HEAD').split('\0'):
        if not row:continue
        fields,path=row.split('\t',1);bits=fields.split()
        if bits[1]=='blob':tree.append({'path':path,'bytes':int(bits[3])})
    paths=sorted({r['path'] for r in tree}|{p for p in EXTRAS if (ROOT/p).is_file()})
    records=[];skips=Counter();details=[];total=0;count=0;bundles=defaultdict(list);bundle_sizes=Counter()
    def save(path,data,source=None,source_data=None,transform=None):
        nonlocal total,count
        target=(dest/path).resolve()
        if not target.is_relative_to(dest):raise ValueError('Escaped destination')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        total+=len(data);count+=1
        if source is not None:records.append({'source':source,'destination':path,'source_sha256':sha(source_data),'export_sha256':sha(data),'bytes':len(data),'transform':transform or 'none'})
    def skip(path,reason):
        skips[reason]+=1
        if reason not in {'not_selected_artifact','raw_or_private_directory'}:details.append({'source':path,'reason':reason})
    # Preserve broad code, documentation, protocols, manuscript versions and audit prose.
    for path in paths:
        p=Path(path);parts=p.parts
        if any(SKIP_PART.fullmatch(x) for x in parts) or p.name.startswith('.env'):
            skip(path,'raw_or_private_directory');continue
        text_file=(p.suffix.lower() in {'.py','.ps1','.md','.yml','.yaml','.toml','.rst','.jinja','.diff'} or p.name in {'LICENSE','requirements.txt'})
        if not text_file:continue
        source=ROOT/path
        if not source.is_file() or source.is_symlink():skip(path,'missing_or_symlink');continue
        data=source.read_bytes()
        if len(data)>3_000_000:skip(path,'oversize_text');continue
        try:text=data.decode('utf-8-sig')
        except UnicodeDecodeError:skip(path,'not_utf8');continue
        if SECRET.search(text):skip(path,'credential_pattern');continue
        changes=0
        try:
            if p.suffix=='.md':text,changes=markdown(text)
            elif p.suffix=='.py':text,changes=python_text(text)
            elif CLINICAL.search(text):skip(path,'clinical_marker_other_text');continue
        except (ValueError,SyntaxError,tokenize.TokenError):skip(path,'unredactable_python_literal');continue
        if SECRET.search(text) or CLINICAL.search(text):skip(path,'remaining_blocked_marker');continue
        output='README_SOURCE.md' if path=='README.md' else path
        save(output,text.encode('utf-8'),path,data,{'redacted_lines_or_literals':changes} if changes else None)
    # Numeric figures; source-paper screenshots and clinical illustrations are not copied.
    for path in paths:
        p=Path(path)
        if not path.startswith('outputs/') or p.suffix.lower() not in {'.png','.svg'} or not FIG_NAME.search(p.stem) or any(SKIP_PART.fullmatch(x) for x in p.parts):continue
        data=(ROOT/path).read_bytes()
        if p.suffix=='.svg':
            text=data.decode('utf-8-sig')
            if SECRET.search(text) or CLINICAL.search(text):skip(path,'blocked_figure_text');continue
        else:
            paired=(ROOT/path).with_suffix('.svg')
            if paired.exists() and (SECRET.search(paired.read_text(encoding='utf-8-sig')) or CLINICAL.search(paired.read_text(encoding='utf-8-sig'))):skip(path,'blocked_paired_figure');continue
        save(path,data,path,data)
    required_size=total
    # Per-task aggregate bundles avoid a new file-count problem.
    candidates=[]
    for path in paths:
        p=Path(path);parts=p.parts
        if any(SKIP_PART.fullmatch(x) for x in parts):continue
        if p.suffix=='.json' and parts[0] in {'outputs','docs','reviews'}:
            if len(parts)>5 or p.name.lower() in {'request.json','response.json','receipt.json','tokenizer.json','config.json'}:continue
            if not AGG_NAME.search(p.stem) and path!='docs/reports/导师汇报_F4_raw复核.json':continue
            candidates.append(path)
        elif p.suffix=='.csv' and parts[0] in {'outputs','reviews'} and len(parts)<=5 and CSV_NAME.search(p.stem) and not re.search(r'case|prediction|candidate|material|input|request|response|receipt',p.stem,re.I):
            candidates.append(path)
    def rank(path):
        p=Path(path);m=re.search(r'(?:^|/)(\d{3})_',path)
        number=int(m[1]) if m else 999
        return (-number,0 if re.search(r'metric|result|analys|paired|selfcheck|verif',p.stem,re.I) else 1,path)
    def group(path):
        parts=Path(path).parts
        return parts[1] if parts[0]=='outputs' else parts[0]+'_reference'
    for path in sorted(candidates,key=rank):
        source=ROOT/path;data=source.read_bytes()
        if len(data)>8_000_000:skip(path,'oversize_aggregate');continue
        try:text=data.decode('utf-8-sig')
        except UnicodeDecodeError:skip(path,'not_utf8_aggregate');continue
        if SECRET.search(text):skip(path,'credential_pattern');continue
        redactions=Counter()
        try:
            if Path(path).suffix=='.json':
                value=clean_json(json.loads(text),counter=redactions)
            else:
                reader=csv.reader(io.StringIO(text));header=next(reader)
                if any(re.search(r'^(?:id|case_id|proposition_id|request_id|claim|text|reference|reason|note_id|body_sha256)$',h,re.I) for h in header):skip(path,'per_case_csv');continue
                rows=list(reader)
                if len(rows)>20000 or CLINICAL.search(text):skip(path,'large_or_clinical_csv');continue
                value={'columns':header,'rows':rows}
        except (ValueError,StopIteration,RecursionError):skip(path,'invalid_aggregate');continue
        record={'source_path':path,'source_sha256':sha(data),'reading_export_redactions':dict(redactions),'data':value}
        size=len(encoded(record))+1
        if total+sum(bundle_sizes.values())+size>90_000_000:skip(path,'aggregate_budget');continue
        g=group(path);bundles[g].append(record);bundle_sizes[g]+=size
        records.append({'source':path,'destination':f'reading_data/{g}.json','source_sha256':sha(data),'bytes_in_bundle':size,'transform':dict(redactions) or 'none'})
    for task,documents in sorted(bundles.items()):
        value={'task':task,'reading_export_not_original_freeze':True,'documents':documents}
        save(f'reading_data/{task}.json',encoded(value)+b'\n')
    guide=f'''# Research-VeriFact：信息扩展阅读镜像

这是提供给Gemini网页端的阅读快照，保留代码、协议、报告、论文稿、审计、汇总指标及图表；不是8文件简报。

源仓库：https://github.com/Nicoodoz/research-verifact
源HEAD：`{head}`；快照包含当前工作区尚未提交的文档更新。导出日期：2026-10-25。研究实际进度截止097，不据导出日期推断开展了新实验。

## 阅读顺序

1. [项目现状](docs/PROJECT_STATUS.md)、[工作约定](AGENTS.md)、[研究原则](docs/RESEARCH_EXECUTION.md)。
2. [前处理与推理汇报](docs/reports/2026-10-15_导师汇报_前处理与大模型推理.md)、`reading_data/docs_reference.json`内的F4离线复核。
3. 097、096、095、092、090、087、084、078、071、069、068、066的`outputs/.../report.md`及`tasks/.../protocol.md`。
4. [原论文/源码审读](docs/reading/01_原论文源码与路线审读.md)、[文献筛查](docs/reading/02_27项文献筛查.md)、`docs/sources/`中的作者代码。
5. `src/verifact_research/evaluation/`、009/008检索打包、051推理控制、071示例、078消融、092训练及095–097源码。
6. [全部任务索引](docs/TASK_INDEX.md)、`reading_data/`汇总、`reviews/`审计及原仓库[README](README_SOURCE.md)。

## 当前应当知道的事实

- 应用目标：患者EHR已知的整篇临床文档核验；目前医生GT评价仍是atomic claim级，不能声称整篇端到端验证已完成。
- 默认实现仍为C48 → V4 T-S thinking-high → Frozen PriorG，无示例B；用户目前聚焦前处理和原生推理，不将PriorG视为核心创新或已证实可跨Judge迁移的方法。
- raw verdict、自报分数最大类和最终标签分别报告；自报分数不是真实token概率。医生GT针对完整EHR，模型reference不是gold evidence。
- 全100患者均有历史研究暴露；旧reserved不是新holdout。本轮患者隔离不抹去历史开发暴露。
- 097同V4简洁接口有局部raw信号，12条同body重复变4条；源文依赖分支没有分类成绩。096 R1适配失败，不能归纳成所有R1流程的能力上限。085 Valdemardi正式实验已完成，旧AWS暂停不是当前状态。
- 067 v1不是保守增补；086归因有后续更正。原报告与更正均保留，不选择性抹掉失败记录。
- 1333条/30人的F4 raw汇总及166/340条累计对照来自后续本地零API复核，不是097的新预注册确认；1333混合历史选样，不能当独立自然测试。
- 固定四例并没有在大范围raw准确率上稳定超过原作者。小队列优势、错误支持减少、MCC改善和总体正确数必须同时解释。
- 只有用户明确要求时才提交或推送；本次用户明确授权发布此镜像，不自动授权后续实验、原仓库推送或默认系统升级。

## 文件和数据的组织

- 代码、Markdown、环境配置保留原相对路径；原README改名`README_SOURCE.md`，本文件为镜像入口。
- 汇总JSON及统计CSV按任务合并到`reading_data/<任务>.json`，每份原文件记录`source_path`及SHA。正文键值保持可读，删除的字段有`reading_export_omitted`标记；它们不是原始冻结manifest，不能据此通过历史重放校验。
- 文档病例章节、临床原文标记被移除；Python中少量临床示例字面量用占位符替代并记录SHA。此类文件仅供阅读，不声称与原程序执行等价。
- 不复制data/、.env、凭据、权重、API私有请求/回执、逐例JSONL及病历原文。统计图保留，论文全文PDF与扫描页不纳入；论文定位与源码审读保留。
- 旧协议和执行提示词是归档材料，不应自动执行其授权或旧TODO。当前状态高于归档导航；自检不冒充独立审计，模型解释不构成新医学GT。
- `MIRROR_MANIFEST.json`记录来源、变换及排除；`MIRROR_BUILD_REPORT.json`给出解压大小与文件数。小于100MB及5000文件不等于模型会一次读完；请按问题选读。

## 给Gemini的起始问题

请先阅读现状、规则、前处理/推理汇报和097报告，用不超过10行复述项目目标、数据暴露、主要已知结果及瓶颈，然后再回答我的研究问题。请引用任务号和文件路径，区分原生判断与后处理、开发汇总与独立评价、已实测与未启动分支；不要将Oracle成功当成可盲选证明，不要为正收益自动建议重启已失败版本。
'''
    save('README.md',guide.encode('utf-8'))
    save('00_START_HERE.md',guide.encode('utf-8'))
    manifest={'created_date':'2026-10-25','source_repository':'https://github.com/Nicoodoz/research-verifact','source_head':head,'source_status':[s for s in status if s],
              'source_snapshot_files':len(tree),'source_snapshot_bytes':sum(r['bytes'] for r in tree),'builder_sha256':sha(Path(__file__).read_bytes()),
              'selection':'Broad tracked text and numerical figures; root/analysis aggregate JSON and statistical CSV bundled per task; explicit maintained untracked documentation/builders only.',
              'records':records,'skipped_counts':dict(skips),'skipped_selected_details':details,
              'not_a_replay_repository':True,'no_new_model_calls':True,'original_repository_not_committed_or_pushed':True}
    save('MIRROR_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')+b'\n')
    # Scan every exported text, and independently total every path excluding Git metadata.
    files=[p for p in dest.rglob('*') if p.is_file() and '.git' not in p.relative_to(dest).parts]
    size=sum(p.stat().st_size for p in files)
    secret_hits=[];clinical_hits=[]
    for p in files:
        if p.suffix.lower()=='.png':continue
        s=p.read_text(encoding='utf-8-sig')
        if SECRET.search(s):secret_hits.append(p.relative_to(dest).as_posix())
        if CLINICAL.search(s):clinical_hits.append(p.relative_to(dest).as_posix())
    if secret_hits or clinical_hits:raise AssertionError({'secret_file_count':len(secret_hits),'clinical_marker_file_count':len(clinical_hits)})
    if size>=BYTE_LIMIT or len(files)+1>FILE_LIMIT:raise AssertionError(('Gemini limit guard',size,len(files)))
    stats={'source_head':head,'mirror_files':len(files)+1,'mirror_uncompressed_bytes_before_report':size,'text_and_figures_bytes':required_size,
           'source_documents_included':len(records),'aggregate_bundle_files':len(bundles),'aggregate_documents_included':sum(len(v) for v in bundles.values()),
           'source_transforms':sum(bool(r.get('transform') not in (None,'none')) for r in records),
           'secret_scan_hits':0,'clinical_marker_scan_hits':0,'size_limit_bytes':BYTE_LIMIT,'file_limit':FILE_LIMIT,'paid_API_calls':0,
           'source_index_untouched':True,'only_target_repository_to_be_pushed':True,'skipped_counts':dict(skips)}
    save('MIRROR_BUILD_REPORT.json',json.dumps(stats,ensure_ascii=False,indent=2).encode('utf-8')+b'\n')
    print(json.dumps(stats,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

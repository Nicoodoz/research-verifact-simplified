"""Build local Gemini reading exports; never stages, commits, pushes or calls an API."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LIMIT_BYTES = 90_000_000
LIMIT_FILES = 4500
TEXT_EXT = {'.md', '.py', '.ps1', '.yaml', '.yml', '.toml', '.rst'}
SECRET = re.compile(r'\bsk-(?:ws-)?[A-Za-z0-9._-]{24,}|\bAKIA[A-Z0-9]{16}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
CLINICAL = re.compile(r'\[\*\*[^\]\r\n]{3,}\*\*\]|\b21\d{2}[-/]\d{1,2}[-/]\d{1,2}\b')
CASE_HEADING = re.compile(r'病例|逐例|案例|case\s*(?:study|analysis|ledger|book)|representative\s+cases', re.I)
CASE_TABLE = re.compile(r'claim\s*(?:text|—|–|-)|proposition\s*text|命题原文|原文|引文|输出理由|病例|患者\s*(?:ID|编号|号)|subject_id', re.I)
CASE_ID = re.compile(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b|`[a-f0-9]{8}`', re.I)
QUICK_PROTOCOL_TASKS = {'009','051','066','068','069','071','078','084','090','092','095','096','097'}
QUICK_CODE = {
    'tasks/008_retrieval_planning/planning_core.py',
    'tasks/009_retrieval_baselines/retrieval_baseline.py',
    'tasks/009_retrieval_baselines/study009.py',
    'tasks/019_support_boundary_screen/common019.py',
    'tasks/051_thinking_mode_validation/common051.py',
    'tasks/071_judge_icl_feasibility/scan_examples071.py',
    'tasks/071_judge_icl_feasibility/analyze071.py',
    'tasks/078_component_ablation/common078.py',
    'tasks/078_component_ablation/analyze078.py',
    'tasks/092_task_adapted_verifier/model092.py',
    'tasks/092_task_adapted_verifier/train092.py',
    'tasks/092_task_adapted_verifier/folds092.py',
    'tasks/095_anchored_minimal_contrast/method095.py',
    'tasks/095_anchored_minimal_contrast/analyze_baseline095.py',
    'tasks/096_r1_native_priorg/common096.py',
    'tasks/096_r1_native_priorg/cached_bridge096.py',
    'tasks/097_native_judge_source_dependence/common097.py',
    'tasks/097_native_judge_source_dependence/analyze_a.py',
    'tasks/097_native_judge_source_dependence/audit_source_parent_b.py',
}


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def selected(path: str) -> bool:
    p = Path(path)
    parts = p.parts
    if not parts or p.name.startswith('.env'):
        return False
    if len(parts) == 1:
        return p.name in {'AGENTS.md','README.md','pyproject.toml'} or p.name.startswith('environment.')
    top = parts[0]
    if top in {'src','scripts','tasks','tests'}:
        return p.suffix.lower() in TEXT_EXT or p.name in {'LICENSE','requirements.txt'}
    if top == 'docs':
        if any(x in parts for x in ('history','maintenance')) or '执行提示词' in p.name:
            return False
        return p.suffix.lower() in TEXT_EXT or p.name in {'LICENSE','导师汇报_F4_raw复核.json'}
    if top == 'reviews':
        return p.suffix == '.md'
    if top == 'outputs':
        if not re.match(r'^\d{3}_', parts[1]) or any(x in parts for x in ('attempts','replays','synthetic_transport_tests')):
            return False
        name = p.name.lower()
        return (p.suffix == '.md' and (name in {'readme.md','current_status.md','evidence_map.md','audit_handoff.md','manuscript_implications.md','manuscript_zh.md'}
                or name.startswith('report') or name.endswith('tables.md') or 'correction' in name)
                and (name != 'manuscript_zh.md' or parts[1].startswith('095_')))
    return False


def redact_markdown(text: str) -> tuple[str, int]:
    lines = text.splitlines()
    output = []
    skipped = 0
    blocked_depth = None
    fence = False
    table_blocked = False
    i = 0
    while i < len(lines):
        line = lines[i]
        heading = re.match(r'^(#{1,6})\s+(.+)', line)
        if heading:
            depth = len(heading[1])
            if blocked_depth is not None and depth <= blocked_depth:
                blocked_depth = None
            if CASE_HEADING.search(heading[2]):
                blocked_depth = depth
        if blocked_depth is not None:
            skipped += 1
            i += 1
            continue
        if re.match(r'^\s*(?:```|~~~)', line):
            fence = not fence
            skipped += 1
            i += 1
            continue
        if fence or line.lstrip().startswith('>'):
            skipped += 1
            i += 1
            continue
        if line.lstrip().startswith('|'):
            if i == 0 or not lines[i-1].lstrip().startswith('|'):
                table_blocked = bool(CASE_TABLE.search(line))
            if table_blocked:
                skipped += 1
                i += 1
                continue
        else:
            table_blocked = False
        if CLINICAL.search(line) or CASE_ID.search(line):
            skipped += 1
        else:
            output.append(line)
        i += 1
    if skipped:
        output.insert(0, '> 阅读导出版：已省略病例段落、逐例标识、引用块和代码围栏；请用原仓库核查完整报告。\n')
    return '\n'.join(output).rstrip() + '\n', skipped


def code_section(path: str, text: str) -> str:
    ext = Path(path).suffix.lstrip('.') or 'text'
    return f'\n\n## SOURCE: {path}\n\n~~~~{ext}\n{text.rstrip()}\n~~~~\n'


def text_section(path: str, text: str) -> str:
    return f'\n\n---\n\n## SOURCE: {path}\n\n{text.rstrip()}\n'


def report_tables(text: str) -> str:
    """Keep complete tables with their headings and adjacent denominator context."""
    lines=text.splitlines()
    kept=[]
    intro=[]
    for block in text.split('\n\n'):
        if block and not block.startswith(('#','|','>')) and len(block)<1000:
            intro.append(block)
        if len(intro)==2:
            break
    kept.extend(intro)
    heading=''
    i=0
    while i<len(lines):
        if lines[i].startswith('#'):
            heading=lines[i]
        if lines[i].lstrip().startswith('|'):
            table=[]
            while i<len(lines) and lines[i].lstrip().startswith('|'):
                table.append(lines[i]);i+=1
            if heading:
                kept.append(heading)
            kept.append('\n'.join(table))
            continue
        i+=1
    return '\n\n'.join(kept)+'\n'


def zip_folder(folder: Path, target: Path) -> None:
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file():
                z.write(p, p.relative_to(folder).as_posix())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='outputs/replays/gemini_handoff_2026-10-25')
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    if not out.is_relative_to((ROOT / 'outputs/replays').resolve()):
        raise ValueError('Export must stay in the existing ignored outputs/replays directory')
    if out.exists():
        raise FileExistsError(f'Will not overwrite an existing export: {out}')
    head = git('rev-parse','HEAD').strip()
    status = git('status','--porcelain','-z').split('\0')
    tree = []
    for raw in git('ls-tree','-r','-l','-z','HEAD').split('\0'):
        if not raw:
            continue
        info, path = raw.split('\t',1)
        bits = info.split()
        if bits[1] == 'blob':
            tree.append(dict(path=path,bytes=int(bits[3])))
    categories = defaultdict(lambda:dict(files=0,bytes=0))
    for r in tree:
        c = categories[r['path'].split('/')[0]]
        c['files'] += 1
        c['bytes'] += r['bytes']
    candidates = sorted({r['path'] for r in tree if selected(r['path'])})
    # Explicitly include this session's new aggregate audit, never arbitrary untracked files.
    extra = 'docs/reports/导师汇报_F4_raw复核.json'
    if (ROOT / extra).is_file() and extra not in candidates:
        candidates.append(extra)
    code_folder = out / 'Research-VeriFact-Gemini-code'
    quick = out / 'Research-VeriFact-Gemini-8files'
    records, omitted, contents = [], [], {}
    for path in sorted(candidates):
        src = ROOT / path
        if not src.is_file():
            omitted.append(dict(path=path,reason='missing_worktree_file'))
            continue
        data = src.read_bytes()
        if len(data) > 2_000_000:
            omitted.append(dict(path=path,reason='single_text_file_over_2MB'))
            continue
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            omitted.append(dict(path=path,reason='not_utf8_text'))
            continue
        if SECRET.search(text):
            omitted.append(dict(path=path,reason='credential_pattern_not_exported'))
            continue
        removed = 0
        if src.suffix == '.md':
            text, removed = redact_markdown(text)
        elif CLINICAL.search(text):
            omitted.append(dict(path=path,reason='clinical_text_marker_not_exported'))
            continue
        if SECRET.search(text) or CLINICAL.search(text):
            raise AssertionError('Redaction did not remove a blocked marker')
        exported = text.encode('utf-8')
        write(code_folder/path,text)
        records.append(dict(path=path,source_sha256=digest(data),export_sha256=digest(exported),source_bytes=len(data),export_bytes=len(exported),redacted_lines=removed))
        contents[path] = text
    guide = f'''# Research-VeriFact：Gemini阅读入口

生成日期：2026-10-25；源HEAD：`{head}`。资料截止097，不能按包的生成日期推断开展了新实验。

## 先理解这六件事

1. 目标：用已知患者EHR核验临床文档。当前实测单位为医生标注atomic claim，整篇文档核验尚未完成端到端验证。
2. 当前实现：C48 → DeepSeek V4 T-S thinking-high → Frozen PriorG，无示例B。用户希望研究重点放在前处理与推理；不把PriorG当核心创新或已证实跨Judge可迁移的方法。
3. C48先召回48候选，再按约束选最多16段、约8000字符；F4是其他患者的固定四个医生示例。raw标签、分数最大类和最终系统标签必须分开。
4. 100患者全部已有研究暴露。历史reserved不能再称未见测试；本轮患者隔离不抹去历史暴露。医生GT针对完整EHR，检索包不是gold evidence。
5. 097同V4简洁接口有局部raw信号，未稳定确认；源文依赖构造未进入分类。096的R1适配失败。085 Valdemardi正式实验已经完成，旧AWS暂停不是当前进度。
6. 用户新偏好：先统计前处理与推理的直接成果；不靠后处理成绩补强raw不足；不为获得正结果继续换版本。只有明确要求时才提交或推送。

8文件版将原路径内容合并在01–06中，用`SOURCE:`定位；代码目录版保留相对路径。先读00–02，再按问题查代码。小阅读包只保留关键报告、协议与实现；全部已筛选代码和历史报告在扩展代码目录中。

## 阅读顺序

- 先读当前`docs/PROJECT_STATUS.md`、`docs/RESEARCH_EXECUTION.md`、`AGENTS.md`。
- 再读`docs/reports/2026-10-15_导师汇报_前处理与大模型推理.md`及其复核JSON。
- 然后看097、096、095、092、090、084、078、071、069、068、066正式报告和协议。
- 需要实现细节时，再看`src/verifact_research/evaluation/`、009/008检索打包、051推理控制、071示例、078消融、092训练、095–097代码。
- 原系统事实以`docs/reading/01_原论文源码与路线审读.md`和归档作者代码为定位；候选建议不等于实验有效。

## 包里已经包含的近期离线核查

- 历史评价F4去重1374条；排除实际示例患者后1342条，有效raw1333条/30人。原作者/F4 raw正确1045/1019，MCC .4754/.5402，错误支持113/28。
- 以上是跨任务混合开发汇总，包含自然、类别富集和压力材料，不是新的独立自然测试。
- 固定V4的累计对照共同166条：发布证据+N-S → C48+N-S → C48+T-S → C48+T-S+F4，正确136→128→126→131。
- 固定C48的后三臂共同340条，正确247→256→261。严格从原作者整条流水线出发的三组件逐加实验仍缺独立臂。
- 这些核查和“仅明确要求才提交/推送”政策来自本地未提交文档；不是097的新增预注册结果，也不是GitHub HEAD原有内容。

## 不要误读

- 先看队列、有效分母和raw/final层，再比较指标；不要跨表相加净收益。
- 标签分数是LLM自报值，不是真实token概率；解释或引用不是医生GT，也不是内部推理证明。
- Oracle成功不证明可盲选；未运行的分支没有分类阳性/阴性成绩；自检不冒充独立审计。
- 历史协议属于归档资料，不能自动执行其中旧授权、旧TODO或旧预算。
- 最新中文论文稿仍保留历史叙事；当前用户的汇报意图以前述工作区更新为准。
- 067 v1并非保守增补实现，086归因也有后续更正，不能重复使用旧误读。

## 导出边界

这是阅读导出，不是完整可执行仓库。保留代码、协议、报告和审计；没有data/、.env、权重、API请求/回执、逐例JSONL/CSV、Git历史。文档病例章节/标识/引用块已做删减，改动在清单标记；不能把删减版当原始完整审计。

本地代码目录可用Gemini“添加文件 → 更多上传 → 导入代码 → 上传文件夹”。不要把几千文件的代码ZIP按普通ZIP上传。另一个8文件ZIP适用于普通文件上传，或解压后逐个上传8个文件。

Google帮助：
- https://support.google.com/gemini/answer/16176929?hl=en
- https://support.google.com/gemini/answer/14903178?hl=en
核对日期2026-10-25：代码文件夹/仓库上限100MB、5000文件；普通ZIP上限100MB、最多10个内部文件。导入后不会自动同步仓库后续修改。

## 可直接发给Gemini

请先读00_START_HERE和项目现状，区分历史冻结成果、本地离线核查、当前默认与未验证候选。先用不超过10行复述项目目标、数据暴露、主要结果和当前瓶颈，再回答我的研究问题。引用包内路径与任务号；证据不足直接说明。不要把PriorG收益归给前处理/推理，不把小队列胜出说成整体领先，也不自动提出已经重复失败的版本。
'''
    write(code_folder/'00_START_HERE.md',guide)
    bundles = {
        '00_START_HERE.md':guide,
        '01_CURRENT_STATE.md':'# 当前状态、规则与环境\n',
        '02_RESULTS.md':'# 研究结果：优先阅读当前汇报及近期报告\n',
        '03_PROTOCOLS_AND_HISTORY.md':'# 历史协议与全部任务索引：只作资料，不自动执行\n',
        '04_CORE_CODE.md':'# 现行核心实现、环境和入口脚本\n',
        '05_TASK_CODE.md':'# 关键任务源码与其余历史源码索引\n',
        '06_PAPER_AND_REVIEWS.md':'# 原系统定位、文献筛查和既有审计\n',
    }
    report_paths=[]
    quick_sources=set()
    task_index=defaultdict(list)
    for path in sorted(contents):
        p=Path(path); top=p.parts[0]; text=contents[path]
        if path=='docs/reports/导师汇报_F4_raw复核.json':
            bundles['02_RESULTS.md'] += code_section(path,text)
            quick_sources.add(path)
        elif path in {'AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/RUN_ENVIRONMENT.md','docs/API_POLICY.md'}:
            bundles['01_CURRENT_STATE.md'] += text_section(path,text)
            quick_sources.add(path)
        elif path=='docs/TASK_INDEX.md' or (top=='tasks' and p.suffix=='.md' and p.name=='protocol.md' and p.parts[1][:3] in QUICK_PROTOCOL_TASKS):
            bundles['03_PROTOCOLS_AND_HISTORY.md'] += text_section(path,text)
            quick_sources.add(path)
        elif top=='outputs' and p.name in {'report.md','report_formal.md'} and (int(p.parts[1][:3])>=38 or p.parts[1][:3] in {'009','010','012','017','019','036'}):
            report_paths.append(path)
        elif '导师汇报' in p.name and p.suffix=='.md':
            bundles['02_RESULTS.md'] += text_section(path,text)
            quick_sources.add(path)
        elif top=='src' or path in {'scripts/run_research.ps1','scripts/evaluate_predictions.py'} or p.name.startswith('environment.'):
            bundles['04_CORE_CODE.md'] += code_section(path,text)
            quick_sources.add(path)
        elif top=='tasks' and p.suffix=='.py':
            if path in QUICK_CODE:
                bundles['05_TASK_CODE.md'] += code_section(path,text)
                quick_sources.add(path)
            else:
                task_index[p.parts[1]].append(p.name)
        elif path in {'docs/reading/01_原论文源码与路线审读.md','docs/reading/02_27项文献筛查.md','reviews/095_anchored_minimal_contrast/final_review.md'}:
            bundles['06_PAPER_AND_REVIEWS.md'] += code_section(path,text) if p.suffix=='.py' else text_section(path,text)
            quick_sources.add(path)
    bundles['05_TASK_CODE.md'] += '\n\n## 其余源码：扩展代码目录中的任务索引\n\n'
    for task,names in sorted(task_index.items()):
        bundles['05_TASK_CODE.md'] += f'- `tasks/{task}/`：{len(names)}个其余源码文件。\n'
    # Newest first; all selected old reports remain available in the source folder.
    for path in sorted(report_paths,reverse=True):
        bundles['02_RESULTS.md'] += text_section(path,report_tables(contents[path]))
        quick_sources.add(path)
    for name,text in bundles.items():
        write(quick/name,text)
    manifest=dict(created_date='2026-10-25',source_head=head,working_tree_status=[x for x in status if x],
                  snapshot_files=len(tree),snapshot_bytes=sum(r['bytes'] for r in tree),snapshot_categories=dict(categories),
                  limits=dict(uncompressed_bytes=LIMIT_BYTES,code_files=LIMIT_FILES,quick_files=8),
                  selection='tracked text whitelist + explicit local aggregate audit; worktree versions; no arbitrary untracked files',
                  exclusions=['data','credentials','Git history','weights','raw request/response artifacts','per-case JSONL/CSV','binary/PDF files','old navigation snapshots'],
                  included_sources=records,omitted_selected_sources=omitted,
                  redaction='markdown case sections, code fences, quote blocks, case tables/identifiers and clinical markers removed; code with clinical markers omitted',
                  quick_documents=[dict(path=k,bytes=len(v.encode('utf-8')),sha256=digest(v.encode('utf-8'))) for k,v in bundles.items()])
    manifest_text=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    quick_manifest={k:v for k,v in manifest.items() if k not in {'included_sources','working_tree_status'}}
    quick_manifest['included_sources']=[r for r in records if r['path'] in quick_sources]
    quick_manifest['quick_transform']='Full current docs and selected code; reports retain first two short introductory paragraphs and complete tables; full sanitized reports remain in extended folder.'
    quick_manifest['full_source_manifest']='Research-VeriFact-Gemini-code/EXPORT_MANIFEST.json'
    write(quick/'07_MANIFEST.json',json.dumps(quick_manifest,ensure_ascii=False,indent=2)+'\n')
    write(code_folder/'EXPORT_MANIFEST.json',manifest_text)
    stats={}
    for name,folder in [('code_folder',code_folder),('quick',quick)]:
        files=[p for p in folder.rglob('*') if p.is_file()]
        size=sum(p.stat().st_size for p in files)
        assert len(files)<=LIMIT_FILES and size<LIMIT_BYTES,(name,len(files),size)
        assert not any(p.name.startswith('.env') for p in files)
        for p in files:
            if SECRET.search(p.read_text(encoding='utf-8')):
                raise AssertionError('Blocked credential pattern in export')
        stats[name]=dict(path=str(folder),files=len(files),bytes=size)
    assert stats['quick']['files']==8
    zip_folder(quick,out/'Research-VeriFact-Gemini-8files.zip')
    zip_folder(code_folder,out/'Research-VeriFact-Gemini-code.zip')
    for name in ('Research-VeriFact-Gemini-8files.zip','Research-VeriFact-Gemini-code.zip'):
        with zipfile.ZipFile(out/name) as z:
            assert z.testzip() is None
            assert sum(i.file_size for i in z.infolist())<LIMIT_BYTES
    stats.update(source_head=head,source_snapshot_MB=round(sum(r['bytes'] for r in tree)/1e6,3),
                 source_files=len(tree),included_sources=len(records),omitted_candidates=len(omitted),
                 redacted_documents=sum(r['redacted_lines']>0 for r in records),
                 quick_zip_bytes=(out/'Research-VeriFact-Gemini-8files.zip').stat().st_size,
                 code_zip_bytes=(out/'Research-VeriFact-Gemini-code.zip').stat().st_size,
                 commits=0,pushes=0,paid_API_calls=0)
    write(out/'BUILD_REPORT.json',json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    write(out/'使用说明.md',guide+'\n\n## 实际大小\n\n```json\n'+json.dumps(stats,ensure_ascii=False,indent=2)+'\n```\n')
    print(json.dumps(stats,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

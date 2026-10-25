"""Record the tested replay-only revision without rewriting historical audits."""
from datetime import datetime,timezone
import difflib
import subprocess
import study009 as s


def append_preserving_bytes(path,text):
    raw=path.read_bytes()
    nl='\r\n' if b'\r\n' in raw else '\n'
    path.write_bytes(raw+text.replace('\n',nl).encode('utf-8'))


if __name__=='__main__':
    out=s.OUT/'revision_001'
    assert not (out/'handoff.json').exists()
    v=s.read_json(out/'verification_001/verification.json')
    assert v['tests']['success'] and v['tests']['run']==146
    assert 'reviews/README.md' in v['tracked_changes']
    assert sum(len(x) for x in v['byte_identical_replays'].values())==109
    before=s.read_json(out/'before.json')
    for name,digest in before['preserved_review_files'].items():
        assert s.pilot.digest_file(s.ROOT/name)==digest,'Existing audit content changed: '+name
    assert s.pilot.digest_file(s.OUT/'handoff_001.json')==before['original_handoff_sha256']
    append_preserving_bytes(s.TASK/'README.md','\n## 009 审计后的重放修订\n\n审计指出的工作区文件白名单阻塞已作执行修订，待定向独立复核。Git变更仅作为诊断信息；冻结实验材料继续严格校验，旧自查程序版本单列来源记录。当前146项断网测试通过，109个内容文件重放不变，无API调用。修订说明与实际版本见[revision_001](../../outputs/009_retrieval_baselines/revision_001/README.md)。此前143项测试、原交审清单和独立审计意见保持历史记录。\n')
    append_preserving_bytes(s.OUT/'README.md','\n## 当前重放修订入口\n\n009独立审计最终意见为有条件通过，原文及末尾追加保持不变。针对正常审计索引更新阻塞重放的问题，执行修订已完成，等待定向复核。请审阅[revision_001修订说明](revision_001/README.md)及[最新被审版本](revision_001/handoff.json)；上表handoff_001为历史首次交审版本。原主报告、预测、指标和费用均未修改，本次没有API调用。\n')
    readme='''# 009 重放入口修订：等待独立复核

**已修复正常修改审计索引导致重放失败的问题。** 只改重放检查及其回归测试，没有修改实验、原回答、指标或费用，也没有调用API。独立审计的原“有条件通过”及必须修正意见保留，由审计模型定向复核后决定是否关闭。

## 改了什么

- 删除末尾针对全仓库未提交路径的白名单断言。`git_head`与`tracked_changes`仍记录，但不据此阻断重放；无关工作区文件同样仅为诊断。是否拒绝由冻结输入、配置、实际计算代码、回执和输出指纹决定，不扩充一串允许修改的文档名单。
- 历史自查manifest中的`verify009.py`是当时验证程序版本，现按历史来源记录旧/新SHA及是否匹配。仅此一项、且仅自查产物的代码来源绑定作信息处理；该manifest内结果文件、全部依赖、其他计算代码仍严格检查。非自查实验manifest的任何代码绑定仍拒绝差异。原程序字节另保存在[original_verify009.py.txt](original_verify009.py.txt)，原manifest不回写。
- 新增3项回归测试：正常审计/无关工作区变化可记录；历史验证程序可升级但冻结输入/回执/输出/配置/计算代码/自查结果遭修改仍拒绝；实验manifest的程序绑定不能套用此例外。

没有处理本审计的非阻塞建议（干预控制、rerank token汇总），也未改变研究方案或指标解释。

## 实际验证

使用当前真实工作区直接运行正式入口，**没有提交或撤销`reviews/README.md`的修改，没有绕过输出位置检查或其他校验**：

```powershell
python -B tasks/009_retrieval_baselines/verify009.py --output outputs/009_retrieval_baselines/revision_001/verification_001
```

- 新目录的[verification.json](verification_001/verification.json)与manifest完整生成；`tracked_changes`实际包含AGENTS.md、README.md、reviews/README.md。
- **146项断网测试全部通过**，含3项新增回归；6种冻结材料篡改在隔离临时文件上均被拒绝。见[tests.log](verification_001/tests.log)。
- 两队列语料、向量、排名、候选、真实重排分数、reference/body与缓存核查通过。开发/确认评分、53条件诊断、案例渲染及汇总共**109个内容文件逐字节一致**；覆盖原预测、分母、指标、费用及案例材料。
- API原费用仍为¥18.08218167，provider token记录与原自查CSV逐字节一致。本次无推理调用、无密钥读取、无新增患者或reserved test查看。
- 原主报告、论文底稿、历史run/manifest、首次handoff及全部审计文件指纹保持；修改范围和其余历史文件检查见[revision_checks.json](revision_checks.json)。

## 给审计模型的版本

基础分支`main`，HEAD与本次fetch后的origin/main均为`42d28c4909b901056207c6770e1be733998123cf`，未提交/推送。实际被审版本为该HEAD加[handoff.json](handoff.json)清单中的工作区文件；它包含本次修订、已有009成果及原审计材料的当前指纹。首次handoff_001仍保存旧版本，不应要求它与已修订程序匹配。

重点检查[verify009.py](../../../tasks/009_retrieval_baselines/verify009.py)、[新增测试](../../../tests/test_retrieval_replay_guard.py)、[程序差异](verify009.diff)及本目录verification。复核可用同一命令换一个不存在的输出目录；程序不会调用API。新增的自查/修订文档不是独立审计结论。

执行修订完成，等待独立复核；交回后停止编辑同批成果。
'''
    (out/'README.md').write_text(readme,encoding='utf-8')
    original=(out/'original_verify009.py.txt').read_text(encoding='utf-8').splitlines()
    revised=(s.TASK/'verify009.py').read_text(encoding='utf-8').splitlines()
    (out/'verify009.diff').write_text('\n'.join(difflib.unified_diff(original,revised,fromfile='original/verify009.py',tofile='current/verify009.py',lineterm=''))+'\n',encoding='utf-8')
    old=s.read_json(s.OUT/'handoff_001.json')
    changed=[name for name,digest in old['files'].items() if s.pilot.digest_file(s.ROOT/name)!=digest]
    assert set(changed)=={'tasks/009_retrieval_baselines/verify009.py','tasks/009_retrieval_baselines/README.md','outputs/009_retrieval_baselines/README.md'}
    assert (out/'verification_001/provider_token_accounting.csv').read_bytes()==(s.OUT/'verification_001/provider_token_accounting.csv').read_bytes()
    raw_old=(out/'original_verify009.py.txt').read_bytes()
    raw_new=(s.TASK/'verify009.py').read_bytes()
    assert (b'\r\n' in raw_old)==(b'\r\n' in raw_new)
    s.pilot.write_json(out/'revision_checks.json',dict(original_inventory_files=len(old['files']),original_files_changed=changed,
        original_files_unchanged=len(old['files'])-len(changed),preserved_audit_files=len(before['preserved_review_files']),
        original_report_and_paper_unchanged=True,provider_token_csv_byte_identical=True,tests=146,replay_files_identical=109,
        original_line_endings_preserved=True,new_api_calls=0,independent_audit='pending'))
    git=lambda *args:subprocess.check_output(['git',*args],cwd=s.ROOT,text=True).strip()
    assert git('rev-parse','HEAD')==git('rev-parse','origin/main')==s.BASE_HEAD
    files=[s.ROOT/name for name in old['files']]+[s.ROOT/name for name in before['preserved_review_files']]
    files += [p for base in (s.TASK,s.OUT) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files.append(s.ROOT/'tests/test_retrieval_replay_guard.py')
    hashes={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in sorted(set(files))}
    s.pilot.write_json(out/'handoff.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),branch=git('branch','--show-current'),head=s.BASE_HEAD,
        origin_main=git('rev-parse','origin/main'),working_tree_status=git('status','--short'),
        actual_version='HEAD plus listed uncommitted files; historical handoff_001 retained',files=hashes,inventory_sha256=s.pilot.fingerprint(hashes),
        handoff_excludes_itself=True,independent_audit='pending',new_api_calls=0))
    assert all(s.pilot.digest_file(s.ROOT/name)==digest for name,digest in hashes.items())
    print(s.pilot.canonical(dict(status='execution_revision_complete_pending_independent_review',files=len(hashes),inventory_sha256=s.pilot.fingerprint(hashes),historical_files_changed=changed)))

"""Finalize concise interpretation and check mutable documentation, no API."""
import json,collections,subprocess,hashlib,ast
from materials073 import ROOT,OUT,read,lines,sha,put
from update_status073 import rewrite
import run073 as r
def main():
 a,answers=r.attempt_state();status=collections.Counter(x['parsed']['status'] for x in answers.values())
 valid=sum(status[k] for k in r.c53.VALID)
 old='295个成功回答、成功同体不重复'
 new=f'295/295 HTTP200（{valid}核心有效），成功同体不重复'
 for name in ['README.md','AGENTS.md','docs/PROJECT_STATUS.md','outputs/073_clinical_example_matching/README.md','outputs/073_clinical_example_matching/CURRENT_STATUS.md','tasks/073_clinical_example_matching/CURRENT_STATUS.md']:
  rewrite(ROOT/name,lambda t:t.replace(old,new))
 p=OUT/'report.md';text=p.read_text(encoding='utf-8')
 intro='''
**结论：停止当前动态匹配版本，也不升级静态F4，默认保留无示例B。** 修掉D4的泛词/回退退化，没有转化为超过静态示例的性能。F4在另一批60条新命题上最终净收益0，错误支持增加2条，未通过事前确认门槛。

- 探索36条：B/F4/D4/L4/M4最终正确31/33/30/31/31。F4净+2中1条来自输出截断后的旧U2回退；只看共同核心有效34条，F4净+1。L4/M4均较D4净+1，但相对B净0、相对F4净−2；两动态方案没有进入60条确认，不能称其已在确认集失败。
- 确认60条：B/F4最终49/49，MCC 0.6698/0.6419，false-S 1/3；2救回、2伤害。raw为46/47，只有净+1（MCC差的患者区间跨0），没有支持继续延长本路线的足够收益。
- 确认按GT类别正确：S 35→36/40、NS 9→7/10、NA 5→6/10。收益并非完全没有，但NS损失抵消了其他收益。10名患者的最终净正确数都为0，因此PA的患者bootstrap区间机械地为[0,0]；这不证明调用稳定。
- F4平均输入比B多5638 token（3161→8799），按同一保守价格每次平均费用约0.02665→0.04124元，约增加55%。没有用满20元预算来继续追逐小信号。

病例拆分见[探索病例说明](pilot_case_notes.md)、[全部救回/伤害](transition_diagnostics.jsonl)、[去除核心无效的敏感性分析](core_valid_sensitivity.json)。本轮的负面结论来自完整配对结果，不是因为没有重复成功调用。
'''
 text=text.replace('# 073 临床核验教学示例匹配：实验报告\n','# 073 临床核验教学示例匹配：实验报告\n'+intro,1)
 text=text.replace('教学24人和评价16人隔离','教学可用患者24人（示例实际来自14人）和评价16人隔离')
 text=text.replace('分别报告作者类别。','分别报告作者类别。')
 text=text.replace('S/NS/NA=65/16/15；','S/NS/NA=65/16/15；其中LLM为47S/1NS，human为18S/15NS/15NA，')
 text=text.replace('成功回答295','HTTP200回执295（293核心有效，2核心无效）')
 p.write_text(text,encoding='utf-8',newline='\n')
 # Preserve the initial verification artifact and add end-of-task checks.
 for stage in ['pilot','confirmation']:r.check_frozen(stage)
 assert not (OUT/'run.lock').exists()
 assert len(a)==295 and len(answers)==295 and valid==293
 assert sha(ROOT/'tasks/073_clinical_example_matching/decide073.py')==read(OUT/'decision_policy_binding.json')['decision_code_sha256']
 for p in (ROOT/'tasks/073_clinical_example_matching').glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
 changed=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines()
 assert set(changed)<= {'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md'},changed
 put(OUT/'closure_checks.json',dict(status='PASS',created_utc=r.now(),HTTP200=295,core_valid=valid,parsed_status=dict(status),historical_tracked_files_changed=False,gitignore_changed=False,mutable_docs_changed=changed,live_lock=False,decision_policy_hash_verified=True,new_paid_calls_after_confirmation=0))
 files=[p for folder in [OUT,ROOT/'tasks/073_clinical_example_matching'] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 put(OUT/'manifest.json',dict(created_utc=r.now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files={p.relative_to(ROOT).as_posix():sha(p) for p in files},raw_data_and_historical_runs='not modified',independent_audit='not performed'))
 print(json.dumps(dict(status='PASS',HTTP200=295,core_valid=valid,tracked_changes=changed,manifest_files=len(files)),ensure_ascii=False))
if __name__=='__main__':main()

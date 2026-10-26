"""Offline final delivery and current navigation; never starts paid work or Git."""
from pathlib import Path
import json,subprocess,sys
import common100 as c

def write_preserving(p,text):
 b=p.read_bytes();bom=b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'';eol='\r\n' if b'\r\n' in b else '\n';p.write_bytes(bom+text.replace('\r\n','\n').replace('\n',eol).encode())
def line_replace(rel,predicate,new):
 p=c.ROOT/rel;text=p.read_text(encoding='utf-8-sig');rows=text.splitlines();found=[i for i,line in enumerate(rows) if predicate(line)];assert len(found)==1,(rel,found);rows[found[0]]=new;write_preserving(p,'\n'.join(rows)+'\n')
def run(name):subprocess.run([sys.executable,'-B',str(c.TASK/name)],cwd=c.ROOT,check=True)
def main():
 assert not (c.PRIVATE/'run.lock').exists()
 branch=c.read(c.OUT/'branch_decision.json')
 if branch['branch']=='evidence':
  dev=c.read(c.OUT/'development_decision.json')
  if dev['winner'] is not None:assert (c.OUT/'confirmation_decision.json').exists()
 else:assert (c.OUT/'confirmation_decision.json').exists()
 for name in ['material_summary100.py','error_analysis100.py','detailed_tables100.py','report100.py','selfcheck100.py']:run(name)
 report=c.read(c.OUT/'report_content.json');status=report['status'];cost=c.read(c.OUT/'cost_ledger.json');d98=c.read(c.ROOT/'outputs/098_p90_native_confirmation/decision.json');a98=c.read(c.ROOT/'outputs/098_p90_native_confirmation/analysis.json')['panels']['natural']['tables']
 c.put(c.OUT/'complete.json',dict(utc=c.utc(),status='COMPLETE',scientific_status=status,report_sha256=c.sha(c.OUT/'report.md'),night_summary_sha256=c.sha(c.OUT/'night_summary.md'),selfcheck_sha256=c.sha(c.OUT/'selfcheck.json'),
   total_new_API_or_reserved_cny=cost['total_new_cost_or_reserved_cny'],default_changed=False,independent_audit=False,Git_publication_separately_authorized_after_completion=True))
 summary=f"098已完整收尾：2120目标+2构造，P未通过对O/Q/C的继续/实用门槛，停止该版本。100按既定证据分支完成，最终为{status}；开发48自然+24压力，确认预冻192自然+32压力、重复16，实际执行范围见报告。新API累计及预留¥{cost['total_new_cost_or_reserved_cny']:.6f}/130；旧098成本不重置，其累计仍≤50。默认不变。[今晚一页结论](../outputs/100_preregistered_followup/night_summary.md) · [100报告](../outputs/100_preregistered_followup/report.md) · [098报告](../outputs/098_p90_native_confirmation/report.md)。"
 line_replace('docs/PROJECT_STATUS.md',lambda s:s.startswith('# 项目现状'),'# 项目现状（2026-10-27，098—100已结项）')
 line_replace('docs/PROJECT_STATUS.md',lambda s:s.startswith('097与099选型已完成；') or s.startswith('098已完整收尾：'),summary)
 line_replace('docs/PROJECT_STATUS.md',lambda s:s.startswith('099已完成四种Qwen Judge选型：'),'099四种Qwen Judge选型已完成；原推荐qwen3.5-35b-a3b、备选qwen3.5-27b保持原结论，不据100改变排名，不自动升级默认。[099报告](../outputs/099_judge_selection/report.md)。')
 line_replace('README.md',lambda s:s.startswith('临床文本与患者EHR的一致性核验研究。'),f'临床文本与患者EHR的一致性核验研究。098—100已完整结项；098 P90停止，100最终：**{status}**。默认系统不变。[今晚一页结论](outputs/100_preregistered_followup/night_summary.md) · [100报告](outputs/100_preregistered_followup/report.md)。')
 line_replace('README.md',lambda s:s.startswith('最接近同模型公平比较的是097'), '最新同模型患者隔离确认见[100一页结论](outputs/100_preregistered_followup/night_summary.md)；结论为失败停止。下面097表只保留此前强对照背景，共同158条：')
 line_replace('AGENTS.md',lambda s:s.startswith('- 097与099已完成，'),'- 098—100已结项；100是明确授权的098收尾及单一后续分支，原始GT、默认系统和099选型未改变。正式结果、费用与限制以[PROJECT_STATUS](docs/PROJECT_STATUS.md)和对应报告为准，不在规则文件重复维护整套数值。')
 line_replace('docs/TASK_INDEX.md',lambda s:s.startswith('# 全部任务与当前入口'),'# 全部任务与当前入口（研究完成至100；2026-10-27）')
 line_replace('docs/TASK_INDEX.md',lambda s:s.startswith('|098_p90_native_confirmation|'),'|098_p90_native_confirmation|[正式报告](../outputs/098_p90_native_confirmation/report.md) · [主表](../outputs/098_p90_native_confirmation/main_table.csv)|[执行者自检](../outputs/098_p90_native_confirmation/selfcheck.json)，独立审计未执行|全部冻结请求完成；P对O/Q/C均未达门槛，压力/重复亦有失败，停止本版|')
 p=c.ROOT/'docs/TASK_INDEX.md';t=p.read_text(encoding='utf-8-sig');row=f"|100_preregistered_followup|[一页结论](../outputs/100_preregistered_followup/night_summary.md) · [正式报告](../outputs/100_preregistered_followup/report.md)|[执行者自检](../outputs/100_preregistered_followup/selfcheck.json)，独立审计未执行|{status}；32患者隔离确认，未升级默认，不自动新实验|\n"
 if '|100_preregistered_followup|' not in t:write_preserving(p,t.replace('|099_judge_selection|',row+'|099_judge_selection|',1))
 # Prevent future Windows checkout from rewriting the newly frozen source bytes.
 p=c.ROOT/'.gitattributes';t=p.read_text(encoding='utf-8-sig');added='\n# Preserve frozen098-100 source bytes across checkout (2026-10-27).\ntasks/098_p90_native_confirmation/** -text\ntasks/099_judge_selection/** -text\ntasks/100_preregistered_followup/** -text\n'
 if 'tasks/100_preregistered_followup/** -text' not in t:write_preserving(p,t.rstrip('\n')+'\n'+added)
 oldstatus=c.ROOT/'.local_models/098_p90_native_confirmation/background_status.json';backup=c.PRIVATE/'background_status_before_completed.json'
 if oldstatus.exists() and not backup.exists():backup.write_bytes(oldstatus.read_bytes())
 oldstatus.write_bytes((json.dumps(dict(status='COMPLETE',updated_utc=c.utc(),completed_via='100 handoff',complete_artifact='outputs/098_p90_native_confirmation/complete.json',no_pending_target_requests=True),ensure_ascii=False,indent=2)+'\n').encode())
 command="Get-ScheduledTask -TaskName 'Research-VeriFact-098-Resume' -ErrorAction SilentlyContinue | Disable-ScheduledTask | Select-Object TaskName,State"
 result=subprocess.run(['pwsh','-NoProfile','-Command',command],capture_output=True,text=True);assert result.returncode==0,result.stderr
 c.put(c.OUT/'operational_completion.json',dict(utc=c.utc(),task098_complete=True,old_scheduler_disabled=True,no_GPU=True,no_API_in_finalization=True,default_unchanged=True,Git_publication_pending=True))
 print(c.canonical(dict(complete=True,status=status,total_new_cny=cost['total_new_cost_or_reserved_cny'],ready_for_authorized_publication=True)))
if __name__=='__main__':main()

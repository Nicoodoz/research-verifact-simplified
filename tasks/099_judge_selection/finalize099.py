"""Presentation clarification and navigation only; never sends API requests."""
import common099 as c
import report099

def edit(rel,old,new):
    p=c.ROOT/rel
    raw=p.read_bytes();bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text=raw[len(bom):].decode('utf-8');eol='\r\n' if '\r\n' in text else '\n'
    normalized=text.replace('\r\n','\n')
    if new in normalized:return
    assert normalized.count(old)==1,rel
    p.write_bytes(bom+normalized.replace(old,new,1).replace('\n',eol).encode('utf-8'))

def main():
    marker=c.OUT/'presentation_clarification.json'
    if marker.exists():return
    s=c.read(c.OUT/'selection.json');cost=c.read(c.OUT/'cost_ledger.json')
    frozen={name:c.sha(c.OUT/name) for name in ['analysis.json','predictions.jsonl','selection.json','cost_ledger.json','attempt_ledger.jsonl','usage.jsonl']}
    history=c.PRIVATE/'presentation_history';history.mkdir(exist_ok=True)
    before={}
    for name in ['report.md','selfcheck.json']:
        p=c.OUT/name;backup=history/name
        if not backup.exists():backup.write_bytes(p.read_bytes())
        before[name]=c.sha(backup)
        if p.exists():p.unlink()
    report099.main()
    summary=f"099已完成四种Qwen Judge选型：608 HTTP200、0重试，目录价¥{cost['used_or_reserved_cny']:.6f}/20；主候选{s['primary']}、备选{s['backup']}。原reference自然共同78条，主候选MCC0.5225、PA79.49%、false-S2/19；诊断与C48存在代价，不能主张全面更安全。默认未修改，098独立按原冻结执行。"
    edit('docs/PROJECT_STATUS.md','# 项目现状（2026-10-26，研究完成至097）','# 项目现状（2026-10-26，097与099已完成，098独立执行）')
    edit('docs/PROJECT_STATUS.md','## 最近结果与可主张范围','## 最近结果与可主张范围\n\n'+summary+'[099正式报告](../outputs/099_judge_selection/report.md) · [费用](../outputs/099_judge_selection/cost_ledger.json) · [A800桥接方案](../outputs/099_judge_selection/A800_bridge_plan.md)。')
    edit('docs/TASK_INDEX.md','# 全部任务与当前入口（研究截至097，文档核对2026-10-26）','# 全部任务与当前入口（097与099完成，098独立执行；2026-10-26）')
    edit('docs/TASK_INDEX.md','|098_p90_native_confirmation|','|099_judge_selection|[正式报告](../outputs/099_judge_selection/report.md) · [费用](../outputs/099_judge_selection/cost_ledger.json)|[执行者自检](../outputs/099_judge_selection/selfcheck.json)，独立审计未执行|四模型608 HTTP200；主35B-A3B、备27B，O优先但诊断/C48有代价；默认与098不变|\n|098_p90_native_confirmation|')
    edit('README.md','研究实验已完成至 **097**；','097与099选型已完成；[099推荐与限制](outputs/099_judge_selection/report.md)（主qwen3.5-35b-a3b、备qwen3.5-27b；默认不变）。')
    edit('AGENTS.md','- 研究完成至097；098已获2026-10-26用户正式授权并启动，尚无完整结论。正式结果、费用与限制以','- 097与099已完成，098独立按原冻结执行；099是选型建议、不自动升级默认。正式结果、费用与限制以')
    for name,d in frozen.items():assert c.sha(c.OUT/name)==d
    c.put(marker,dict(utc=c.utc(),changes=['Label model names in O-to-C rows','Explain natural NA / diagnostic false-S / C48 losses','Explain strict five-case intersection and both recommended models strict80/80','Navigation only'],
        before=before,after_report_sha256=c.sha(c.OUT/'report.md'),original_generator_sha256=c.read(c.OUT/'offline_analysis_freeze.json')['files']['tasks/099_judge_selection/report099.py'],
        updated_generator_sha256=c.sha(c.TASK/'report099.py'),scientific_results_unchanged=frozen,first_selfcheck_passed=True,history_private_path=history.relative_to(c.ROOT).as_posix()))
    print(c.canonical(dict(navigation_updated=True,science_unchanged=True,final_selfcheck_pending=True)))

if __name__=='__main__':main()

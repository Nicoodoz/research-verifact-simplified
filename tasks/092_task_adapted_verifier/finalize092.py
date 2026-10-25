"""Publish task state after analyses and checks; no training or next-task launch."""
import common092 as c
def main():
    assert c.read(c.OUT/'selfcheck.json')['status']=='PASS'
    assert c.read(c.OUT/'final_selfcheck.json')['status']=='PASS'
    notice='**092完成（2026-09-27）：** 用户AutoDL训练后，本地完成100患者9065条双臂OOF与唯一融合。原作者/Frozen/Fine正确7331/7204/7530，MCC0.4959/0.4433/0.5156；Fine较Frozen净+326、false-S764→745，但NS召回仅8.95%，不能全面超越原作者。共同956条B/F4/Fine/偏置对照/融合正确783/793/770/786/795，融合较B净+12但false-S41→64、MCC未提高；较偏置对照净+9且false-S−15，保留有限增量、不升级默认。完整中文稿和类/患者/成本分析已更新；0新收费API，云GPU租金未知。执行者自检PASS，独立审计未执行。092明确授权全部100人标签用于新患者分组CV，不改036历史、不称新holdout；旧本地暂停工件另存，不自动093。'
    for name in ['AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md']:
        path=c.ROOT/name;raw=path.read_bytes()
        if '**092完成'.encode() in raw:continue
        end=b'\r\n' if b'\r\n' in raw else b'\n';position=raw.index(b'\n')+1;prefix='../' if name.startswith('docs/') else ''
        paragraph=notice+' [报告]('+prefix+'outputs/092_task_adapted_verifier/report.md) · [完整稿]('+prefix+'outputs/092_task_adapted_verifier/manuscript_zh.md)。'
        path.write_bytes(raw[:position]+end+paragraph.encode('utf-8')+end+raw[position:])
    artifacts=['oof_predictions.jsonl','metrics.json','paired.json','fusion_predictions.jsonl','fusion_models.json','fusion_results.json','fusion_supplement.json','final_costs.json','report.md','manuscript_zh.md','cloud_training_manifest.json','case_analysis.md','evidence_map.md']
    c.put(c.OUT/'completion.json',dict(status='COMPLETE',utc=c.now(),default_upgraded=False,next_task_started=False,independent_audit=False,API_calls=0,API_cost_cny=0,artifacts_sha256={name:c.sha(c.OUT/name) for name in artifacts},main_conclusion='Fine improves Frozen OOF but NS remains weak; fusion has limited bias-controlled incremental signal, no overall default upgrade.',missing_scientific_delivery=[],known_limits=['cloud rental cost unavailable','cloud full command log unavailable','single seed/one-block/CE only','no new external test']))
    (c.OUT/'CURRENT_STATUS.md').write_text('# 092 COMPLETE\n\n双臂9065 OOF、唯一融合、完整类别与患者分析、部署检查、中文报告及完整论文稿完成。默认仍为B＋Frozen PriorG。\n\n本地暂停为历史：旧工件保留在local_pause_archive，云端与本地计算分开记录。0新收费API；租金未知。执行者自检通过，独立审计未执行。按用户授权提交推送后停止，不自动重训或093。\n\n入口：[报告](report.md)、[完整论文](manuscript_zh.md)、[证据对应](evidence_map.md)、[自检](selfcheck.json)、[最终核查](final_selfcheck.json)、[完成指纹](completion.json)。\n',encoding='utf-8')
    print('092 final state recorded; no research process started.')
if __name__=='__main__':main()

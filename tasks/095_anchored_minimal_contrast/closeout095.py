"""Finalize navigable delivery after real analysis, self-check and separate review."""
from pathlib import Path
import json,re,subprocess
import common095 as c

def main():
    assert not (c.PRIVATE/'run.lock').exists()
    assert c.read(c.OUT/'selfcheck.json')['status']=='PASS'
    review=c.ROOT/'reviews/095_anchored_minimal_contrast/final_review.md'
    assert review.exists(),'Do not replace separate final review with executor self-check'
    cov=c.read(c.OUT/'baseline_coverage.json');cost=c.read(c.OUT/'cost_ledger.json');tab=c.read(c.OUT/'baseline_metrics.json')['common_core'];a,b=tab['Original'],tab['B_PriorG']
    text=f'''# 095 当前状态：研究结项，C构造停止，默认不变

B成功覆盖{cov['successful_B']}/9065，core有效{cov['core_valid_B']}、raw有效{cov['raw_valid_B']}、缺失{cov['missing']}。成功无效回答保留，不重复或填旧标签。同ID共同core原作者/B＋G正确{a['correct']}/{b['correct']}，MCC {a['MCC']:.4f}/{b['MCC']:.4f}，false-S {a['false_S']}/{b['false_S']}。

300构造＋117核对完成，95个自动拟触发并不等于真实合格；来源语义复核发现时点、作用域、关系绑定问题，全局停止E/C最终Judge。实际C分类调用0；未执行同期B/E/C、600扩量或顺序控制，不能写成分类阴性或等效。

新增API目录价及未知预留¥{cost['total_directory_price_or_unknown_cny']:.6f}/150，{cost['attempts']}次尝试，{cost['retry_attempts']}次重试。全量B与C共享原SQLite账本，未知/在途未清零；无新增GPU或检索收费。

执行者自检与独立执行者复核分别完成，以各自原报告的范围和限制为准；不等于独立医生审评。所有100患者已有开发暴露，当前比较不是新外部测试。默认仍C48→T-S无示例B→Frozen PriorG。

[先读总报告](report.md) · [数值解释](baseline_findings.md) · [完整中文稿](manuscript_zh.md) · [独立复核](../../reviews/095_anchored_minimal_contrast/final_review.md) · [自检](selfcheck.json) · [准确恢复入口](../../tasks/095_anchored_minimal_contrast/README.md)。

完成本轮交付后提交推送并停止，不自动096、下一候选、训练或默认升级。恢复命令只检查原B缺口；成功覆盖完整时不发生新调用。
'''
    with (c.OUT/'CURRENT_STATUS.md').open('w',encoding='utf-8',newline='\n') as f:f.write(text)
    # Check local delivery links, never fetch external sites here.
    checked=0
    for p in [c.OUT/n for n in ['report.md','manuscript_zh.md','baseline_findings.md','baseline_cases.md','evidence_map.md','CURRENT_STATUS.md']]+[c.TASK/'README.md']:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
            if target.startswith(('http:','https:','#','mailto:')):continue
            target=target.split('#',1)[0]
            assert (p.parent/target).exists(),(str(p),target)
            checked+=1
    # These raw content fields do not belong in any public numeric artifact.
    forbidden={'messages','body_text','reasoning_content','original_claim','alternative_claim','quote','reference','clinical_text','api_key','authorization'}
    def inspect(v,path):
        if isinstance(v,dict):
            assert not (set(v)&forbidden),(str(path),sorted(set(v)&forbidden))
            for x in v.values():inspect(x,path)
        elif isinstance(v,list):
            for x in v:inspect(x,path)
    for folder in [c.OUT,c.ROOT/'reviews/095_anchored_minimal_contrast']:
        for p in folder.glob('*.json*'):
            if p.suffix=='.json':inspect(c.read(p),p)
            elif p.suffix=='.jsonl':
                for r in c.lines(p):inspect(r,p)
    protected=subprocess.run(['git','diff','--name-only','--','.gitignore','src'],cwd=c.ROOT,capture_output=True,text=True,check=True)
    assert not protected.stdout.strip()
    files={}
    for folder in [c.TASK,c.OUT,c.ROOT/'reviews/095_anchored_minimal_contrast']:
        for p in sorted(folder.rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or p.name in {'delivery_manifest.json','progress.jsonl'}:continue
            assert p.stat().st_size<50*1024**2,(p,'unexpected large public artifact')
            files[p.relative_to(c.ROOT).as_posix()]=dict(sha256=c.sha(p),bytes=p.stat().st_size)
    for name in ['AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/TASK_INDEX.md','docs/API_POLICY.md','docs/RESEARCH_EXECUTION.md','docs/REPRODUCIBILITY.md','docs/aliyun/CURRENT.md','reviews/README.md']:
        p=c.ROOT/name;files[name]=dict(sha256=c.sha(p),bytes=p.stat().st_size)
    c.put(c.OUT/'delivery_manifest.json',dict(utc=c.now(),task='095',status='completed_with_candidate_stopped_before_classification',start_HEAD='5ec748edd63be29d35fa920f10874aa158501ae5',baseline_coverage=cov,API_cost_or_reserved_CNY=cost['total_directory_price_or_unknown_cny'],links_checked=checked,private_content_field_check=True,independent_review_path=review.relative_to(c.ROOT).as_posix(),independent_review_sha256=c.sha(review),new_default=False,auto_next_task=False,files=files,note='This manifest identifies delivery artifacts, not an independent medical audit or evidence of new-method classification benefit. Commit identity is recorded by Git; manifest does not hash itself.'))
    print('DELIVERY_READY',len(files),'files;',checked,'local links verified')

if __name__=='__main__':main()

"""Pause-only documentation and integrity checks; does not invoke research execution."""
import ast,json,subprocess
import common092 as c

def main():
    message='**092用户暂停（2026-09-27）：** 任务适配文本核验实验已按用户指令停止，包括训练及父级流水线。9065条/100人C48和47219窗口编码完成；Frozen fold0完成，Fine-tuned fold0保存至第5轮1024/5685，其余折未启动。全量OOF和方法比较未完成，不判定成败。私有检查点/缓存保留，0新收费API；默认与历史成果不变。本轮曾获明确授权全部100人标签用于新患者分组CV，不改写036历史。只有用户明确恢复才继续；本次按要求交接并推送。'
    for name in ['AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md']:
        path=c.ROOT/name;raw=path.read_bytes()
        if '**092用户暂停'.encode() in raw:continue
        ending=b'\r\n' if b'\r\n' in raw else b'\n';position=raw.index(b'\n')+1
        target=('../' if name.startswith('docs/') else '')+'outputs/092_task_adapted_verifier/report.md'
        inserted=ending+(message+' [暂停报告]('+target+')。').encode('utf-8')+ending
        path.write_bytes(raw[:position]+inserted+raw[position:])
    checks=[]
    def check(ok,name):
        checks.append(dict(name=name,passed=bool(ok)))
        assert ok,name
    snapshot=c.read(c.OUT/'pause_snapshot.json')
    check(snapshot['status']=='PAUSED_BY_USER','pause status')
    check(snapshot['checkpoint']['cursor']==1024 and snapshot['checkpoint']['completed_epochs']==4,'checkpoint cursor')
    check(c.sha(c.PRIVATE/'finetuned_fold0/resume.pt')==snapshot['checkpoint']['sha256'],'checkpoint hash stable after stop')
    check(c.read(c.OUT/'training_progress.json')==snapshot['last_progress'],'progress stable after stop')
    check(snapshot['completed_models']==['frozen_fold0'],'one complete model only')
    check(not (c.OUT/'oof_predictions.jsonl').exists(),'no claimed full OOF')
    for name,sha in c.read(c.OUT/'training_freeze_v3.json')['code'].items():check(c.sha(c.TASK/name)==sha,'frozen '+name)
    for name,sha in c.read(c.OUT/'inventory.json')['source_hashes'].items():check(c.sha(c.ROOT/'outputs'/name)==sha,'history '+name)
    check(c.read(c.OUT/'cache_manifest.json')['complete'],'encoding complete')
    check((c.PRIVATE/'activations/lower23.npy').exists(),'activation junction accessible')
    check(subprocess.run(['git','check-ignore','-q','.local_models/092/finetuned_fold0/resume.pt'],cwd=c.ROOT).returncode==0,'private checkpoint ignored')
    check(subprocess.run(['git','diff','--quiet','--','.gitignore'],cwd=c.ROOT).returncode==0,'gitignore unchanged')
    process_query="@(Get-Process -Id 15956,10252,20664,31208,11276,9688,12688 -ErrorAction SilentlyContinue).Count"
    count=subprocess.check_output(['pwsh','-NoProfile','-Command',process_query],text=True).strip()
    check(count=='0','all recorded research process IDs stopped')
    guard=subprocess.run(['E:/miniconda3/python.exe',str(c.TASK/'continue092.py')],capture_output=True,text=True)
    check(guard.returncode!=0 and '092 paused by user' in guard.stderr,'resume entry blocked by marker')
    for path in c.TASK.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'));check(True,'syntax '+path.name)
    forbidden={'text','reference','claim','content','reasoning_content','input_ids','api_key','password'}
    def scan(value):
        if isinstance(value,dict):
            check(not forbidden.intersection(value),'public row excludes private fields')
            for child in value.values():scan(child)
        elif isinstance(value,list):
            for child in value:scan(child)
    for path in c.OUT.rglob('*.jsonl'):
        for row in c.lines(path):scan(row)
    c.put(c.OUT/'pause_selfcheck.json',dict(status='PASS',scope='pause handoff only, not final research evaluation',executor_selfcheck=True,independent_audit=False,checks=len(checks),failed=0,utc=c.now(),research_process_count=0,checkpoint_load_verified_in='pause_snapshot.json',API_calls=0,API_cost_cny=0))
    print('Pause handoff checks PASS',len(checks))
if __name__=='__main__':main()

"""Run220 -> fixed160 check -> resume369 -> fixed160, under one unchanged stage clock."""
from pathlib import Path
import json,subprocess,os,signal,time,shutil
P=Path(__file__).resolve().parent;PY='/root/verifact_image/envs/venv103/bin/python'
def read(path):return json.loads(Path(path).read_text())
def put(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def launch(stage,args,deadline):
    log=(P/(stage+'.log')).open('ab');child=subprocess.Popen([PY,'-u','-B',*args],cwd=P,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    put(P/'active_child.json',dict(stage=stage,pid=child.pid,started=time.time()))
    try:return child.wait(timeout=max(1,deadline-time.time()-90))
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=45)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        return 124

def midpoint_inference(out,deadline):
    ready=read(out/'midpoint_ready.json');source=Path(ready['checkpoint']);dest=out/'midpoint220'
    if not dest.exists():shutil.copytree(source,dest)
    E=P/'mid_eval220';E.mkdir(exist_ok=True)
    for sub in ('104_supervision_evidence','105_brief_supervision','136_claim_repeat_transfer','144_native_confidence'):
        shutil.copytree(P/'tasks'/sub,E/'tasks'/sub,dirs_exist_ok=True)
    lengths={r['id']:r for r in map(json.loads,(P/'data/screen_lengths.jsonl').read_text().splitlines())};inputs=[]
    for r in map(json.loads,(P/'data/screen.jsonl').read_text().splitlines()):
        sha=lengths[r['id']]['prompt_token_sha256'];inputs.append(dict(r,prompt_token_sha256=sha,source_prompt_token_sha256=sha))
    (E/'data').mkdir(exist_ok=True)
    (E/'data/inputs.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in inputs))
    shutil.copy2(P/'data/screen_lengths.jsonl',E/'data/lengths.jsonl');shutil.copy2(P/'data/session.json',E/'data/session.json')
    import hashlib
    ids=sorted(lengths,key=lambda i:(lengths[i]['input_tokens'],i));batches=[ids[i:i+2] for i in range(0,len(ids),2)]
    old=read(P/'data/job156.json');job=dict(task=156,arm='claim_repeat_sft',scope='step220_screen160',model_dir=old['model_dir'],adapter=str(dest),
        adapter_sha256=hashlib.sha256((dest/'adapter_model.safetensors').read_bytes()).hexdigest(),adapter_bytes=(dest/'adapter_model.safetensors').stat().st_size,
        inputs='data/inputs.jsonl',ids=ids,batches=batches,expected_N=160,target_N=160,prior_N=0,compute_limit_seconds=750,save_reserve_seconds=180,new_training=False)
    put(E/'data/job.json',job)
    worker=(P/'inference_template.py').read_text().replace("job['task']==155 and arm=='native_train'","job['task']==156 and arm=='claim_repeat_sft'").replace('task=155','task=156').replace("source_checkpoint='120_final369'","source_checkpoint='156_step220'")
    T=E/'tasks/156_claim_repeat_sft';T.mkdir(exist_ok=True);(T/'infer220.py').write_text(worker,encoding='utf-8')
    if not (E/'controller_done.json').exists():
        put(E/'pid.json',dict(started=time.time(),controller_parent=os.getpid()))
        code=launch('midpoint160',[str(T/'infer220.py')],deadline)
        if code:raise RuntimeError('Midpoint inference did not complete: '+str(code))
    if read(E/'controller_done.json')['exit_code']!=0:raise RuntimeError('Midpoint inference failed; preserve')
    put(out/'midpoint_evaluation_complete.json',dict(N=160,checkpoint=str(dest),evidence=str(E/'results'),epoch=time.time()))

def main():
    job=read(P/'data/job156.json');session=read(P/'data/session.json');out=P/'results'/job['name'];out.mkdir(parents=True,exist_ok=True)
    if not (P/'runtime156.json').exists():put(P/'runtime156.json',dict(started=time.time(),phase_deadline_epoch=min(session['end_epoch'],time.time()+17400),no_shutdown=True))
    deadline=read(P/'runtime156.json')['phase_deadline_epoch']
    if time.time()+1200>=deadline:raise TimeoutError('Insufficient unchanged phase window')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU occupied')
    for part in range(2):
        if (out/'complete.json').exists():break
        code=launch('training_part'+str(part),[str(P/'tasks/156_claim_repeat_sft/worker156.py'),'--job','data/job156.json'],deadline)
        if code==75:
            midpoint_inference(out,deadline)
            continue
        if code:raise RuntimeError('Training stopped: '+str(code))
        break
    if not (out/'complete.json').exists():raise RuntimeError('No complete369 proof')
    put(P/'controller_done.json',dict(task=156,exit_code=0,steps=369,fixed160_complete=True,epoch=time.time(),no_shutdown=True,no_release=True))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        put(P/'controller_failure.json',dict(error_type=type(error).__name__,error=str(error),epoch=time.time(),no_shutdown=True));raise

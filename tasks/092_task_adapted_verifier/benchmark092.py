"""Run only after all OOF models finish; fixed hash sample, original-text deployment."""
import os,sys,time,subprocess
import common092 as c

def main():
    for family in ['frozen','finetuned']:
        for fold in range(5):
            assert (c.OUT/f'{family}_fold{fold}'/'complete.json').exists()
    fold=c.read(c.OUT/'folds.json')[0]
    test_ids={r['id'] for r in c.lines(c.OUT/'cohort.jsonl') if r['sid'] in fold['test']}
    rows=[r for r in c.lines(c.PRIVATE/'inputs.jsonl') if r['proposition_id'] in test_ids]
    rows=sorted(rows,key=lambda r:c.digest('092-deployment-benchmark:'+r['proposition_id']))[:12]
    path=c.PRIVATE/'deployment_benchmark_inputs.jsonl'
    c.jsonl(path,[dict(proposition_id=r['proposition_id'],text=r['text'],reference=r['reference']) for r in rows])
    summary={}
    for family in ['frozen','finetuned']:
        output=c.PRIVATE/f'deployment_benchmark_{family}.jsonl'
        started=time.time()
        subprocess.run([sys.executable,str(c.TASK/'infer092.py'),'--checkpoint',str(c.PRIVATE/f'{family}_fold0'/'best.pt'),'--input',str(path),'--output',str(output)],check=True)
        elapsed=time.time()-started
        observed=c.lines(output)
        expected={r['id']:r for r in c.lines(c.OUT/f'{family}_fold0'/'predictions.jsonl')}
        summary[family]=dict(N=len(observed),process_wall_seconds=elapsed,forward_seconds=sum(r['seconds'] for r in observed),rows=[dict(**r,OOF_prediction=expected[r['id']]['prediction']) for r in observed],label_disagreements=sum(r['prediction']!=expected[r['id']]['prediction'] for r in observed),note='Fixed hash-selected outer fold0 claims; full lower23 online plus top block and head; excludes retrieval; process time includes loading. Batch-size floating-point effects are measured, not used for choosing predictions.')
    c.put(c.OUT/'deployment_benchmark.json',summary)
    print(summary,flush=True)
if __name__=='__main__':main()

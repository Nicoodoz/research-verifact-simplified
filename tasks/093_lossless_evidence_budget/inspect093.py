"""Local case review only; private text is never written to public outputs."""
import common093 as c
def main():
    d=c.read(c.OUT/'analysis.json')
    for panel,z in d['panels'].items():
        print(panel,'raw',{a:v['correct'] for a,v in z['native_raw_metrics'].items()})
        for method in ['raw','PriorG']:
            for pair,p in z['comparisons'][method].items():print(method,pair,{k:p[k] for k in ['rescue','harm','net','patient_win_loss_tie','rescue_by_GT','harm_by_GT','independent_supplement_CI95']})
    rows=c.lines(c.OUT/'predictions_public.jsonl');private={r['id']:r for r in c.lines(c.PRIVATE/'pool_inputs.jsonl')};ops={r['id']:r for r in c.lines(c.OUT/'pool_operations.jsonl')}
    corpus={r['passage_id']:r for r in c.lines(c.ROOT/'outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl')}
    for r in rows:
        if r['A_added'] and (len({r['labels'][a]['PriorG'] for a in ['B','F','A']})>1 or len({r['labels'][a]['raw'] for a in ['B','F','A']})>1):
            print('CASE',r['id'],r['panel'],r['GT'],r['labels'],{a:r['arms'][a]['scores'] for a in ['B','F','A']})
            print('CLAIM',private[r['id']].get('claim'))
            print('ADDED',[(i,corpus[i]['text']) for i in ops[r['id']]['added_ids']])
            print('BASE',private[r['id']]['B'])
if __name__=='__main__':main()

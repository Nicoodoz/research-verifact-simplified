"""Local diagnostic view; no clinical text is written to public artifacts."""
import common094 as c
def main():
    a=c.read(c.OUT/'analysis.json')
    for panel,d in a['panels'].items():
        print(panel,'status',d['full_status'])
        for method,pairs in d['comparisons'].items():
            for name,z in pairs.items():print(method,name,{k:z[k] for k in ['rescue','harm','net','rescue_by_GT','harm_by_GT','false_S_added','false_S_prevented','patient_win_loss_tie']})
    inputs={r['id']:r for r in c.lines(c.PRIVATE/'inputs.jsonl')};ext={(r['id'],r['arm']):r for r in c.lines(c.PRIVATE/'extracted_aligned.jsonl')};review={r['id']:r for r in c.read(c.OUT/'content_review.json')['rows']}
    for r in c.lines(c.OUT/'predictions_public.jsonl'):
        if len({r['labels'][a]['raw'] for a in ['B','V','Q']})==1 and len({r['labels'][a]['PriorG'] for a in ['B','V','Q']})==1:continue
        print('CASE',r['id'],r['panel'],r['GT'],r['labels'],{a:r['arms'][a]['scores'] for a in ['B','V','Q']})
        print('CLAIM',inputs[r['id']]['text']);print('CONTENT REVIEW',review.get(r['id']))
        for arm in ['V','Q']:
            if (r['id'],arm) in ext:print(arm,ext[r['id'],arm]['record'])
if __name__=='__main__':main()

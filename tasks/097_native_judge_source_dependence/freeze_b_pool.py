"""Prospective natural B utility IDs, disjoint from A; no request is authorized yet."""
import common097 as c

def main():
    a={r['id'] for r in c.lines(c.OUT/'a_execution_panel.jsonl')}
    candidates=[r for r in c.lines(c.ROOT/'outputs/096_r1_native_priorg/main_panel.jsonl') if r['eligible'] and r['id'] not in a]
    selected=sorted(candidates,key=lambda r:c.digest('097/B/utility/v1/'+r['id']))[:300]
    rows=[dict(id=r['id'],sid=r['sid'],author=r['author'],GT=r['GT'],C48_source=r['C48_source']) for r in selected]
    c.write_lines(c.OUT/'b_prospective_panel.jsonl',rows)
    c.write_json(c.OUT/'b_prospective_freeze.json',dict(N=len(rows),patients=len({r['sid'] for r in rows}),A_overlap=0,selection='natural 096 eligible non-A, fixed SHA256 097/B/utility/v1/ID; GT only recorded for evaluation, never source construction or Judge',panel_sha256=c.sha(c.OUT/'b_prospective_panel.jsonl'),status='candidate only; B gate not passed, no paid body or method score authorized'))
    print('B prospective',len(rows),'patients',len({r['sid'] for r in rows}))
if __name__=='__main__':main()

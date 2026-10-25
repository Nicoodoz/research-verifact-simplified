"""GT-blind structural census on all existing C48, before any new inference."""
from collections import Counter
import common093 as c
from operation093 import factor
def main():
    source=c.ROOT/'.local_models/092/inputs.jsonl'
    c.put(c.OUT/'inventory_freeze.json',dict(utc=c.now(),HEAD='e3999daa6c7012efcadcd3c2dce641651be3592c',GT_read=False,protocol_sha256=c.sha(c.TASK/'protocol.md'),operation_sha256=c.sha(c.TASK/'operation093.py'),input_sha256=c.sha(source),API_cap_cny=20,API_calls=0))
    metadata={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/bags.jsonl')}
    public=[];private=[];errors=[]
    for r in c.lines(source):
        pid=r['proposition_id']
        try:
            f=factor(r['reference'])
        except ValueError as e:
            errors.append(dict(id=pid,error=str(e)));continue
        public.append(dict(id=pid,reference_sha256=c.h(r['reference']),source=metadata[pid]['source'],baseline_chars=len(r['reference']),factored_chars=len(f['reference']),saved_chars=f['saved'],groups=f['groups'],occurrences=f['occurrences']))
        if f['saved']>0:private.append(dict(id=pid,**f))
    c.putl(c.OUT/'structural_inventory.jsonl',public);c.putl(c.PRIVATE/'factored_inputs.jsonl',private)
    affected=[r for r in public if r['saved_chars']>0]
    summary=dict(N=len(public),errors=errors,changed=len(affected),changed_by_source=dict(Counter(r['source'] for r in affected)),sum_saved_chars=sum(r['saved_chars'] for r in affected),maximum_saved=max([r['saved_chars'] for r in affected] or [0]),cases_saving_at_least_400=sum(r['saved_chars']>=400 for r in affected),cases_saving_at_least_700=sum(r['saved_chars']>=700 for r in affected),GT_read=False,API_calls=0)
    c.put(c.OUT/'structural_summary.json',summary);print(summary)
if __name__=='__main__':main()

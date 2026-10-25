"""Offline runtime metadata correction; scientific parser/result unchanged."""
import common096 as c
import marlin096 as m
def main():
    m.activate();old=c.read(m.O/'stage_calibration.json');jj=[j for j in m.r.jobs() if j['stage']=='calibration'];new=m.r.metrics(jj,old['wall_seconds'])
    assert new['success']==old['success']==143 and new['core_valid']==old['core_valid']==142
    for j in jj:
        a=m._original_parsed(j);b=m.parsed(j)
        for k in ['valid','verdict','label_scores','invalid_reason']:assert a[k]==b[k]
    assert m.metrics([],1)['finish_reasons']=={}
    c.put(m.O/'stage_calibration_metadata_correction.json',dict(original_stage_sha256=c.sha(m.O/'stage_calibration.json'),corrected_metadata=new,classification_changed=False,GT_read=False,reason='native usage and finish preserved even when content=None; original stage retained'))
    c.append(m.O/'runtime_ledger.jsonl',dict(event='calibration_metadata_corrected',utc=c.now(),file='stage_calibration_metadata_correction.json',original_wall_seconds=old['wall_seconds'],HTTP200=143,core_valid=142))
    print('METADATA_REPAIR_PASS',new['finish_reasons'],'completion_tokens',new['completion_tokens'])
if __name__=='__main__':main()

"""Authorized source review only: display complete current references by exact ID.

Clinical output must remain in the confirmed permitted review service. Never
redirect it to public outputs. This is a viewer, not a labeling or repair rule.
"""
import argparse
import common106 as c


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('ids',nargs='+')
    p.add_argument('--start',type=int,default=0)
    p.add_argument('--end',type=int)
    a=p.parse_args()
    data={r['id']:r for r in c.rows(c.PRIVATE/'A_source_review_dossiers.jsonl')}
    for pid in a.ids:
        r=data[pid]
        print(c.canonical({k:r[k] for k in ('id','GT','before','after','groups','reference_sha256')}))
        print('CLAIM:',r['claim'])
        print('FULL ACTUAL REFERENCE; Python char offsets refer to the exact original string:')
        for unit in r['complete_unit_spans']:
            start=max(a.start,unit['start']);end=min(a.end if a.end is not None else len(r['full_reference']),unit['end'])
            if end<=start:continue
            print(f"[unit @{start}:{end}]")
            print(r['full_reference'][start:end])
        print(f"END DISPLAYED REFERENCE {pid}; range={a.start}:{a.end or len(r['full_reference'])}; total_characters={len(r['full_reference'])}")


if __name__=='__main__':
    main()

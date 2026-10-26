"""Freeze formatting-only correction after artificial fixtures, without GT access."""
import json
import common099 as c
from parse099 import parse

def main():
    payload=json.dumps(dict(verdict='Not Supported',reason='fixture'))
    wrap=lambda text:dict(http_status=200,body_text=json.dumps(dict(choices=[dict(message=dict(content=text),finish_reason='stop')])))
    tr=wrap('```json\n'+payload+'\n```')
    assert not c.parse(tr)['valid'] and parse(tr)['verdict']=='Not Supported'
    assert parse(wrap(payload))['verdict']=='Not Supported'
    assert not parse(wrap('Comment\n'+payload))['valid']
    assert not parse(wrap('```json\n'+payload[:-1]+'\n```'))['valid']
    paths=[c.TASK/'parse099.py',c.TASK/'format_amendment.md']
    c.put(c.OUT/'format_amendment_freeze.json',dict(utc=c.utc(),GT_joined=False,classification_quality_not_computed=True,
          request_or_sample_changed=False,old_parser_preserved=True,no_new_API_calls=True,fixtures=4,
          files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths}))
    print('Outer-fence-only normalization4fixtures PASS; strict parser unchanged')

if __name__=='__main__':main()

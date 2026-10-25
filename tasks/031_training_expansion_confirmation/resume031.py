"""Task-local user-authorized account override; no changed scientific settings."""
import argparse
import common031 as c
import api031 as a
import pipeline031 as pipeline
def main(stage):
    auth=c.read(c.OUT/'account_override_001.json');c.require(auth['user_reply']=='授权使用下一启用账号' and auth['skip_aliases']==['account_2'] and auth['is_balance_exhaustion'] is False,'Account authorization changed')
    path=c.OUT/'account_override_manifest_001.json'
    if path.exists():
        for p,h in c.read(path)['sha256'].items():c.require(c.sha(c.ROOT/p)==h,'Override changed')
    else:c.put(path,dict(created_utc=c.now(),sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [c.OUT/'account_override_001.json',c.TASK/'resume031.py',c.TASK/'api031.py',c.OUT/'embedding_execution_summary_001.json']}))
    original=a.load_accounts;a.load_accounts=lambda p:[account for account in original(p) if account.alias not in auth['skip_aliases']];pipeline.main(stage)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('embedding','rerank','score','auxiliary'));main(p.parse_args().stage)

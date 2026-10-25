import argparse
import common095 as c
import workflow095 as flow
import method095 as method
import sourcefix095 as fixed

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['checks','collect']);a=p.parse_args()
    for path,hh in c.read(c.OUT/'sourcefix_freeze.json')['sources'].items():assert c.sha(c.ROOT/path)==hh,path
    method.parse_builder=fixed.parse_builder
    if a.action=='checks':flow.build_checks(False)
    else:flow.collect(False)

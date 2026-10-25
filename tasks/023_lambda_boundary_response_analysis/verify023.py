"""Safe zero-network replay and independent dense-decode/monotonicity checks."""
from pathlib import Path
import argparse,math,socket,subprocess
import numpy as np
from pypdf import PdfReader
import common023 as c
from analyze023 import run as analyze
from summarize023 import run as describe

NAV={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md','reviews/README.md','.gitattributes'}
def safe_output(path):
    path=path.resolve()
    c.require(not path.exists(),'Output exists')
    c.require(path.parent==c.OUT or path.is_relative_to(c.ROOT/'outputs/replays'),'Use a new023 sibling or outputs/replays directory')
    return path
def compare_files(old,new):
    paths=[p for p in old.iterdir() if p.is_file() and p.name!='manifest.json']
    c.require({p.name for p in paths}=={p.name for p in new.iterdir() if p.is_file() and p.name!='manifest.json'},'Replay inventory')
    for p in paths:c.require(p.read_bytes()==(new/p.name).read_bytes(),'Replay mismatch: '+p.name)
    return len(paths)

def verify(out):
    out=safe_output(out)
    def blocked(*a,**kw):raise RuntimeError('023 replay prohibits network')
    socket.create_connection=blocked;socket.socket.connect=blocked;socket.socket.connect_ex=blocked
    for name in ('preparation_001','analysis_001','description_001'):c.check(c.OUT/name)
    rows=c.jl(c.OUT/'preparation_001/scores.jsonl');ids=c.read(c.OUT/'analysis_001/prediction_ids.json');checks=0
    for group in c.GROUPS:
        rr=c.subset(rows,group);pred=np.load(c.OUT/'analysis_001'/('predictions_'+group+'.npy'),allow_pickle=False)
        c.require(ids[group]==[r['proposition_id'] for r in rr] and pred.shape==(401,len(rr)),'Dense prediction alignment')
        # Deliberately use max over the original NS,NA,S ordered labels, independent of023 vector decoder.
        for i,r in enumerate(rr):
            ordered=(c.LABELS[1],c.LABELS[2],c.LABELS[0]);logs={key:math.log(max(r['scores'][key]/100,1e-6)) for key in ordered}
            expected=[c.LABELS.index(max(ordered,key=lambda key:logs[key]+(lam if key=='Supported' else 0))) for lam in c.GRID]
            c.require(pred[:,i].tolist()==expected,'Independent dense prediction mismatch');checks+=401
            c.require(not any(a==0 and b!=0 for a,b in zip(expected,expected[1:])),'S monotonicity')
        c.require(all(r['repeat']==0 for r in rr) if group=='pooled_R0' else True,'Pooled repeat leakage')
    dense=c.csvrows(c.OUT/'analysis_001/dense_grid.csv')
    for group in c.GROUPS:
        for author in ('all','human','llm'):
            rr=[r for r in dense if r['group']==group and r['author']==author];c.require(len(rr)==401,'Curve count')
            for a,b in zip(rr,rr[1:]):
                for key in ('S_correct','rescue','harm','wrong_to_falseS','false_S','NS_to_S','NA_to_S'):c.require(int(a[key])<=int(b[key]),'Monotone count violation')
                for key in ('NS_correct','NA_correct'):c.require(int(a[key])>=int(b[key]),'NonS recall monotonicity')
    for r in c.jl(c.OUT/'analysis_001/switches.jsonl'):
        if r['status']=='switch_in_0_4':c.require(c.bits(r['first_S_lambda'])-c.bits(r['previous_nonS_lambda'])==1,'Nonadjacent switch floats')
    # Figure hashes and PDF structure; actualPDF raster review is separately recorded.
    figs=c.OUT/'figures_001';manifest=c.read(figs/'manifest.json');pdfs=[]
    for name,sha in manifest['files'].items():c.require(c.sha(figs/name)==sha,'Figure changed')
    for name,sha in manifest['data_hashes'].items():c.require(c.sha(c.OUT/'analysis_001'/name)==sha,'Plot source changed')
    for p in figs.glob('*.pdf'):
        pdf=PdfReader(p);c.require(len(pdf.pages)==1,'Expected one-page figure');text=pdf.pages[0].extract_text()
        c.require('019 discovery' in text and '020 R0' in text and '020 R1' in text,'Missing PDF labels')
        pdfs.append(dict(file=p.name,pages=1,width_pt=float(pdf.pages[0].mediabox.width),height_pt=float(pdf.pages[0].mediabox.height),text_extractable=True))
    policy=c.ROOT/'docs/API_POLICY.md';head_policy=subprocess.check_output(['git','show','HEAD:docs/API_POLICY.md'],cwd=c.ROOT)
    c.require(policy.read_bytes()==head_policy,'023 must not change API policy')
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines();c.require(set(changed)<=NAV,'Unexpected historical change')
    out.mkdir(parents=True);analyze(out/'analysis');describe(out/'description')
    counts={name:compare_files(c.OUT/old,out/new) for name,old,new in [('analysis','analysis_001','analysis'),('description','description_001','description')]}
    summary=dict(status='executor_checks_pass_not_independent_audit',independent_dense_decodes=checks,replayed_content_files=counts,anchor_checks=33,pdf_structure=pdfs,network_blocked=True,API_policy_unchanged=True,new_API_calls=0,cost_cny=0,fixed_lambda=2,lambda_reselected=False,reserved_test_used=False)
    c.write(out/'summary.json',summary);c.seal(out,[c.OUT/'preparation_001/manifest.json',c.OUT/'analysis_001/manifest.json',figs/'manifest.json'],[Path(__file__)])
    print(c.canonical(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'verification_001');verify(p.parse_args().output)

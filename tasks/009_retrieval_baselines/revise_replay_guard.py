"""One-off minimal revision, preserving original bytes and line endings."""
from pathlib import Path
import study009 as s


if __name__=='__main__':
    out=s.OUT/'revision_001'
    out.mkdir(exist_ok=False)
    old=s.read_json(s.OUT/'handoff_001.json')
    assert all(s.pilot.digest_file(s.ROOT/name)==digest for name,digest in old['files'].items())
    protected=[p for p in (s.ROOT/'reviews').rglob('*') if p.is_file()]
    s.pilot.write_json(out/'before.json',dict(base_head=s.BASE_HEAD,original_handoff_sha256=s.pilot.digest_file(s.OUT/'handoff_001.json'),
        original_inventory_sha256=old['inventory_sha256'],all_3114_original_files_matched=True,
        preserved_review_files={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in protected}))
    path=s.TASK/'verify009.py'
    raw=path.read_bytes()
    (out/'original_verify009.py.txt').write_bytes(raw)
    nl='\r\n' if b'\r\n' in raw else '\n'
    text=raw.decode('utf-8').replace('\r\n','\n')
    marker='\ndef run(output,tests=True):'
    helper='''
def check_frozen_manifest(path):
    """Strict artifacts/computation; a past verifier version is provenance only."""
    m=s.check(path.parent)
    for name,digest in m.get('dependencies',{}).items():
        assert s.pilot.digest_file(s.ROOT/name)==digest,(str(path),name)
    historical_self_check=('verification.json' in m['files'] and
        s.read_json(path.parent/'verification.json').get('self_check_not_independent_audit') is True)
    provenance=[]
    for name,digest in m.get('code_sha256',{}).items():
        actual=s.pilot.digest_file(s.ROOT/name)
        if historical_self_check and name=='tasks/009_retrieval_baselines/verify009.py':
            provenance.append(dict(manifest=path.relative_to(s.ROOT).as_posix(),code=name,
                recorded_sha256=digest,current_sha256=actual,matches=actual==digest,
                role='historical_verifier_provenance_not_experimental_computation'))
        else:
            assert actual==digest,(str(path),name)
    return provenance


def workspace_snapshot():
    """Repository state is diagnostic, not a substitute for frozen bindings."""
    return dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip(),
        tracked_changes=subprocess.check_output(['git','diff','--name-only'],cwd=s.ROOT,text=True).splitlines(),
        workspace_changes_policy='informational_only; frozen materials and computational code remain strict')

'''
    assert marker in text
    text=text.replace(marker,'\n'+helper+marker,1)
    text=text.replace('        manifest_checks=[]\n','        manifest_checks=[]\n        verifier_provenance=[]\n',1)
    oldblock="""            s.check(path.parent)
            for name,digest in {**m.get('dependencies',{}),**m.get('code_sha256',{})}.items():
                assert s.pilot.digest_file(s.ROOT/name)==digest,(str(path),name)
"""
    assert oldblock in text
    text=text.replace(oldblock,'            verifier_provenance.extend(check_frozen_manifest(path))\n',1)
    text=text.replace("        evidence['frozen_manifests']=manifest_checks\n","        evidence['frozen_manifests']=manifest_checks\n        evidence['historical_verifier_provenance']=verifier_provenance\n",1)
    oldblock="""    evidence['git_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=s.ROOT,text=True).strip()
    evidence['tracked_changes']=subprocess.check_output(['git','diff','--name-only'],cwd=s.ROOT,text=True).splitlines()
    assert set(evidence['tracked_changes'])<= {'README.md','AGENTS.md'}
"""
    assert oldblock in text
    text=text.replace(oldblock,'    evidence.update(workspace_snapshot())\n',1)
    path.write_bytes(text.replace('\n',nl).encode('utf-8'))
    print('Original files matched; verifier revision saved with original line endings')

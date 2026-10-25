from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import json,hashlib,sys,difflib,shutil
ROOT=Path('D:/Research-VeriFact'); OUT=ROOT/'outputs/009_retrieval_baselines'; TMP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tasks/009_retrieval_baselines'))
import study009 as s
import verify009 as v
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
new=read(OUT/'revision_001/handoff.json'); old=read(OUT/'handoff_001.json')
assert all(sha(ROOT/p)==h for p,h in new['files'].items())
changed=[p for p,h in old['files'].items() if sha(ROOT/p)!=h]
assert set(changed)=={'tasks/009_retrieval_baselines/verify009.py','tasks/009_retrieval_baselines/README.md','outputs/009_retrieval_baselines/README.md'}
original=OUT/'revision_001/original_verify009.py.txt'
source=ROOT/'tasks/009_retrieval_baselines/verify009.py'
assert sha(original)==old['files']['tasks/009_retrieval_baselines/verify009.py']
before=read(OUT/'revision_001/before.json')['preserved_review_files']
assert all(sha(ROOT/p)==h for p,h in before.items())
result={'head':v.workspace_snapshot()['git_head'],'revision_handoff_sha256':sha(OUT/'revision_001/handoff.json'),
    'revision_handoff_files_matched':len(new['files']),'old_handoff_changed':changed,'old_handoff_unchanged':len(old['files'])-len(changed),
    'old_verifier_snapshot_matches':True,'prior_audit_files_preserved':len(before),'negative_controls':[],'inference_calls':0}
(TMP/'actual_verifier.diff').write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True),source.read_text().splitlines(True),fromfile='historical',tofile='revision')),encoding='utf-8')
def reject(name,call):
    try:call()
    except (ValueError,AssertionError):result['negative_controls'].append(name)
    else:raise AssertionError('Accepted corruption: '+name)
with ExitStack() as stack:
    for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
        stack.enter_context(patch(target,side_effect=AssertionError('No audit network')))
    # Build independent fixtures with real frozen-manifest structures. Successful
    # checks precede mutations and run again after byte-for-byte restoration.
    fixture=TMP/'fixture'; fixture.mkdir()
    code=fixture/'tasks/009_retrieval_baselines/verify009.py';code.parent.mkdir(parents=True)
    computation=fixture/'score.py'; config=fixture/'config.json'; code.write_text('old verifier');computation.write_text('frozen score');config.write_text('{}')
    target=fixture/'selfcheck';target.mkdir()
    for name in ('input.json','receipt.json','predictions.csv'):(target/name).write_text('original '+name)
    (target/'verification.json').write_text(json.dumps({'self_check_not_independent_audit':True}))
    with patch.object(s,'ROOT',fixture):
        s.seal(target,[config],[code,computation])
        code.write_text('new verifier')
        assert v.check_frozen_manifest(target/'manifest.json')[0]['matches'] is False
        for p in [target/'input.json',target/'receipt.json',target/'predictions.csv',target/'verification.json',computation,config]:
            raw=p.read_bytes();p.write_bytes(raw+b' changed')
            reject(p.name,lambda:v.check_frozen_manifest(target/'manifest.json'))
            p.write_bytes(raw);v.check_frozen_manifest(target/'manifest.json')
        experimental=fixture/'experiment';experimental.mkdir();(experimental/'predictions.csv').write_text('original')
        s.seal(experimental,[],[code]);raw=code.read_bytes();code.write_bytes(raw+b' changed')
        reject('verifier bound as experimental computation',lambda:v.check_frozen_manifest(experimental/'manifest.json'))
        code.write_bytes(raw)
        dependency=fixture/'selfcheck_dependency';dependency.mkdir();(dependency/'verification.json').write_text(json.dumps({'self_check_not_independent_audit':True}))
        s.seal(dependency,[code],[]);code.write_bytes(raw+b' changed')
        reject('verifier listed as strict dependency',lambda:v.check_frozen_manifest(dependency/'manifest.json'))
        code.write_bytes(raw)
    snap=v.workspace_snapshot();assert 'reviews/README.md' in snap['tracked_changes']
    result['actual_workspace_snapshot']=snap
    with patch.object(v.subprocess,'check_output',side_effect=['head\n','reviews/README.md\nreviews/new.md\nsrc/unrelated.py\n']):
        assert 'src/unrelated.py' in v.workspace_snapshot()['tracked_changes']
    result['unrelated_workspace_changes_informational']=True
    print('Revision hashes, restricted exception and eight negative controls verified',flush=True)
    # The only adaptation is the output guard, keeping all replay computation
    # and checks unchanged while placing new artifacts outside the repository.
    text=source.read_text(encoding='utf-8'); oldguard='assert output.is_relative_to(s.OUT) and not output.exists()'
    assert text.count(oldguard)==1
    scope={'__file__':str(source),'__name__':'independent_revision_replay'}
    exec(compile(text.replace(oldguard,'assert not output.exists()'),str(source),'exec'),scope)
    scope['run'](TMP/'replay',True)
    replay=read(TMP/'replay/verification.json')
    assert replay['tests']['success'] and replay['tests']['run']==146
    assert 'reviews/README.md' in replay['tracked_changes']
    assert (TMP/'replay/manifest.json').is_file()
    result['tests']=replay['tests']
    result['replay_files_identical']=sum(len(x) for x in replay['byte_identical_replays'].values());assert result['replay_files_identical']==109
    assert (TMP/'replay/provider_token_accounting.csv').read_bytes()==(OUT/'verification_001/provider_token_accounting.csv').read_bytes()
    result['provider_tokens_unchanged']=True;result['historical_verifier_provenance']=replay['historical_verifier_provenance']
    result['replay_complete_with_review_index_modified']=True
assert all(sha(ROOT/p)==h for p,h in new['files'].items())
result['revision_handoff_unchanged_after_audit']=True
(TMP/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:val for k,val in result.items() if k!='historical_verifier_provenance'},ensure_ascii=False,indent=2),flush=True)

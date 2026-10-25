from pathlib import Path
import sys,json,subprocess,hashlib,socket
ROOT=Path('D:/Research-VeriFact');TEMP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tasks/014_qwen27b_baseline_comparison'))
sys.path.insert(0,str(ROOT/'tasks/015_disagreement_adjudication'))
import common014,common015,verify014,verify015
original=Path.relative_to
def relative(self, other, *args):
    try:return original(self,other,*args)
    except ValueError:
        if str(self).startswith(str(TEMP)) and Path(other)==ROOT:return self
        raise
Path.relative_to=relative
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('Network blocked'))
results={}
for number,module,verify in [('014',common014,verify014),('015',common015,verify015)]:
    original_hash=common014.file_hash
    replacement=TEMP/('reviews_README_'+number+'.md')
    replacement.write_bytes((ROOT/'reviews/README.md').read_bytes()+b'\n<!-- independent audit index addition -->\n')
    def routed(path):
        return original_hash(replacement if Path(path).resolve()==(ROOT/'reviews/README.md').resolve() else path)
    common014.file_hash=routed
    try:
        verify.verify(TEMP/('negative_index_final_'+number))
    except ValueError as exc:
        results[number]=dict(index_edit_blocked=True,error=str(exc))
    else:results[number]=dict(index_edit_blocked=False)
    finally:common014.file_hash=original_hash
    history=module.read(module.OUT/'preparation_001/history_sha256.json')
    results[number]['locked_mutable_paths']=[p for p in history if p=='.gitattributes' or p.startswith('reviews/') or p.endswith('/README.md')]
prefix=TEMP/'checkout_final';prefix.mkdir()
target='tasks/014_qwen27b_baseline_comparison/common014.py'
subprocess.run(['git','checkout-index','--prefix='+prefix.as_posix()+'/','--',target],cwd=ROOT,check=True,capture_output=True)
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results['checkout']=dict(path=target,core_autocrlf=subprocess.check_output(['git','config','--get','core.autocrlf'],cwd=ROOT).decode().strip(),
    working_sha256=hashfile(ROOT/target),checkout_sha256=hashfile(prefix/target),
    same_bytes=(ROOT/target).read_bytes()==(prefix/target).read_bytes())
summary={k:{a:b for a,b in v.items() if a!='locked_mutable_paths'} for k,v in results.items()}
(TEMP/'negative_final.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))

"""Compile-only extension check; does not read results, prepare data or run code."""
from pathlib import Path
import ast,json


def main():
    root=Path(__file__).resolve().parents[2]
    files=['prepare_eval140.py','worker_eval140.py']
    for name in files:
        path=Path(__file__).parent/name;source=path.read_text(encoding='utf-8')
        ast.parse(source,filename=str(path));compile(source,str(path),'exec')
        assert not path.read_bytes().startswith(b'\xef\xbb\xbf')
    source=(Path(__file__).parent/'worker_eval140.py').read_text(encoding='utf-8')
    assert "job['task']==140 and arm=='kl_anchor'" in source
    assert 'dict(task=138' not in source and 'from prompt136 import prompt_ids' in source
    assert 'adapter_sha256' in source and "'batches'" in source
    from prepare_eval140 import render_template
    templates=root/'.local_models/138_rationale_tasks/extension/templates'
    for name in ('start.py','monitor.py'):
        rendered=render_template((templates/name).read_text(encoding='utf-8-sig'))
        ast.parse(rendered)
        assert 'outputs/138_rationale_tasks' not in rendered
        assert 'worker_eval138.py' not in rendered and 'verifact138_eval_' not in rendered
        if name=='monitor.py':
            assert "P=R/'.local_models/140_kl_anchor/extension'/args.scope" in rendered
            assert "O=R/'outputs/140_kl_anchor'" in rendered
    print(json.dumps(dict(status='COMPILE_PASS',task=140,files=files,
        rendered_template_paths_checked=True,prepared_or_packed=False,GPU_or_SSH_called=False,checkpoint_not_required_for_compile=True)))


if __name__=='__main__':main()

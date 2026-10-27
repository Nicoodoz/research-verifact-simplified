import shutil,tarfile,json
import common103 as c
def main():
 src=c.PRIVATE/'bundle';dest=c.PRIVATE/'bundle_a800';shutil.copytree(src,dest)
 plan=c.read(dest/'gpu_plan.json');plan.update(candidates=['qwen3.5-9b','qwen3.8-27b'],unresolved_neighbour='qwen3.6-35b-a3b',hardware_branch='A80080GB_fallback_before_training',reason='same BF16 r16 full-expert MoE memory not guaranteed on80GB; no lower precision or truncation')
 (dest/'gpu_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 manifest=dict(files={p.name:c.sha(p) for p in dest.iterdir() if p.is_file() and p.name!='manifest.json'},private_clinical_data=True)
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 target=c.PRIVATE/'gpu_bundle_a800.tar.gz'
 with tarfile.open(target,'w:gz') as t:t.add(dest,arcname='bundle')
 c.put(c.OUT/'a800_fallback_manifest.json',dict(utc=c.utc(),sha256=c.sha(target),bytes=target.stat().st_size,candidates=plan['candidates'],before_GPU=True,only_if_primary96GB_unavailable=True,shared_GPU_cap_cny=60,shared_GPU_hours=8,files=manifest['files']))
 print('A800 fallback bundle ready, no GPU execution')
if __name__=='__main__':main()

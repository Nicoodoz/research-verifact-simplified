"""Register tested postprocessing implementation before any reserved GT join."""
import common036 as c
import api036 as a
def archive_before():
    out=c.OUT/'evaluation_freeze_001/import_fix_before_sources';assert not out.exists()
    expected=c.read(c.OUT/'evaluation_freeze_001/implementation_repair.json')['before_sha256']
    blocks={'predict036.py':("from numerics036 import old,l,cal\n", "sys.path.insert(0,str(c.ROOT/'tasks/035_lambda_boundary_calibration'))\nimport common as old\nimport learning as l\nsys.path.insert(0,str(c.ROOT/'tasks/022_competition_aware_support_calibration'))\nimport calibration022 as cal\n"),'evaluate036.py':("from numerics036 import old,a\n", "sys.path.insert(0,str(c.ROOT/'tasks/035_lambda_boundary_calibration'))\nimport common as old\nimport analysis as a\n")}
    for name,(after,before) in blocks.items():
        text=(c.TASK/name).read_text(encoding='utf-8');assert text.count(after)==1;reconstructed=text.replace(after,before)
        import hashlib
        assert hashlib.sha256(reconstructed.encode()).hexdigest()==expected[name].lower()
        c.write_text(out/name,reconstructed)
    c.write_text(out/'README.md','# 导入修复前代码\n\n从当前文件恢复原导入语句，所得完整文件SHA256与首次失败前记录逐字节一致。这是可验证的旧版本恢复，保存时间晚于修复；不是新的研究版本，不应运行或用于结果。当前正式实现见tasks/036中的同名文件与numerics036.py。\n')
    c.put(out/'manifest.json',dict(created_utc=c.now(),reconstruction_checked_against_pre_fix_hash=True,files={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('Exact pre-fix source bytes archived and hash-verified.')
def main():
    out=c.OUT/'evaluation_freeze_001';assert not out.exists() and not (c.OUT/'predictions_blind_001').exists()
    files=[c.TASK/n for n in ('predict036.py','evaluate036.py','numerics036.py','test036.py')]
    c.put(out/'implementation_repair.json',dict(created_utc=c.now(),issue='Generic common.py import collision: API retrieval imported a different historical common before035 numerics. Three pre-evaluation unit checks errored; no reserved metrics produced.',before_sha256={'predict036.py':'AEFEB28848F3131A78F6D3923EBF488422544B30781D6D3199039246DFA9C743','evaluate036.py':'4B0F168D8DF22C3575DB0742033152680BE7A2D3093AAD15C716B83A301B46F5'},fix='Import035 helpers by unique module aliases and temporarily bind their common dependency during import only.',verification='7 tests PASS, includes all3675 development predictions against035 infer and all370 candidate Gate features against031 inference',scientific_definition_changed=False,reserved_GT_used=False))
    cfg=a.api.load_config(c.ROOT/'.env.aliyun')
    c.put(out/'service_registration.json',dict(created_utc=c.now(),aliyun_base_url=cfg.base_url,models=a.api.MODELS,SiliconFlow_BGE_models=[a.api.old.baseline.EMBED_MODEL,a.api.old.baseline.RERANK_MODEL],credential_values_not_recorded=True,model_return_mismatch_stops=True,price_documentation_checked=True))
    c.put(out/'manifest.json',dict(created_utc=c.now(),sha256={str(p.relative_to(c.ROOT)):c.sha(p) for p in files},reserved_performance_available=False))
    print('Prediction and evaluation code sealed before reserved labels; endpoint registered without credentials.')
if __name__=='__main__':
    import sys
    archive_before() if '--archive-before' in sys.argv else main()

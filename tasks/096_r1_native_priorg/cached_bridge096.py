"""Offline078 published-reference + V4 bridge; no new inference or selection."""
import sys
import common096 as c
from live_run096 import O
sys.path.insert(0,str(c.ROOT/'src'));sys.path.insert(0,str(c.ROOT/'tasks/095_anchored_minimal_contrast'))
from metrics095 import score,paired
def main():
    src=c.ROOT/'outputs/078_component_ablation/predictions.jsonl';rows=c.lines(src);out=[];invalid=[];sources={str(src.relative_to(c.ROOT)):c.sha(src)}
    for r in rows:
        if 'RT' not in r['arms']:continue
        if not all(r['arms'][a]['valid'] for a in ['TS','RT']):invalid.append(r['id']);continue
        for arm in ['TS','RT']:
            z=r['arms'][arm];rq=c.read(c.ROOT/z['request_source']);b=rq['job']['body']
            #078 canonical request hash uses its native implementation.
            sys.path.insert(0,str(c.ROOT/'tasks/078_component_ablation'))
            import common078
            assert common078.digest(b)==z['body_sha256'];assert b['model']=='deepseek-v4-flash-0731'
            sources[z['request_source']]=c.sha(c.ROOT/z['request_source']);sources[z['receipt_source']]=c.sha(c.ROOT/z['receipt_source'])
        out.append(dict(id=r['id'],sid=r['sid'],GT=r['GT'],author=r['author'],predictions={name:r['methods'][old]['label'] for name,old in [('Original','Original'),('published_reference_V4_raw','RT_raw'),('C48_V4_raw','TS_raw'),('published_reference_V4_PriorG','RT_PriorG'),('C48_V4_PriorG','TS_PriorG')]},probabilities={}))
    models=list(out[0]['predictions']);data=dict(status='REUSED_078_NO_NEW_CALLS',historical_full_panel=192,common_TS_RT_core_N=len(out),excluded_invalid_ids=invalid,new_API_cost=0,metrics=score(out,models),paired_raw=paired(out,'published_reference_V4_raw','C48_V4_raw'),paired_final=paired(out,'published_reference_V4_PriorG','C48_V4_PriorG'),source_sha256=sources,not_original_full_pipeline=True,not_current096_natural_panel=True)
    c.put(O/'cached_published_reference_bridge.json',data);c.putl(O/'cached_bridge_predictions.jsonl',out)
    c.write(O/'optional_bridge.md',f'''# Published-reference + V4 bridge（历史078复用）

复用原192条桥接，TS/RT共同核心有效{len(out)}条；剔除无效，不沿用旧表fallback。078每患者GT盲hash抽取8条，共24患者。此为历史单独队列，不能冒充096新自然面板，也不是完整Original VeriFact pipeline + V4。

原claim、发布reference不裁剪，使用本研究deepseek-v4-flash-0731 T-S核验提示；与C48＋同T-S比较。精确请求/回执哈希已核对，统计与患者配对区间见cached_published_reference_bridge.json。新增API为0，不部署检索或辅助模型。

旧零API准备中的Original-style不可行说明针对完整原Judge链，本次附件明确允许published-reference桥接，因此直接复用已经合法运行的078，不重复调用。''')
    print('CACHED_BRIDGE_READY',len(out))
if __name__=='__main__':main()

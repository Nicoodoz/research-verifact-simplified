import common092 as c
models=[('BAAI/bge-m3','bge-m3/pytorch_model.bin','5617a9f61b028005a4858fdac845db406aefb181','b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38'),('BAAI/bge-reranker-v2-m3','bge-reranker-v2-m3/model.safetensors','953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e','d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286')]
records=[]
for model,relative,revision,expected in models:
    path=c.ROOT/'.local_models/021'/relative;actual=c.sha(path);assert actual==expected,model
    records.append(dict(model=model,revision=revision,weights_sha256=actual,bytes=path.stat().st_size,dtype='float16',local_files_only=True))
c.put(c.OUT/'local_retrieval_provenance.json',dict(models=records,embedding_pooling='CLS + L2 normalize',rerank_order='raw local logits; same deterministic C48 packing',candidate_rule='009 alternate dense and BM25 until 48 unique passages',packing_code_sha256=c.sha(c.ROOT/'tasks/008_retrieval_planning/planning_core.py'),candidate_code_sha256=c.sha(c.ROOT/'tasks/009_retrieval_baselines/study009.py'),equivalence_warning='021 final embedding used FP32; this task explicitly uses local FP16 for newly materialized 20 exploration patients. No API equivalence claim. Both verifier arms see identical frozen references.',price_cny=0))
print('Existing BGE weight hashes verified')

"""Resume only the four before models after completed input/protocol freeze."""
import common031 as c
def run():
    freeze=c.read(c.OUT/'freeze_001/manifest.json')
    for p,h in freeze['sha256'].items():c.require(c.sha(c.ROOT/p)==h,'Frozen preparation changed')
    c.require(not (c.OUT/'attempts').exists(),'Before models must precede031 API')
    train=c.lines(c.base.PREP/'features.jsonl');config=c.read(c.base.PREP/'config.json');test=c.read(c.OUT/'planning_001/split.json')['confirmation12']
    for method in ('A','B','C','D'):
        path=c.OUT/'before_models'/f'{method}.json'
        if path.exists():continue
        fitted=c.learning.fold(train,[],c.base.FEATURES[method],'Logistic',config,test);c.put(path,dict(method=method,training_scope='original16,15 candidate-bearing',**fitted))
    c.put(c.OUT/'before_models/manifest.json',dict(created_utc=c.now(),files={p.name:c.sha(p) for p in (c.OUT/'before_models').iterdir() if p.is_file()},precedes_new_API=True));print('All four original-training Gates frozen before031 API')
if __name__=='__main__':run()

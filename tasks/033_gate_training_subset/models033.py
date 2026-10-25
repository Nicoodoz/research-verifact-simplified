"""Cache exact training-patient/model recipes, reusing030/031 before fitting."""
import common033 as s

class Models:
    def __init__(self,rows):
        self.rows=rows;old_order=[r['proposition_id'] for r in s.lines(s.old.PREP/'features.jsonl')];allf={r['proposition_id']:r for r in s.candidate_rows(rows)};self.features=[allf[p] for p in old_order]+[r for r in s.candidate_rows(rows) if r['proposition_id'] not in set(old_order)];self.subjects={r['subject_id'] for r in rows};self.active={r['subject_id'] for r in self.features};self.config=s.read(s.c.PREP/'config.json');self.registry={};self.usage={};self.new=0;self.new_inner=0
        for mid,m in s.read(s.HIST/'model_index.json').items():self.registry[mid]=s.HIST/'models'/f'{mid}.json'
        for era in ('before','after'):
            for method in ('A','B','D'):
                p=s.P31/(era+'_models')/(method+'.json');m=s.read(p);self.registry[s.old.model_id(method,m['final_fit']['training_patients'])]=p
        for p in (s.OUT/'models').glob('*.json'):self.registry[p.stem]=p;self.new+=1;self.new_inner+=len(s.read(p)['inner_folds'])
    def get(self,method,patients):
        active=sorted(set(patients)&self.active);mid=s.old.model_id(method,active);train=[r for r in self.features if r['subject_id'] in active];p=self.registry.get(mid)
        if p is None:
            s.require(self.new<350,'Prespecified new final fit limit350 reached');s.require(all(r['human_gt'] in s.LABELS for r in train),'Cannot fit blinded patients before selection freeze');model=s.old.learning.fold(train,[],s.c.FEATURES[method],'Logistic',self.config,self.subjects-set(active));p=s.OUT/'models'/f'{mid}.json';s.put(p,dict(method=method,model_id=mid,**model));self.registry[mid]=p;self.new+=1;self.new_inner+=len(model['inner_folds'])
        model=s.read(p);meta=model['final_fit'];s.require(set(meta['training_ids'])=={r['proposition_id'] for r in train} and meta['features']==s.c.FEATURES[method],'Cache identity mismatch');self.usage[mid]=dict(path=p.relative_to(s.ROOT).as_posix(),sha256=s.sha(p),method=method,patients=active,n=meta['n'],R=meta['R'],threshold=model['threshold'],new_final_fit=p.parent==s.OUT/'models')
        return model,mid
    def save(self,name):s.put(s.OUT/name,dict(created_utc=s.now(),new_final_fits=self.new,new_inner_fits=self.new_inner,total_new_fit_states=self.new+self.new_inner,used_models=self.usage,API_calls=0))

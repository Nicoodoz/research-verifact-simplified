"""Serialize independent, GT-blind retrospective construction-quality observations."""
import json,hashlib,re,sqlite3
from pathlib import Path
R=Path(__file__).resolve().parents[2];P=R/'.local_models/095';O=R/'outputs/095_anchored_minimal_contrast';D=Path(__file__).parent
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def h(s):return hashlib.sha256(s.encode()).hexdigest()
observations=[
('good',[1,2,4],'仅换药物身份，另一个药名明确来自同一门诊用药获取事件，引用保留未能取得处方的否定语境。这里good只表示是可核对的同事件实体对照，不证明替代命题被支持；原本剂量限定也未获新证据认证。'),
('unknown',[8],'过去能耐受与此前耐受的差异可能只是重述/时间具体化。出处和事件存在，但原claim没有明确参照时点，不能确认构成有实质辨识力的时间差异。'),
('good',[1],'同一精神状态改变的另一原因在原文明确以可能性语气记载，替换保留原来的可能性限定，其他关系不变。不是用另一患者或单纯药名共现拼接。'),
('good',[2,12],'对疾病陈述增加入院时点，来源明确将该疾病与原次住院的入院事件连接。仅作时间限定差异，不能由此推断现在一定没有疾病，也不是已认证负例。'),
('unknown',[4,7,8,11,14],'实际变化是附加既往手术日期，但构造器标为entity；来源确认手术日期而未确认首次入院日期，原句日期附着又有歧义。历史与本次入院并存，不宜把它视作已确认的单事件时间对照。'),
('definite_violation',[5],'把初始低血压及其数值整个搬入仍保留复苏后限定的句子，同时改状态、数值和隐含时点。来源值虽真实，保留的时间条件不兼容。'),
('good',[5,9],'仅替换手术日期，手术接收事件、具体手术及术后天数相互印证，同一手术的日期有原文锚定。原claim日期保持不变，不用新假设改标原命题。'),
('definite_violation',[8],'把宽泛运动及反应表现替为睁眼和不发声两个可独立成立的观察，同时换具体表现与否定语音状态；一个文本跨度隐藏多个属性，不满足本轮单属性要求。'),
('unknown',[1,2,5,6,8],'替代数值是后续累计补液总量，原命题没有时间或累计范围。当前资料存在不同阶段的补液，不能确认替代与原数量属于同一计量事件；不能因数值不同即算反证。'),
('definite_violation',[2,7],'替换药物执行状态时一并删除原有家用方案、剂量与给药频率限定。即使停药有出处，也不是保留其他属性的最小差异。'),
('unknown',[1],'新增相对日期来自来源中的当天，原claim无叙述参照日期；复制相对词并不自动保留其时间指代。不能确认只增加了可靠单属性信息而未引入指代歧义。'),
('unknown',[3,4,6,13,14],'早期影像的动态改善与更晚影像的少量残留均真实。对照把变化趋势换成某时点残留程度，原claim未限定单次检查，难确认属于同一属性/同一检查事件。两说法可同时成立不是失败原因，缺少事件绑定才是限制。')
]
sample=[x for x in rows(O/'construction_quality_sample.jsonl') if x['reviewer']=='independent_source_reviewer'];inputs={x['id']:x for x in rows(P/'screen_inputs.jsonl')};checked={x['id']:x for x in rows(P/'checked.jsonl')}
assert len(sample)==len(observations)==12
out=[]
for row,(judgment,ids,note) in zip(sample,observations):
    pid=row['id'];ref=inputs[pid]['reference'];v=checked[pid];assert v['operated']
    ms=list(re.finditer(r'(?m)^(\d+)\. Date:',ref));entries={int(m.group(1)):ref[m.start():ms[k+1].start() if k+1<len(ms) else len(ref)] for k,m in enumerate(ms)}
    citations=[]
    for no in ids:
        e=entries[no];span=re.search(r'Raw characters: \[(\d+),(\d+)\)',e);raw=e.split(' | Text: ',1)[1][:int(span.group(2))-int(span.group(1))]
        citations.append(dict(reference_id=no,note_id=re.search(r'Note ID: ([^,]+)',e).group(1),raw_text_sha256=h(raw),source_entry_sha256=h(e)))
    out.append(dict(id=pid,panel=row['panel'],reviewer='independent_source_reviewer',judgment=judgment,observation_zh=note,citations=citations,claim_sha256=h(inputs[pid]['text']),reference_sha256=h(ref),alternative_sha256=h(v['alternative']),GT_read=False,classification_predictions_read=False,deployment_permission=False,medical_gold=False))
with (D/'construction_quality_review.jsonl').open('x',encoding='utf-8',newline='\n') as f:
    for row in out:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
con=sqlite3.connect('file:'+str(P/'budget.sqlite').replace('\\','/')+'?mode=ro',uri=True);reuse=[]
for j in rows(P/'check_pilot_jobs.jsonl'):
    n,ok=con.execute('select count(*),sum(status=200) from attempts where rid=?',(j['request_id'],)).fetchone();assert (n,ok)==(1,1)
    reuse.append(dict(id=j['id'],request_id=j['request_id'],attempts=n,HTTP200=ok))
con.close()
with (D/'pilot_checker_reuse_check.json').open('x',encoding='utf-8') as f:json.dump({'four_original_checker_calls_not_repeated':reuse},f,indent=2)
print({j:sum(r['judgment']==j for r in out) for j in ['good','definite_violation','unknown']})

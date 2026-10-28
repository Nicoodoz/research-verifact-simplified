"""Inventory only the original 103 training 512 and prepare GT-blind review material."""
from collections import Counter, defaultdict
from itertools import combinations
import csv
import re
import duckdb
import common104 as c

S_SEED = '104_review_s_v1'
ORDER_SEED = '104_blind_order_v1'
RATER = 'v1.1.0-rater-121'

def quote_candidates(text, reference):
    """Literal quotation provenance only; never semantic correctness certification."""
    result = []
    for match in re.finditer(r'"([^"\n]{8,1000})"|“([^”\n]{8,1000})”', text or ''):
        quote = match.group(1) or match.group(2)
        start = reference.find(quote)
        result.append(dict(quote=quote, start=start if start >= 0 else None,
                           end=start + len(quote) if start >= 0 else None,
                           exact_source_match=start >= 0))
    return result

def normalize(text):
    return ' '.join(re.findall(r'[a-z]+|\d+(?:\.\d+)?', text.lower()))

def main():
    original = c.ROOT / '.local_models/103_lora_selection/train512.jsonl'
    public_source = c.ROOT / 'outputs/103_lora_selection/train512_ids.jsonl'
    freeze103 = c.read(c.ROOT / 'outputs/103_lora_selection/data_freeze.json')
    assert c.sha(original) == freeze103['files'][original.relative_to(c.ROOT).as_posix()]
    rows = c.lines(original)
    public = {r['id']: r for r in c.lines(public_source)}
    roles = c.read(c.ROOT / 'outputs/103_lora_selection/patient_roles.json')['patients']
    train_patients = set(roles['train'])
    assert len(rows) == len(public) == 512
    assert {r['sid'] for r in rows} <= train_patients
    assert not train_patients & (set(roles['selection']) | set(roles['confirmation']))
    assert Counter(r['GT'] for r in rows) == dict(zip(c.LABELS, [320, 96, 96]))
    for row in rows:
        source = public[row['id']]
        assert row['role'] == 'train'
        assert all(row[k] == source[k] for k in ['GT', 'author', 'sid', 'reference_id'])
        assert c.digest(row['claim']) == source['claim_sha256']
        assert c.digest(row['reference']) == source['reference_sha256'] == row['reference_id']

    selected = [r for r in rows if r['GT'] != 'Supported']
    selected += sorted([r for r in rows if r['GT'] == 'Supported'], key=lambda r: c.digest(S_SEED + r['id']))[:96]
    selected = sorted(selected, key=lambda r: c.digest(ORDER_SEED + r['id']))
    assert Counter(r['GT'] for r in selected) == dict(zip(c.LABELS, [96, 96, 96]))
    blind = [dict(review_index=i+1, **{k: r[k] for k in ['id', 'sid', 'author', 'claim', 'reference', 'reference_id']}, reference_sha256=c.digest(r['reference'])) for i, r in enumerate(selected)]
    key = [dict(review_index=i+1, id=r['id'], GT=r['GT']) for i, r in enumerate(selected)]
    c.putl(c.PRIVATE/'blind_cases.jsonl', blind)
    c.putl(c.PRIVATE/'gt_key.jsonl', key)
    c.putl(c.PRIVATE/'train512_original.jsonl', rows)
    print(c.canonical(dict(blind_ready=True, N=len(blind), reference_characters=sum(len(r['reference']) for r in blind))), flush=True)

    raw = c.ROOT / 'data/00_raw/verifact-bhc/1.1.0'
    with duckdb.connect() as db:
        db.execute('CREATE TEMP TABLE wanted(id VARCHAR, reference_id VARCHAR)')
        db.executemany('INSERT INTO wanted VALUES (?,?)', [(r['id'],r['reference_id']) for r in rows])
        payloads = dict(db.execute('SELECT p.reference_id,p.reference FROM read_parquet(?) p JOIN (SELECT DISTINCT reference_id FROM wanted) w USING(reference_id)', [str(raw/'verifact/reference_payloads.parquet')]).fetchall())
        props = db.execute('SELECT p.proposition_id,p.text,p.subject_id,p.author_type FROM read_csv_auto(?,all_varchar=true) p JOIN wanted w ON p.proposition_id=w.id', [str(raw/'propositions/propositions.csv.gz')]).fetchall()
        doctors_cursor = db.execute('SELECT p.* FROM read_csv_auto(?,all_varchar=true) p JOIN wanted w ON p.proposition_id=w.id', [str(raw/'propositions/human_verdicts.csv.gz')])
        doctor_columns = [d[0] for d in doctors_cursor.description]
        doctors = {r[0]:dict(zip(doctor_columns,r)) for r in doctors_cursor.fetchall()}
        teachers_cursor = db.execute('SELECT v.* FROM read_parquet(?) v JOIN wanted w ON v.proposition_id=w.id WHERE v.reference_id=w.reference_id ORDER BY v.proposition_id,v.rater_alias', [str(raw/'verifact/verdicts.parquet')])
        teacher_columns = [d[0] for d in teachers_cursor.description]
        teachers = [dict(zip(teacher_columns,r)) for r in teachers_cursor.fetchall()]
        allteacher_counts = db.execute('SELECT v.proposition_id,count(*),sum(CASE WHEN v.reference_id=w.reference_id THEN 1 ELSE 0 END) FROM read_parquet(?) v JOIN wanted w ON v.proposition_id=w.id GROUP BY v.proposition_id', [str(raw/'verifact/verdicts.parquet')]).fetchall()
        schemas = {name:db.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(raw/'verifact'/name)]).fetchall() for name in ['verdicts.parquet','reference_payloads.parquet']}
    props = {r[0]:r for r in props}
    lookup = {r['id']:r for r in rows}
    teacher_by_id = defaultdict(list)
    for t in teachers:
        r = lookup[t['proposition_id']]
        assert payloads[t['reference_id']] == r['reference']
        t['prediction_matches_GT'] = t['verdict'] == r['GT']
        t['reference_sha256'] = c.digest(r['reference'])
        t['claim_sha256'] = c.digest(r['claim'])
        t['reason_quotes'] = quote_candidates(t['reason'], r['reference'])
        t['source_claim_reference_verified'] = True
        teacher_by_id[t['proposition_id']].append(t)
    c.putl(c.PRIVATE/'teachers_same_reference.jsonl', teachers)
    c.putl(c.PRIVATE/'doctor_annotations_train512.jsonl', [doctors[r['id']] for r in rows])
    c.put(c.OUT/'source_schema.json', dict(parquet=schemas, doctor_columns=doctor_columns, excluded_raw_columns=['parent_text_chunk','brief_hospital_course'], outside_train_clinical_text_read=False))

    exact = defaultdict(list)
    normalized = defaultdict(list)
    same_reference = defaultdict(list)
    for r in rows:
        exact[c.digest(r['claim'])].append(r['id'])
        normalized[c.digest(normalize(r['claim']))].append(r['id'])
        same_reference[r['reference_id']].append(r['id'])
    near=[]
    by_patient=defaultdict(list)
    for r in rows:by_patient[r['sid']].append(r)
    for patient_rows in by_patient.values():
        for a,b in combinations(patient_rows,2):
            left,right=set(normalize(a['claim']).split()),set(normalize(b['claim']).split())
            j=len(left&right)/max(1,len(left|right))
            if j>=.8 and a['claim']!=b['claim']:
                near.append(dict(first=a['id'],second=b['id'],token_set_jaccard=j,same_GT=a['GT']==b['GT'],same_reference=a['reference_id']==b['reference_id']))
    near_map=defaultdict(list)
    for pair in near:
        near_map[pair['first']].append(pair['second']);near_map[pair['second']].append(pair['first'])

    selected_ids={r['id'] for r in selected}
    allcounts={pid:(alln,samen) for pid,alln,samen in allteacher_counts}
    inventory=[]
    for r in rows:
        pid=r['id'];d=doctors[pid];prop=props[pid];ts=teacher_by_id[pid]
        assert prop[1]==r['claim'] and str(prop[2])==r['sid'] and prop[3]==r['author']
        assert d['text']==r['claim'] and d['human_gt']==r['GT']
        assert payloads[r['reference_id']]==r['reference']
        main=[t for t in ts if t['rater_alias']==RATER]
        assert len(main)==1 and main[0]['verdict']==r['paper_r1']
        matches=[t for t in ts if t['prediction_matches_GT'] and t.get('reason')]
        mainreason=main[0]
        counts=Counter(v for k,v in d.items() if re.fullmatch(r'verdict[1-5]',k) and v)
        inv={k:r[k] for k in ['id','sid','GT','author','reference_id','role']}
        inv.update(claim_sha256=c.digest(r['claim']),reference_sha256=c.digest(r['reference']),claim_chars=len(r['claim']),reference_chars=len(r['reference']),reference_utf8_bytes=len(r['reference'].encode()),reference_word_proxy=len(re.findall(r'\S+',r['reference'])),review_selected=pid in selected_ids,semantic_review_status='pending' if pid in selected_ids else 'not_selected_224S',round1_num_raters_agree=d['round1_num_raters_agree'],round1_majority_vote=d['round1_majority_vote'],round2_decision=d['round2_decision'],doctor_vote_counts=dict(counts),doctor_comments_present=sum(bool(d.get(k)) for k in ['comment1','comment2','comment3','comment4','comment5','adjudicated_comment']),paper_r1_prediction=mainreason['verdict'],paper_r1_matches_GT=mainreason['prediction_matches_GT'],paper_r1_reason_present=bool(mainreason.get('reason')),paper_r1_reasoning_chain_present=bool(mainreason.get('reasoning_chain')),paper_r1_reasoning_final_answer_present=bool(mainreason.get('reasoning_final_answer')),all_published_teacher_rows=allcounts[pid][0],same_reference_teacher_rows=len(ts),same_reference_correct_reason_candidates=len(matches),same_reference_correct_reason_models=sorted({t['model'] for t in matches}),explicit_quote_candidates=sum(len(t['reason_quotes']) for t in matches),explicit_quote_exact_matches=sum(sum(q['exact_source_match'] for q in t['reason_quotes']) for t in matches),claim_exact_duplicate_count=len(exact[c.digest(r['claim'])])-1,normalized_duplicate_count=len(normalized[c.digest(normalize(r['claim']))])-1,near_duplicate_ids=near_map[pid],same_reference_other_claims=len(same_reference[r['reference_id']])-1)
        inventory.append(inv)
    c.putl(c.PRIVATE/'asset_inventory512.jsonl', [dict(r,claim=lookup[r['id']]['claim'],reference=lookup[r['id']]['reference']) for r in inventory])
    c.putl(c.OUT/'asset_inventory512.jsonl', inventory)
    c.put(c.OUT/'near_duplicate_candidates.json', dict(rule='Within training patient only; claim token-set Jaccard>=0.8; candidates, not semantic duplicates',pairs=near))

    summary={}
    for label in c.LABELS:
        rr=[r for r in inventory if r['GT']==label]
        summary[label]=dict(N=len(rr),patients=len({r['sid'] for r in rr}),authors=dict(Counter(r['author'] for r in rr)),review_selected=sum(r['review_selected'] for r in rr),paper_r1_reason_present=sum(r['paper_r1_reason_present'] for r in rr),paper_r1_reasoning_chain_present=sum(r['paper_r1_reasoning_chain_present'] for r in rr),paper_r1_matches_GT=sum(r['paper_r1_matches_GT'] for r in rr),same_reference_correct_reason_candidate_coverage=sum(r['same_reference_correct_reason_candidates']>0 for r in rr),explicit_quote_candidate_coverage=sum(r['explicit_quote_candidates']>0 for r in rr),all_extractable_quotes_match_coverage=sum(r['explicit_quote_candidates']>0 and r['explicit_quote_candidates']==r['explicit_quote_exact_matches'] for r in rr),round1_agreement=dict(Counter(str(r['round1_num_raters_agree']) for r in rr)),reference_chars_min=min(r['reference_chars'] for r in rr),reference_chars_max=max(r['reference_chars'] for r in rr),reference_chars_mean=sum(r['reference_chars'] for r in rr)/len(rr))
    c.put(c.OUT/'asset_summary.json',dict(N=512,train_patients=len({r['sid'] for r in rows}),review_N=288,not_semantically_reviewed_S=224,by_GT=summary,same_reference_teacher_rows=len(teachers),other_reference_teacher_rows_not_reused=sum(a-b for _,a,b in allteacher_counts),exact_claim_duplicate_groups=sum(len(v)>1 for v in exact.values()),normalized_claim_duplicate_groups=sum(len(v)>1 for v in normalized.values()),near_duplicate_candidate_pairs=len(near),quote_matching_is_not_semantic_validation=True,new_API_calls=0))
    paths=[original,public_source,c.ROOT/'outputs/103_lora_selection/patient_roles.json',c.PRIVATE/'blind_cases.jsonl',c.PRIVATE/'gt_key.jsonl',c.OUT/'asset_inventory512.jsonl',c.TASK/'inventory104.py']
    c.put(c.OUT/'inventory_freeze.json',dict(created_utc=c.utc(),source_HEAD='42e357f314a928253ed64c54dc45801e6307c1b7',train512_unchanged=True,train_patient_scope=40,review_N=288,S_selection_seed=S_SEED,blind_order_seed=ORDER_SEED,hash_function='SHA256(seed + proposition_id)',review_order_ids=[r['id'] for r in selected],no_selection_or_confirmation_clinical_text=True,files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths}))
    print(c.canonical(c.read(c.OUT/'asset_summary.json')))

if __name__=='__main__':main()

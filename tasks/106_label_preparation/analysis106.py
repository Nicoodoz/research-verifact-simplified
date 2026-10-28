"""Read existing 105 predictions and prepare complete-reference review dossiers locally.

No model calls. Clinical text is only written to gitignored private files, never stdout
or public outputs. Structural verification and lexical locations are not a semantic
review, a new gold label, or a model mechanism attribution.
"""
from collections import Counter, defaultdict
from pathlib import Path
import re
import sys
import common106 as c

OLD = c.ROOT / 'outputs/105_brief_supervision'


def transition(key, before, after):
    return dict(**key, before=before, after=after,
                rescue=before != key['GT'] == after,
                harm=before == key['GT'] != after,
                false_S_added=key['GT'] != 'Supported' and before != 'Supported' and after == 'Supported',
                false_S_prevented=key['GT'] != 'Supported' and before == 'Supported' and after != 'Supported')


def summary(part):
    counts = Counter((r['GT'], r['before'], r['after']) for r in part)
    result = dict(N=len(part), patients=len({r['sid'] for r in part}),
                  rescued=sum(r['rescue'] for r in part), harmed=sum(r['harm'] for r in part),
                  false_S_added=sum(r['false_S_added'] for r in part),
                  false_S_prevented=sum(r['false_S_prevented'] for r in part),
                  transitions=[dict(GT=g, before=b, after=a, N=n) for (g,b,a),n in sorted(counts.items())],
                  by_GT={})
    for label in c.LABELS:
        rr = [r for r in part if r['GT'] == label]
        result['by_GT'][label] = dict(N=len(rr),
            before_correct=sum(r['before'] == label for r in rr),
            after_correct=sum(r['after'] == label for r in rr),
            before_S=sum(r['before'] == 'Supported' for r in rr),
            after_S=sum(r['after'] == 'Supported' for r in rr),
            rescued=sum(r['rescue'] for r in rr), harmed=sum(r['harm'] for r in rr))
    result['before_predicted_S'] = sum(r['before'] == 'Supported' for r in part)
    result['after_predicted_S'] = sum(r['after'] == 'Supported' for r in part)
    return result


def select_cases(part):
    selected = defaultdict(set)
    groups = {
        'all_new_false_S': lambda r: r['false_S_added'],
        'all_prevented_false_S': lambda r: r['false_S_prevented'],
        'NS_NA_changes': lambda r: r['before'] != r['after'] and
            {r['before'], r['after']} == {'Not Supported', 'Not Addressed'},
        'S_rescue': lambda r: r['GT'] == 'Supported' and r['rescue'],
        'NA_rescue': lambda r: r['GT'] == 'Not Addressed' and r['rescue'],
        'NS_kept_correct': lambda r: r['GT'] == r['before'] == r['after'] == 'Not Supported',
        'NA_kept_correct': lambda r: r['GT'] == r['before'] == r['after'] == 'Not Addressed',
        'S_kept_correct': lambda r: r['GT'] == r['before'] == r['after'] == 'Supported',
    }
    for name, predicate in groups.items():
        candidates = sorted([r for r in part if predicate(r)], key=lambda r: c.digest('106_A_v1/'+name+'/'+r['id']))
        # Every added/avoided false-S is included; fixed other panels are diagnostic only.
        chosen = candidates if name.startswith('all_') else candidates[:4]
        for r in chosen:
            selected[r['id']].add(name)
    return selected


def unit_spans(reference):
    hits = list(re.finditer(r'(?m)^\d+\. Date: .*? \| Text: ', reference))
    # Header remains visible as a separate unit; no source character is omitted.
    starts = sorted(set([0] + [h.start() for h in hits] + [len(reference)]))
    spans = [dict(start=a, end=b, sha256=c.digest(reference[a:b])) for a,b in zip(starts,starts[1:]) if b>a]
    assert ''.join(reference[s['start']:s['end']] for s in spans) == reference
    return spans


def lexical_locations(claim, reference):
    # All occurrences, not just the first hit. Location cues only, never a classifier.
    words = sorted(set(re.findall(r'[A-Za-z][A-Za-z0-9-]{3,}', claim.lower())))
    return [dict(term_sha256=c.digest(word), occurrences=[dict(start=m.start(),end=m.end())
                for m in re.finditer(r'(?i)(?<!\w)'+re.escape(word)+r'(?!\w)',reference)])
            for word in words]


def main():
    keys = c.rows(OLD/'eval_keys.jsonl')
    predictions = {(r['arm'],r['id']):r for r in c.rows(OLD/'predictions_sanitized.jsonl')}
    valid, invalid = [], []
    for k in keys:
        before, after = [predictions[a,k['id']] for a in ('base_judge','label_only')]
        if before['parsed']['valid'] and after['parsed']['valid']:
            assert before['prompt_token_sha256'] == after['prompt_token_sha256']
            valid.append(transition(k,before['parsed']['verdict'],after['parsed']['verdict']))
        else:
            invalid.append(dict(**k, base_valid=before['parsed']['valid'], label_valid=after['parsed']['valid'],
                                base_finish=before['finish_reason'],label_finish=after['finish_reason']))
    c.putl(c.OUT/'label_transitions.jsonl',valid)
    c.putl(c.OUT/'label_invalid.jsonl',invalid)
    # Reuse the repository's fixed label mapping and patient bootstrap, not a new metric.
    sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'))
    from evaluate105 import cohort, preds, paired_compare, risk_deltas
    panels={}
    for panel in ('natural','pressure'):
        rr=[r for r in valid if r['panel']==panel]
        paired_rows=[dict(r,pred={'base_judge':r['before'],'label_only':r['after']}) for r in rr]
        panels[panel]=summary(rr)
        panels[panel]['paired']=paired_compare(cohort(paired_rows),preds(paired_rows,'base_judge'),preds(paired_rows,'label_only'))
        panels[panel]['risk']=risk_deltas(paired_rows,'base_judge','label_only')
    selected={}
    for p in ('natural','pressure'):
        for pid, groups in select_cases([r for r in valid if r['panel']==p]).items():
            selected.setdefault(pid,set()).update(groups)
    lookup={r['id']:r for r in valid}
    inputs={r['id']:r for r in c.rows(c.ROOT/'.local_models/105_brief_supervision/eval_inputs.jsonl')}
    source_manifest={r['id']:r for r in c.rows(OLD/'eval_manifest.jsonl')}
    assert set(inputs)=={r['id'] for r in keys}
    for pid, inp in inputs.items():
        assert c.digest(inp['claim']) == source_manifest[pid]['claim_sha256']
        assert c.digest(inp['reference']) == source_manifest[pid]['reference_sha256']
    roles=c.read(c.ROOT/'outputs/103_lora_selection/patient_roles.json')['patients']
    assert {r['sid'] for r in keys} <= set(roles['selection'])
    assert not {r['sid'] for r in keys} & set(roles['train'])
    private=[]; public=[]
    for pid, groups in sorted(selected.items()):
        inp=inputs[pid]; tr=lookup[pid]
        assert inp['sid']==tr['sid']
        # Frozen evaluation inputs intentionally carry no GT into the model request.
        if 'GT' in inp:
            assert inp['GT']==tr['GT']
        reference=inp['reference']; spans=unit_spans(reference)
        base=dict(**tr, groups=sorted(groups), claim_sha256=c.digest(inp['claim']),
                  reference_sha256=c.digest(reference), reference_characters=len(reference),
                  complete_reference_units=len(spans), complete_reference_preserved=True,
                  semantic_review_status='not_reviewed_service_permission_pending',
                  source_of_label='unchanged_original_doctor_GT',
                  no_training_or_prompt_examples=True)
        public.append(base)
        private.append(dict(**base,claim=inp['claim'],full_reference=reference,
                            complete_unit_spans=spans,all_lexical_occurrences=lexical_locations(inp['claim'],reference),
                            review_fields=dict(object=None,event=None,time=None,degree=None,quantity=None,
                            negation=None,causality=None,decisive_spans=[],counterevidence_spans=[],
                            current_reference_sufficient=None,only_full_EHR_evidence=None,ambiguity=None)))
    c.putl(c.PRIVATE/'A_source_review_dossiers.jsonl',private)
    c.putl(c.OUT/'label_case_index.jsonl',public)
    c.put(c.OUT/'label_analysis.json',dict(
        comparison='105 label_only versus base_judge; pair-valid set, not evidence_brief intersection',
        panels=panels, invalid=summary_invalid(invalid), fixed_dossier_N=len(private),
        full_reference_structural_check=True, new_semantic_adjudication=False,
        service_permission='pending; clinical text only processed by local scripts',
        source_files={str(p.relative_to(c.ROOT)).replace('\\','/'):c.sha(p) for p in
            (OLD/'predictions_sanitized.jsonl',OLD/'eval_keys.jsonl',OLD/'eval_manifest.jsonl',c.ROOT/'.local_models/105_brief_supervision/eval_inputs.jsonl')},
        selection_or_confirmation_rows_in_training=False, new_API_calls=0))
    print(c.canonical(dict(panels={p:{k:v for k,v in s.items() if k not in ('transitions','paired','risk')} for p,s in panels.items()}, invalid_N=len(invalid),fixed_dossier_N=len(private))))


def summary_invalid(records):
    return dict(N=len(records), by_panel=dict(Counter(r['panel'] for r in records)),
                finish_reason=dict(Counter(r['base_finish'] for r in records)),
                medical_error_attribution=False, repaired_or_retried=False)


if __name__=='__main__':
    main()

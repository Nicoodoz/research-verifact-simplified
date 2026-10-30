"""Independent127 targets and exact token groups; no reason generation or GPU."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/104_supervision_evidence'))
import training104 as original
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
from data105 import offsets,training_plan

LABELS=original.LABELS
VERSION='127_optional_reason_v1'
_task, _separator, _old_output=original.INSTRUCTIONS.partition('\n4. ')
if not _separator or '\n\n## Input JSON:\n' not in _old_output:
    raise RuntimeError('104 prompt structure changed; inspect instead of silently adapting')
OUTPUT_RULE=(
    '4. Return a JSON object with the required key "verdict" and optional key "reason". '
    'If a reason is included, write 1 to 3 concise sentences based only on the current reference '
    'and consistent with the verdict. Preserve the assertion\'s subject, event, time, negation '
    'and qualifications. Do not invent evidence. "Not Addressed" means the supplied reference '
    'does not address the assertion; it does not establish that the patient never had that fact. '
    'Provide a brief evidence-based explanation, not a private chain of thought. Return only JSON.'
)
INSTRUCTIONS=_task+'\n'+OUTPUT_RULE+'\n\n## Input JSON:\n'


def canonical(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def validate_source(row):
    if row.get('GT') not in LABELS or not isinstance(row.get('id'),str) or not str(row.get('sid','')):
        raise ValueError('Original id, patient and three-class physician GT are required')
    if not isinstance(row.get('claim'),str) or not row['claim'].strip() or not isinstance(row.get('reference'),str):
        raise ValueError('Keep the original claim/reference strings')


def inference_input(row):
    """Explicit whitelist: GT, review flags, evidence and answers cannot leak."""
    return {key:row[key] for key in ('id','claim','reference')}


def messages(claim,reference):
    # The104 task and class definitions are byte-identical; only output rule4 changes.
    base=original.messages(claim,reference)
    payload=json.dumps({'text':claim,'reference':reference},ensure_ascii=False,indent=4)
    return [base[0],dict(role='user',content=INSTRUCTIONS+payload)]


def prompt_ids(tokenizer,row):
    value=inference_input(row)
    return tokenizer.apply_chat_template(messages(value['claim'],value['reference']),tokenize=True,
        add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')


def reason_issues(row,annotation):
    """Check submitted attestations/offsets, never invent or clinically approve text."""
    issues=[]
    disagreement=row.get('paper_r1') in LABELS and row['paper_r1']!=row['GT']
    if annotation is None:
        return ['missing_reason']+(['teacher_disagreement_requires_review'] if disagreement else [])
    if not isinstance(annotation,dict):return ['invalid_reason_annotation']
    if annotation.get('id')!=row['id'] or ('GT' in annotation and annotation['GT']!=row['GT']):
        issues.append('annotation_identity_or_GT_mismatch')
    sentences=annotation.get('reason_sentences')
    if not isinstance(sentences,list) or not 1<=len(sentences)<=3:
        issues.append('reason_sentence_count_not_1_to_3')
    elif any(not isinstance(s,str) or not s.strip() for s in sentences):
        issues.append('empty_or_invalid_reason_sentence')
    if annotation.get('ai_assisted') is not True:issues.append('ai_assisted_must_be_true_for_this_batch')
    review=annotation.get('review') or {}
    if not isinstance(review,dict):review={};issues.append('invalid_review_metadata')
    if review.get('status')!='approved':issues.append('review_not_approved')
    if (review.get('complete_sentences') is not True or not isinstance(sentences,list)
        or type(review.get('sentence_count')) is not int or review['sentence_count']!=len(sentences)):
        issues.append('complete_sentence_count_not_attested')
    if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():issues.append('missing_reviewer')
    for name in ('verdict_consistent','input_grounded'):
        if review.get(name) is not True:issues.append(name+'_not_confirmed')
    if row['GT']=='Not Addressed' and review.get('na_not_absence_checked') is not True:
        issues.append('NA_absence_distinction_not_checked')
    if disagreement and review.get('teacher_disagreement_reviewed') is not True:
        issues.append('teacher_disagreement_requires_review')
    unresolved=review.get('unresolved_issues',[])
    if not isinstance(unresolved,list):issues.append('invalid_unresolved_issues')
    else:issues.extend(str(x) for x in unresolved if x)
    submitted=annotation.get('issue_codes',[])
    if not isinstance(submitted,list):issues.append('invalid_submitted_issue_codes')
    else:issues.extend(str(x) for x in submitted if x)
    sources=annotation.get('evidence_sources')
    if not isinstance(sources,list) or not sources:issues.append('missing_evidence_metadata')
    else:
        for source in sources:
            if not isinstance(source,dict):issues.append('invalid_evidence_metadata');continue
            if source.get('kind')=='reference_span':
                start,end=source.get('start'),source.get('end');quote=source.get('quote')
                if (type(start) is not int or type(end) is not int or not 0<=start<end<=len(row['reference'])
                    or not isinstance(quote,str) or row['reference'][start:end]!=quote):
                    issues.append('reference_span_mismatch')
            elif source.get('kind')=='whole_reference':
                record=source.get('review_record')
                if (source.get('reference_sha256')!=digest(row['reference']) or source.get('fully_read') is not True
                    or not isinstance(record,(str,dict)) or not record):
                    issues.append('whole_reference_review_unverified')
            else:issues.append('unsupported_evidence_source_type')
    return list(dict.fromkeys(issues))


def reason_state(annotation,issues):
    """Pending work is not a semantic rejection; preserve it for later review."""
    review=annotation.get('review',{}) if isinstance(annotation,dict) else {}
    if not isinstance(review,dict):return 'not_reviewed'
    if not issues:return 'approved'
    if (review.get('status') in ('approved','reviewed_unresolved','rejected')
        or review.get('review_completed') is True or review.get('primary_full_reference_read') is True):
        return 'reviewed_unresolved'
    return 'not_reviewed'


def construct_answer(gt,reason_sentences=None):
    if gt not in LABELS:raise ValueError('Preserve original physician GT')
    prefix='{"verdict":'
    value=canonical(gt)
    span=(len(prefix)+1,len(prefix)+len(value)-1)
    text=prefix+value
    if reason_sentences is not None:
        if not isinstance(reason_sentences,list) or not 1<=len(reason_sentences)<=3:
            raise ValueError('Supply1--3 previously reviewed sentences')
        text+=',"reason":'+canonical(' '.join(reason_sentences))
    text+='}'
    if text[span[0]:span[1]]!=gt:raise AssertionError('Serialization-time verdict span changed')
    return text,span


def build_record(row,fit_role,arm,annotation=None):
    validate_source(row)
    if fit_role not in ('train','validation') or arm not in ('label_only','verdict_reason'):
        raise ValueError('Only the fixed127 patient roles and targets are supported')
    issues=reason_issues(row,annotation)
    if arm=='verdict_reason' and issues:raise ValueError('Reason is not approved: '+','.join(issues))
    sentences=annotation['reason_sentences'] if arm=='verdict_reason' else None
    answer,_=construct_answer(row['GT'],sentences)
    return dict(row,fit_role=fit_role,arm=arm,answer=answer,contract_version=VERSION,
        issue_codes=issues,reason_metadata=annotation,
        teacher_disagreement=row.get('paper_r1') in LABELS and row['paper_r1']!=row['GT'])


def encode(tokenizer,row):
    validate_source(row)
    if row.get('contract_version')!=VERSION:raise ValueError('Explicit127 contract required')
    arm=row['arm'];annotation=row.get('reason_metadata')
    if arm=='verdict_reason':
        issues=reason_issues(row,annotation)
        if issues:raise ValueError('Unapproved reason cannot enter supervision')
        text,span=construct_answer(row['GT'],annotation['reason_sentences'])
    elif arm=='label_only':text,span=construct_answer(row['GT'])
    else:raise ValueError('Unknown127 target')
    if text!=row['answer']:raise ValueError('Target differs from explicit fields')
    answer_ids,spans=offsets(tokenizer,text);value=[];covered=set()
    for i,(start,end) in enumerate(spans):
        if start<span[1] and span[0]<end:
            if not span[0]<=start<end<=span[1]:raise ValueError('Token crosses verdict/structure boundary')
            value.append(i);covered.update(range(start,end))
    if covered!=set(range(*span)):raise ValueError('Incomplete verdict token coverage')
    prefix=prompt_ids(tokenizer,row);eos=tokenizer.convert_tokens_to_ids('<|im_end|>')
    if not isinstance(eos,int) or eos<0:raise ValueError('Missing original EOS')
    suffix=answer_ids+[eos]
    groups=[0]*len(prefix)+[1 if i in value else 2 for i in range(len(suffix))]
    return dict(input_ids=prefix+suffix,labels=[-100]*len(prefix)+suffix,groups=groups,
        prompt_tokens=len(prefix),answer_tokens=len(suffix),verdict_answer_token_indices=value,
        verdict_value_chars=list(span),answer_token_offsets=[list(x) for x in spans],
        prompt_token_sha256=digest(canonical(prefix)),answer_sha256=digest(text))


def pad_encoded(examples,pad_token_id):
    if not examples:raise ValueError('Empty batch')
    width=max(len(x['input_ids']) for x in examples)
    result={k:[] for k in ('input_ids','labels','groups','attention_mask')}
    for x in examples:
        extra=width-len(x['input_ids'])
        result['input_ids'].append(x['input_ids']+[pad_token_id]*extra)
        result['labels'].append(x['labels']+[-100]*extra)
        result['groups'].append(x['groups']+[0]*extra)
        result['attention_mask'].append([1]*len(x['input_ids'])+[0]*extra)
    return result


def assert_pair(label,reason):
    for key in ('id','sid','GT','claim','reference','fit_role'):
        if label[key]!=reason[key]:raise ValueError('Paired source differs: '+key)
    if messages(label['claim'],label['reference'])!=messages(reason['claim'],reason['reference']):
        raise ValueError('Paired prompt differs')
    if json.loads(label['answer'])!={'verdict':label['GT']}:raise ValueError('Label-only target invalid')
    obj=json.loads(reason['answer'])
    if set(obj)!={'verdict','reason'} or obj['verdict']!=reason['GT']:raise ValueError('Reason target invalid')

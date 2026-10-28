"""Freeze blind judgments before GT join; build strictly paired private supervision.

No model calls. Quote location certifies literal provenance, not clinical meaning.
The default mode is --validate-only and never reads the GT key.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

import common104 as c

REVIEW_NAMES = ('review_root.jsonl', 'review_b.jsonl', 'review_c.jsonl')
VERDICTS = set(c.LABELS) | {'Unclear'}
SLOTS = ('subject', 'event', 'time', 'qualifiers')
SUPERVISION_METADATA_FIELDS = {'teacher_review','relation_origin','teacher_semantic_reviewed'}
HEADER = re.compile(r'(?m)^(?P<number>\d+)\.\s+Date:\s*(?P<meta>[^\n]*?)\s*\|\s*Text:\s*')


def offsets(reference: str, quote: str) -> list[dict]:
    """Return every exact occurrence; do not select an arbitrary repeated source."""
    if not isinstance(quote, str) or not quote or not quote.strip():
        raise ValueError('Evidence quotes must be nonempty strings')
    found = []
    start = 0
    while True:
        start = reference.find(quote, start)
        if start < 0:
            break
        found.append(dict(start=start, end=start+len(quote), quote_sha256=c.digest(quote)))
        start += 1
    return found


def reference_units(reference: str) -> list[dict]:
    """Parse only metadata explicitly rendered in the published reference.

    A display number is not an original note ID. Missing IDs remain null.
    """
    headers = list(HEADER.finditer(reference))
    result = []
    for index, match in enumerate(headers):
        meta = match.group('meta')
        note_id = re.search(r'(?:^|,\s*)Note ID:\s*([^,|]+)', meta)
        result.append(dict(display_number=int(match.group('number')),
                           header_start=match.start(), text_start=match.end(),
                           end=headers[index+1].start() if index+1<len(headers) else len(reference),
                           note_id=note_id.group(1).strip() if note_id else None,
                           note_id_status='explicit' if note_id else 'not_published_in_reference',
                           rendered_source_metadata=meta))
    return result


def evidence_spans(reference: str, quotes: list[str]) -> tuple[list[dict], list[str]]:
    units = reference_units(reference)
    spans, issues = [], []
    if not isinstance(quotes, list):
        raise ValueError('evidence_quotes must be a list')
    for ordinal, quote in enumerate(quotes, 1):
        locations = offsets(reference, quote)
        if not locations:
            issues.append(f'quote_{ordinal}_not_exactly_in_reference')
        annotated = []
        for location in locations:
            end, start = location['end'], location['start']
            sources = []
            for unit in units:
                if unit['header_start'] < end and start < unit['end']:
                    sources.append(dict(unit,
                                        overlap_start=max(start, unit['header_start']),
                                        overlap_end=min(end, unit['end'])))
            annotated.append(dict(location, sources=sources,
                                  source_metadata_status='rendered_unit' if sources else 'unparsed_or_admission_preamble'))
        spans.append(dict(quote=quote, quote_sha256=c.digest(quote),
                          occurrences=annotated, occurrence_count=len(annotated),
                          location_policy='all_exact_occurrences_retained',
                          ambiguous_multiple_locations=len(annotated)>1))
    return spans, issues


def validate_review(review: dict, case: dict) -> dict:
    if review.get('id') != case['id'] or review.get('review_index') != case['review_index']:
        raise ValueError('Review ID/index mismatch')
    if review.get('full_reference_read') is not True:
        raise ValueError('full_reference_read must be explicitly true')
    if review.get('review_stage') != 'blind_v1':
        raise ValueError('First judgment must be blind_v1')
    if review.get('independent_verdict') not in VERDICTS:
        raise ValueError('Unknown independent_verdict')
    if review.get('certainty') not in {'high', 'moderate', 'low'}:
        raise ValueError('Unknown certainty')
    if review.get('na_anchor') not in {'none', 'related_context', 'not_applicable'}:
        raise ValueError('Unknown na_anchor')
    if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():
        raise ValueError('Preserve the actual first reviewer identity')
    if not isinstance(review.get('claim_slots'), dict) or set(review['claim_slots']) != set(SLOTS):
        raise ValueError('All four claim_slots are required')
    if any(not isinstance(review['claim_slots'][key], str) or not review['claim_slots'][key].strip() for key in SLOTS):
        raise ValueError('Claim slots must be explicit, including unspecified qualifiers/time')
    if not isinstance(review.get('relation'), str) or not review['relation'].strip():
        raise ValueError('A concrete relationship explanation must be supplied by the reviewer')
    if not isinstance(review.get('issue_tags'), list) or any(not isinstance(x, str) for x in review['issue_tags']):
        raise ValueError('issue_tags must be a list of strings')
    spans, issues = evidence_spans(case['reference'], review.get('evidence_quotes'))
    no_anchor = review['independent_verdict']=='Not Addressed' and review['na_anchor']=='none' and not spans
    if not spans and not no_anchor:
        issues.append('no_evidence_anchor_for_non_no_anchor_na')
    if review['na_anchor']=='none' and review['independent_verdict']!='Not Addressed':
        issues.append('no_anchor_requires_independent_NA')
    return dict(quote_spans=spans, structural_issues=issues,
                no_anchor_na=no_anchor,
                relation_words=len(re.findall(r"\b[\w'-]+\b", review['relation'])),
                relation_target_words=[50,100],
                word_target_is_not_semantic_certification=True)


def load_cases(private: Path) -> dict[str, dict]:
    cases = c.lines(private/'blind_cases.jsonl')
    if len(cases)!=288 or len({r['id'] for r in cases})!=288:
        raise ValueError('Expected the complete frozen 288-case panel')
    if {r['review_index'] for r in cases} != set(range(1,289)):
        raise ValueError('Unexpected review indexes')
    for case in cases:
        if {'GT','paper_r1','reason','reasoning_chain'} & case.keys():
            raise ValueError('Blind cases contain forbidden label/teacher fields')
        if c.digest(case['reference']) != case['reference_sha256'] or case['reference_sha256'] != case['reference_id']:
            raise ValueError('Frozen reference SHA mismatch')
    return {r['id']:r for r in cases}


def validate_files(private: Path, paths: list[Path], allow_partial=False) -> tuple[list[dict], dict]:
    """This path intentionally does not open gt_key or teacher material."""
    cases = load_cases(private)
    assignments={}
    assignment_path=private/'assignment.json'
    if assignment_path.is_file():
        declared=c.read(assignment_path)
        declared=declared.get('assignments',declared)
        if isinstance(declared,dict):
            by_index={r['review_index']:r for r in cases.values()}
            declared=[dict(review_index=int(index),id=by_index[int(index)]['id'],reviewer=reviewer) for index,reviewer in declared.items()]
        for assignment in declared:
            identifier=assignment['id']
            if identifier not in cases or assignment['review_index']!=cases[identifier]['review_index'] or identifier in assignments:
                raise ValueError('Invalid or duplicate review assignment')
            assignments[identifier]=assignment['reviewer']
        if not allow_partial and set(assignments)!=set(cases):
            raise ValueError('Final review assignment must cover all 288 IDs')
    reviews, seen, errors, quote_failures, repeated = [], set(), [], 0, 0
    for path in paths:
        if not path.is_file():
            if allow_partial:
                continue
            raise ValueError(f'Missing review file: {path.name}')
        for line_no, row in enumerate(c.lines(path),1):
            identifier = row.get('id')
            try:
                if {'GT','human_gt','paper_r1','teacher_verdict','teacher_reason'} & row.keys():
                    raise ValueError('First blind ledger contains forbidden GT/teacher fields')
                if identifier not in cases:
                    raise ValueError('Review is outside the frozen 288')
                if identifier in seen:
                    raise ValueError('Duplicate review ID')
                if identifier in assignments and row.get('reviewer')!=assignments[identifier]:
                    raise ValueError('Actual reviewer differs from the explicit assignment; resolve metadata before freeze')
                checked = validate_review(row,cases[identifier])
                quote_failures += bool(checked['structural_issues'])
                repeated += sum(s['ambiguous_multiple_locations'] for s in checked['quote_spans'])
                row = dict(row,mechanical=checked)
                seen.add(identifier)
                reviews.append(row)
            except (ValueError,TypeError) as exc:
                errors.append(dict(file=path.name,line=line_no,id=identifier,error=str(exc)))
    if errors:
        raise ValueError(c.canonical(dict(schema_errors=errors)))
    if not allow_partial and seen != set(cases):
        raise ValueError(f'Incomplete first judgments: {len(seen)}/288')
    reviews.sort(key=lambda r:r['review_index'])
    summary=dict(N=len(reviews),expected=288,complete=len(reviews)==288,
                 reviewers=dict(Counter(r['reviewer'] for r in reviews)),
                 mechanically_flagged_rows=quote_failures,repeated_quote_strings=repeated,
                 assignment_checked=bool(assignments),
                 GT_read=False,semantic_approval_not_implied=True)
    return reviews,summary


def freeze_blind(private: Path, out: Path, paths: list[Path]) -> dict:
    reviews,summary=validate_files(private,paths)
    folder=private/'blind_review_freeze'
    manifest_path=out/'blind_review_freeze.json'
    if manifest_path.exists():
        frozen=load_frozen_reviews(private,out)
        if [r['id'] for r in frozen] != [r['id'] for r in reviews]:
            raise ValueError('An existing blind freeze cannot be replaced')
        return c.read(manifest_path)
    folder.mkdir(parents=True,exist_ok=True)
    files={}
    for path in paths:
        destination=folder/path.name
        if destination.exists() and destination.read_bytes()!=path.read_bytes():
            raise ValueError('Refuse to overwrite a blind snapshot')
        destination.write_bytes(path.read_bytes())
        files[path.name]=dict(source_sha256=c.sha(path),snapshot_sha256=c.sha(destination))
    assignment_path=private/'assignment.json'
    if assignment_path.is_file():
        (folder/'assignment.json').write_bytes(assignment_path.read_bytes())
    joined=folder/'reviews288.jsonl'
    c.putl(joined,reviews)
    manifest=dict(created_utc=c.utc(),N=288,GT_join_before_freeze=False,
                  blind_cases_sha256=c.sha(private/'blind_cases.jsonl'),files=files,
                  merged_sha256=c.sha(joined),builder_sha256=c.sha(Path(__file__)),
                  assignment_sha256=c.sha(assignment_path) if assignment_path.is_file() else None,
                  statement='Immutable copies precede GT join; source review files remain unchanged.',
                  validation=summary)
    c.put(manifest_path,manifest)
    return manifest


def load_frozen_reviews(private: Path,out: Path) -> list[dict]:
    path=out/'blind_review_freeze.json'
    if not path.is_file():
        raise ValueError('GT join refused: freeze complete blind judgments first')
    manifest=c.read(path)
    if manifest.get('N')!=288 or c.sha(private/'blind_cases.jsonl')!=manifest['blind_cases_sha256']:
        raise ValueError('Blind input freeze mismatch')
    folder=private/'blind_review_freeze'
    if manifest.get('assignment_sha256'):
        if c.sha(private/'assignment.json')!=manifest['assignment_sha256'] or c.sha(folder/'assignment.json')!=manifest['assignment_sha256']:
            raise ValueError('Review assignment changed after freeze')
    for name, hashes in manifest['files'].items():
        if c.sha(private/name)!=hashes['source_sha256'] or c.sha(folder/name)!=hashes['snapshot_sha256']:
            raise ValueError('Blind judgments changed after freeze')
    if c.sha(folder/'reviews288.jsonl') != manifest['merged_sha256']:
        raise ValueError('Merged blind ledger changed after freeze')
    return c.lines(folder/'reviews288.jsonl')


def initial_status(review:dict, GT:str) -> str:
    if review['independent_verdict']=='Not Addressed' and GT in {'Supported','Not Supported'}:
        return 'reference_gap'
    if review['independent_verdict']==GT and review['certainty']!='low' and not review['mechanical']['structural_issues']:
        return 'candidate_gt_explained'
    return 'unresolved'


def shared_messages(claim:str,reference:str) -> list[dict]:
    from training104 import messages
    return messages(claim,reference)


def pair_rows(case:dict,review:dict,GT:str,metadata:dict) -> tuple[dict,dict]:
    messages=shared_messages(case['claim'],case['reference'])
    common=dict(id=case['id'],sid=case['sid'],author=case['author'],GT=GT,
                claim=case['claim'],reference=case['reference'],reference_id=case['reference_id'],
                claim_sha256=c.digest(case['claim']),reference_sha256=c.digest(case['reference']),
                messages=messages,prompt_sha256=c.digest(c.canonical(messages)),metadata=metadata)
    brief=dict(evidence=review['evidence_quotes'],relation=review['relation'],verdict=GT)
    label=dict(verdict=GT)
    return dict(common,answer=c.canonical(label),answer_text=c.canonical(label)),dict(common,answer=c.canonical(brief),answer_text=c.canonical(brief))


def build(private:Path,out:Path,decisions:Path|None=None) -> dict:
    reviews=load_frozen_reviews(private,out)  # Must succeed before opening GT.
    cases=load_cases(private)
    keys={r['id']:r for r in c.lines(private/'gt_key.jsonl')}
    train=c.lines(private/'train512_original.jsonl')
    trainmap={r['id']:r for r in train}
    if len(train)!=512 or len(trainmap)!=512:
        raise ValueError('Original training panel must remain exactly 512 unique IDs')
    if set(keys)!=set(cases) or any(keys[k]['GT']!=trainmap[k]['GT'] for k in keys):
        raise ValueError('GT key differs from the original training labels')
    revision_rows=c.lines(decisions) if decisions else []
    revisions={r['id']:r for r in revision_rows}
    if len(revisions)!=len(revision_rows) or set(revisions)-set(cases):
        raise ValueError('Duplicate or out-of-panel explicit decisions')
    joined=[]
    for original in reviews:
        identifier=original['id'];case=cases[identifier];GT=keys[identifier]['GT']
        if keys[identifier]['review_index']!=case['review_index']:
            raise ValueError('GT key index mismatch')
        row=dict(original,GT=GT,sid=case['sid'],author=case['author'],
                 initial_status=initial_status(original,GT),
                 source_review_sha256=c.digest(c.canonical(original)),
                 source_reference_sha256=case['reference_sha256'])
        row['final_status']=row['initial_status']
        row['quality_approved']=False
        if identifier in revisions:
            revision=revisions[identifier]
            if not revision.get('revision_reason') or not revision.get('reviewer'):
                raise ValueError('Explicit decision needs reviewer and a substantive revision_reason')
            if revision.get('final_status') not in {'gt_explained','reference_gap','unresolved'}:
                raise ValueError('Unknown explicit final_status')
            for field in ('evidence_quotes','relation','na_anchor'):
                if field in revision:
                    row[field]=revision[field]
            validation_view=dict(row)
            if revision['final_status']=='gt_explained' and revision.get('independent_semantic_audit'):
                # Validate the explicitly audited final explanation while retaining
                # the original independent judgment unchanged in the stored row.
                validation_view['independent_verdict']=GT
            row['mechanical']=validate_review(validation_view,case)
            row['final_status']=revision['final_status']
            row['quality_approved']=revision.get('quality_approved') is True
            row['explicit_post_blind_revision']=revision
            supervision=revision.get('supervision_metadata',{})
            if not isinstance(supervision,dict) or set(supervision)-SUPERVISION_METADATA_FIELDS:
                raise ValueError('Only documented teacher provenance metadata may be carried into final supervision')
            if 'teacher_semantic_reviewed' in supervision and type(supervision['teacher_semantic_reviewed']) is not bool:
                raise ValueError('teacher_semantic_reviewed must be a boolean')
            if 'relation_origin' in supervision and (not isinstance(supervision['relation_origin'],str) or not supervision['relation_origin']):
                raise ValueError('relation_origin must be explicit')
            if 'teacher_review' in supervision:
                teacher_review=supervision['teacher_review']
                if not isinstance(teacher_review,dict) or teacher_review.get('id',identifier)!=identifier or teacher_review.get('GT',GT)!=GT:
                    raise ValueError('Teacher provenance cannot change case identity or physician label')
            if row['final_status']=='gt_explained':
                if not row['quality_approved'] or row['mechanical']['structural_issues']:
                    raise ValueError('Accepted final decision needs independent quality approval and valid quotes')
                if not row['evidence_quotes'] and GT!='Not Addressed':
                    raise ValueError('S/NS acceptance needs actual reference evidence')
                if row['independent_verdict']!=GT and not revision.get('independent_semantic_audit'):
                    raise ValueError('Initial disagreement cannot be accepted by GT-forcing; provide an explicit independent semantic audit')
        joined.append(row)
    joined.sort(key=lambda r:next(i for i,x in enumerate(train) if x['id']==r['id']))
    c.putl(private/'review_joined.jsonl',joined)
    initial_path=private/'review_joined_initial.jsonl'
    if decisions is None:
        initial_bytes=''.join(c.canonical(r)+'\n' for r in joined).encode('utf-8')
        if initial_path.exists() and initial_path.read_bytes()!=initial_bytes:
            raise ValueError('Initial GT-joined blind ledger cannot be silently replaced')
        if not initial_path.exists():initial_path.write_bytes(initial_bytes)
    # Before final quality decisions, emit clearly labelled candidate data, not certified data.
    finalized=decisions is not None
    accepted=[r for r in joined if r['final_status']=='gt_explained'] if finalized else [r for r in joined if r['final_status']=='candidate_gt_explained']
    left,right=[],[]
    for review in accepted:
        metadata=dict(review_index=review['review_index'],full_reference_read=True,
                      independent_verdict=review['independent_verdict'],certainty=review['certainty'],
                      evidence_spans=review['mechanical']['quote_spans'],
                      no_anchor_na=not review['evidence_quotes'] and review['GT']=='Not Addressed',
                      quality_approved=review['quality_approved'],
                      supervision_source='machine_assisted_not_new_physician_gold',
                      relation_origin='blind_review_draft' if 'explicit_post_blind_revision' not in review else 'documented_post_blind_revision',
                      original_blind_review_sha256=review['source_review_sha256'])
        metadata.update(review.get('explicit_post_blind_revision',{}).get('supervision_metadata',{}))
        a,b=pair_rows(cases[review['id']],review,review['GT'],metadata)
        assert {k:v for k,v in a.items() if k not in {'answer','answer_text'}} == {k:v for k,v in b.items() if k not in {'answer','answer_text'}}
        left.append(a);right.append(b)
    folder=private/('paired' if finalized else 'candidate_paired')
    c.putl(folder/'label_only.jsonl',left);c.putl(folder/'evidence_brief.jsonl',right)
    safe_keys=('id','sid','author','GT','review_index','independent_verdict','certainty','initial_status','final_status','quality_approved','source_review_sha256','source_reference_sha256')
    c.putl(out/'review_status288.jsonl',[{k:r[k] for k in safe_keys} for r in joined])
    c.putl(private/'quarantine.jsonl',[r for r in joined if r['id'] not in {x['id'] for x in accepted}])
    c.putl(out/'quarantine.jsonl',[{k:r[k] for k in safe_keys} for r in joined if r['id'] not in {x['id'] for x in accepted}])
    manifest=dict(created_utc=c.utc(),N=len(accepted),candidate_only=not finalized,
                  no_classification_improvement_claim=True,GT_modified=False,
                  untouched_unreviewed_S=224,retained_GT=dict(Counter(r['GT'] for r in accepted)),
                  status_by_GT={g:dict(Counter(r['final_status'] for r in joined if r['GT']==g)) for g in c.LABELS},
                  retained_author=dict(Counter(r['author'] for r in accepted)),
                  retained_patients=len({r['sid'] for r in accepted}),
                  no_anchor_na=sum(not r['evidence_quotes'] and r['GT']=='Not Addressed' for r in accepted),
                  paired_prompt_equal=True,source_order='original103_train512_filtered',
                  files={(p.relative_to(c.ROOT).as_posix() if p.is_relative_to(c.ROOT) else str(p)):c.sha(p) for p in (folder/'label_only.jsonl',folder/'evidence_brief.jsonl',(private/'review_joined.jsonl') if finalized else initial_path)},
                  paired_ids=[r['id'] for r in accepted],
                  blind_freeze_sha256=c.sha(out/'blind_review_freeze.json'),
                  decisions_sha256=c.sha(decisions) if decisions else None)
    target_manifest=out/('paired_manifest.json' if finalized else 'candidate_paired_manifest.json')
    if not finalized and target_manifest.exists():
        previous=c.read(target_manifest)
        manifest['created_utc']=previous['created_utc']
        if manifest!=previous:raise ValueError('Original candidate manifest cannot be silently replaced')
    c.put(target_manifest,manifest)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--validate-only',action='store_true')
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--freeze-blind',action='store_true')
    mode.add_argument('--build',action='store_true')
    parser.add_argument('--private',type=Path,default=c.PRIVATE)
    parser.add_argument('--out',type=Path,default=c.OUT)
    parser.add_argument('--reviews',nargs=3,type=Path)
    parser.add_argument('--allow-partial',action='store_true')
    parser.add_argument('--decisions',type=Path)
    args=parser.parse_args()
    paths=args.reviews or [args.private/name for name in REVIEW_NAMES]
    if args.freeze_blind:
        if args.allow_partial:parser.error('Partial first judgments cannot be frozen')
        result=freeze_blind(args.private,args.out,paths)
    elif args.build:
        result=build(args.private,args.out,args.decisions)
    else:
        _,result=validate_files(args.private,paths,args.allow_partial)
    print(c.canonical(result))


if __name__=='__main__':main()

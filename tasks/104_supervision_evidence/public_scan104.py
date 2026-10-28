"""Static privacy/source checks of 104 public outputs and task code only.

This does not open private cases, physician comments, teacher explanations, or
in-progress blind ledgers. It is a pattern/schema check, not a PHI certification.
"""
from pathlib import Path
import argparse
import json
import re

import common104 as c

SECRET = re.compile(r'\bsk-(?:ws-)?[A-Za-z0-9._-]{24,}|\bAKIA[A-Z0-9]{16}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
CLINICAL = re.compile(r'\[\*\*[^\]\r\n]{3,}\*\*\]|\b21\d{2}[-/]\d{1,2}[-/]\d{1,2}\b')
BLOCKED_BODY_KEYS = {'claim','reference','text','reason','relation','reasoning_chain','reasoning_final_answer','claim_slots','evidence_quotes','quote','quotation','evidence_text','clinical_text','patient_text','prompt','messages','answer','answer_text','revision_reason','grounding_assessment','retained_teacher_facts','revision_notes','original_teacher','blind_relation','final_relation','blind_evidence_quotes','teacher_reason','rationale','explanation','assessment','raw_response','response_body','request_body','comment1','comment2','comment3','comment4','comment5','adjudicated_comment'}
TEXT_SUFFIXES = {'.json','.jsonl','.csv','.md','.py','.txt','.yaml','.yml','.toml','.ps1','.sh'}


def structured_issues(value, location='$'):
    result=[]
    if isinstance(value,dict):
        for key,child in value.items():
            here=f'{location}.{key}'
            if key in BLOCKED_BODY_KEYS and child is not None and not isinstance(child,(bool,int,float)):
                result.append(dict(location=here,code='forbidden_free_text_field'))
            result.extend(structured_issues(child,here))
    elif isinstance(value,list):
        for index,child in enumerate(value):
            result.extend(structured_issues(child,f'{location}[{index}]'))
    return result


def scan_text(text,suffix):
    result=[]
    if SECRET.search(text):result.append(dict(code='credential_pattern'))
    if CLINICAL.search(text):result.append(dict(code='clinical_raw_marker_or_date'))
    if suffix=='.json':
        try:result.extend(structured_issues(json.loads(text)))
        except json.JSONDecodeError:result.append(dict(code='invalid_public_JSON'))
    elif suffix=='.jsonl':
        for number,line in enumerate(text.splitlines(),1):
            if not line.strip():continue
            try:result.extend(structured_issues(json.loads(line),f'line_{number}'))
            except json.JSONDecodeError:result.append(dict(code='invalid_public_JSONL',line=number))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=c.OUT/'public_privacy_scan.json')
    args=parser.parse_args()
    records=[];issues=[];skipped=[]
    for folder in (c.OUT,c.TASK):
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.resolve()==args.output.resolve() or '__pycache__' in path.parts:continue
            relative=path.relative_to(c.ROOT).as_posix()
            if path.suffix.lower() not in TEXT_SUFFIXES:
                skipped.append(relative);continue
            data=path.read_bytes()
            try:text=data.decode('utf-8-sig')
            except UnicodeDecodeError:
                issues.append(dict(file=relative,code='non_UTF8_text'));continue
            found=scan_text(text,path.suffix.lower())
            if data.startswith(b'\xef\xbb\xbf'):found.append(dict(code='new_file_UTF8_BOM'))
            issues.extend(dict(file=relative,**item) for item in found)
            records.append(dict(path=relative,sha256=c.sha(path),bytes=len(data)))
    result=dict(created_utc=c.utc(),status='PASS' if not issues else 'FAIL',
                scope='104 public outputs and task code only; static pattern/schema check',
                files_checked=len(records),files=records,issues=issues,skipped_nontext=skipped,
                forbidden_free_text_keys=sorted(BLOCKED_BODY_KEYS),
                source_paths_outside_104_read=False,private_clinical_files_read=False,
                raw_review_ledgers_read=False,independent_clinical_privacy_certification=False,
                snapshot_only_rerun_after_new_public_artifacts=True,
                no_Git_mutation=True,new_API_calls=0)
    c.put(args.output,result)
    print(c.canonical({key:value for key,value in result.items() if key!='files'}))
    if issues:raise SystemExit(1)


if __name__=='__main__':main()

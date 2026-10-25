"""One pre-Judge engineering normalization; original generation stays immutable."""
import common094 as c
PREFIX='Without assuming that any mentioned event occurred, first establish what is documented; if the event/context is not identifiable, state insufficient. Then address: '
REJECT={
 '633e383b-efa2-21c5-7135-ac4713ad22fd':'question changes monitoring action into renal outcome',
 '8351721a-11f9-0c34-f44a-4f6c71ab83e4':'generic treatment question loses identifying context',
 'be031f06-45f7-2132-31be-d3d2d6a4a89e':'generic respiratory condition too broad to identify sleep-related topic',
 'e7d000a0-d057-c3e4-97c3-112086c0b10a':'device/value question loses transition context',
 '928e7e79-2bdc-ce37-758c-47206e2dd702':'generic medication initiation lacks indication or event anchor',
 '8d13647d-8aba-a64a-9301-b8aa7639165e':'generator adds discharge scope absent from original claim'}
def main():
    qs=c.lines(c.PRIVATE/'questions.jsonl');normalized=[];accepted=[];review=[]
    for q in qs:
        valid=q['valid'] and q['id'] not in REJECT
        review.append(dict(id=q['id'],accepted=valid,reason=REJECT.get(q['id'],'target value withheld; topic identifiable; uniform occurrence guard required') if q['valid'] else 'invalid generated question'))
        if valid:
            z=dict(q,question=PREFIX+q['question']);assert len(z['question'])<=350 and len(z['question'].encode())<=1200
            assert z['answer_span'].lower() not in z['question'].lower()
            normalized.append(z);accepted.append(q['id'])
    c.putl(c.PRIVATE/'questions_reviewed.jsonl',normalized)
    c.put(c.OUT/'question_review.json',dict(utc=c.now(),accepted_ids=accepted,decisions=review,review_type='executor semantic review before extraction/Judge; no GT/model predictions consulted',independent_audit=False,normalization='Uniform occurrence guard; one engineering correction, no regeneration, no changed target answers',original_questions_sha256=c.sha(c.PRIVATE/'questions.jsonl'),reviewed_questions_sha256=c.sha(c.PRIVATE/'questions_reviewed.jsonl'),code_sha256=c.sha(c.TASK/'review_questions094.py')))
    print('Accepted',len(accepted),'of',len(qs),'without regeneration')
if __name__=='__main__':main()

"""Pinned tokenizer adversarial string check; does not inspect new patients."""
import common105 as c
from data105 import encode,shared
from tokenize105 import LocalTokenizer

def main():
    tok=LocalTokenizer(c.ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    ref='Supported and Not Supported are literal words in this synthetic example.'
    row=dict(id='synthetic',GT='Not Supported',claim='Check a synthetic proposition.',reference=ref,reference_sha256=c.digest(ref))
    row['answer']=c.canonical(dict(evidence=['Supported'],relation='Supported, Not Supported and Not Addressed here are quoted names, not classification decisions. The final typed field alone provides the supervised classification value.',verdict='Not Supported'))
    row['metadata']=dict(evidence_spans=[dict(quote='Supported',quote_sha256=c.digest('Supported'),occurrences=[dict(start=0,end=9),dict(start=18,end=27)],occurrence_count=2)])
    encoded=encode(tok,row)
    span=encoded['verdict_value_chars'];indices=encoded['verdict_answer_token_indices']
    assert all(span[0]<=encoded['answer_token_offsets'][i][0]<encoded['answer_token_offsets'][i][1]<=span[1] for i in indices)
    assert encoded['groups'].count(1)==2 and encoded['groups'][-1]==2
    print(c.canonical(dict(status='PASS',same_label_words_in_reason_not_classified=True,verdict_tokens=2,classification_span_from_construction=True,EOS_other=True)))

if __name__=='__main__':main()

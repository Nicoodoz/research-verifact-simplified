"""Keep label inputs unchanged; separate auxiliary explanation inputs contain no GT."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/105_brief_supervision'))
from data105 import encode as label_encode
from training104 import SYSTEM,INSTRUCTIONS

def reason_messages(claim,reference):
 instruction=INSTRUCTIONS.split('4. Return a JSON object')[0]
 instruction+='4. In this auxiliary task, explain the support relationship in one to three concise sentences based only on the reference. Return only the short explanation, without JSON. Distinguish incomplete support from an unaddressed assertion; missing documentation does not establish that a fact never occurred.\n\n## Input JSON:\n'
 return [{'role':'system','content':SYSTEM},{'role':'user','content':instruction+json.dumps({'text':claim,'reference':reference},ensure_ascii=False,indent=4)}]

def encode(tokenizer,row):
 if row['kind']=='label':return dict(label_encode(tokenizer,row),kind='label')
 assert row['kind']=='reason'
 prefix=tokenizer.apply_chat_template(reason_messages(row['claim'],row['reference']),tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')
 suffix=tokenizer.encode(row['answer'],add_special_tokens=False)
 assert tokenizer.decode(suffix,skip_special_tokens=False)==row['answer']
 suffix+=[tokenizer.convert_tokens_to_ids('<|im_end|>')]
 return dict(input_ids=prefix+suffix,groups=[0]*len(prefix)+[1]*len(suffix),kind='reason',prompt_tokens=len(prefix),answer_tokens=len(suffix))

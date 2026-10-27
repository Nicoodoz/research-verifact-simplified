"""Frozen runtime plus stop remaining submissions on actual final-answer truncation."""
import json
import common103 as c
import runtime103 as rt
original_process=rt.process
def guarded(j,operating=30.):
 result=original_process(j,operating)
 if result in ['success','cached']:
  folder=rt.completed()[j['request_id']]
  response=json.loads(c.read(folder/'receipt.json')['transport']['body_text'])
  if response['choices'][0].get('finish_reason')=='length':
   raise RuntimeError('Final_answer_truncated_preserve_response_and_inspect_engineering')
 return result
if __name__=='__main__':
 rt.process=guarded
 rt.main()

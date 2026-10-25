import unittest,json
from collections import Counter
import common093 as c
from operation093 import factor,parse,encode_with_dictionary
from api093 import check_budget,cost
class Tests(unittest.TestCase):
    def test_roundtrip_preserves_all_dates_and_source_text(self):
        text='An explicitly synthetic statement for an engineering test. '*12
        ref='Synthetic header\n'+'\n'.join(f'{i}. Date: 2020-01-0{i}, Time: 00:00, Note Category: Test, Note ID: {i}, Raw characters: [0,{len(text)}) | Text: {text}' for i in [1,2,3])
        x=factor(ref);self.assertGreater(x['saved'],0);self.assertEqual(x['occurrences'],3)
        restored=x['body']
        for k,v in x['dictionary'].items():restored=restored.replace(k,v)
        self.assertEqual(restored,ref)
        for i in [1,2,3]:self.assertIn('2020-01-0'+str(i),x['reference'])
    def test_distinct_or_short_sources_not_merged(self):
        ref='\n'.join(f'{i}. Date: X, Time: X, Note Category: Test, Note ID: {i}, Raw characters: [0,5) | Text: short' for i in [1,2])
        self.assertEqual(factor(ref)['reference'],ref)
    def test_remaining_cohort_and_unknown_are_reserved(self):
        jobs=[dict(request_id='a',bound_cny=1),dict(request_id='b',bound_cny=2)]
        self.assertFalse(check_budget([dict(cost_or_reserved_cny=18)],{},Counter(),jobs[0],jobs))
        self.assertEqual(cost(dict(reserved_cny=.12),None),.12)
        self.assertEqual(cost(dict(reserved_cny=.12),dict(http_status=503)),.12)
    def test_actual_source_and_budget_invariants(self):
        rows=c.lines(c.OUT/'pool_operations.jsonl');corpus={p['passage_id']:p for p in c.lines(c.ROOT/'outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl')}
        for r in rows:
            self.assertTrue(r['roundtrip']);self.assertLessEqual(r['A_chars'],r['B_chars']);self.assertLessEqual(r['F_chars'],r['B_chars'])
            self.assertLessEqual(len(r['source_records']),16)
            counts=Counter()
            for p in r['source_records']:
                q=corpus[p['passage_id']];self.assertEqual(c.h(q['text']),p['text_sha256']);self.assertEqual(str(q['subject_id']),r['sid']);counts[q['note_id']]+=1
            self.assertLessEqual(max(counts.values()),2)
    def test_model_input_whitelist_and_immutable_claim(self):
        pool={r['id']:r for r in c.lines(c.PRIVATE/'pool_inputs.jsonl')}
        for j in c.lines(c.PRIVATE/'main_jobs.jsonl'):
            x=json.loads(j['body']['messages'][1]['content']);self.assertEqual(set(x),{'proposition','reference'})
            self.assertEqual(x['proposition'],pool[j['id']]['claim']);self.assertIn(x['reference'],[pool[j['id']][a] for a in ['B','F','A']])
            self.assertEqual(j['body']['max_tokens'],8192);self.assertEqual(j['body']['model'],'deepseek-v4-flash-0731')
if __name__=='__main__':unittest.main()

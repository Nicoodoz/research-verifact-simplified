"""Small deterministic checks for prompt, parser, accounting and source boundaries."""
import json,unittest
from prepare_a import original_style_prompt
from analyze_a import native_label
from audit_source_parent_b import parent_span
from run_a import charge

class Task097Tests(unittest.TestCase):
    def test_original_style_has_only_two_output_fields(self):
        s=original_style_prompt('Synthetic claim','Synthetic reference')
        self.assertIn('"verdict" and "reason"',s)
        self.assertNotIn('label_scores',s)
        self.assertNotIn('supporting_case',s)

    def test_final_label_parser_never_guesses_from_prose(self):
        def transport(content):
            response=dict(model='deepseek-v4-flash-0731',choices=[dict(finish_reason='stop',message=dict(content=content))],usage={})
            return dict(http_status=200,body_text=json.dumps(response))
        self.assertEqual(native_label(transport('{"verdict":"Supported","reason":"Synthetic."}'))[0],'Supported')
        self.assertIsNone(native_label(transport('I think Supported.'))[0])
        self.assertIsNone(native_label(transport('{"verdict":"Supported","verdict":"Not Supported","reason":"Synthetic."}'))[0])

    def test_parent_boundary_is_raw_note_paragraph(self):
        raw='First paragraph.\n\nA long second paragraph contains a synthetic finding.'
        a=raw.index('synthetic');b=a+len('synthetic')
        lo,hi=parent_span(raw,a,b)
        self.assertEqual(raw[lo:hi],'A long second paragraph contains a synthetic finding.')

    def test_unknown_charge_keeps_reservation(self):
        j=dict(bound_cny=.1)
        self.assertEqual(charge(j,dict(http_status=0,outcome_unknown=True)),.1)
        tr=dict(http_status=200,body_text=json.dumps(dict(model='deepseek-v4-flash-0731',usage=dict(prompt_tokens=1000,completion_tokens=100,prompt_tokens_details=dict(cached_tokens=0)))))
        self.assertAlmostEqual(charge(j,tr),.0039)

    def test_upstream_rerank_local_assignment_does_not_reorder_outer_list(self):
        outer=[[('A',.1),('B',.9)]]
        for row in outer:row=sorted(row,key=lambda x:x[1],reverse=True)
        self.assertEqual(outer[0][0][0],'A')
        # This only checks Python list assignment semantics, not historical publication behavior.

if __name__=='__main__':unittest.main()

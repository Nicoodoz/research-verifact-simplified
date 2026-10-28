"""Synthetic engineering fixtures only; no clinical records or model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy

import build104 as b
import common104 as c
import training104 as t
from test_training104 import CharacterTokenizer


def case(index=1,reference='1. Date: TEST, Time: TEST, Note Category: Test | Text: Alpha event occurred.\n'):
    return dict(review_index=index,id=f'synthetic-{index}',sid='synthetic_patient',author='human',claim='Alpha event occurred.',reference=reference,reference_id=c.digest(reference),reference_sha256=c.digest(reference))


def review(item):
    return dict(review_index=item['review_index'],id=item['id'],reviewer={1:'root',2:'semantic_b',0:'semantic_c'}[item['review_index']%3],full_reference_read=True,claim_slots=dict(subject='Synthetic subject',event='Alpha event',time='Unspecified',qualifiers='No additional qualifier'),independent_verdict='Supported',certainty='high',evidence_quotes=['Alpha event occurred.'],relation='The supplied source explicitly states the same event for the same synthetic subject. No further timing or qualifying claim is asserted.',issue_tags=[],na_anchor='not_applicable',review_stage='blind_v1')


class BuildTests(unittest.TestCase):
    def test_all_exact_occurrences_and_source_metadata(self):
        text='1. Date: TEST, Note ID: n1 | Text: Alpha.\n2. Date: TEST | Text: Alpha.'
        spans,issues=b.evidence_spans(text,['Alpha.'])
        self.assertFalse(issues)
        self.assertEqual(spans[0]['occurrence_count'],2)
        self.assertEqual([x['start'] for x in spans[0]['occurrences']],[text.index('Alpha.'),text.rindex('Alpha.')])
        self.assertEqual(spans[0]['occurrences'][0]['sources'][0]['note_id'],'n1')
        self.assertIsNone(spans[0]['occurrences'][1]['sources'][0]['note_id'])

    def test_no_normalization_or_fuzzy_quote_acceptance(self):
        spans,issues=b.evidence_spans('Alpha event.',['alpha event.'])
        self.assertEqual(spans[0]['occurrence_count'],0)
        self.assertTrue(issues)

    def test_full_reference_read_is_required(self):
        item=case();row=review(item);row['full_reference_read']=False
        with self.assertRaises(ValueError):b.validate_review(row,item)

    def test_no_anchor_na_and_gap_are_explicit(self):
        item=case();row=review(item)
        row.update(independent_verdict='Not Addressed',evidence_quotes=[],na_anchor='none')
        row['mechanical']=b.validate_review(row,item)
        self.assertTrue(row['mechanical']['no_anchor_na'])
        self.assertEqual(b.initial_status(row,'Not Addressed'),'candidate_gt_explained')
        self.assertEqual(b.initial_status(row,'Not Supported'),'reference_gap')
        self.assertEqual(b.initial_status(row,'Supported'),'reference_gap')

    def test_low_certainty_is_not_candidate(self):
        item=case();row=review(item);row['certainty']='low'
        row['mechanical']=b.validate_review(row,item)
        self.assertEqual(b.initial_status(row,'Supported'),'unresolved')

    def test_paired_rows_only_differ_in_answer(self):
        item=case();row=review(item)
        label,brief=b.pair_rows(item,row,'Supported',dict(example='synthetic'))
        for field in set(label)-{'answer','answer_text'}:
            self.assertEqual(label[field],brief[field])
        self.assertEqual(json.loads(label['answer']),dict(verdict='Supported'))
        self.assertEqual(json.loads(brief['answer'])['verdict'],label['GT'])
        self.assertNotIn('"verdict": "Supported"',label['messages'][1]['content'])

    def test_freeze_precedes_GT_and_detects_mutation(self):
        with tempfile.TemporaryDirectory(prefix='verifact104_synthetic_') as folder:
            private=Path(folder)/'private';out=Path(folder)/'out';private.mkdir()
            with self.assertRaisesRegex(ValueError,'freeze complete blind judgments'):
                b.build(private,out)
            cases=[case(i) for i in range(1,289)]
            c.putl(private/'blind_cases.jsonl',cases)
            parts={name:[] for name in b.REVIEW_NAMES}
            for item in cases:
                name={1:'review_root.jsonl',2:'review_b.jsonl',0:'review_c.jsonl'}[item['review_index']%3]
                parts[name].append(review(item))
            paths=[private/name for name in b.REVIEW_NAMES]
            for name,rows in parts.items():c.putl(private/name,rows)
            rows,summary=b.validate_files(private,paths)
            self.assertFalse(summary['GT_read'])
            frozen=b.freeze_blind(private,out,paths)
            self.assertFalse(frozen['GT_join_before_freeze'])
            self.assertEqual(len(b.load_frozen_reviews(private,out)),288)
            paths[0].write_bytes(paths[0].read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'changed after freeze'):
                b.load_frozen_reviews(private,out)

    def test_real_builder_to_training_loader_and_loss_masks(self):
        """Use the actual freeze/build/export/parser path with synthetic fixtures."""
        with tempfile.TemporaryDirectory(prefix='verifact104_e2e_synthetic_') as folder:
            private=Path(folder)/'private';out=Path(folder)/'out';private.mkdir()
            cases=[case(i) for i in range(1,289)]
            cases[0]=case(1,reference=cases[0]['reference']+'Repeated source: Alpha event occurred.\n')
            c.putl(private/'blind_cases.jsonl',cases)
            parts={name:[] for name in b.REVIEW_NAMES}
            assignments=[]
            GT={r['id']:'Supported' for r in cases}
            GT[cases[1]['id']]='Not Supported'
            GT[cases[2]['id']]='Not Addressed'
            GT[cases[3]['id']]='Not Supported'
            GT[cases[4]['id']]='Not Addressed'
            for item in cases:
                row=review(item)
                if item['review_index']==73:
                    row['reviewer']='semantic_b'  # Explicit reassignment, not mod-3.
                if item['review_index'] in (3,4):
                    row.update(independent_verdict='Not Addressed',evidence_quotes=[],na_anchor='none')
                if item['review_index']==5:
                    row.update(independent_verdict='Unclear',certainty='low')
                filename={'root':'review_root.jsonl','semantic_b':'review_b.jsonl','semantic_c':'review_c.jsonl'}[row['reviewer']]
                parts[filename].append(row)
                assignments.append(dict(review_index=item['review_index'],id=item['id'],reviewer=row['reviewer']))
            c.put(private/'assignment.json',dict(assignments=assignments))
            paths=[private/name for name in b.REVIEW_NAMES]
            for name,rows in parts.items():c.putl(private/name,rows)
            b.freeze_blind(private,out,paths)
            # GT files are supplied only after the first judgments are frozen.
            c.putl(private/'gt_key.jsonl',[dict(id=r['id'],review_index=r['review_index'],GT=GT[r['id']]) for r in cases])
            training=[dict(r,GT=GT[r['id']]) for r in cases]+[dict(case(i),GT='Supported') for i in range(289,513)]
            c.putl(private/'train512_original.jsonl',training)
            manifest=b.build(private,out)
            self.assertTrue(manifest['candidate_only'])
            initial_sha=c.sha(private/'review_joined_initial.jsonl')
            public_rows=c.lines(out/'review_status288.jsonl')
            for public_row in public_rows:
                self.assertFalse({'claim','reference','claim_slots','evidence_quotes','relation','revision_reason','mechanical'} & public_row.keys())
            self.assertNotIn('Alpha event occurred.',(out/'review_status288.jsonl').read_text(encoding='utf-8'))
            labels=t.load_rows(private/'candidate_paired/label_only.jsonl')
            briefs=t.load_rows(private/'candidate_paired/evidence_brief.jsonl')
            self.assertEqual(len(labels),285)
            self.assertEqual(t.validate_pairs(labels,briefs,{'synthetic_patient'},{'excluded_patient'})['N'],285)
            self.assertEqual(labels[0]['messages'],t.messages(labels[0]['claim'],labels[0]['reference']))
            self.assertEqual(labels[0]['answer'],labels[0]['answer_text'])
            self.assertEqual(briefs[0]['metadata']['evidence_spans'][0]['occurrence_count'],2)
            encoded=[t.encode_lists(CharacterTokenizer(),row) for row in (labels[0],briefs[0])]
            self.assertEqual(t.prompt_ids(CharacterTokenizer(),labels[0]),t.prompt_ids(CharacterTokenizer(),briefs[0]))
            for row,(ids,loss,supervised) in zip((labels[0],briefs[0]),encoded):
                self.assertEqual(CharacterTokenizer().decode(loss[-supervised:-1]),row['answer'])
                self.assertTrue(all(x==-100 for x in loss[:-supervised]))
                self.assertEqual(loss[-1],1)
            bad=deepcopy(briefs[0]);bad['metadata']['evidence_spans'][0]['occurrences']=bad['metadata']['evidence_spans'][0]['occurrences'][:1]
            with self.assertRaises(ValueError):t.parse_answer(bad,'evidence_brief')
            bad=deepcopy(briefs[0]);bad['answer_text']='different'
            with self.assertRaises(ValueError):t.parse_answer(bad,'evidence_brief')
            decisions=[dict(id=r['id'],reviewer='synthetic_quality_reviewer',revision_reason='Synthetic engineering acceptance fixture only; not clinical adjudication.',final_status='gt_explained',quality_approved=True) for r in labels]
            decision_path=private/'synthetic_decisions.jsonl';c.putl(decision_path,decisions)
            final=b.build(private,out,decision_path)
            self.assertFalse(final['candidate_only'])
            self.assertEqual(initial_sha,c.sha(private/'review_joined_initial.jsonl'))
            import teacher_queue104
            self.assertEqual(len(teacher_queue104.candidate_context(private,out)[0]),285)
            self.assertEqual(len(t.load_rows(private/'paired/label_only.jsonl')),285)
            self.assertEqual(t.validate_pairs(t.load_rows(private/'paired/label_only.jsonl'),t.load_rows(private/'paired/evidence_brief.jsonl'),{'synthetic_patient'})['N'],285)


if __name__=='__main__':unittest.main()

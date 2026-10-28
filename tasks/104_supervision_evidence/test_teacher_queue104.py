"""Synthetic source/reuse pipeline checks; no real candidate or teacher file."""
from pathlib import Path
import tempfile
import unittest

import common104 as c
import build104 as b
import teacher_queue104 as q
import training104 as t
from test_build104 import case,review


def teacher(item,model='R1-70B',verdict='Supported',reason='The source states that the synthetic event occurred.'):
    return dict(proposition_id=item['id'],model=model,rater_alias='fixture-'+model,verdict=verdict,reason=reason,
                reference_id=item['reference_id'],reference_sha256=item['reference_sha256'],
                claim_sha256=c.digest(item['claim']),reasoning_chain='Not used as training supervision.',reasoning_final_answer=None)


def context(private,out):
    private.mkdir();cases=[case(i) for i in range(1,289)]
    c.putl(private/'blind_cases.jsonl',cases)
    parts={name:[] for name in b.REVIEW_NAMES}
    for item in cases:
        parts[{1:'review_root.jsonl',2:'review_b.jsonl',0:'review_c.jsonl'}[item['review_index']%3]].append(review(item))
    paths=[private/name for name in b.REVIEW_NAMES]
    for name,rows in parts.items():c.putl(private/name,rows)
    b.freeze_blind(private,out,paths)
    c.putl(private/'gt_key.jsonl',[dict(id=r['id'],review_index=r['review_index'],GT='Supported') for r in cases])
    c.putl(private/'train512_original.jsonl',[dict(case(i),GT='Supported') for i in range(1,513)])
    b.build(private,out)
    teachers=[teacher(cases[0],'Llama-70B'),teacher(cases[0]),teacher(cases[1],verdict='Not Addressed'),teacher(cases[1],'R1-8B'),teacher(cases[1],'Llama-8B'),teacher(cases[4],reason='The source asserts an additional synthetic outcome that is not in the fixture.')]
    c.putl(private/'teachers_same_reference.jsonl',teachers)
    return cases


class TeacherQueueTests(unittest.TestCase):
    def test_priority_and_reference_mismatch_are_not_semantic_approval(self):
        item=case();a=teacher(item,'R1-70B');other=teacher(item,'Llama-70B')
        wrong=teacher(item);wrong['reference_sha256']='other'
        chosen,count,excluded=q.choose_teacher(item,'Supported',[other,wrong,a])
        self.assertEqual(chosen['model'],'R1-70B');self.assertEqual(count,2)
        self.assertEqual(excluded['reference_mismatch'],1)
        chosen,count,_=q.choose_teacher(item,'Not Supported',[a,other])
        self.assertIsNone(chosen);self.assertEqual(count,0)

    def test_export_refuses_before_blind_freeze(self):
        with tempfile.TemporaryDirectory(prefix='verifact104_teacher_synthetic_') as temp:
            with self.assertRaisesRegex(ValueError,'freeze complete blind judgments'):
                q.export_queue(Path(temp)/'private',Path(temp)/'out')

    def test_export_semantic_actions_and_strictly_paired_revised_package(self):
        with tempfile.TemporaryDirectory(prefix='verifact104_teacher_e2e_synthetic_') as temp:
            private=Path(temp)/'private';out=Path(temp)/'out'
            cases=context(private,out)
            source_label_sha=c.sha(private/'candidate_paired/label_only.jsonl')
            source_brief_sha=c.sha(private/'candidate_paired/evidence_brief.jsonl')
            manifest=q.export_queue(private,out)
            self.assertEqual(manifest['N'],288)
            queue=c.lines(private/'teacher_queue.jsonl')
            self.assertEqual(queue[0]['teacher']['model'],'R1-70B')
            self.assertEqual(queue[1]['teacher']['model'],'Llama-8B')
            self.assertIsNone(queue[2]['teacher'])
            decisions=[]
            for item in queue:
                index=item['review_index'];source=item['teacher']
                action={1:'reuse',2:'revise',4:'quarantine',5:'reject_teacher_keep_blind'}.get(index,'new_draft')
                decision=dict(id=item['id'],action=action,reviewer='synthetic_teacher_reviewer',semantic_checked=True,grounding_assessment='Synthetic engineering comparison only, not a clinical judgment.')
                if source:decision['teacher_reason_sha256']=source['reason_sha256']
                if action in {'reuse','revise'}:decision['retained_teacher_facts']=['Synthetic event occurrence.']
                if action=='revise':
                    decision.update(relation=source['reason']+' The claim does not assert any additional outcome.',revision_notes='Explicitly bounded the retained statement to the asserted event.')
                decisions.append(decision)
            path=private/'synthetic_teacher_decisions.jsonl';c.putl(path,decisions)
            checked=q.apply_decisions(private,out,path)
            self.assertEqual(checked['N'],287)
            self.assertEqual(checked['actions']['reuse'],1)
            self.assertEqual(checked['actions']['revise'],1)
            self.assertEqual(checked['actions']['reject_teacher_keep_blind'],1)
            self.assertEqual(checked['actions']['quarantine'],1)
            labels=t.load_rows(private/'candidate_teacher_checked/label_only.jsonl')
            briefs=t.load_rows(private/'candidate_teacher_checked/evidence_brief.jsonl')
            self.assertEqual(t.validate_pairs(labels,briefs,{'synthetic_patient'})['N'],287)
            self.assertEqual(labels[0]['metadata']['relation_origin'],'existing_teacher_exact')
            self.assertEqual(briefs[1]['metadata']['relation_origin'],'existing_teacher_revised')
            self.assertEqual(source_label_sha,c.sha(private/'candidate_paired/label_only.jsonl'))
            self.assertEqual(source_brief_sha,c.sha(private/'candidate_paired/evidence_brief.jsonl'))
            provenance=c.lines(out/'teacher_provenance.jsonl')
            forbidden={'claim','reference','relation','reason','grounding_assessment','retained_teacher_facts','revision_notes'}
            self.assertTrue(all(not forbidden&row.keys() for row in provenance))
            snapshot=private/'teacher_decision_snapshots'/c.sha(path)
            self.assertTrue((snapshot/'decisions.jsonl').is_file())
            self.assertTrue((snapshot/'history.jsonl').is_file())
            # Final build keeps immutable initial source and teacher-adjusted text.
            initial_sha=c.sha(private/'review_joined_initial.jsonl')
            final_decisions=[]
            for label,brief in zip(labels,briefs):
                answer=t.parse_answer(brief,'evidence_brief')
                final_decisions.append(dict(id=label['id'],reviewer='synthetic_final_reviewer',revision_reason='Synthetic quality acceptance only.',final_status='gt_explained',quality_approved=True,
                                            relation=answer['relation'],evidence_quotes=answer['evidence'],
                                            supervision_metadata={k:brief['metadata'][k] for k in b.SUPERVISION_METADATA_FIELDS}))
            final_path=private/'synthetic_final_decisions.jsonl';c.putl(final_path,final_decisions)
            b.build(private,out,final_path)
            self.assertEqual(c.sha(private/'review_joined_initial.jsonl'),initial_sha)
            self.assertEqual(len(q.candidate_context(private,out)[0]),288)
            final_briefs=t.load_rows(private/'paired/evidence_brief.jsonl')
            self.assertEqual(t.parse_answer(final_briefs[0],'evidence_brief')['relation'],queue[0]['teacher']['reason'])
            self.assertEqual(final_briefs[0]['metadata']['relation_origin'],'existing_teacher_exact')
            self.assertEqual(final_briefs[0]['metadata']['teacher_review']['teacher_model'],'R1-70B')
            self.assertTrue(final_briefs[0]['metadata']['teacher_semantic_reviewed'])
            decisions[0]['teacher_reason_sha256']='wrong'
            c.putl(path,decisions)
            with self.assertRaisesRegex(ValueError,'exact teacher reason'):
                q.apply_decisions(private,out,path)


if __name__=='__main__':unittest.main()

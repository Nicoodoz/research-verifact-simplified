"""Actual-corpus invariants and hostile mutation checks; no model or network."""
from collections import Counter
from copy import deepcopy
import json
import unittest

from data106 import ROOT, OUT, PRIVATE, LABELS, QUOTAS, rows, read, digest, messages


def validate_arm(values, original, allowed, excluded, gap_ids):
    if len(values)!=512 or len({r['id'] for r in values})!=512:
        raise ValueError('Fixed N or unique ID contract broken')
    if Counter(r['GT'] for r in values)!=QUOTAS:
        raise ValueError('Fixed class quota broken')
    for r in values:
        if r['id'] not in original or r['sid'] not in allowed or r['sid'] in excluded or r['id'] in gap_ids:
            raise ValueError('Patient, source-pool, or known-gap boundary broken')
        source=original[r['id']]
        for key in ('id','sid','GT','author','claim','reference','reference_id','role'):
            if r[key]!=source[key]:
                raise ValueError('Original source field changed: '+key)
        if digest(r['reference'])!=r['reference_sha256'] or r['reference_sha256']!=r['reference_id']:
            raise ValueError('Reference identity contract broken')
        expected=json.dumps({'verdict':r['GT']},ensure_ascii=False,separators=(',',':'))
        if r['answer']!=expected or r['answer_text']!=expected:
            raise ValueError('Supervision must be only the unchanged original label')
        if r['messages']!=messages(source['claim'],source['reference']):
            raise ValueError('Claim/reference-only frozen prompt contract broken')
    return True


class Data106Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool={r['id']:r for r in rows(PRIVATE/'training_pool.jsonl')}
        role=read(ROOT/'outputs/103_lora_selection/patient_roles.json')['patients']
        cls.allowed=set(role['train']);cls.excluded=set(role['selection']+role['confirmation'])
        cls.gap={r['id'] for r in rows(OUT/'data_isolation.jsonl')}
        cls.data={a:rows(PRIVATE/f'{a}.jsonl') for a in ('ordinary_sample','boundary_cover')}
        cls.meta={a:rows(OUT/f'data_{a}_manifest.jsonl') for a in cls.data}

    def test_actual_data_originals_and_scope(self):
        for values in self.data.values():
            self.assertTrue(validate_arm(values,self.pool,self.allowed,self.excluded,self.gap))
            self.assertEqual({r['sid'] for r in values},self.allowed)

    def test_identical_patient_label_source_length_review_state_per_slot(self):
        a,b=self.meta['ordinary_sample'],self.meta['boundary_cover']
        self.assertTrue(all(x['stratum']==y['stratum'] for x,y in zip(a,b)))
        self.assertEqual(len(a[0]['stratum']),5)
        self.assertEqual(len(set(r['id'] for r in a)&set(r['id'] for r in b)),read(OUT/'data_matching.json')['overlap_N'])

    def test_fixed_difficulty_buckets_and_positive_counterparts(self):
        boundary=self.meta['boundary_cover']
        for gt in LABELS[1:]:
            subset=[r for r in boundary if r['GT']==gt]
            self.assertEqual(sum(r['paper_r1']==LABELS[0] for r in subset),64)
            self.assertEqual(sum(r['paper_r1'] in LABELS[1:] and r['paper_r1']!=gt for r in subset),32)
        pairs=rows(OUT/'data_boundary_cover_pairs.jsonl')
        positive=[r for r in pairs if r['kind']=='S_nonS']
        self.assertEqual(len(positive),192)
        self.assertTrue(all(r['peer_in_same_dataset'] and r['same_patient'] for r in positive))
        self.assertTrue(all(r['nonS_reference_sha256']!=r['peer_reference_sha256'] for r in positive))

    def test_hostile_reference_label_prompt_and_patient_mutations_rejected(self):
        # Only the modified row is copied; the original private sources stay put.
        for key,new in (('reference','tampered'),('GT','changed'),('sid',next(iter(self.excluded))),
                        ('messages',[{'role':'user','content':'leaked physician label'}])):
            values=list(self.data['ordinary_sample']);values[0]=dict(values[0]);values[0][key]=new
            with self.assertRaises(ValueError,msg=key):
                validate_arm(values,self.pool,self.allowed,self.excluded,self.gap)

    def test_development_ids_never_enter_training(self):
        selection={r['id'] for r in rows(ROOT/'outputs/105_brief_supervision/eval_keys.jsonl')}
        for values in self.data.values():
            self.assertFalse(selection&{r['id'] for r in values})


if __name__=='__main__':unittest.main()

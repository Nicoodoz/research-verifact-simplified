"""Synthetic end-to-end evaluator test; isolated temporary output, no API and no study effect."""
import contextlib,io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import analyze024_core as a
c=a.c
class Pipeline(unittest.TestCase):
    def test_distinct_missing_sets_end_to_end(self):
        rows=[dict(proposition_id=f'test{i:04}',subject_id=str(i%10),author_type='human' if i%2 else 'llm',human_gt=c.LABELS[i%3]) for i in range(879)]
        hist=[dict(r,**{k:r['human_gt'] for k in ('B','V_raw','U0','U2','O')}) for r in rows]
        jobs=[];terminal={};attempts=[]
        for r in rows:
            for model in c.MODELS:
                for arm in ('B','S'):
                    rid=r['proposition_id']+model+arm;j=dict(request_id=rid,proposition_id=r['proposition_id'],model_key=model,arm=arm);jobs.append(j)
                    bad=(r['proposition_id']=='test0001' and model=='deepseek' and arm=='B') or (r['proposition_id']=='test0002' and model=='qwen' and arm=='S')
                    terminal[rid]=dict(status='invalid_core_fields' if bad else 'valid',verdict=None if bad else 'Supported',scores=None if bad or arm=='B' else {'Supported':40,'Not Supported':55,'Not Addressed':5},errors=['synthetic_missing'] if bad else [],adherence=[],model_returned=c.MODELS[model],usage={'prompt_tokens':1,'completion_tokens':1})
                    attempts.append(dict(request_id=rid,model_key=model,charge_cny=.000001,charge_basis='peak_no_cache_usage_estimate',http_status=200))
        replay=c.ROOT/'outputs/replays';replay.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='024_synthetic_',dir=replay) as td:
            c.require(Path(td).resolve().is_relative_to(replay.resolve()),'Unsafe temporary test directory')
            out=Path(td);(out/'preparation_001').mkdir();c.put(out/'preparation_001/manifest.json',{})
            actual_csv=c.csvread
            def csvread(path):return hist if 'predictions_r' in str(path) else rows
            with patch.object(c,'OUT',out),patch.object(c,'verify_inputs',return_value=jobs),patch.object(c,'load_attempts',return_value=(attempts,terminal)),patch.object(c,'csvread',side_effect=csvread),contextlib.redirect_stdout(io.StringIO()):
                a.run(out/'analysis')
            cohorts=c.read(out/'analysis/comparison_cohorts.json')
            self.assertEqual(cohorts['deepseek/all/U2-minus-U0']['valid_n'],879)
            self.assertEqual(cohorts['deepseek/all/U2-minus-B']['valid_n'],878)
            self.assertEqual(cohorts['qwen/all/U2-minus-U0']['valid_n'],878)
            self.assertEqual(cohorts['qwen-minus-deepseek/all/U2']['valid_n'],878)
            self.assertEqual(cohorts['qwen-minus-deepseek/all/B']['valid_n'],878)
            self.assertEqual(len(c.read(out/'analysis/invalid_missing.json')),2)
            sensitivity=actual_csv(out/'analysis/missing_as_error.csv')
            self.assertTrue(all(int(r['frozen_n'])==879 for r in sensitivity if r['author']=='all'))
if __name__=='__main__':unittest.main()

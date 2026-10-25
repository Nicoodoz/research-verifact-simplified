import unittest,json
import pricing095 as p
class Pricing(unittest.TestCase):
    def tr(self,s,e):return dict(started_utc=s,ended_utc=e,body_text=json.dumps(dict(model='deepseek-v4-flash-0731',usage=dict(prompt_tokens=1000,completion_tokens=100,prompt_tokens_details=dict(cached_tokens=100)))))
    def test_idle_and_actual_cache(self):
        t=self.tr('2026-09-27T15:00:00+00:00','2026-09-27T15:01:00+00:00');self.assertAlmostEqual(p.charge({'bound_cny':1},t),.001815)
    def test_boundaries_and_unknown(self):
        for s,e in [('2026-09-27T13:59:59+00:00','2026-09-27T14:00:01+00:00'),('2026-09-27T23:59:59+00:00','2026-09-28T00:00:01+00:00')]:self.assertFalse(p.inside_one_idle_window(self.tr(s,e)))
        self.assertEqual(p.charge({'bound_cny':1},{}),1)
        self.assertFalse(p.inside_one_idle_window(self.tr('2026-09-27T15:00:00','2026-09-27T15:01:00')))
if __name__=='__main__':unittest.main()

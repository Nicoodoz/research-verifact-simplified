"""Use unspent stopped-branch budget for the original B, never reset total cap."""
import statistics,datetime,copy
import common095 as c
import state095 as s
import run095_v3 as runtime

def main():
    assert not (c.PRIVATE/'run.lock').exists();assert c.read(c.OUT/'construction_stop.json')['decision']=='STOP_C_FINAL_JUDGE_CONTINUE_A_F'
    jobs=runtime.remaining_baseline(c.lines(c.PRIVATE/'baseline_jobs.jsonl'),s.successful_jobs());aa=s.attempts();used=sum(a['charge_or_reserved_cny'] for a in aa);us=[a['usage'] for a in aa if a['arm']=='B' and a['http_status']==200 and a['usage']]
    mean_busy=statistics.mean((u['prompt_tokens']*3+u['completion_tokens']*9)/1e6 for u in us)
    local=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)));remaining_idle_hours=(8-local.hour-local.minute/60) if local.hour<8 else (32-local.hour-local.minute/60) if local.hour>=22 else 0
    seconds=[a['elapsed_seconds'] for a in aa if a['arm']=='B' and a['http_status']==200 and a['elapsed_seconds']];forecast_hours=len(jobs)*statistics.mean(seconds)/16/3600*2
    factor=.5 if remaining_idle_hours>forecast_hours+.25 else 1.;expected=len(jobs)*mean_busy*factor
    plan=dict(utc=c.now(),remaining=len(jobs),already_spent_or_reserved_cny=used,mean_busy_no_cache_cny=mean_busy,tariff_factor_for_forecast=factor,remaining_expected_cny=expected,expected_hours_with2x_margin=forecast_hours,remaining_idle_hours=remaining_idle_hours,extra_baseline_phase_cap_cny=25,shared_task_normal_cap_cny=130,shared_task_hard_cap_cny=150,reason='Specified candidate globally stopped on operation fidelity, no final Judge or expansion. Release unspent method allocation to complete unchanged original B in original fixed order, same SQLite total. Not a new task or reset budget.')
    assert expected*1.25+2<=25 and used+expected*1.25+2<=130,('remaining full baseline forecast cannot fit conservative completion allocation',plan)
    for j in jobs:j['phase']='baseline_completion'
    path=c.PRIVATE/'baseline_completion_jobs.jsonl'
    if not path.exists():c.putl(path,jobs);plan['jobs_sha256']=c.sha(path);plan['code_sha256']=c.sha(c.TASK/'finish_baseline095.py');c.put(c.OUT/'baseline_completion_plan.json',plan)
    else:
        frozen=c.read(c.OUT/'baseline_completion_plan.json');assert c.sha(path)==frozen['jobs_sha256'] and c.sha(c.TASK/'finish_baseline095.py')==frozen['code_sha256']
    runtime.runner.LIMITS['baseline_completion']=25
    runtime.run('baseline_completion',16)
if __name__=='__main__':main()

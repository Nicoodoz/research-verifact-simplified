"""Distinct computation and save deadlines; no clock or GPU side effects."""


def deadlines(started, session, job):
    global_end = session['start_epoch'] + 3600 * session['GPU_cap_CNY'] / session['hourly_CNY']
    reserve = job['save_reserve_seconds']
    compute_end = min(started + job['compute_limit_seconds'], global_end - reserve)
    return dict(global_end=global_end, compute_end=compute_end,
                stage_end=min(started + job['compute_limit_seconds'] + reserve, global_end),
                save_reserve_seconds=reserve, available_compute_seconds=max(0, compute_end - started))

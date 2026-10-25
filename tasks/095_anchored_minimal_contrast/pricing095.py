"""Verified ordinary-service time tariff; unknowns retain the peak maximum."""
import datetime,json
import common095 as c

def inside_one_idle_window(tr):
    try:
        start=datetime.datetime.fromisoformat(tr['started_utc']);end=datetime.datetime.fromisoformat(tr['ended_utc'])
        if start.tzinfo is None or end.tzinfo is None or end<start:return False
        zone=datetime.timezone(datetime.timedelta(hours=8));start=start.astimezone(zone);end=end.astimezone(zone)
        if (end-start).total_seconds()>3600:return False
        def window(t):
            if t.hour>=22:return t.date()
            if t.hour<8:return t.date()-datetime.timedelta(days=1)
            return None
        return window(start) is not None and window(start)==window(end)
    except (KeyError,ValueError,TypeError):return False

def charge(j,tr):
    try:
        n=json.loads(tr['body_text']);u=n['usage'];i=u['prompt_tokens'];o=u['completion_tokens'];cached=u.get('prompt_tokens_details',{}).get('cached_tokens',0)
        assert all(type(v)is int and v>=0 for v in [i,o,cached]) and cached<=i
        assert n.get('model')==c.MODEL
        peak=((i-cached)*3+cached*.3+o*9)/1e6
        assert peak<=j['bound_cny']+1e-8
        return peak*(.5 if inside_one_idle_window(tr) else 1.)
    except (ValueError,KeyError,AssertionError,TypeError):return j['bound_cny']

"""Reject unknown/error envelopes before releasing any pre-send maximum reserve."""
from pricing095 import inside_one_idle_window
import pricing095

def charge(j,tr):
    if not tr or tr.get('http_status')!=200 or tr.get('outcome_unknown') is True:return j['bound_cny']
    return pricing095.charge(j,tr)

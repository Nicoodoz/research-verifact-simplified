"""Pure accounting checks; not an API runner. StageA has an empty attempt ledger."""
from decimal import Decimal
import common022 as c

def total(attempts,cap='80'):
    seen={}
    for a in attempts:
        key=a['attempt_id'];c.require(isinstance(key,str) and key,'Attempt ID required')
        value=Decimal(str(a['cost_or_reservation_cny']))
        c.require(value.is_finite() and value>=0,'Bad cost')
        if key in seen:c.require(seen[key]==a,'Conflicting restored attempt')
        seen[key]=a
    result=sum((Decimal(str(a['cost_or_reservation_cny'])) for a in seen.values()),Decimal('0'))
    c.require(result<=Decimal(cap),'Task cap exceeded')
    return result

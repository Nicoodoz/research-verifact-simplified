"""Continue bounded017 batches; pause on errors or provider migration for notification."""
import common017 as c
from run017 import run

if __name__=='__main__':
    for _ in range(30):
        result=run(64,8)
        if result['halt'] or result['received']==result['total']:break
    else:raise ValueError('Batch bound reached; inspect checkpoint')

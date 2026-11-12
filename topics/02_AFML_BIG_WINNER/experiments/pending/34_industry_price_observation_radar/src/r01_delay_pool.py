"""Candidate confirmation wrapper; daily input must contain past-only features."""
import numpy as np
from r01_pool import ObservationPool


class DelayedPool:
    def __init__(self,config,delay):
        self.pool=ObservationPool(config);self.delay=delay;self.pending={};self.era=None

    def step(self,era,date,day,rows,daily):
        if self.era!=era:self.pending.clear()
        self.era=era
        active=set(self.pool.active) if self.pool.era==era else set()
        exits=self.pool.exits if self.pool.era==era else {}
        adjusted=[];waiting=set();seeds={}
        for row in rows:
            r=dict(row);code=r['industry_code']
            known=bool(r['eligible']) and np.isfinite(r['score'])
            cooling=code in exits and day-exits[code]<self.pool.c['cooldown_sessions']
            if code in active or cooling or not known or r['score']<=0:
                self.pending.pop(code,None)
            else:
                seed=self.pending.get(code,day)
                history=daily.get(code)
                if history is None:
                    continuous=False
                else:
                    window=history[(history.day_i>=seed)&(history.day_i<=day)]
                    continuous=(np.array_equal(window.day_i.to_numpy(),np.arange(seed,day+1))
                                and window.eligible.eq(True).all() and window.score.gt(0).all())
                if not continuous:seed=day
                self.pending[code]=seed;seeds[code]=seed
                if day-seed<self.delay:
                    r['score']=0.0;waiting.add(code)
            adjusted.append(r)
        states,events=self.pool.step(era,date,day,adjusted)
        for code in waiting:
            if states[code]['state']=='NOT_TRIGGERED':states[code]['reason']='WAITING_CONTINUOUS_CONFIRMATION'
        for event in events:
            if event['event']=='NEW':
                code=event['industry_code'];event['candidate_day']=seeds[code]
                event['confirmation_wait']=day-seeds[code];self.pending.pop(code,None)
        return states,events

"""Weekly attention state machine. Receives past-only scores, never process labels."""
import hashlib
import numpy as np


class ObservationPool:
    def __init__(self,config):
        self.c=config;self.active={};self.exits={};self.era=None;self.last_day=None;self.last_week=None

    def close_era(self,date,day_i):
        if self.last_day is not None and day_i<self.last_day:raise ValueError('boundary precedes prior review')
        events=[dict(era=self.era,industry_code=code,date=date,day_i=day_i,event='EXIT',reason='CLASSIFICATION_BOUNDARY',**old)
                for code,old in sorted(self.active.items())]
        self.active.clear();self.exits.clear();self.era=None;self.last_day=day_i
        return events

    def step(self,era,date,day_i,catalog_scores):
        week=str(date.to_period('W-SUN'))
        if self.last_day is not None and day_i<=self.last_day:raise ValueError('reviews must be strictly chronological')
        if self.last_week==week:raise ValueError('one review per calendar week')
        events=[]
        if self.era is not None and era!=self.era:
            for code,old in sorted(self.active.items()):
                events.append(dict(era=self.era,industry_code=code,date=date,day_i=day_i,event='EXIT',reason='CLASSIFICATION_BOUNDARY',**old))
            self.active.clear();self.exits.clear()
        self.era=era;self.last_day=day_i;self.last_week=week
        by_code={r['industry_code']:r for r in catalog_scores}
        if len(by_code)!=len(catalog_scores):raise ValueError('duplicate catalog industry')
        if set(self.active)-set(by_code):raise ValueError('full catalog required, missing active industry')
        states={};exited=set()
        for code,old in list(sorted(self.active.items())):
            r=by_code[code];known=bool(r['eligible']) and np.isfinite(r['score'])
            old['missing_reviews']=0 if known else old['missing_reviews']+1
            reason=None
            if day_i-old['entry_day']>=self.c['max_age_sessions']:reason='MAX_OBSERVATION_AGE'
            elif not known and old['missing_reviews']>=self.c['missing_reviews_to_exit']:reason='REPEATED_DATA_UNKNOWN'
            elif known and r['score']<=0:reason='NONPOSITIVE_MOMENTUM'
            if reason:
                events.append(dict(era=era,industry_code=code,date=date,day_i=day_i,event='EXIT',reason=reason,**old))
                self.exits[code]=day_i;del self.active[code];exited.add(code)
                states[code]=dict(state='EXIT',reason=reason,observation_id=old['observation_id'],in_pool=False)
            else:
                states[code]=dict(state='TRACKING' if known else 'DATA_INSUFFICIENT',reason='CONTINUING' if known else 'SUSPENDED_UNKNOWN',observation_id=old['observation_id'],in_pool=True)
                events.append(dict(era=era,industry_code=code,date=date,day_i=day_i,event='UPDATE',reason=states[code]['reason'],**old))
        candidates=[r for code,r in by_code.items() if code not in self.active and code not in exited
                    and r['eligible'] and np.isfinite(r['score']) and r['score']>0
                    and (code not in self.exits or day_i-self.exits[code]>=self.c['cooldown_sessions'])]
        candidates.sort(key=lambda r:(-r['score'],r['industry_code']))
        slots=min(self.c['weekly_new_cap'],self.c['pool_cap']-len(self.active))
        for r in candidates[:max(0,slots)]:
            code=r['industry_code'];oid=hashlib.sha256(f"{self.c['version']}|{era}|{code}|{date.date()}".encode()).hexdigest()[:24]
            entry=dict(observation_id=oid,entry_day=day_i,entry_date=date,missing_reviews=0)
            self.active[code]=entry
            events.append(dict(era=era,industry_code=code,date=date,day_i=day_i,event='NEW',reason='POSITIVE_MOMENTUM_CAPACITY_RANK',**entry))
            states[code]=dict(state='NEW',reason='POSITIVE_MOMENTUM_CAPACITY_RANK',observation_id=oid,in_pool=True)
        for code,r in by_code.items():
            if code in states:continue
            known=bool(r['eligible']) and np.isfinite(r['score'])
            reason='DATA_UNKNOWN' if not known else 'NONPOSITIVE_MOMENTUM' if r['score']<=0 else 'COOLDOWN' if code in self.exits and day_i-self.exits[code]<self.c['cooldown_sessions'] else 'CAPACITY_NOT_SELECTED'
            states[code]=dict(state='NOT_TRIGGERED' if known else 'DATA_INSUFFICIENT',reason=reason,observation_id=None,in_pool=False)
        assert len(self.active)<=self.c['pool_cap']
        assert sum(e['event']=='NEW' for e in events)<=self.c['weekly_new_cap']
        return states,events

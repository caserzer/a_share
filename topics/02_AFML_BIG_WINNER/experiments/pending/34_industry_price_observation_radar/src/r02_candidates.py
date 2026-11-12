"""Common candidate schedule independent of rankings and future outcomes."""
import hashlib
import numpy as np


class CommonCandidates:
    def __init__(self,cooldown=20):
        self.cooldown=cooldown;self.previous={};self.last_ticket={};self.last_day={}

    def step(self,era,date,day,rows):
        if era in self.last_day and day<=self.last_day[era]:raise ValueError('nonchronological review')
        self.last_day[era]=day
        codes=[x['industry_code'] for x in rows]
        if len(codes)!=len(set(codes)):raise ValueError('duplicate industry')
        output=[]
        for row in rows:
            r=dict(row);key=(era,r['industry_code']);old=self.previous.get(key)
            known=bool(r['eligible']) and all(np.isfinite(r[x]) for x in ['r5','r20','delta20'])
            current=None if not known else bool(r['r5']>0)
            ticket=None
            if current is None:reason='DATA_UNKNOWN'
            elif not current:reason='NONPOSITIVE_SHORT_FEEDBACK'
            elif old is True:reason='SAME_POSITIVE_SEGMENT'
            elif key in self.last_ticket and day-self.last_ticket[key]<self.cooldown:reason='COMMON_TICKET_COOLDOWN'
            else:
                reason='NEW_COMMON_CANDIDATE';self.last_ticket[key]=day
                ticket=hashlib.sha256(f'R02|{era}|{r["industry_code"]}|{date.date()}'.encode()).hexdigest()[:24]
            self.previous[key]=current
            output.append(dict(**r,era=era,date=date,day_i=day,previous_feedback_unknown=old is None,reason=reason,ticket_id=ticket))
        return output


def select(rows,score,cap=5):
    candidates=[r for r in rows if r['ticket_id'] is not None]
    return sorted(candidates,key=lambda r:(-r[score],r['industry_code']))[:cap]

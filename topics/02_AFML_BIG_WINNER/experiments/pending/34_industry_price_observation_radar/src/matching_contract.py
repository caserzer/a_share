"""Draft accounting primitives. No real signal evaluation is authorized by this module."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Process:
    process_id: str
    identity: str
    origin: int
    end: int
    evidence_start: int
    evidence_end: int
    window_start: int
    window_end: int
    known: bool = True
    left_origin_uncertain: bool = False

    def validate(self):
        if self.end < self.origin or self.evidence_start < self.origin or self.evidence_end < self.evidence_start:
            raise ValueError('invalid process or evidence interval')
        if self.known and self.evidence_end > self.end:
            raise ValueError('confirmed evidence extends beyond process')
        if self.window_end < self.window_start:
            raise ValueError('empty identification window')


@dataclass(frozen=True)
class Alert:
    alert_id: str
    identity: str
    day: int
    post_valid: bool | None
    label_coverage_known: bool = True
    is_new: bool = True
    evaluation_status: str | None = None


def match_draft(processes, alerts):
    """Deterministic first ownership. post_valid is assessed elsewhere using only post-alert prices."""
    processes=list(processes);alerts=list(alerts)
    if len({p.process_id for p in processes}) != len(processes):
        raise ValueError('duplicate process identity')
    new=[a for a in alerts if a.is_new]
    if len({a.alert_id for a in new}) != len(new):
        raise ValueError('duplicate new observation identity')
    for p in processes:p.validate()
    claimed={};results=[]
    for a in sorted(alerts,key=lambda a:(a.day,a.alert_id,not a.is_new)):
        result=dict(alert_id=a.alert_id,day=a.day,process_id=None,recall_credit=False,evaluation_status=a.evaluation_status)
        if not a.is_new:
            result.update(outcome='UPDATE',new_observation_denominator=False)
            results.append(result);continue
        eligible=[p for p in processes if p.identity==a.identity and p.window_start<=a.day<=p.window_end]
        if not eligible:
            unknown=not a.label_coverage_known or a.post_valid is None
            result.update(outcome='UNKNOWN' if unknown else 'UNMATCHED_FAILURE',new_observation_denominator=not unknown)
        else:
            p=min(eligible,key=lambda p:(abs(p.origin-a.day),p.origin,p.process_id))
            result['process_id']=p.process_id
            known=p.known and not p.left_origin_uncertain and a.post_valid is not None and a.label_coverage_known
            if p.process_id in claimed:
                result.update(outcome='DUPLICATE' if known else 'UNKNOWN_DUPLICATE',
                              first_alert_id=claimed[p.process_id],new_observation_denominator=known)
            else:
                claimed[p.process_id]=a.alert_id
                success=known and bool(a.post_valid)
                result.update(outcome='SUCCESS' if success else ('FIRST_FAILURE' if known else 'UNKNOWN'),
                              new_observation_denominator=known,recall_credit=success)
        if a.evaluation_status=='IMMATURE' and result['outcome'] in ['UNKNOWN','UNKNOWN_DUPLICATE']:
            result['outcome']='IMMATURE_DUPLICATE' if result['outcome']=='UNKNOWN_DUPLICATE' else 'IMMATURE'
        results.append(result)
    assert len([r['process_id'] for r in results if r['recall_credit']])==len({r['process_id'] for r in results if r['recall_credit']})
    return results

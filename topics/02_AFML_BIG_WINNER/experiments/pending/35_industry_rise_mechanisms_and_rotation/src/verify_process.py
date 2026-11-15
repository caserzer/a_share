import pandas as pd
from common import *


def run():
    out=ROOT/'outputs/r09';r=json.loads((out/'receipt.json').read_text())
    assert sha(ROOT/'protocols/r09.json')==r['protocol_sha256']
    for path,h in r['source_hashes'].items():assert sha(path)==h,path
    a=pd.read_parquet(out/'alerts.parquet');events=pd.read_csv(out/'confirmation_events.csv',parse_dates=['date'])
    hits=pd.read_csv(out/'event_hits.csv',parse_dates=['date','first_alert'])
    s=pd.read_csv(out/'summary.csv');keys=KEY+['date']
    assert not a.duplicated(keys+['strategy']).any()
    raw=a[a.strategy.eq('daily')].set_index(keys);monthly=a[a.strategy.eq('monthly')].set_index(keys);cd=a[a.strategy.eq('daily_cooldown20')].set_index(keys)
    assert monthly.index.isin(raw.index).all() and cd.index.isin(raw.index).all()
    assert np.allclose(monthly.score,raw.loc[monthly.index,'score'])
    for _,g in a[a.strategy.eq('daily_cooldown20')].groupby(KEY):assert g.sort_values('day_i').day_i.diff().dropna().gt(20).all()
    assert hits.loc[hits.hit,'lead_sessions'].between(1,20).all()
    assert (hits.loc[hits.hit,'first_alert']<hits.loc[hits.hit,'date']).all()
    assert not hits.loc[~hits.evaluable,'hit'].any()
    assert events.loc[events.evaluable,'prior_scored_days'].eq(20).all()
    assert s.groupby(['era','level']).events.nunique().eq(1).all()
    assert ((s.mature_alerts+s.unknown_alert_outcomes)==s.alerts).all()
    for row in s.itertuples():
        sub=hits[(hits.era==row.era)&(hits.level==row.level)&(hits.strategy==row.strategy)&hits.evaluable]
        assert len(sub)==row.events and int(sub.hit.sum())==row.hit_events
        assert np.isclose(row.process_recall,row.hit_events/row.events)
    js(out/'verification.json',dict(status='PASS',monthly_matches_r02_max_error=r['monthly_max_error'],
        scored_rows=r['daily_scored_rows'],event_rows=len(events),alert_rows=len(a),
        same_event_denominator=True,strictly_prior_alerts=True,full_prior_window=True,cooldown_without_replacement=True,
        unknown_outcomes_not_failures=True,does_not_prove_economic_onset=True))
    print('PROCESS VERIFIED',len(events),'events;',len(a),'alerts')

if __name__=='__main__':run()

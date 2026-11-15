"""Past-only features and direct prefix targets; no method evaluation or fitting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha
from v2_s11_duration_identity_guarded import excursions

FEATURES_BASE = ['r5', 'r20', 'r40']
FEATURES_CHANGE = FEATURES_BASE + ['prior20', 'change5', 'change20', 'drawdown20', 'rebound20', 'vol20', 'negative_share20']


def feature_group(g):
    g = g.sort_values('day_i').copy()
    for h in (5, 10, 20, 40):
        good = g.nav.gt(0) & g.nav.shift(h).gt(0) & g.block.notna() & g.block.eq(g.block.shift(h)) & g.day_i.sub(g.day_i.shift(h)).eq(h)
        g[f'r{h}'] = (g.nav / g.nav.shift(h) - 1).where(good)
    r = g.nav.pct_change(fill_method=None)
    g['prior20'] = (1 + g.r40) / (1 + g.r20) - 1
    g['change20'] = g.r20 - g.prior20
    g['change5'] = g.r5 - ((1 + g.r10) / (1 + g.r5) - 1)
    g['drawdown20'] = g.nav / g.nav.rolling(20, min_periods=20).max() - 1
    g['rebound20'] = g.nav / g.nav.rolling(20, min_periods=20).min() - 1
    g['vol20'] = r.rolling(20, min_periods=20).std()
    g['negative_share20'] = r.lt(0).where(r.notna()).rolling(20, min_periods=20).mean()
    g.loc[g.r40.isna(), FEATURES_CHANGE] = np.nan
    return g


def target_at(y, t, horizon=8):
    """Use exactly t+horizon prefix. Never read later prices or final identities."""
    if t < 8 or t + horizon >= len(y):
        return None, 'INSUFFICIENT_CONTEXT_OR_FUTURE', None
    prefix = np.asarray(y[:t + horizon + 1], dtype=float)
    matches = [p for p in excursions(prefix) if p['start_i'] <= t <= p['end_i']]
    assert len(matches) <= 1
    if not matches:
        return 0, 'NO_IDENTIFIED_PROCESS_WITHIN8', None
    p = matches[0]
    if p['left_context_unknown']:
        return None, 'LEFT_CONTEXT_UNKNOWN', p['start_i']
    if p['status'] != 'CONFIRMED':
        return 0, 'NOT_CONFIRMED_WITHIN8', p['start_i']
    early = p['start_i'] < t <= p['visible_i'] + 1 and prefix[t] > prefix[p['start_i']]
    return int(early), 'EARLY_CONFIRMED_WITHIN8' if early else 'CONFIRMED_BUT_NOT_EARLY_ALIGNED', p['start_i']


def main():
    out = EP / 'outputs/v3_m01_preparation'
    if out.exists():
        raise FileExistsError(out)
    out.mkdir()
    rawpath = PRIOR / 'daily_industries.parquet'
    receipt = json.loads((PRIOR / 'receipt.json').read_text())
    calpath = Path(next(k for k in receipt['inputs'] if k.endswith('/calendar.parquet')))
    catpath = EP / 'outputs/r01/weekly_catalog.parquet'
    sources = [rawpath, calpath, catpath, Path(__file__), EP/'src/v2_s11_duration_identity_guarded.py', EP/'protocols/v3_r00/m01_plan.md', EP/'protocols/v3_r00/evaluation_alignment.md']
    (out/'started.json').write_text(json.dumps({str(p):sha(p) for p in sources},indent=2)+'\n')
    raw = pd.read_parquet(rawpath, columns=['date','day_i','era','industry_code','block','nav'])
    cal = pd.read_parquet(calpath); cal['week'] = cal.date.dt.to_period('W-SUN')
    expected = cal.groupby('week').size()
    cat = pd.read_parquet(catpath,columns=['date','era','industry_code','industry_name'])
    parts = []; prefix_checks = 0
    for key, g in raw.groupby(['era','industry_code'], sort=True):
        f = feature_group(g); parts.append(f)
        # Prefix invariance on every industry's first and last supported daily cut.
        positions = np.flatnonzero(f.r40.notna().to_numpy())
        if len(positions):
            for j in sorted(set([int(positions[0]), int(positions[len(positions)//2])])):
                truncated = feature_group(g.sort_values('day_i').iloc[:j+1])
                np.testing.assert_allclose(truncated[FEATURES_CHANGE].iloc[-1].to_numpy(float), f[FEATURES_CHANGE].iloc[j].to_numpy(float), equal_nan=True)
                prefix_checks += 1
    panel = cat.merge(pd.concat(parts), on=['date','era','industry_code'], how='left', validate='one_to_one')
    records = []; target_checks = 0; valid = raw[raw.nav.gt(0)&raw.block.notna()]
    for group_i, (key,g) in enumerate(valid.groupby(['era','industry_code','block'],sort=True)):
        g = g.sort_values('day_i').copy(); g['week']=g.date.dt.to_period('W-SUN'); g['y']=np.log(g.nav)
        w=g.groupby('week').agg(y=('y','median'),date=('date','max'),days=('date','size')).reset_index()
        complete=w.days.eq(w.week.map(expected))
        if cal.date.max().weekday()<4:
            complete &= w.week.ne(cal.date.max().to_period('W-SUN'))
        w['run']=(~complete).cumsum()
        for run,z in w[complete].groupby('run'):
            z=z.reset_index(drop=True); y=z.y.to_numpy()
            assert len(z)<2 or np.all(np.diff(expected.index.get_indexer(z.week))==1)
            for t in range(len(z)):
                label,kind,ref=target_at(y,t)
                available=z.date.iloc[t+8] if t+8<len(z) else pd.NaT
                if t>=8 and t+9<len(z) and t%13==0:
                    altered=y.copy();altered[t+9:]+=np.linspace(10,20,len(y)-t-9)
                    assert target_at(altered,t)==(label,kind,ref)
                    target_checks+=1
                records.append(dict(era=key[0],industry_code=key[1],block=key[2],date=z.date.iloc[t],label=label,label_kind=kind,
                    label_available_date=available,training_parent_ref=None if ref is None else f'{key[0]}/{key[1]}/{key[2]}/{run}/{z.date.iloc[ref].date()}'))
        if group_i%100==0:
            print('prefix groups',group_i,'rows',len(records),flush=True)
    labels=pd.DataFrame(records)
    panel=panel.merge(labels,on=['era','industry_code','block','date'],how='left',validate='one_to_one')
    panel['eligible']=panel.r5.gt(0)&panel[FEATURES_CHANGE].notna().all(axis=1)
    panel['week']=panel.date.map({d:i for i,d in enumerate(sorted(cat.date.unique()))})
    panel=panel.sort_values(['era','industry_code','date'])
    prev=panel.groupby(['era','industry_code'])[['week','block','r20','eligible']].shift(1)
    adjacent=panel.week.sub(prev.week).eq(1)&panel.block.eq(prev.block)
    panel['enhance']=adjacent&panel.r20.gt(prev.r20)
    panel['confirmed']=panel.eligible&adjacent&prev.eligible.eq(True)
    panel['eligible_original']=panel.eligible&panel.r20.gt(0)
    panel['confirmed_original']=panel.confirmed&panel.r20.gt(0)&prev.r20.gt(0)
    assert len(panel)==len(cat) and not panel.duplicated(['era','industry_code','date']).any()
    mature=panel.eligible&panel.label.notna()
    assert panel.loc[mature,'label_available_date'].gt(panel.loc[mature,'date']).all()
    yearly=[]
    for year in range(2020,2027):
        cutoff=pd.Timestamp(year=year,month=1,day=1)
        tr=panel[mature&panel.label_available_date.lt(cutoff)]
        yearly.append(dict(year=year,train_rows=len(tr),positive=int(tr.label.sum()),negative=int(tr.label.eq(0).sum()),positive_parents=tr.loc[tr.label.eq(1),'training_parent_ref'].nunique(),
            latest_train_observation=str(tr.date.max()),latest_label_available=str(tr.label_available_date.max())))
    panel.to_parquet(out/'training_panel.parquet',index=False)
    pd.DataFrame(yearly).to_csv(out/'training_support.csv',index=False)
    panel.assign(year=panel.date.dt.year).groupby(['year','era','eligible','label_kind'],dropna=False).size().rename('rows').to_csv(out/'label_inventory.csv')
    result=dict(directory_rows=len(panel),eligible=int(panel.eligible.sum()),known_eligible=int(mature.sum()),positive=int(panel.loc[mature,'label'].sum()),
        feature_prefix_checks=prefix_checks,label_future_perturbation_checks=target_checks,features_base=FEATURES_BASE,features_change=FEATURES_CHANGE,
        training_target='Early parent stage confirmed in fixed eight complete future weeks; NOT final E02 process effectiveness',
        direct_prefix_reconstruction=True,final_parent_or_child_labels_read=False)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(result,indent=2));print(pd.DataFrame(yearly).to_string(index=False))


if __name__=='__main__':
    main()

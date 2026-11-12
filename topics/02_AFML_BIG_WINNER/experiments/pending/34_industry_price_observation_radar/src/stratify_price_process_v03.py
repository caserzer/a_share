"""Label support and contemporaneous market context, without signal results."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, CACHE, sha


def main():
    processfile=EP/'outputs/r00_price_process_v03/processes.parquet'
    dailyfile=PRIOR/'daily_industries.parquet'
    marketfile=CACHE/'forecast_v5/CSI_ALL.parquet'
    coveragefile=EP/'outputs/r00_coverage/evaluation_coverage.parquet'
    receipt=json.loads((PRIOR/'receipt.json').read_text())
    calendar=next(Path(f) for f in receipt['inputs'] if f.endswith('/calendar.parquet'))
    days=pd.DatetimeIndex(pd.read_parquet(calendar).date).sort_values()
    market=pd.read_parquet(marketfile).close.sort_index().reindex(days)
    p=pd.read_parquet(processfile);d=pd.read_parquet(dailyfile)
    groups={k:g.sort_values('date').reset_index(drop=True) for k,g in d[d.nav.notna()].groupby(['era','industry_code','block'])}
    rows=[]
    for r in p.itertuples():
        g=groups[(r.era,r.industry_code,r.block)];start=int(r.start);v=g.iloc[start-60:start+61]
        q=v.stale_members.gt(0)|v.boundary_proxy.eq(True)
        i=days.get_indexer([r.start_date])[0]
        past=market.iloc[i]/market.iloc[i-126]-1 if i>=126 and market.iloc[i-126:i+1].notna().all() else np.nan
        row=dict(process_id=r.process_id,family_id=r.family_id,era=r.era,industry_code=r.industry_code,
                 year=r.start_date.year,start_date=r.start_date,kind=r.kind,left_origin_uncertain=r.left_origin_uncertain,
                 history_proxy=bool(q.iloc[:61].any()),future_proxy=bool(q.iloc[61:].any()),
                 max_stale_days=int(v.max_stale_days.max()),regime='UNKNOWN' if not np.isfinite(past) else 'UP' if past>0 else 'NONUP',
                 market_past126=float(past))
        for h in [20,60]:
            price=g.nav.iloc[start+h]/g.nav.iloc[start]-1
            mret=market.iloc[i+h]/market.iloc[i]-1 if market.iloc[i:i+h+1].notna().all() else np.nan
            row[f'absolute{h}']=float(price);row[f'market{h}']=float(mret);row[f'excess{h}']=float(price-mret)
        rows.append(row)
    f=pd.DataFrame(rows)
    annual=[]
    for (era,year),g in f.groupby(['era','year']):
        annual.append(dict(era=era,year=int(year),processes=len(g),families=int(g.family_id.nunique()),
                           warming=int(g.kind.eq('WARMING').sum()),heating=int(g.kind.eq('HEATING').sum()),
                           left_uncertain=int(g.left_origin_uncertain.sum()),history_proxy=int(g.history_proxy.sum()),
                           future_proxy=int(g.future_proxy.sum()),any_proxy=int((g.history_proxy|g.future_proxy).sum()),
                           all_observed=int((~g.history_proxy&~g.future_proxy).sum()),
                           regimes=g.regime.value_counts().to_dict()))
    coverage=pd.read_parquet(coveragefile,columns=['era','date'])
    weeks=coverage.assign(week=coverage.date.dt.to_period('W-SUN').astype(str))[['era','week']].drop_duplicates()
    counts=f.assign(week=f.start_date.dt.to_period('W-SUN').astype(str)).groupby(['era','week']).size().rename('new_processes')
    weeks=weeks.merge(counts.reset_index(),on=['era','week'],how='left');weeks.new_processes=weeks.new_processes.fillna(0).astype(int)
    assert weeks.new_processes.sum()==len(p)
    out=EP/'outputs/r00_v03_support';out.mkdir(exist_ok=True)
    f.to_parquet(out/'process_context.parquet',index=False);weeks.to_json(out/'weekly_origin_counts.json',orient='records',indent=2)
    summary=dict(status='LABEL_SUPPORT_NOT_METHOD_EFFECTIVENESS',annual=annual,
                 regimes=f.regime.value_counts().to_dict(),weeks=len(weeks),
                 weekly_origin_distribution=weeks.new_processes.describe(percentiles=[.5,.9,.95,.99]).to_dict(),
                 total_proxy=int((f.history_proxy|f.future_proxy).sum()),all_observed=int((~f.history_proxy&~f.future_proxy).sum()),
                 inputs={str(x):sha(x) for x in [processfile,dailyfile,marketfile,coveragefile,calendar,Path(__file__)]})
    (out/'receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['regimes','weeks','weekly_origin_distribution','total_proxy','all_observed']},ensure_ascii=False))
    print(pd.DataFrame(annual)[['year','processes','heating','left_uncertain','any_proxy','all_observed']].to_string(index=False))


if __name__=='__main__':main()

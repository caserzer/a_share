"""Pre-registered financial timing sensitivity on matched and available cohorts."""
import pandas as pd
from common import *
from supplement_financials import asof_values
from evaluate_r01 import scores


def company_at(raw, cutoff):
    parts=[]
    for field in ['profit_dedt','grossprofit_margin']:
        f=asof_values(raw,cutoff,field)
        cur=f[f.end_date.dt.year.eq(2026)];old=f[f.end_date.dt.year.eq(2025)].copy();old['end_date']=old.end_date+pd.DateOffset(years=1)
        z=cur.merge(old,on=['ts_code','end_date'],suffixes=('_current','_prior'),validate='one_to_one')
        if field=='profit_dedt':
            denominator=z.value_current.abs()+z.value_prior.abs()
            z['dedt_change']=(z.value_current-z.value_prior)/denominator.where(denominator.gt(0))
            z['profit_sign_regime']=np.select([z.value_current.isna()|z.value_prior.isna(),denominator.eq(0),z.value_current.ge(0)&z.value_prior.ge(0),z.value_current.lt(0)&z.value_prior.lt(0),z.value_current.ge(0)&z.value_prior.lt(0)],
                ['missing','both_zero','nonnegative_both','negative_both','loss_to_profit'],default='profit_to_loss')
            parts.append(z[['ts_code','end_date','dedt_change','profit_sign_regime']])
        else:
            z['margin_delta']=z.value_current-z.value_prior;parts.append(z[['ts_code','end_date','margin_delta']])
    z=parts[0].merge(parts[1],on=['ts_code','end_date'],how='outer',validate='one_to_one').sort_values('end_date').drop_duplicates('ts_code',keep='last')
    z['instrument']=z.ts_code.str[-2:]+z.ts_code.str[:6]
    return z


def industry_at(m, company, origin, delay):
    j=m.merge(company,on='instrument',how='left',validate='many_to_one');rows=[]
    for key,g in j.groupby(KEY):
        denominator=len(g)+int(g.unresolved.max());r=dict(zip(KEY,key),date=origin,delay=delay,members=len(g),denominator=denominator)
        for name in ['dedt_change','margin_delta']:
            count=int(g[name].notna().sum());r[name+'_valid']=count;r[name+'_coverage']=count/denominator
            r[name]=g[name].mean() if count>=5 and count/denominator>=.8 else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def evaluation(g,cohort,delay):
    rows=[]
    if len(g)<20:return [dict(level=g.level.iloc[0] if len(g) else None,date=g.date.iloc[0] if len(g) else None,delay=delay,cohort=cohort,n_signal=len(g),status='fewer_than20')]
    f=scores(g).F;c=(centered_rank(g.dedt_change)+centered_rank(g.margin_delta))/2
    for h in [20,60]:
        y=g[f'excess{h}'];valid=y.notna()
        for name,s in [('F',f),('C',c),('FCfund',(f+c)/2)]:
            rows.append(dict(level=g.level.iloc[0],date=g.date.iloc[0],delay=delay,cohort=cohort,method=name,horizon=h,
                n_signal=len(g),n_outcome=int(valid.sum()),ic=s[valid].corr(y[valid],method='spearman') if valid.sum()>=20 else np.nan,status='descriptive_only'))
    return rows


def run():
    out=ROOT/'outputs/r07';raw_path=ROOT/'data/financial_archive_all_market.parquet'
    assert sha(raw_path)==json.loads((ROOT/'outputs/r03/archive_receipt.json').read_text())['output_sha256']
    raw=pd.read_parquet(raw_path);members=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=KEY+['month','security_id','instrument','unresolved'])
    panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet');panel=panel[panel.era.eq('SW2021')&panel.date.between('2026-04-01','2026-09-30')]
    calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
    parts=[];company_counts=[];archive_counts=[]
    for date in sorted(panel.date.unique()):
        date=pd.Timestamp(date);ix=calendar.get_loc(date);m=members[members.era.eq('SW2021')&members.month.eq(date.to_period('M')-1)]
        for delay in [0,5,20]:
            cutoff=calendar[ix-delay];company=company_at(raw,cutoff)
            parts.append(industry_at(m,company,date,delay))
            for sign,n in company.profit_sign_regime.value_counts(dropna=False).items():company_counts.append(dict(date=date,delay=delay,profit_sign_regime=sign,companies=n))
        close=date.tz_localize('Asia/Shanghai')+pd.Timedelta(hours=15)
        archived=raw[raw.archived_available_at.le(close)]
        archive_counts.append(dict(date=date,archived_records=len(archived),archived_companies=archived.ts_code.nunique(),note='actual archive clock; announcement backdating disallowed'))
    factors=pd.concat(parts,ignore_index=True);factors.to_parquet(ROOT/'data/r07_industry_factors.parquet',index=False)
    # Delay0 must exactly reproduce R03, no hidden factor change.
    previous=pd.read_parquet(ROOT/'data/industry_financial_factors.parquet')
    chk=factors[factors.delay.eq(0)].merge(previous,on=KEY+['date'],suffixes=('_now','_r03'),validate='one_to_one')
    for name in ['dedt_change','margin_delta','dedt_change_valid','margin_delta_valid','denominator']:
        assert np.allclose(chk[name+'_now'],chk[name+'_r03'],equal_nan=True)
    joint=panel.merge(factors,on=KEY+['date'],how='left',suffixes=('','_financial'),validate='one_to_many')
    metrics=[];coverage=[]
    for (level,date),full in joint.groupby(['level','date']):
        ready=full[full.price_ready].dropna(subset=['dedt_change','margin_delta'])
        counts=ready.groupby('industry_code').delay.nunique();common=set(counts[counts.eq(3)].index)
        for delay,g in full.groupby('delay'):
            available=g[g.price_ready].dropna(subset=['dedt_change','margin_delta']);matched=available[available.industry_code.isin(common)]
            coverage.append(dict(level=level,date=date,delay=delay,price_ready=int(g.price_ready.sum()),available=len(available),common_all_delays=len(matched)))
            for label,z in [('available',available),('matched_all_delays',matched)]:
                for row in evaluation(z,label,delay):row.update(level=level,date=date);metrics.append(row)
    pd.DataFrame(metrics).to_csv(out/'date_metrics.csv',index=False);pd.DataFrame(coverage).to_csv(out/'coverage.csv',index=False)
    pd.DataFrame(company_counts).to_csv(out/'profit_sign_regimes.csv',index=False);pd.DataFrame(archive_counts).to_csv(out/'archive_clock_coverage.csv',index=False)
    conflicts=[]
    subset=raw[raw.api.eq('fina_indicator_vip')]
    for field in ['profit_dedt','grossprofit_margin']:
        f=subset.copy();f[field]=pd.to_numeric(f[field],errors='coerce')
        stats=f.groupby(['ts_code','end_date','proxy_available_date'])[field].agg(rows='size',distinct=lambda x:x.nunique(dropna=False)).reset_index()
        z=stats[stats.distinct.gt(1)].copy();z['field']=field;conflicts.append(z)
    conflicts=pd.concat(conflicts,ignore_index=True);conflicts.to_csv(out/'field_conflicts.csv',index=False)
    result=pd.DataFrame(metrics);summary=result[result.status.eq('descriptive_only')].groupby(['level','cohort','delay','method','horizon']).ic.agg(['count','mean']);summary.to_csv(out/'summary.csv')
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r07.json'),code_sha256=sha(__file__),
        source_hashes={str(p):sha(p) for p in [raw_path,ROOT/'data/monthly_panel.parquet',CACHE/'extension_v2/products/assignments.parquet',ROOT/'src/supplement_financials.py',ROOT/'src/evaluate_r01.py']},
        delay0_exact_r03_match=True,matched_rows_checked=len(chk),conflicting_keys=len(conflicts),archived_mode_has_historical_rows=bool(sum(r['archived_records'] for r in archive_counts)),
        conclusion='descriptive_insufficient_months; no delay picked as winner'))
    print(summary.query("cohort=='matched_all_delays' and horizon==20").to_string(),flush=True)

if __name__=='__main__':run()

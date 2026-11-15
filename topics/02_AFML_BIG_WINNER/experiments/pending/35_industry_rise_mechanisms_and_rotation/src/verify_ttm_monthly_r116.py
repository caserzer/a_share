"""Independent raw-report clocks and exhaustive latest-period replay."""
import pandas as pd
from common import *
def same(a,b):assert (pd.isna(a) and pd.isna(b)) or a==b

def run():
    out=ROOT/'outputs/r116';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    raw=pd.read_parquet(ROOT/'outputs/r115/financial_rows.parquet');prior=pd.read_parquet(ROOT/'outputs/r115/ttm_candidates.parquet');e=pd.read_parquet(out/'report_events.parquet');pd.testing.assert_frame_equal(e[prior.columns],prior)
    ix=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index).sort_values();ends=[max(ix[ix.to_period('M')==m]) for m in ix.to_period('M').unique() if m>=pd.Period('2020-01') and m.end_time.normalize()<=ix.max()]
    events=e.set_index(['secucode','report_period']);checked=0
    for (code,period),g in raw.groupby(['SECUCODE',pd.to_datetime(raw.REPORT_DATE)]):
        if not 2020<=period.year<=2026:continue
        row=events.loc[(code,period)];assert list(row.current_row_ids)==g.row_id.tolist();checked+=1
        notice=pd.to_datetime(g.NOTICE_DATE,errors='coerce');update=pd.to_datetime(g.UPDATE_DATE,errors='coerce');nd=max(notice).normalize() if notice.notna().all() and notice.ge(period).all() else pd.NaT;ud=max(nd,max(update).normalize()) if pd.notna(nd) and update.notna().all() else pd.NaT
        for clock,date in [('notice',nd),('update',ud)]:
            same(row[clock+'_report_proxy_date'],date);eligible=ix[ix>date] if pd.notna(date) else [];same(row[clock+'_report_available_at'],eligible[0] if len(eligible) else pd.NaT)
    assert checked==len(e)
    p=pd.read_parquet(out/'monthly_ttm.parquet');assert not p.duplicated(['secucode','date','clock']).any();assert len(p)==raw.SECUCODE.nunique()*len(ends)*2
    lookup=p.set_index(['secucode','clock','date']);visited=0
    for code in sorted(raw.SECUCODE.unique()):
        g=e[e.secucode==code].sort_values('report_period');records=g.to_dict('records')
        for clock in ['notice','update']:
          for date in ends:
            row=lookup.loc[(code,clock,date)];visited+=1;visible=[x for x in records if pd.notna(x[clock+'_report_available_at']) and x[clock+'_report_available_at']<=date]
            if not visible:
                assert row.status=='no_visible_report' and row[['report_period','report_available_at','component_available_at','ttm_profit','report_age_days']].isna().all();continue
            chosen=max(visible,key=lambda x:x['report_period']);same(row.report_period,chosen['report_period']);same(row.report_available_at,chosen[clock+'_report_available_at']);same(row.component_available_at,chosen[clock+'_available_at']);assert row.report_age_days==(date-chosen['report_period']).days
            status='known_ttm'
            if chosen['status']!='valid_components':status='latest_components_invalid'
            elif pd.isna(chosen[clock+'_available_at']):status='unknown_component_clock'
            elif chosen[clock+'_available_at']>date:status='latest_components_not_yet_available'
            assert row.status==status;same(row.ttm_profit,chosen['ttm_profit'] if status=='known_ttm' else np.nan)
    assert visited==len(p)
    pairs=pd.read_parquet(out/'clock_pairs.parquet');assert not pairs.duplicated(['secucode','date']).any() and len(pairs)*2==len(p)
    for clock in ['notice','update']:
        source=p[p.clock==clock].set_index(['secucode','date']).reindex(pd.MultiIndex.from_frame(pairs[['secucode','date']]))
        for c in ['report_period','report_available_at','component_available_at','status','ttm_profit','report_age_days']:pd.testing.assert_series_equal(pairs[c+'_'+clock].reset_index(drop=True),source[c].reset_index(drop=True),check_names=False)
    flags={'both_known':pairs.status_notice.eq('known_ttm')&pairs.status_update.eq('known_ttm'),'both_selected':pairs.report_period_notice.notna()&pairs.report_period_update.notna()}
    flags['different_period']=flags['both_selected']&pairs.report_period_notice.ne(pairs.report_period_update);flags['different_known_value']=flags['both_known']&pairs.ttm_profit_notice.ne(pairs.ttm_profit_update)
    for k,v in flags.items():assert v.equals(pairs[k])
    coverage=pd.read_csv(out/'monthly_coverage.csv',parse_dates=['date']).set_index(['date','clock','status'])['rows'];expected=p.groupby(['date','clock','status']).size();pd.testing.assert_series_equal(coverage.sort_index(),expected.sort_index(),check_names=False)
    trans=pd.read_csv(out/'transitions.csv').set_index(['status_notice','status_update'])['rows'];expected=pairs.groupby(['status_notice','status_update']).size();pd.testing.assert_series_equal(trans.sort_index(),expected.sort_index(),check_names=False)
    sm=json.loads((out/'summary.json').read_text());assert sm['statuses']=={str(k):v for k,v in p.groupby(['clock','status']).size().to_dict().items()}
    counts=dict(companies=raw.SECUCODE.nunique(),months=len(ends),monthly_rows=len(p),company_month_pairs=len(pairs),**{k:int(v.sum()) for k,v in flags.items()})
    for k,v in counts.items():assert sm[k]==v
    assert sm['first_date']==str(min(ends).date()) and sm['last_date']==str(max(ends).date()) and sm['strict_PIT']==sm['price_comparison']==False
    js(out/'verification.json',dict(status='PASS',report_events=len(e),monthly_rows=len(p),paired_rows=len(pairs),latest_before_component_gate=True,strict_PIT=False));print('PASS',counts)
if __name__=='__main__':run()

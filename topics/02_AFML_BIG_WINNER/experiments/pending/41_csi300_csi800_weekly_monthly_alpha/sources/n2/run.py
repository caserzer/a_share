from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent))
from reserves import *

def main():
    m,cards=prepare()
    ep35=next(BASE.glob('35_*'))/'data'
    src=pd.read_parquet(ep35/'r11_analyst_forecasts.parquet').query('basis=="eps_cny_per_share"').copy()
    src['instrument']=np.where(src.stock_code.str.startswith('6'),'SH','SZ')+src.stock_code
    key=['instrument','broker','fiscal_year'];idkey=key+['publication_proxy_date']
    conflicts=src.groupby(idkey).value.transform('nunique')>1
    events=src.loc[~conflicts].sort_values(idkey+['infoCode']).drop_duplicates(idkey,keep='last')
    events['previous']=events.groupby(key).value.shift()
    events['move']=np.sign(events.value-events.previous)
    # No publication hour: begin eligibility on the first strictly later trading date.
    events['available_idx']=m.days.searchsorted(events.publication_proxy_date,side='right')
    events=events.dropna(subset='move')
    events.to_parquet(OUT/'eps_events.parquet',index=False)
    fs=pd.read_parquet(ep35/'financial_archive_all_market.parquet',columns=['ts_code','api','effective_ann_date','timing_valid'])
    fs=fs[fs.timing_valid.eq(True)&fs.api.eq('income_vip')].copy()
    fs['instrument']=fs.ts_code.str[-2:]+fs.ts_code.str[:6]
    fs['idx']=m.days.searchsorted(pd.to_datetime(fs.effective_ann_date.astype(str)),side='right')
    fs=fs[['instrument','idx']].drop_duplicates()
    plan={k:{} for k in ['ridge','rank','equal20','half60']};choices=[];support=[]
    for e,core,p,n in cards:
        i=e-1;dt=m.days[i]
        rr=p.instrument.to_numpy();full=np.r_[core,rr[:n]]
        plan['rank'][e]=m.symbols.get_indexer(full)
        # Ridge's original names are recovered from frozen scores below.
        valid=events[(events.available_idx<=i)&(events.available_idx>i-180)&(events.fiscal_year==dt.year)&events.instrument.isin(rr)]
        latest=valid.sort_values(['available_idx','publication_proxy_date']).drop_duplicates(['instrument','broker'],keep='last').copy()
        latest['age']=i-latest.available_idx
        report=set(fs.loc[fs.idx.between(i-19,i),'instrument'])
        vis=[]
        for name,h in [('equal20',latest[latest.age<20].copy()),('half60',latest.copy())]:
            h['w']=1. if name=='equal20' else 2.**(-h.age/60)
            h['v']=h.move*h.w
            agg=h.groupby('instrument').agg(w=('w','sum'),v=('v','sum'),brokers=('broker','size'),age=('age','mean'))
            score=(agg.v/agg.w).reindex(rr).to_numpy();p['brokers']=agg.brokers.reindex(rr).to_numpy()
            pick=choose(p,n,score,'n2')
            plan[name][e]=m.symbols.get_indexer(np.r_[core,rr[pick]])
            mask=np.isfinite(score);nonzero=mask&(score!=0)
            vis.append(mask)
            support.append(dict(signal_date=dt,entry_idx=e,spec=name,candidates=len(p),baseline_buy_slots=n,covered_candidates=mask.sum(),nonzero=nonzero.sum(),covered_buy_slots=mask[:n].sum(),distinct_changed=len(set(rr[pick])-set(rr[:n])),valid_brokers=len(h),reporting_candidates=sum(s in report for s in rr),with_reports_and_signal=sum(s in report and v for s,v in zip(rr,mask)),info_age=h.age.mean()))
            for j,s in enumerate(rr):
                choices.append((dt,e,name,s,j+1,score[j],p.brokers.iloc[j],agg.age.get(s,np.nan),s in report,j<n,j in pick))
        support[-1]['common_supported_buy_slots']=support[-2]['common_supported_buy_slots']=sum((vis[0]&vis[1])[:n])
    r=pd.read_parquet(HERE.parent/'p2/results/scores.parquet')
    for e,g in r.groupby('entry_idx'):
        plan['ridge'][e]=m.symbols.get_indexer(g.sort_values(['R','instrument'],ascending=False).instrument.head(len(g)//10))
    support=pd.DataFrame(support)
    support.to_csv(OUT/'coverage.csv',index=False)
    pd.DataFrame(choices,columns='signal_date entry_idx spec instrument reserve_rank score brokers age recent_financial_report baseline_buy selected'.split()).to_parquet(OUT/'choices.parquet',index=False)
    d=evaluate(m,plan,[('2021-01-11','2025-03-03'),('2025-03-03','2026-10-12')],OUT)
    jsonbody=dict(raw_eps=len(src),discarded_same_day_conflicting_rows=int(conflicts.sum()),comparable=len(events),first=str(src.publication_proxy_date.min()),last=str(src.publication_proxy_date.max()))
    import json
    (OUT/'source.json').write_text(json.dumps(jsonbody,indent=2)+'\n')
if __name__=='__main__':main()

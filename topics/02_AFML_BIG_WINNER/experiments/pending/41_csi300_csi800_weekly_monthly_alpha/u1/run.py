"""Compare the marginal buy rule in the historical 300 intersection and complement."""
from pathlib import Path
import sys
HERE1=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE1.parent/'u2'))
from common import *
OUT=HERE1/'results'
OUT.mkdir(exist_ok=True)

def main():
    s=Study()
    s.style()
    source=pd.read_parquet(DEST/'daily_scores.parquet',columns=['signal_date','instrument','R'])
    z=s.ranks.merge(source,on=['signal_date','instrument'],validate='1:1')
    max_r=(z.transfer_R-z.R).abs().max()
    phase0=pd.concat([pd.read_parquet(f,columns=['signal_date','instrument','T69']) for f in sorted((DEST/'folds').glob('*.parquet'))])
    tree=s.ranks.merge(phase0,on=['signal_date','instrument'],validate='1:1')
    max_t=(tree.transfer_T-tree.T69).abs().max()
    assert max(max_r,max_t)<1e-10 and len(tree)==40700
    audit=[dict(source='daily transfer Ridge scores on intersection',rows=len(z),max_R=max_r),
           dict(source='frozen 69-feature tree on phase zero overlap',rows=len(tree),max_T=max_t)]
    ov=next(PENDING.glob('38_*/three_track/results/wide_feature_parity.csv'))
    ff=pd.read_csv(ov)
    assert ff.missing_mask_equal.all() and ff.max_abs_error.max()<1e-10
    audit.append(dict(source='archived 78-column feature parity',rows=ff.common_rows.min(),cols=len(ff),max_feature=ff.max_abs_error.max()))
    pd.DataFrame(audit).to_csv(OUT/'overlap_check.csv',index=False)
    plans={};coverage=[];pairs=[];exposure=[]
    for mode in ['refit','transfer']:
        for domain in ['inside','outside']:
            for buy in ['tree','ridge','unchanged']:
                plans[(mode,domain,buy)]=s.blank()
    for domain in ['inside','outside']:
        for buy in ['tree','ridge']:
            plans[('matched',domain,buy)]=s.blank()
    for e,g in s.ranks.groupby('entry_idx'):
        ids=s.symbols.get_indexer(g.instrument)
        domainmask=s.narrow[e-1,ids]
        group_masks=dict(inside=domainmask,outside=~domainmask)
        sector=s.sectors[e-1,ids]
        cap=pct(s.cap[e-1,ids]);adv=pct(s.adv.iloc[e-1,ids].to_numpy())
        raw_ridge=g.refit_R.to_numpy()
        rank=np.zeros(len(ids))
        legs={}
        for mode in ['refit','transfer']:
            r=g[mode+'_R'].to_numpy();t=g[mode+'_T'].to_numpy()
            for name,mask in group_masks.items():
                local=np.flatnonzero(mask)
                rr=local[np.lexsort((-ids[local],-r[local]))]
                k=len(rr)//10;m=k//5
                top=rr[:k];reserve=rr[k:2*k]
                sorted_t=lambda vec:vec[np.lexsort((-ids[vec],-t[vec]))]
                core=sorted_t(top)[:-m]
                tb=sorted_t(reserve)[:m];rb=reserve[:m]
                for buy,selection in [('tree',np.r_[core,tb]),('ridge',np.r_[core,rb]),('unchanged',top)]:
                    plans[mode,name,buy][e,:k]=ids[selection]
                if mode=='refit':
                    rank[rr]=np.arange(1,len(rr)+1)/len(rr)
                    legs[name,'tree']=tb;legs[name,'ridge']=rb
                    legs[name,'k']=k
                coverage.append(dict(date=s.days[e-1],mode=mode,domain=name,eligible=len(rr),seats=k,buy_seats=m,buy_target_share=m/k,
                                     shared_buys=len(np.intersect1d(tb,rb)),first_ridge_rank=k+1,last_ridge_rank=2*k))
        # For each buy rule match inside/outside bought stocks. Both rules must
        # support a full cross-domain contrast on this signal; residual budget is cash.
        both={}
        for buy in ['tree','ridge']:
            a,b=match(legs['inside',buy],legs['outside',buy],sector,cap,adv,rank)
            order=np.argsort(abs(cap[a]-cap[b])+abs(adv[a]-adv[b])+abs(rank[a]-rank[b]),kind='stable')
            both[buy]=(a[order],b[order])
        available=min(len(both['tree'][0]),len(both['ridge'][0]))
        denom=max(legs['inside','k'],legs['outside','k'])
        exposure.append((s.days[e-1],len(both['tree'][0]),len(both['ridge'][0]),available,denom,available/denom))
        for buy,(a,b) in both.items():
            for name,vec in [('inside',a),('outside',b)]:
                plan=plans['matched',name,buy][e]
                plan[:denom]=-2 # explicit empty cash seats
                plan[:available]=ids[vec[:available]]
            for x,y in zip(a[:available],b[:available]):
                pairs.append((s.days[e-1],buy,s.symbols[ids[x]],s.symbols[ids[y]],sector[x],cap[x]-cap[y],adv[x]-adv[y],rank[x]-rank[y],1/denom))
    pd.DataFrame(coverage).to_parquet(OUT/'eligibility.parquet',index=False)
    pd.DataFrame(exposure,columns='date tree_max_pairs ridge_max_pairs common_pairs budget_denom target_share'.split()).to_csv(OUT/'support.csv',index=False)
    pd.DataFrame(pairs,columns='date buy inside outside sector d_cap_pct d_adv_pct d_domain_rank_pct weight'.split()).to_parquet(OUT/'matched_seats.parquet',index=False)
    holdings=[];daily=[];orders=[];months=[];gaps=[]
    for (mode,domain,buy),plan in plans.items():
        for e in s.ks.index:
            index=plan[e,plan[e]>=0]
            if len(index):
                holdings.append((mode,domain,buy,s.days[e-1],int((plan[e]!=-1).sum()),list(s.symbols[index])))
        for seg,period in PERIODS.items():
            d,o,gap=s.replay(plan,period,keep_orders=True)
            meta=dict(mode=mode,domain=domain,buy=buy,segment=seg)
            daily.append(d.reset_index().assign(**meta))
            orders.append(o.assign(**meta))
            if gap:gaps.append(dict(**meta,**gap))
            for month,v in monthly(d,s.days).items():months.append(dict(**meta,month=month,net=v))
    pd.DataFrame(holdings,columns='mode domain buy date denominator targets'.split()).to_parquet(OUT/'targets.parquet',index=False)
    pd.DataFrame(gaps,columns='mode domain buy segment date stock side'.split()).to_csv(OUT/'gaps.csv',index=False)
    pd.concat(daily).to_parquet(OUT/'accounts.parquet',index=False)
    pd.concat(orders).to_parquet(OUT/'net_orders.parquet',index=False)
    p=pd.DataFrame(months).pivot(index=['mode','segment','month'],columns=['domain','buy'],values='net')
    gap=pd.DataFrame({name:(p[name,'tree']-p[name,'ridge'])*1e4 for name in group_masks}).dropna()
    gap['outside_minus_inside']=gap.outside-gap.inside
    gap.groupby(['mode','segment']).mean().to_csv(OUT/'including_start_month.csv')
    gap=gap.reset_index()
    gap['registered_month']=~((gap.segment=='later')&(gap.month=='2025-03'))
    gap.to_csv(OUT/'monthly.csv',index=False)
    gap=gap[gap.registered_month].drop(columns='registered_month').set_index(['mode','segment','month'])
    stats=gap.groupby(['mode','segment']).mean().join(gap.groupby(['mode','segment']).size().rename('n'))
    stats.to_csv(OUT/'summary.csv')
    print(stats)
    files=[Path(__file__),HERE/'common.py',HERE/'book.cpp',OUT800/'scores.parquet',DEST/'daily_scores.parquet',ov]
    (OUT/'receipt.json').write_text(json.dumps({str(f):sha(f) for f in files+sorted(p for p in OUT.iterdir() if p.suffix!='.json')},indent=2)+'\n')
if __name__=='__main__':main()

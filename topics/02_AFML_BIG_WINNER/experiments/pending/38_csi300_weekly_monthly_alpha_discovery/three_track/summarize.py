from shared import *
import hashlib
keys=['model','scope','cost']
wide_names=['transfer','wide_train']
def load(name):
    return pd.read_parquet(OUT/(name+'.parquet'))

def main():
    days=pd.read_parquet(PRIVATE/'market.parquet').index
    w=pd.concat([load('windows'),load('wide_windows')],ignore_index=True)
    daily=pd.concat([load('daily'),load('wide_daily')],ignore_index=True)
    w['signal_date']=days[w.entry_idx-1];w['gross']=w.net+w.fee
    z=load('rankings').query('cost=="base"').copy()
    v=load('wide_scores');wide=[]
    for name in wide_names:
        p=v[KEY+['entry_idx','h10',name]].rename(columns={name:'score'}).sort_values(['signal_date','score','instrument'])
        rank=p.groupby('signal_date').cumcount()
        p['selected']=rank>=p.groupby('signal_date').score.transform('size')-p.groupby('signal_date').score.transform('size')//10
        p['model']=name;wide.append(p)
    wp=pd.concat(wide);wp.to_parquet(OUT/'wide_rankings.parquet',index=False)
    combo=load('combination_rankings').query("cost=='base'").drop_duplicates(KEY)
    panel=pd.concat([z,wp,combo],ignore_index=True)
    orig=z[z.model=='original'].set_index(KEY).selected
    ranks=[]
    for (name,d),g in panel.groupby(['model','signal_date']):
        picks=g[g.selected];idx=pd.MultiIndex.from_frame(picks[KEY]);truth=orig.reindex(idx).eq(True)
        ranks.append(dict(model=name,signal_date=d,eligible=len(g),known=g.h10.count(),d10=len(picks),d10_known=picks.h10.count(),rankic=g.h10.corr(g.score,'spearman'),top_overlap=truth.sum()/len(picks),gross_vs_pool=picks.h10.mean()-g.h10.mean()))
    ranks=pd.DataFrame(ranks);ranks.to_csv(OUT/'ranking_by_date.csv',index=False)
    w=w.merge(ranks,on=['model','signal_date'],validate='m:1');w.to_parquet(OUT/'all_windows.parquet',index=False)
    idx=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    benchmarks={'300':pd.DataFrame(idx['items'],columns=idx['fields']),'800':load('index800')}
    for k,g in benchmarks.items(): benchmarks[k]=g.set_index(pd.to_datetime(g.trade_date)).close
    summaries=[];monthly=[];pairs=[]
    for group,g in w.groupby(keys):
        name,scope,cost=group;h=daily[(daily.model==name)&(daily.scope==scope)&(daily.cost==cost)].sort_values('date')
        start,end=h.date.iloc[0],h.date.iloc[-1];n=days.get_loc(end)-days.get_loc(start)
        idx=benchmarks['800' if name in wide_names+['transfer_selection'] else '300'];bcagr=(idx.at[end]/idx.at[start])**(252/n)-1
        ret=h.nav.iloc[-1]**(252/n)-1
        summaries.append(dict(zip(keys,group))|dict(start=start,end=end,windows=len(g),rankic=g.rankic.mean(),overlap=g.top_overlap.mean(),gross_vs_pool_bp=1e4*g.gross_vs_pool.mean(),gross_bp=g.gross.mean()*1e4,net_bp=g.net.mean()*1e4,turnover=g.turnover.mean(),paid_fee_bp=g.fee.mean()*1e4,fees_initial_nav=h.fees.sum(),nav=h.nav.iloc[-1],cagr=ret,mdd=(h.nav/h.nav.cummax().clip(lower=1)-1).min(),benchmark_cagr=bcagr,excess_cagr=ret-bcagr))
    summary=pd.DataFrame(summaries);summary.to_csv(OUT/'summary.csv',index=False)
    for candidate,reference in [('pruned','original'),('selection','original'),('net','selection'),('net','gross'),('net','original'),('gross','original'),('transfer','original'),('wide_train','original'),('wide_train','transfer'),('transfer_selection','transfer'),('transfer_selection','selection')]:
        for scope in ['primary','later','primary_prefix','primary_restart']:
            for cost in ['base','zero','double']:
                block=w[(w.scope==scope)&(w.cost==cost)]
                a=block[block.model==candidate].set_index('entry_idx');b=block[block.model==reference].set_index('entry_idx')
                if a.empty or b.empty or not a.index.equals(b.index):continue
                diff=a.net-b.net;arr=diff.to_numpy()*1e4
                rng=np.random.default_rng(3803)
                indexes=(rng.integers(len(arr),size=(10000,(len(arr)+2)//3,1))+np.arange(3))%len(arr)
                ci=np.quantile(arr[indexes.reshape(10000,-1)[:,:len(arr)]].mean(axis=1),[.025,.975])
                nav=daily[(daily.scope==scope)&(daily.cost==cost)&daily.model.isin([reference,candidate])].pivot(index='date',columns='model',values='nav')
                month=nav.groupby(nav.index.to_period('M')).last();mr=month/month.shift().fillna(1)-1
                md=mr[candidate]-mr[reference]
                monthly.extend(dict(model=candidate,reference=reference,scope=scope,cost=cost,month=str(m),net_diff_bp=x*1e4) for m,x in md.items())
                pairs.append(dict(model=candidate,reference=reference,scope=scope,cost=cost,n=len(arr),net_diff_bp=arr.mean(),gross_diff_bp=(a.gross-b.gross).mean()*1e4,fee_diff_bp=(a.fee-b.fee).mean()*1e4,turnover_diff=(a.turnover-b.turnover).mean(),ci_low=ci[0],ci_high=ci[1],best_month=str(md.idxmax()),best_month_bp=md.max()*1e4,worst_month=str(md.idxmin()),worst_month_bp=md.min()*1e4))
    pd.DataFrame(monthly).to_csv(OUT/'monthly_pairs.csv',index=False)
    pd.DataFrame(pairs).to_csv(OUT/'paired.csv',index=False)
    saved=pd.read_csv(OLD/'outputs/rankic_by_date.csv',parse_dates=['signal_date'])
    ref=ranks[ranks.model=='original'].merge(saved[saved.model==BASE],on='signal_date',suffixes=('','_old'))
    np.testing.assert_allclose(ref.rankic,ref.rankic_old,atol=1e-12)
    for scope in ['primary','later']:
        frozen=pd.read_csv(ROUNDS/f'133_midpoint_matched_orders/results/{scope}_accounts.csv').query("phase==0 and model=='original'")
        check=summary[(summary.model=='original')&(summary.scope==scope)].merge(frozen,on='cost')
        np.testing.assert_allclose(check.nav_x,check.nav_y,atol=1e-10)
        baseline=load('orders').query("scope==@scope and cost=='base'")
        assert len(baseline)>0
    v=load('wide_attribution');v[~v.in300].groupby(['scope','model','industry'])[['weight','net_contribution','turnover']].sum().div(v.groupby(['scope','model']).signal_date.nunique().reindex(v[~v.in300].groupby(['scope','model','industry']).size().index.droplevel('industry')).to_numpy()[:,None]).to_csv(OUT/'outside_industry.csv')
    a=load('effective800');b=load('membership_proxy')
    cmp=a.merge(b,on=['signal_date','code'],how='outer',indicator=True)
    cmp=cmp[cmp.signal_date.isin(set(a.signal_date)&set(b.signal_date))]
    cmp[cmp._merge.ne('both')].to_csv(OUT/'vendor_disagreements.csv',index=False)
    checks=cmp.groupby(['signal_date','_merge'],observed=False).size().unstack(fill_value=0);checks.to_csv(OUT/'vendor_by_date.csv')
    src=load('wide_scores')
    gaps=outer()[KEY].merge(src[KEY],on=KEY,how='left',indicator=True).query('_merge=="left_only"')
    gaps.assign(reason='legacy_300_constituent_absent_from_effective_800').to_csv(OUT/'overlap_gaps.csv',index=False)
    print(summary[summary.cost.eq('base')][['model','scope','windows','rankic','cagr','net_bp','overlap','excess_cagr']].round(4).to_string(index=False))
if __name__=='__main__':main()

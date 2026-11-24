from experiment import Experiment
from shared import BASE
from wide_panel import *
import account

def main():
    narrow=Experiment()
    account.PRIVATE=LOCAL;accounts.PRIVATE=LOCAL;accounts.OUT=OUT
    m,actions=setup('flat');scores=pd.read_parquet(OUT/'wide_scores.parquet')
    mem300=pd.read_parquet(PRIVATE/'daily_members.parquet').reindex(columns=m.symbols,fill_value=False)
    industry=pd.read_parquet(PRIVATE/'industry.parquet')
    industry['instrument']=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
    combination=[];daily=[];orders=[];windows=[];attrib=[];coverage=[];status=[]
    op,cl=m.marks['flat']
    for model in ['transfer','wide_train','transfer_selection']:
        panel=pd.read_parquet(OUT/'wide_calibration_panel.parquet') if model=='transfer_selection' else scores
        col='transfer' if model=='transfer_selection' else model
        rule='selection' if model=='transfer_selection' else 'original'
        ex=Experiment.__new__(Experiment)
        ex.m=m;ex.actions=actions;ex.open=op;ex.close=cl
        ex.groups=list(panel.sort_values(KEY).groupby('entry_idx',sort=True));ex.entries=np.array([e for e,_ in ex.groups])
        ex.ids=[m.symbols.get_indexer(g.instrument) for _,g in ex.groups]
        ex.y=[g.h10.to_numpy() for _,g in ex.groups]
        ex.parts=[np.column_stack([g[col],np.zeros((len(g),5))]) for _,g in ex.groups]
        later=m.days[ex.entries]>=pd.Timestamp('2025-03-03')
        fail_day=m.days.get_loc(pd.Timestamp('2023-06-16'))
        # Window containing the first unpriceable holding is left open.
        primary=(~later)&(m.days[ex.entries-1].year>=2021)
        scopes=[('primary',primary),('later',later),
                ('primary_prefix',primary&(ex.entries+10<fail_day)),
                ('primary_restart',primary&(ex.entries>fail_day))]
        for scope,mask in scopes:
            ix=np.flatnonzero(mask)
            for cost,mul in [('base',1),('zero',0),('double',2)]:
                meta=dict(model=model,scope=scope,cost=cost);books={}
                stop=ix[-1]+1
                while stop>ix[0]:
                    try:
                        w,d,p,r,o=ex.run(ix[0],stop,rule,(1.,)*5,.001*mul,.002*mul,True,books=books)
                        break
                    except ValueError as err:
                        # Never invent a mark. Report the longest verifiable prefix.
                        if err.args[0][0] not in ['open','valuation']:raise
                        bad_day=err.args[0][1]
                        status.append(dict(**meta,failure_date=str(bad_day.date()),names=list(err.args[0][2])))
                        stop=min(stop-1,np.searchsorted(m.days[ex.entries+10],bad_day))
                if stop<=ix[0]:continue
                if model=='transfer_selection':combination.append(r.assign(**meta))
                wx=pd.DataFrame(w,columns=['entry_idx','net','fee','turnover']);windows.append(wx.assign(**meta))
                dx=pd.DataFrame(d,columns=['idx','date','nav','cash','buy','sell','fees'])
                daily.append(dx.assign(**meta))
                ox=pd.DataFrame(o,columns=['idx','instrument','net_amount','pretrade_nav']);orders.append(ox.assign(**meta))
                if cost!='base':continue
                byday={i:g for i,g in ox.groupby('idx')}
                for t,plan,win in zip(range(ix[0],stop),p,w):
                    e,g=ex.groups[t];x=e+10;datestr=g.signal_date.iloc[0].strftime('%Y%m%d')
                    mem=mem300.iloc[e-1].to_numpy()
                    active=industry[industry.in_date.le(datestr)&(industry.out_date.isna()|industry.out_date.gt(datestr))][['instrument','l1_name']].drop_duplicates()
                    inds=active.loc[~active.instrument.duplicated(False)].set_index('instrument').l1_name.reindex(m.symbols).fillna('未知')
                    u,cash,_=books[t];u=u.copy()
                    nav0=cash+u@np.nan_to_num(op[e]);pnl=np.zeros(m.n);traded=np.zeros(m.n)
                    for a,b,listing in actions:
                        if e>=listing and u[a]>0:
                            u[b]+=u[a]*op[e,a]/op[e,b];u[a]=0.
                    last=np.nan_to_num(op[e]);terminal=t==stop-1
                    for i in range(e,x+1):
                        price=np.nan_to_num(op[i]);held=u>1e-12
                        # Opening marks are only needed on trade dates, the listing, and H10 endpoints.
                        if i==x or i in byday or any(i==j for _,_,j in actions):
                            assert np.isfinite(op[i,held]).all(),(model,m.days[i],m.symbols[held&~np.isfinite(op[i])])
                            pnl+=u*(price-last)
                            for a,b,j in actions:
                                if j==i and u[a]:
                                    u[b]+=u[a]*price[a]/price[b];u[a]=0.
                            if i in byday and (i<x or terminal):
                                oo=byday[i];ids=m.symbols.get_indexer(oo.instrument);flow=oo.net_amount.to_numpy()
                                u[ids]+=flow/price[ids];traded[ids]+=abs(flow)
                                pnl[ids]-=np.where(flow>0,.001*flow,-.002*flow)
                            last=price
                        if i==e:post=u*price/nav0
                    np.testing.assert_allclose(pnl.sum()/nav0,win[1],atol=1e-9)
                    chosen=plan['selected']
                    coverage.append(dict(**meta,signal_date=m.days[e-1],members=800,eligible=len(g),target=len(chosen),actual_positions=int((post>1e-10).sum()),actual_target_held=int((post[chosen]>1e-10).sum()),buy_filled_names=int((byday[e].net_amount>0).sum()),outside300_weight=post[~mem].sum(),outside300_contribution=pnl[~mem].sum()/nav0,outside300_traded=traded[~mem].sum()/nav0))
                    for j in np.flatnonzero((abs(pnl)+traded+post)>1e-10):
                        attrib.append(dict(**meta,signal_date=m.days[e-1],instrument=m.symbols[j],industry=inds.iloc[j],in300=mem[j],weight=post[j],net_contribution=pnl[j]/nav0,turnover=traded[j]/nav0))
    pd.concat(combination,ignore_index=True).to_parquet(OUT/'combination_rankings.parquet',index=False)
    for scope,mask in scopes[2:]:
        subset=ex.entries[mask];ids=np.searchsorted(narrow.entries,subset)
        for narrow_arm in ['original','selection']:
          for cost,mul in [('base',1),('zero',0),('double',2)]:
            w,d,p,r,o=narrow.run(ids[0],ids[-1]+1,narrow_arm,(1.,)*5,.001*mul,.002*mul,True)
            meta=dict(model=narrow_arm,scope=scope,cost=cost)
            windows.append(pd.DataFrame(w,columns=['entry_idx','net','fee','turnover']).assign(**meta))
            daily.append(pd.DataFrame(d,columns=['idx','date','nav','cash','buy','sell','fees']).assign(**meta))
    for items,name in [(windows,'wide_windows'),(daily,'wide_daily'),(orders,'wide_orders')]:
        pd.concat(items,ignore_index=True).to_parquet(OUT/(name+'.parquet'),index=False)
    pd.DataFrame(attrib).to_parquet(OUT/'wide_attribution.parquet',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'wide_coverage.csv',index=False)
    (OUT/'wide_status.json').write_text(json.dumps(status,indent=2))
if __name__=='__main__':main()

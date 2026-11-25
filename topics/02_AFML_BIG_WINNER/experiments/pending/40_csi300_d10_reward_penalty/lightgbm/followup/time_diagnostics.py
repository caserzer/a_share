from accounts_followup import *
sys.path.insert(0,str(ROOT))
from summarize import read,save,interval
def main():
    ledger.accounts.OUT=DEST
    m,actions=ledger.setup('flat');op=m.marks['flat'][0]
    w=read('windows');d=read('daily');p=read('positions');s=read('daily_scores')
    p=p.query('phase==0 and h==10 and delay==0 and mul==1')
    ref=pd.read_parquet(OUT/'rankings.parquet').query('arm=="baseline"')
    days=m.days
    edges=dict(primary=days.get_loc('2025-03-03'),later=days.get_loc('2026-10-12'))
    decay=[];effects=[];random=[];recipe=[]
    for scope,end in edges.items():
        period=ref[ref.scope==scope];dates=period.signal_date.unique()
        for arm in ['R','T','B','A','X11']:
            sel=p[(p.scope==scope)&(p.arm==arm)&(p.weight>0)]
            for e,g in sel.groupby('entry_idx'):
                if e+20>end:continue
                ids=m.symbols.get_indexer(g.instrument);prices=op[np.ix_(e+np.array([0,5,10,20]),ids)]
                ok=np.isfinite(prices).all(axis=0)
                parts=(np.diff(prices[:,ok],axis=0)/prices[0,ok])@g.weight.to_numpy()[ok]
                decay.append(dict(scope=scope,arm=arm,entry=e,weight=g.weight.sum(),covered_weight=g.weight.to_numpy()[ok].sum(),first=parts[0],second=parts[1],third=parts[2]))
            g=w.query('scope==@scope and arm==@arm and h==10 and phase==0 and mul==1')
            wide=g.assign(signal_entry=g.entry_idx-g.delay).pivot(index='signal_entry',columns='delay',values='net').dropna()
            effects.append(dict(scope=scope,arm=arm,n=len(wide),base=wide[0].mean(),delay=wide[1].mean(),change=(wide[1]-wide[0]).mean()))
        g=w.query('scope==@scope and h==10 and phase==0 and delay==0 and mul==1')
        ret=g.groupby('arm').net.mean()
        for a,z in ret[ret.index.str.match('P[0-9]')].items():
            random.append(dict(scope=scope,arm=a,p_minus_r_bp=(z-ret.R)*1e4,b_minus_p_bp=(ret.B-z)*1e4))
        f=s[s.signal_date.isin(dates)].merge(pd.concat([pd.read_parquet(f) for f in (DEST/'folds').glob('*.parquet')])[KEY+['F00']],on=KEY).merge(period[KEY+['h10']],on=KEY)
        fold_path=PRIVATE.parent/'outputs/fold_predictions/expanding'
        weekly=pd.concat([pd.read_parquet(path,filters=[('model_id','=','E2'),('seed_or_ensemble','=','equal_seed_ensemble')]) for path in fold_path.glob('*.parquet')])
        weekly=weekly[weekly.score.notna()&weekly.signal_date.between(min(dates),max(dates))].merge(pd.read_parquet(PRIVATE/'labels.parquet',columns=KEY+['h10']),on=KEY)
        overlap=f.merge(weekly[KEY+['score']],on=KEY)
        np.testing.assert_allclose(overlap.F00,overlap.score,rtol=0,atol=1e-10)
        for cal,df,c in [('weekly',weekly,'score'),('H10',f,'F00')]:
            both=set(f.signal_date)&set(weekly.signal_date)
            for date,g in df.groupby('signal_date'):
                z=g.sort_values([c,'instrument'])
                for denom in [5,10]:
                    top=z.tail(len(z)//denom)
                    recipe.append(dict(scope=scope,calendar=cal,date=date,common=date in both,denom=denom,seats=len(top),known=top.h10.count(),gross=top.h10.mean(),pool=g.h10.mean()))
    save('decay',decay);save('delay_common',effects);save('random_controls',random);save('e2_calendar',recipe)
    # Calendar-month stock contribution in units of each month's starting NAV.
    rows=[]
    orders=read('orders').query('phase==0 and h==10 and delay==0 and mul==1')
    for (scope,arm),g in orders[orders.arm.isin(['R','T','B','X11','A'])].groupby(['scope','arm']):
        trades={i:t for i,t in g.groupby('idx')}
        v=d.query('scope==@scope and arm==@arm and phase==0 and h==10 and delay==0 and mul==1')
        u=np.zeros(m.n);last=np.zeros(m.n);prior=1.;month=None
        for row in v.itertuples():
            i=row.idx;current=row.date.to_period('M')
            if month!=current:base=prior;month=current
            marks=op[i] if i==v.idx.iloc[-1] else m.marks['flat'][1][i]
            pnl=np.zeros(m.n)
            if i in trades or any(i==j for _,_,j in actions):
                held=u>1e-12;price=np.nan_to_num(op[i]);assert np.isfinite(op[i,held]).all()
                pnl+=u*(price-last)
                for a,b,j in actions:
                    if i>=j and u[a]>0:
                        u[b]+=u[a]*price[a]/price[b];u[a]=0
                if i in trades:
                    t=trades[i];ids=m.symbols.get_indexer(t.instrument)
                    u[ids]+=t.net_amount.to_numpy()/price[ids]
                    pnl[ids]-=np.where(t.net_amount>0,.001*t.net_amount,-.002*t.net_amount)
                last=price
            mark=np.nan_to_num(marks);pnl+=u*(mark-last);last=mark
            np.testing.assert_allclose(pnl.sum(),row.nav-prior,rtol=0,atol=1e-9)
            for j in np.flatnonzero(abs(pnl)>1e-13):rows.append((scope,arm,str(current),m.symbols[j],pnl[j]/base))
            prior=row.nav
    stocks=pd.DataFrame(rows,columns='scope arm month instrument net'.split()).groupby(['scope','arm','month','instrument']).net.sum().unstack('arm',fill_value=0.)
    stocks.sub(stocks.R,axis=0).to_parquet(DEST/'calendar_month_stock_delta.parquet')
if __name__=='__main__':main()

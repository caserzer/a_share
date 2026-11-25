from accounts_followup import *
sys.path.insert(0,str(ROOT))
from summarize import read,save,interval
from scipy.stats import spearmanr
import hashlib

def original(f):return f.query('phase==0 and h==10 and delay==0 and mul==1').copy()
def main():
    w=original(read('windows'));d=original(read('daily'));p=original(read('positions'));o=original(read('orders'))
    for name,new,keys,cols in [
        ('windows',w,['scope','entry_idx'],['net','fee','turnover']),
        ('daily',d,['scope','idx'],['nav','buy','sell','cash','fees']),
        ('orders',o,['scope','idx','instrument'],['net_amount','pretrade_nav'])]:
        old=pd.read_parquet(OUT/(name+'.parquet')).query('cost=="base"')
        for a,b in [('R','baseline'),('T','tree_rank')]:
            x=new[new.arm==a].set_index(keys).sort_index()
            y=old[old.arm==b].set_index(keys).sort_index()
            # Tiny rounding residuals in unchanged holdings can generate dust orders.
            if name=='orders':
                x=x[x.net_amount.abs()>1e-13];y=y[y.net_amount.abs()>1e-13]
            pd.testing.assert_index_equal(x.index,y.index)
            np.testing.assert_allclose(x[cols],y[cols],atol=1e-11,rtol=0)
    ref=pd.read_parquet(OUT/'rankings.parquet').query('arm=="baseline"')
    s=read('daily_scores').merge(ref[KEY+['scope','h10','decile']],on=KEY,validate='1:1')
    f=pd.concat([pd.read_parquet(path) for path in (DEST/'folds').glob('*.parquet')])
    s=s.merge(f,on=KEY,validate='1:1')
    s['K']=s.groupby('signal_date').R.transform('size')//10
    for a in ['R','T']:
        s[a+'_ord']=s.sort_values('instrument',ascending=False).groupby('signal_date')[a].rank(method='first',ascending=False)
        s[a+'_dec']=10-((s[a+'_ord']-1)*10//s.groupby('signal_date').R.transform('size')).astype(int)
    s['vs_pool']=s.h10-s.groupby('signal_date').h10.transform('mean')
    for k in [1,10]:s['d'+str(k)]=s.decile.eq(k).where(s.decile.notna()).astype(float)
    by=['scope','signal_date','R_dec','T_dec']
    cell=s.groupby(by).agg(rows=('R','size'),known=('h10','count'),ret=('vs_pool','mean'),D1=('d1','mean'),D10=('d10','mean')).reset_index()
    save('disagreement',cell.groupby(['scope','R_dec','T_dec']).agg(dates=('rows','size'),names=('rows','sum'),known=('known','sum'),pool_excess=('ret','mean'),D1=('D1','mean'),D10=('D10','mean')).reset_index())
    s['fold']=s.signal_date.dt.to_period('Q').astype(str)
    cut=pd.concat([pd.read_csv(path) for path in (DEST/'folds').glob('*.csv')]).groupby('fold').first().market_vol_cut
    s['regime']=np.where(s.market_mom20>=0,'up','down')
    s['regime']+=np.where(s.market_vol20>=s.fold.map(cut),'_high','_low')
    style=['vol20','amp20','mom5','mom60','dd60']
    for col in style:s[col+'_pct']=s.groupby('signal_date')[col].rank(pct=True)
    ind=industries(s.signal_date.unique())
    s['industry']=pd.concat([g.instrument.map(ind[dt]) for dt,g in s.groupby('signal_date')]).fillna('未知')
    pool=s.groupby(['scope','signal_date','industry']).size().div(s.groupby(['scope','signal_date']).size()).groupby(['scope','industry']).mean()
    pos=p.merge(s.drop(columns=['scope']),on=['entry_idx','instrument'],how='left',validate='m:1')
    pos['bucket']=pos.decile.fillna(0).astype(int);pos['industry']=pos.industry.fillna('未知')
    pos['net']=pos.gross-pos.fee
    pos['tier']=np.where(pos.R_ord<=pos.K,'R_top',np.where(pos.R_ord<=2*pos.K,'R_second','outside'))
    count=w.groupby(['scope','arm']).size()
    def agg(keys):
        sums=pos.groupby(['scope','arm']+keys)[['weight','gross','fee','net']].sum().reset_index()
        sums[['weight','gross','fee','net']]=sums[['weight','gross','fee','net']].div(count.reindex(pd.MultiIndex.from_frame(sums[['scope','arm']])).values,axis=0)
        return sums
    save('tails',agg(['bucket']));save('ridge_tiers',agg(['tier']))
    amounts=agg(['industry'])
    # Denominator includes dates where the industry has zero eligible stocks.
    universe=s.groupby(['scope','signal_date','industry']).size()/s.groupby(['scope','signal_date']).size()
    pool=universe.groupby(['scope','industry']).sum()/s.groupby('scope').signal_date.nunique()
    amounts['pool']=pool.reindex(pd.MultiIndex.from_frame(amounts[['scope','industry']])).values
    save('industry',amounts)
    gaps=[];stocks=[];why=[];examples=[];reg=[];ics=[]
    for (scope,date),g in s.groupby(['scope','signal_date']):
        for a in ['T','R','T20','G1','G2','T69','R69','F00','F01','F10','no_amp','no_path','no_dd','leaf100','l2_5','E']:
            c=g[g.R_ord<=2*g.K]
            ics.append(dict(scope=scope,date=date,arm=a,ic=g[a].corr(g.h10,'spearman'),pool_ic=c[a].corr(c.h10,'spearman')))
    save('rankic',ics)
    for scope,allp in pos.groupby('scope'):
        rr=allp[allp.arm=='R']
        for a in ['B','T','X11','A','T69','no_amp','no_dd','no_path']:
            aa=allp[allp.arm==a]
            keys=['entry_idx','instrument']
            both=aa.merge(rr,on=keys,how='outer',suffixes=('','_r'))
            both['group']=np.select([both.target.eq(True)&both.target_r.eq(True),both.target.eq(True),both.target_r.eq(True)],['common','incoming','outgoing'],default='legacy')
            for col in ['weight','net','gross','fee']:
                both[col+'_delta']=both[col].fillna(0)-both[col+'_r'].fillna(0)
            both['bucket']=both.bucket.fillna(both.bucket_r)
            both['date']=both.signal_date.fillna(both.signal_date_r)
            both['industry']=both.industry.fillna(both.industry_r)
            delta=both.groupby('entry_idx').net_delta.sum()
            wins=w[w.scope==scope].pivot(index='entry_idx',columns='arm',values='net')
            np.testing.assert_allclose(delta,wins[a]-wins.R,atol=1e-9,rtol=0)
            n=len(delta);cols=['weight_delta','gross_delta','fee_delta','net_delta']
            gaps.append((both.groupby(['group','bucket'])[cols].sum()/n).reset_index().assign(scope=scope,arm=a))
            stock=both.groupby('instrument')[cols].sum().sort_values('weight_delta')
            symbols=stock.head(5).index.union(stock.tail(5).index)
            examples.append(both[both.instrument.isin(symbols)].merge(s[KEY+style+['R','T','h10']],left_on=['date','instrument'],right_on=KEY,how='left',suffixes=('','_signal'))[['date','instrument','industry','group','R_signal','T_signal','h10_signal',*style,*cols]].assign(scope=scope,arm=a))
            both['month']=both.date.dt.to_period('M').astype(str)
            stocks.append(both.groupby(['month','instrument','industry'])[cols].sum().reset_index().assign(scope=scope,arm=a))
            state=s[s.scope==scope].groupby('entry_idx').regime.first()
            for state_name,entries in state.groupby(state).groups.items():
                h=both[both.entry_idx.isin(entries)]
                reg.append(dict(scope=scope,arm=a,regime=state_name,n=len(entries),net_bp=h.net_delta.sum()*1e4/len(entries),d1_gross_bp=h[h.bucket==1].gross_delta.sum()*1e4/len(entries),d10_gross_bp=h[h.bucket==10].gross_delta.sum()*1e4/len(entries)))
    save('bridge',pd.concat(gaps));save('regime',reg)
    pd.concat(examples).to_parquet(DEST/'examples.parquet',index=False)
    pd.concat(stocks).to_parquet(DEST/'signal_month_stock.parquet',index=False)
    style_cols=[c+'_pct' for c in style]
    denom=pos[style_cols].notna().mul(pos.weight,axis=0).groupby([pos.scope,pos.arm]).sum()
    for c in style_cols:pos[c]=pos[c]*pos.weight
    save('styles',(pos.groupby(['scope','arm'])[style_cols].sum()/denom).reset_index())
    save('style_coverage',denom.div(pos.groupby(['scope','arm']).weight.sum(),axis=0).reset_index())
    print('Baseline reproduction and P&L bridges passed.')
if __name__=='__main__':main()

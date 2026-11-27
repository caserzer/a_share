"""Nested, quarterly, continuous-account calibration; outer dates never select a weight."""
import argparse
import os
from functools import lru_cache
from core42 import *
from inputs42 import get_index

BASES=[0.,.0875,.175,.2625,.35]
SLOPES=[0,1,-1]

class Calibration:
    def __init__(self,board,states,wide=False):
        self.board=board; self.m=board.m;self.wide=wide
        self.z=states.reindex(board.dates)
        self.values=self.z[['Z1','Z2','Z3','Z4']].to_numpy()
        self.history=[]

    def weight(self,b,s,zidx=0,extra=0):
        z=self.values
        raw=b+s*.175*np.nan_to_num(2*z[:,0]-1,nan=0)
        if zidx:
            raw+=extra*.0875*np.nan_to_num(2*z[:,zidx]-1,nan=0)
        return np.clip(raw,0,.35)

    @lru_cache(maxsize=48)
    def packed(self,b,s,idx=0,a=0):
        return self.board.pack(self.weight(b,s,idx,a))

    def spans(self,q):
        dates=self.board.dates
        cal=self.m.days
        quarters=[]
        for j in range(8,0,-1):
            old=q-j
            expected=cal[cal.to_period('Q')==old]
            # The last date of the preceding quarter has already closed.
            if len(expected) and expected.isin(dates).all():
                quarters.append(old)
            else:
                quarters=[]
        if len(quarters)<4:return []
        lo=cal.searchsorted(quarters[0].start_time)+1
        hi=cal.searchsorted(q.start_time)-1
        # A narrow universe has no valuation break here. Allow no reused capital across a wide break.
        gap=cal.get_loc('2023-06-16')
        if self.wide and lo<=gap<=hi:
            return [(lo,hi,gap-1),(gap+1,hi,hi)]
        return [(lo,hi,hi)]

    def fit(self,q,extra_states):
        intervals=self.spans(q)
        if not intervals:
            return dict(q=str(q),b=0.,s=0,avg=0.,z2=0,z3=0,z4=0,fallback=True,months=0)
        def measure(b,s,j=0,a=0):
            packed=self.packed(b,s,j,a)
            values=[]
            for span in intervals:
                daily=replay(self.m,packed,span)
                mo=monthly(daily,self.m.days)
                values.append(mo.net)
            return pd.concat(values)
        def choose(runs,family):
            # Valuation gaps can vary by rule. Compare on an identical set of months.
            mat=pd.concat(runs,axis=1).dropna()
            scores=mat.mean()
            for tag,v in scores.items():
                self.history.append(dict(quarter=str(q),family=family,candidate=tag,months=len(mat),mean_net=v,
                    first_month=mat.index.min(),last_month=mat.index.max(),last_mature_date=self.m.days[intervals[-1][1]]))
            return (scores.idxmax() if len(mat) else None), len(mat)
        b,n=choose({b:measure(b,0) for b in BASES},'static')
        if b is None:return dict(q=str(q),b=0.,s=0,avg=0.,z2=0,z3=0,z4=0,fallback=True,months=0)
        s,n=choose({s:measure(b,s) for s in SLOPES},'Z1')
        if s is None:s=0
        past=np.zeros(len(self.board.rows),bool)
        for lo,end,stop in intervals:past|=(self.board.entries>=lo)&(self.board.entries<=min(end-10,stop))
        result=dict(q=str(q),b=b,s=s,avg=self.weight(b,s)[past].mean(),fallback=False,months=n)
        for j in [1,2,3]:
            v=0
            if extra_states:
                v,_=choose({v:measure(b,s,j,v) for v in SLOPES},'Z'+str(j+1))
            result['z'+str(j+1)]=int(v or 0)
        return result

def series_for(board,states,fit):
    f=fit.reindex(board.dates.to_period('Q').astype(str)).set_index(board.dates)
    z=states.reindex(board.dates)
    b=f.b.fillna(0);s=f.s.fillna(0)
    def w(value):return (b+s*.175*(2*value-1).fillna(0)).clip(0,.35)
    # Confirmation uses all historical closes, including the inner warmup.
    history=states.Z1
    band=np.where(history<1/3,-1,np.where(history>2/3,1,0)).astype(float)
    band[history.isna()]=np.nan
    active=None;pending=None;run=0;previous=np.nan;vals=[];age=[];prevband=None;age_now=0
    for group,value in zip(band,history):
        if not np.isfinite(value):
            active=pending=None;run=0;previous=np.nan;age_now=0;prevband=None
        else:
            age_now=age_now+1 if group==prevband else 1;prevband=group
            if group==active:previous=value;pending=None;run=0
            else:
                run=run+1 if pending==group else 1;pending=group
                if run>=5:active=group;previous=value;run=0;pending=None
        vals.append(previous);age.append(age_now)
    cols=pd.DataFrame(index=board.dates)
    cols['R']=0.;cols['T']=1.;cols['fixed175']=.175;cols['static']=b;cols['dynamic']=w(z.Z1)
    cols['trained_mean']=f.avg.fillna(0)
    raw=b+s*.175*(2*z.Z1-1).fillna(0)
    for j in [2,3,4]:
        cols['plus_Z'+str(j)]=(raw+f['z'+str(j)].fillna(0)*.0875*(2*z['Z'+str(j)]-1).fillna(0)).clip(0,.35)
    cols['lag20']=w(history.shift(20).reindex(board.dates))
    cols['confirm5']=w(pd.Series(vals,index=states.index).reindex(board.dates))
    meta=z[['Z1','Z2','Z3','Z4']].copy()
    meta['state_age']=pd.Series(age,index=states.index).reindex(board.dates)
    meta['b']=b;meta['s']=s;meta['entry_idx']=board.entries
    return cols,meta

def run_accounts(board,plans,spans,dest,trace_arms):
    m=board.m;dates=[];months=[];years=[];gaps=[]
    for arm,packed in plans.items():
        for seg,span in enumerate(spans,1):
            for fee in [1,2]:
                use_trace=arm in trace_arms and fee==1
                with tempfile.NamedTemporaryFile() as temp:
                    frame=replay(m,packed,span,fee=fee,trace=temp.name if use_trace else None)
                    assert len(frame)>0
                    if use_trace:
                        tr=read_trace(temp.name)
                        g=tr.groupby('day')[['overnight','intraday','fee']].sum()
                        g.index=m.days[g.index]
                        daily_terms=g.reindex(frame.index,fill_value=0)
                        np.testing.assert_allclose(daily_terms.overnight+daily_terms.intraday,frame.gross_pnl,rtol=0,atol=1e-10)
                        np.testing.assert_allclose(daily_terms.fee,frame.fee,rtol=0,atol=1e-11)
                        tr.to_parquet(dest/f'trace_{arm}_{seg}.parquet',index=False)
                if frame.index[-1]!=pd.Timestamp(span[2]):
                    gaps.append(dict(arm=arm,segment=seg,fee_multiple=fee,last=frame.index[-1],expected=span[2]))
                label=arm if fee==1 else arm+'_2fee'
                dates.append(frame.reset_index().assign(arm=label,segment=seg))
                months.append(monthly(frame,m.days).reset_index().assign(arm=label,segment=seg))
                prior=frame.nav.shift().fillna(1)
                for y,g in frame.groupby(frame.index.year):
                    years.append(dict(arm=label,segment=seg,year=y,start=g.index[0],end=g.index[-1],net=g.nav.iloc[-1]/prior.loc[g.index[0]]-1,
                                      mdd=(g.nav/g.nav.cummax().clip(lower=prior.loc[g.index[0]])-1).min()))
    daily=pd.concat(dates,ignore_index=True)
    daily.to_parquet(dest/'daily.parquet',index=False)
    mo=pd.concat(months,ignore_index=True)
    mo.to_csv(dest/'monthly.csv',index=False)
    pd.DataFrame(years).to_csv(dest/'annual.csv',index=False)
    pd.DataFrame(gaps,columns=['arm','segment','fee_multiple','last','expected']).to_csv(dest/'valuation_stops.csv',index=False)
    return mo

def main(alt=False):
    dest=OUT/('shallow' if alt else 'main');dest.mkdir(exist_ok=True)
    m=market();scores=pd.read_parquet(OUT/'scores.parquet')
    if alt:
        add=pd.concat([pd.read_parquet(EP42/'scale/results'/name) for name in ['shallow_early_history.parquet','shallow_early.parquet']])
        scores=scores.drop(columns='T').merge(add.rename(columns={'shallow_early':'T'}),on=['signal_date','instrument','entry_idx'],validate='1:1')
    board=Board(m,scores)
    states=pd.read_parquet(OUT/'states.parquet').set_index('signal_date')
    cal=Calibration(board,states)
    fits=[]
    for q in pd.period_range('2021Q1','2026Q3',freq='Q'):
        fits.append(cal.fit(q,not alt))
        print(dest.name,q,flush=True)
    fit=pd.DataFrame(fits).set_index('q')
    fit.to_csv(dest/'weights_quarterly.csv')
    pd.DataFrame(cal.history).to_csv(dest/'inner_objectives.csv',index=False)
    weights,meta=series_for(board,states,fit)
    weights.join(meta).to_parquet(dest/'weights_daily.parquet')
    arms=['R','T','static','dynamic','fixed175','trained_mean']
    if not alt:arms+=['plus_Z2','plus_Z3','plus_Z4','lag20','confirm5']
    plans={arm:board.pack(weights[arm]) for arm in arms}
    if not alt:
        for name,truncate in [('budget',False),('budgetK',True)]:
            for arm in ['static','dynamic']:
                plans[name+'_'+arm]=board.pack(weights[arm],budget=True,truncate=truncate)
    targets=[]
    for name,packed in plans.items():
        for e in board.entries:
            ids=packed[0][e];ok=ids>=0
            targets.append((name,e,ids[ok],packed[2][e,ok] if len(packed)==3 else np.full(ok.sum(),1/packed[1][e])))
    pd.DataFrame(targets,columns=['arm','entry_idx','stock_indices','weights']).to_parquet(dest/'targets.parquet',index=False)
    pd.Series(m.symbols).to_csv(dest/'symbols.csv',index=False)
    mo=run_accounts(board,plans,SEG300,dest,set(plans))
    combos=[('dynamic','static'),('dynamic','R'),('dynamic','T'),('dynamic','trained_mean'),('dynamic','fixed175')]
    if not alt:combos+=[(a,'dynamic') for a in ['plus_Z2','plus_Z3','plus_Z4','lag20','confirm5']]+[(s+'_dynamic',s+'_static') for s in ['budget','budgetK']]
    stats=pd.concat([contrast(mo,arm+suffix,base+suffix) for arm,base in combos for suffix in ['','_2fee']])
    stats.to_csv(dest/'comparisons.csv',index=False)
    if not alt:
        df=pd.read_parquet(dest/'daily.parquet')
        old=pd.read_parquet(EP41/'models/results/funded_daily.parquet')
        checks=[]
        for arm,reference in [('R','R'),('T','top_M1_raw')]:
            for seg,scope in [(1,'primary'),(2,'later')]:
                left=df.query('arm==@arm and segment==@seg').set_index('date')
                right=old.query('arm==@reference and segment==@scope and hold==10').set_index('date')
                assert len(right)==len(left) and left.index.equals(right.index)
                diff=(left[['nav','cash','fee','crossed']]-right[['nav','cash','fee','crossed']]).abs().max()
                assert diff.max()<1e-10,(arm,seg,diff)
                checks.append(dict(arm=arm,segment=seg,dates=len(left),**diff))
        pd.DataFrame(checks).to_csv(dest/'baseline_parity.csv',index=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--shallow',action='store_true')
    main(parser.parse_args().shallow)


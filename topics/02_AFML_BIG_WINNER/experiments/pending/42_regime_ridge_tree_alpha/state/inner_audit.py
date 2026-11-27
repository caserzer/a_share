"""Reconcile the chosen inner scores to full cash, realized turnover and clipping records."""
from mixture import *
def main():
    m=market()
    board=Board(m,pd.read_parquet(OUT/'scores.parquet'))
    z=pd.read_parquet(OUT/'states.parquet').set_index('signal_date')
    cal=Calibration(board,z)
    root=OUT/'main'
    fits=pd.read_csv(root/'weights_quarterly.csv').set_index('q')
    hist=pd.read_csv(root/'inner_objectives.csv')
    rows=[]
    for q,qs in hist.groupby('quarter'):
        spans=cal.spans(pd.Period(q))
        b,s=fits.loc[q,['b','s']].astype(float)
        for t in qs.itertuples(index=False):
            cb,cs,j,ca=b,s,0,0
            if t.family=='static':cb,cs=t.candidate,0
            elif t.family=='Z1':cs=t.candidate
            else:j=int(t.family[1])-1;ca=t.candidate
            packed=cal.packed(cb,cs,j,ca);w=cal.weight(cb,cs,j,ca)
            for lo,hi,stop in spans:
                sub=(board.entries>=lo)&(board.entries<=min(stop,hi-10))
                f=replay(m,packed,(lo,hi,stop));mo=monthly(f,m.days)
                assert len(mo)==t.months and abs(mo.net.mean()-t.mean_net)<1e-12
                rows.append((q,t.family,t.candidate,m.days[lo],m.days[hi],f.index[-1],m.days[board.entries[sub][-1]+10],
                    sub.sum(),((w[sub]==0)|(w[sub]==.35)).sum(),f.planned.sum(),f.buy.sum(),f.sell.sum(),f.fee.sum(),f.cash.mean(),t.months))
    pd.DataFrame(rows,columns='quarter family candidate start cutoff last_strict last_signal_mature dates weight_at_bound planned broker_buy broker_sell paid_fee mean_cash months'.split()).to_csv(root/'inner_funding.csv',index=False)
if __name__=='__main__':main()


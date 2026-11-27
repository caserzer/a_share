"""Add EP41 equal-weight and total-return index references at identical capital endpoints."""
from scale_common import *
import json
def main():
    x=json.loads((ep.PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    raw=pd.DataFrame(x['items'],columns=x['fields'])
    index=raw.set_index(pd.to_datetime(raw.trade_date)).close.sort_index()
    eq=pd.read_parquet(EP41/'p2/results/funded_daily.parquet',filters=[('arm','=','equal'),('mul','=',1)],columns=['date','scope','nav'])
    d=pd.read_parquet(RES/'daily.parquet',columns=['date','segment','arm','fee_multiple','prev','nav','fee'])
    out=[]
    for (seg,arm,fee),gg in d.groupby(['segment','arm','fee_multiple']):
        ev=eq[eq.scope.eq(seg)].set_index('date').nav
        g=gg.set_index('date').sort_index()
        for year,h in [('all',g),*g.groupby(g.index.year)]:
            t=h.index[0];u=h.index[-1];at=g.index.get_loc(t);start=g.index[at-1] if at else t
            eqnet=ev.at[u]/(ev.at[start] if at else 1.)-1
            ix=index.at[u]/index.at[start]-1
            nav=h.nav.iloc[-1]/h.prev.iloc[0]-1
            out.append((seg,arm,fee,str(year),t,u,nav,eqnet,ix,nav-eqnet,nav-ix))
    pd.DataFrame(out,columns='segment arm fee_multiple year start end net equal_net index_total_return minus_equal minus_index'.split()).to_csv(RES/'annual_benchmarks.csv',index=False)
if __name__=='__main__':main()

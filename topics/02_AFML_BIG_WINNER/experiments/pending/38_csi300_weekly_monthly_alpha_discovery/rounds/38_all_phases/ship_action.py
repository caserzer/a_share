"""Keep the successor entitlement in a distinct lot until its first executable sale."""
from unittest.mock import patch
import pandas as pd
import numpy as np
from evaluate import accounts,PRIVATE
from account import replay
from execution import net_account

def replay_with_ship_action(targets,dest):
    market=accounts.Market()
    src,dst="SH601989","SH600150"
    old,new=market.symbols.get_indexer([src,dst]);assert min(old,new)>=0
    start=market.days.get_loc("2025-09-05");listing=market.days.get_loc("2025-09-16")
    op=pd.read_parquet(PRIVATE/"open.parquet",columns=[src,dst])
    cl=pd.read_parquet(PRIVATE/"close.parquet",columns=[src,dst])
    last=cl[src].iloc[:start].last_valid_index()
    raw_factor=market.c[market.days.get_loc(last),old]/cl.at[last,src]
    ratio=.1339
    units_factor=ratio*raw_factor*op.iloc[listing][dst]/market.o[listing,new]
    om,cm=market.marks["flat"]
    assert not market.buy[start:,old].any() and not market.sell[start:,old].any()
    for mat,raw in [(om,op),(cm,cl)]:
        mat[start:listing,old]=raw[dst].iloc[start:listing].to_numpy()*ratio*raw_factor
        assert np.isfinite(mat[start:listing,old]).all()
        mat[listing:,old]=mat[listing:,new]*units_factor
    market.sell[listing:,old]=market.sell[listing:,new]
    receipts=[]
    def run(m,g,end,mode,bf,sf):
        daily,orders,status=net_account(m,g,end,mode,bf,sf)
        before=orders[(orders.instrument==src)&(orders.date<market.days[start])]
        entitled=((before.buy-before.sell)/before.price).sum()
        shipped=orders[(orders.instrument==src)&(orders.date>=market.days[start])&((orders.buy+orders.sell)>0)]
        assert shipped.buy.sum()==0
        if entitled>1e-12:
            assert len(shipped)==1 and shipped.date.iloc[0]==market.days[listing]
            other=orders[(orders.instrument==dst)&(orders.date==market.days[listing])]
            assert other.buy.sum()<1e-12, "Successor must net overlapping orders"
            value=entitled*raw_factor*ratio*op.iloc[listing][dst]
            np.testing.assert_allclose(shipped.sell.sum(),value,atol=1e-12)
            receipts.append(dict(model=g.model.iloc[0],buy_fee=bf,old_adjusted_units=entitled,
                successor_raw_shares=entitled*raw_factor*ratio,successor_open=op.iloc[listing][dst],sell_value=value,date=market.days[listing]))
        else:assert shipped.empty
        return daily,orders,status
    with patch.object(accounts,"Market",return_value=market),patch("account.net_account",run):
        replay(targets,dest)
    pd.DataFrame(receipts).to_csv(dest/"ship_conversion.csv",index=False)

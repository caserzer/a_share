import numpy as np
import pandas as pd
from peer_ranking import pair_concordance,calendar_pivot


def test_discordant_peer_pairs_and_ties():
    values,mask=pair_concordance([.8,.3,.4,.2,.8],[.2,.8,.4,.9,.1],[1,0,1,1,np.nan],[0,1,0,1,0])
    np.testing.assert_array_equal(mask,[True,True,True,False,False])
    np.testing.assert_array_equal(values,[1.,1.,.5])


def test_unavailable_peer_month_keeps_calendar_position():
    dates=pd.to_datetime(['2021-01-29','2021-02-26','2021-03-31'])
    rows=pd.DataFrame(dict(date=[dates[0],dates[2]],model=['G','G'],concordance=[.4,.6]))
    result=calendar_pivot(rows,dates)
    assert len(result)==3 and np.isnan(result.G.iloc[1])

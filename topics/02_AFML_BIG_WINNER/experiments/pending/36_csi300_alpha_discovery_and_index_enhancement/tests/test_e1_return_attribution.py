import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from e1_return_attribution import log_link,wealth_scale,daily_returns


def test_link_is_continuous_at_identical_returns():
 r=np.array([0.,.1,-.2])
 np.testing.assert_allclose(log_link(r,r),1/(1+r))
 np.testing.assert_allclose(log_link(r+1e-14,r),1/(1+r),rtol=1e-10)


def test_compounded_active_attribution_includes_opportunity_cost():
 portfolio=pd.Series([1.10,1.045,1.20]);benchmark=pd.Series([1.02,.969,1.05])
 rp=daily_returns(portfolio);rb=daily_returns(benchmark)
 linked=(rp-rb)*log_link(rp,rb)
 assert linked.sum()==pytest.approx(np.log(1.2/1.05),abs=1e-12)
 assert linked.sum()*wealth_scale(1.2,1.05)==pytest.approx(15.,abs=1e-10)


def test_wealth_conversion_when_no_excess():
 assert wealth_scale(1.2,1.2)==pytest.approx(120.)


def test_arithmetic_excess_cannot_be_naively_summed():
 p=pd.Series([1.2,1.5]);b=pd.Series([1.1,1.2])
 rp=daily_returns(p);rb=daily_returns(b)
 assert not np.isclose((rp-rb).sum(),p.iloc[-1]-b.iloc[-1])
 linked=(rp-rb)*log_link(rp,rb)
 assert linked.sum()*wealth_scale(p.iloc[-1],b.iloc[-1])==pytest.approx(30.)


def test_log_control_bridge_telescopes_without_return_relabeling():
 values=[.8,.9,.92,1.1,1.2]
 logparts=np.diff(np.log(values))
 assert logparts.sum()*wealth_scale(values[-1],values[0])==pytest.approx(40.)
 n=1001
 cagrparts=np.diff(np.array(values)**(252/n)-1)
 assert cagrparts.sum()==pytest.approx(values[-1]**(252/n)-values[0]**(252/n))

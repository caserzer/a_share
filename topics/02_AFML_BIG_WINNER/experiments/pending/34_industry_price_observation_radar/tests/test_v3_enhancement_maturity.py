import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from v3_m02_targets import prefix_targets,TARGETS
from v3_m01_prepare import target_at


def heating_path():
    y=np.r_[-.01*np.arange(16),-.15+.003*np.arange(1,50)]
    y[35:]+=.01*np.arange(len(y)-35)
    return y


def test_new_heating_is_distinct_from_parent_early():
    r=prefix_targets(heating_path(),36)[0]
    assert r['child_early_target']==1 and r['child_coverage_target']==1
    assert r['parent_coverage_target']==1 and r['parent_early_target']==0


def test_target_tail_invariance_and_cache_equivalence():
    y=heating_path();cache={}
    for t in range(8,len(y)-8):
        a=prefix_targets(y,t,cache);b=prefix_targets(y,t,{})
        assert a==b
        changed=y.copy();changed[t+9:]=-100
        assert prefix_targets(changed,t,{})==b
        assert b[0]['parent_early_target']==target_at(y,t)[0]


def test_immature_unknown_not_zero():
    r=prefix_targets(heating_path(),60)[0]
    assert all(r[x] is None for x in TARGETS)


def test_steady_rise_is_not_new_heating():
    y=np.r_[-.01*np.arange(16),-.15+.003*np.arange(1,50)]
    assert all(prefix_targets(y,t)[0]['child_coverage_target']==0 for t in range(16,len(y)-8))

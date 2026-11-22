import pandas as pd
import numpy as np
from select_targets import pair_group,FIELDS


def frame(names,x):
    return pd.DataFrame([[v,0.,0.] for v in x],columns=FIELDS,index=names)


def test_maximum_feasible_cardinality_before_minimum_distance():
    # The greedy closest pair b-y blocks a; the optimal assignment uses two pairs.
    entrants=frame(["a","b"],[-.95,0.1])
    stayers=frame(["x","y"],[1.05,0.0])
    got=pair_group(entrants,stayers,np.ones(3))
    assert {(a,b) for a,b,_ in got}=={("a","y"),("b","x")}


def test_outside_caliper_or_empty_control_never_matches():
    a=frame(["a"],[1.01])
    b=frame(["b"],[0.])
    assert not pair_group(a,b,np.ones(3))
    assert not pair_group(a,b.iloc[:0],np.ones(3))

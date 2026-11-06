import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from rank15 import redistribute


def test_probability_mass_preserved_with_monotone_ranking():
    for anchor in [.001,.1,.9]:
        for strength in [.5,1]:
            p=redistribute(np.arange(30),anchor,strength)
            assert np.isclose(p.mean(),anchor,atol=1e-12) and (np.diff(p)>0).all()


def test_ties_do_not_create_false_ordering():
    p=redistribute([2,2,2,2],.15,.5)
    np.testing.assert_allclose(p,.15)


def test_zero_one_and_empty_boundaries():
    assert len(redistribute([],0,.5))==0
    assert (redistribute([1,2],0,1)==0).all()
    assert (redistribute([1,2],1,1)==1).all()

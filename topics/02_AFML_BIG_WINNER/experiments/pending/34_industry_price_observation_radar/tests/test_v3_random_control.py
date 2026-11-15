import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from v3_m06_replay import random_score

def test_random_control_has_prefix_and_order_stability():
    ids=[('2020-01-03','SW2014',str(i)) for i in range(30)]
    first={k:random_score(*k,341060) for k in ids}
    other={k:random_score(*k,341060) for k in reversed(ids+[('2026-01-09','SW2021','new')])}
    assert all(first[k]==other[k] for k in ids)
    assert all(0<=v<1 for v in first.values())

def test_random_seeds_produce_different_rankings():
    a=sorted(range(30),key=lambda k:random_score('2020-01-03','SW2014',str(k),341060))
    b=sorted(range(30),key=lambda k:random_score('2020-01-03','SW2014',str(k),341061))
    assert a!=b

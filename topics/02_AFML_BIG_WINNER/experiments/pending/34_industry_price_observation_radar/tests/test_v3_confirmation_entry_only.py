import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from v3_m07_replay import choices

def row(code,score,confirmed):return SimpleNamespace(industry_code=code,score=score,eligible=True,confirmed=confirmed)

def test_wait_restricts_only_new_candidates():
    now={('x',str(i)):row(str(i),100-i,False) for i in range(20)}
    now[('x','new')]=row('new',85,True)
    pool={k:{} for k in list(now)[:20]}
    candidates,held=choices(now,pool,{},5,'eligible','score',True,'confirmed')
    assert candidates==[('x','new')] and held[0]==('x','0') and held[-1]==('x','19')

def test_single_positive_week_does_not_pass_wait():
    now={('x','new'):row('new',100,False)}
    assert choices(now,{}, {},5,'eligible','score',True,'confirmed')[0]==[]
    assert choices(now,{}, {},5,'eligible','score',True)[0]==[('x','new')]

import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from v3_m05_replay import choices

def row(code,score,eligible=True):return SimpleNamespace(industry_code=code,score=score,eligible=eligible)

def test_competitor_must_rank_in_joint_twenty():
    now={('x',str(i)):row(str(i),100-i) for i in range(22)}
    pool={k:{} for k in list(now)[:20]}
    assert choices(now,pool,{},10,'eligible','score',True)[0]==[]
    assert len(choices(now,pool,{},10,'eligible','score',False)[0])==2

def test_ineligible_incumbent_below_eligible_candidate():
    now={('x',str(i)):row(str(i),100-i,i!=0) for i in range(21)}
    pool={k:{} for k in list(now)[:20]}
    candidates,held=choices(now,pool,{},10,'eligible','score',True)
    assert candidates==[('x','20')] and held[-1]==('x','0')

def test_cooldown_cannot_be_bypassed_by_competition():
    now={('x','a'):row('a',10)}
    assert choices(now,{}, {('x','a'):7},10,'eligible','score',True)[0]==[]
    assert choices(now,{}, {('x','a'):6},10,'eligible','score',True)[0]==[('x','a')]

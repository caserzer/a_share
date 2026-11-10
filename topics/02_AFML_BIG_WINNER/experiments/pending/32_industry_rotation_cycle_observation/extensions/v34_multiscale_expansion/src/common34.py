from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];EXT=ROOT.parent;EP=EXT.parent
sys.path.insert(0,str(EXT/'v31_all_signal_economics/src'))
from common31 import sha,js,md,clean,episode_starts,top_k,OLD,CACHE as ECON
OUT=ROOT/'outputs';CACHE=OLD.parent/'multiscale_v34'
KEY=['era','level','industry_code','block']
IDENTITY=['era','level','industry_code','date','threshold','benchmark']
GROUPS={
 'levels':['turn_short','turn_medium','volume_short','turn_rank504','turn_rank756','share_short'],
 'paths':['turn_slope63','turn_acceleration','turn_persistence','expansion_breadth','breadth_change21'],
 'stage':['stage_turn_change','stage_share_change','stage_breadth_change','stage_turn_speed'],
}
ADDED=sum(GROUPS.values(),[])


def freeze():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    refs={}
    for root in [EP]+sorted(EXT.glob('v*')):
        if root==ROOT:continue
        m=root/'outputs/manifest.json'
        if not m.exists():continue
        manifest=json.loads(m.read_text())
        for f in manifest['files']:
            p=root/f['path'];assert sha(p)==f['sha256'],p
            refs[str(p)]=f['sha256']
        refs[str(m)]=sha(m)
    refs[str(EP/'FOLLOWUP.md')]=sha(EP/'FOLLOWUP.md')
    js(OUT/'predecessors.json',refs)
    js(OUT/'freeze.json',dict(plan_sha256=sha(ROOT/'research_plan.md'),groups=GROUPS,
        main_scope=dict(level='L3',threshold=.15,benchmark='CSI_ALL'),
        input_quality='Historical-proxy',strict_PIT='BLOCKED_DATA',independent_holdout=False))


def mean(series,window):
    return series.rolling(window,min_periods=int(np.ceil(.8*window))).mean()


def logratio(a,b):
    return np.log(a.where(a.gt(0))/b.where(b.gt(0)))


def stock_features(turn,volume,pe):
    out=pd.DataFrame(index=turn.index)
    out['turn_short']=logratio(mean(turn,21),mean(turn.shift(21),63))
    out['turn_medium']=logratio(mean(turn,63),mean(turn.shift(63),126))
    out['volume_short']=logratio(mean(volume,21),mean(volume.shift(21),63))
    for w in [504,756]:out['turn_rank'+str(w)]=turn.rolling(w,min_periods=int(np.ceil(.75*w))).rank(pct=True)
    for w in [21,63]:
        positive=pe.where(pe.gt(0))
        out['pe_change'+str(w)]=np.log(positive/positive.shift(w)).where(positive.rolling(w+1,min_periods=w+1).count().eq(w+1))
    return out


def path_features(frame):
    g=frame.sort_values('date').copy()
    turn=mean(g.turn_median,21);share=mean(g.money_share,21)
    g['turn21']=turn;g['share21']=share
    g['share_short']=logratio(share,mean(g.money_share.shift(21),63))
    logturn=np.log(turn.where(turn.gt(0)))
    g['turn_slope63']=(logturn-logturn.shift(63))/63
    g['turn_acceleration']=(logturn-logturn.shift(21))-(logturn.shift(21)-logturn.shift(42))
    rising=pd.concat([(logturn.shift(i*21)-logturn.shift((i+1)*21)).rename(str(i)) for i in range(6)],axis=1)
    g['turn_persistence']=rising.gt(0).mean(axis=1).where(rising.notna().all(axis=1))
    g['breadth_change21']=g.expansion_breadth-g.expansion_breadth.shift(21)
    g['block_day']=np.arange(len(g))
    return g

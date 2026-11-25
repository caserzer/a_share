from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common_inputs import *
LOCAL=Path.home()/'.cache/a_share/ep38_three_track/market'
OUT800=HERE/'results'
STORE=TRACK/'results'
def membership(days,symbols):
    raw=pd.read_parquet(STORE/'effective800.parquet')
    blocks=raw[['effective','code']].drop_duplicates()
    blocks['instrument']=np.where(blocks.code.str.startswith('6'),'SH','SZ')+blocks.code
    changes=blocks.assign(member=True).pivot(index='effective',columns='instrument',values='member').eq(True)
    events=pd.read_csv(STORE/'effective_changes.csv',parse_dates=['effective'])
    assert set(events.effective[(events.effective>=days[0])&(events.effective<=raw.signal_date.max())])<=set(changes.index)
    assert not set(changes.columns)-set(symbols)
    m=changes.reindex(index=days,method='ffill').reindex(columns=symbols,fill_value=False).eq(True)
    m.loc[days>raw.signal_date.max()]=False
    assert m.loc['2021-01-08':'2026-09-30'].sum(axis=1).eq(800).all()
    return m

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from parse_historical_industry import parse_rows
from build_historical_industry import identity,peer_state
from run_historical_industry_models import conditional_atoms
from run_market_time_models import weighted_class_distribution
from run_direct_probability import classes


def test_merged_cells_forward_only():
    state={0:'',1:'',2:''}
    rows=[['制造业(C)','26','化工','000001','甲'],[None,None,None,'000002','乙'],['金融业(J)','66','银行','600001','丙']]
    assert [r['major'] for r in parse_rows(rows,state)]==['C26','C26','J66']
    assert parse_rows([[None,None,None,'600002','丁']],state)[0]['major']=='J66'


def test_new_format_does_not_inherit_missing_subclass():
    rows=[['000001','甲','C','制造业','CE','化工','26','化学'],['000002','乙','J','金融业','','','66','银行']]
    got=parse_rows(rows,{0:'',1:'',2:''});assert got[1]['sub']=='' and got[1]['major']=='J66'


def test_publication_cutoff_and_unknown(tmp_path):
    f=tmp_path/'table.parquet';pd.DataFrame(dict(code=['000001'],major=['J66'],sector=['J'])).to_parquet(f)
    releases=[dict(published='2021-01-10',table_path=str(f))];pool=pd.DataFrame(dict(instrument=['SZ000001','SH600001']))
    assert identity(pool,pd.Timestamp('2021-01-10'),releases).industry_id.eq('unknown').all()
    got=identity(pool,pd.Timestamp('2022-01-11'),releases)
    assert got.industry_id.tolist()==['legacy:J66','unknown'] and got.industry_stale.eq(1).all()


def test_peers_exclude_self_and_require_five():
    f=pd.DataFrame(dict(industry_id=['x']*6,mom21=[100,1,2,3,4,5],mom63=[100,1,2,3,4,5],mom126=[100,1,2,3,4,5]))
    got=peer_state(f);assert got.loc[0,'industry_mom63']==3 and got.loc[0,'industry_relative63']==97
    assert peer_state(f.iloc[:5]).industry_mom63.isna().all()
    f['industry_id']='unknown';assert peer_state(f).industry_mom63.isna().all()


def test_local_quantile_fallback_by_class():
    y=np.array([-.3]*35+[-.1]*10+[.3]*35);labels=classes(y);weights=np.ones(len(y))
    a,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),weights)
    local,counts,used=conditional_atoms(y,labels,weights,np.array(['x']*len(y)),np.array(['x','unknown','new']),a[0])
    assert used[0].tolist()==[True,False,False,False,False,False,True]
    assert not used[1:].any();np.testing.assert_array_equal(local[1],a[0]);assert counts[0,1]==10


def test_visibly_clipped_sector_is_not_guessed():
    rows=[['水利(N)','78','公共设施','000001','甲'],['居民服务、修理和','80','修理','300736','百邦科技']]
    out=parse_rows(rows,{0:'',1:'',2:''})
    assert out[1]['sector']=='unknown' and out[1]['major']=='unknown80'

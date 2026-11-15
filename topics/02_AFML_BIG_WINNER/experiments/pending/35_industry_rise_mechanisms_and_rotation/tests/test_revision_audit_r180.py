import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from revision_audit_r180 import differences,FIELDS


def test_added_removed_null_and_small_revision_are_distinct():
    a=pd.DataFrame([dict(era='SW2021',level='L2',industry_code='x',date=pd.Timestamp('2026-01-01')+pd.Timedelta(days=i),**{f:1. for f in FIELDS}) for i in range(3)])
    a.loc[0,'breadth21']=np.nan
    b=a.copy();b.loc[0,'nav']+=1e-10;b.loc[0,'coverage']=np.nan
    b.loc[1,'breadth21']=np.nan;b.loc[2,'date']=pd.Timestamp('2026-01-04')
    p,c=differences(a,b,'2026-01-04')
    assert p.change.value_counts().to_dict()=={'removed':1,'added':1}
    assert set(c.field)=={'nav','coverage','breadth21'} and len(c)==3
    assert c.new_value.isna().sum()==2
    p,c=differences(a,b,'2026-01-01');assert len(p)==0 and set(c.field)=={'nav','coverage'}


def test_duplicate_identity_rejected():
    a=pd.DataFrame([dict(era='SW2021',level='L2',industry_code='x',date=pd.Timestamp('2026-01-01'),**{f:1. for f in FIELDS})])
    with pytest.raises(ValueError,match='duplicate'):differences(pd.concat([a,a]),a,'2026-01-01')

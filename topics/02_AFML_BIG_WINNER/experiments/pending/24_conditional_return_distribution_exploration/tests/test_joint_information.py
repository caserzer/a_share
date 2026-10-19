import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from build_joint_information import attach
from run_joint_information import score


def frames():
    original=pd.DataFrame(dict(date=pd.to_datetime(['2021-01-29','2021-01-29']),instrument=['SH600000','SZ000001'],control=[1.,2.],y_1=[.1,-.1]))
    source=original[['date','instrument']].iloc[::-1].assign(new=[20.,np.nan])
    return original,source


def test_join_uses_keys_and_preserves_missing_and_original_rows():
    original,source=frames();out=attach(original,source,['new'])
    pd.testing.assert_frame_equal(out[original.columns],original)
    assert np.isnan(out.new.iloc[0]) and out.new.iloc[1]==20


def test_missing_or_duplicate_source_stock_is_rejected():
    original,source=frames()
    with pytest.raises(AssertionError):attach(original,source.iloc[:1],['new'])
    with pytest.raises(AssertionError):attach(original,pd.concat([source.iloc[:1]]*2),['new'])
    source.loc[source.index[0],'instrument']='SZ999999'
    with pytest.raises(AssertionError):attach(original,source,['new'])


def test_existing_control_cannot_be_overwritten():
    original,source=frames();source['control']=99
    with pytest.raises(AssertionError):attach(original,source,['control'])


def test_raw_and_mixed_scores_use_the_same_probability_rule():
    template=pd.DataFrame(dict(actual=[.1,-.1],p_down=[.7,.7],p_zero=[0.,0.],p_up=[.3,.3]))
    ba=np.tile([-.1,.1],(2,1));bw=np.tile([.7,.3],(2,1))
    atoms=np.tile(np.repeat([-.3,-.1,-.02,0.,.02,.1,.3],32),(2,1))
    p=np.array([[.1,.1,.1,0.,.2,.2,.3],[.2,.2,.2,0.,.1,.1,.2]])
    raw=score(template,ba,bw,atoms,p,1.);mixed=score(template,ba,bw,atoms,p,.5)
    np.testing.assert_allclose(raw.p_up,[.7,.4]);np.testing.assert_allclose(mixed.p_up,[.5,.35])
    assert raw.p_up.gt(raw.p_down).tolist()==[True,False]
    assert mixed.p_up.gt(mixed.p_down).tolist()==[False,False]
    np.testing.assert_allclose(mixed.brier,[.25,.1225])

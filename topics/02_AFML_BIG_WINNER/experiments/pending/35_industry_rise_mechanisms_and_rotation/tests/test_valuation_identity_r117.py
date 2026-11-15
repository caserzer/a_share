import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
from valuation_identity_r117 import interval_choice

def test_exclusive_code_cutover_and_no_current_alias_fallback():
    g=pd.DataFrame(dict(instrument=['BJ800001','BJ920001'],start=pd.to_datetime([None,'2025-10-09']),end=pd.to_datetime(['2025-10-09',None])))
    assert interval_choice(g,pd.Timestamp('2025-10-08'),'BJ920001')==('BJ800001','explicit_interval_proxy')
    assert interval_choice(g,pd.Timestamp('2025-10-09'),'BJ920001')==('BJ920001','explicit_interval_proxy')
    assert interval_choice(g.iloc[:1],pd.Timestamp('2025-10-09'),'BJ920001')==(None,'missing_code_interval')

def test_overlap_unknown_and_static_label():
    g=pd.DataFrame(dict(instrument=['SZ000001','SZ000002'],start=pd.to_datetime([None,None]),end=pd.to_datetime([None,None])))
    assert interval_choice(g,pd.Timestamp('2020-01-31'),'SZ000002')==(None,'ambiguous_code_interval')
    assert interval_choice(g.iloc[:0],pd.Timestamp('2020-01-31'),'SZ000002')==('SZ000002','static_metadata_proxy')

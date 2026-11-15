import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import pytest
from evaluate_adapter_r182 import validate_evaluation_sources


def test_source_clock_checked_independently_of_price_date():
    s={'identity':{'asof':'2026-06-30'}}
    d=pd.DataFrame({'date':pd.to_datetime(['2026-06-30']),'known_at':pd.to_datetime(['2026-07-01'])})
    l=pd.DataFrame({'date':pd.to_datetime(['2026-06-30'])});b=pd.DataFrame({'close':[1.]},index=pd.to_datetime(['2026-06-30']))
    with pytest.raises(ValueError,match='future evaluation'):validate_evaluation_sources(s,d,l,b,'2026-06-30')
    validate_evaluation_sources(s,d,l,b,'2026-07-01')
    with pytest.raises(ValueError,match='before observation'):validate_evaluation_sources(s,d,l,b,'2026-06-29')
    d['known_at']=pd.NaT
    with pytest.raises(ValueError,match='missing evaluation clock'):validate_evaluation_sources(s,d,l,b,'2026-07-01')


def test_auxiliary_sources_cannot_silently_extend_cutoff():
    s={'identity':{'asof':'2026-06-30'}};d=pd.DataFrame({'date':pd.to_datetime(['2026-06-30']),'known_at':pd.to_datetime(['2026-06-30'])})
    l=d[['date']];b=pd.DataFrame({'close':[1.]},index=pd.to_datetime(['2026-07-01']))
    with pytest.raises(ValueError,match='future auxiliary'):validate_evaluation_sources(s,d,l,b,'2026-06-30')

import numpy as np
import pandas as pd
from build_guidance_events import at_date,available_date,TITLE


def history():
    rows=[]
    for date,revision,loss in [('2024-01-21',False,False),('2024-04-22',True,True)]:
        row=dict(available=pd.Timestamp(date),revision=revision,**{c:False for c in TITLE})
        row['gd_loss90']=loss;rows.append(row)
    return pd.DataFrame(rows)


def test_revision_does_not_replace_or_leak_into_original_history():
    raw=history();before=at_date(raw,pd.Timestamp('2024-02-29'))
    assert before['gd_count90']==1 and before['gd_revision90']==0 and before['gd_loss90']==0
    assert before==at_date(raw.iloc[:1],pd.Timestamp('2024-02-29'))
    after=at_date(raw,pd.Timestamp('2024-04-30'))
    assert after['gd_count365']==2 and after['gd_revision90']==1 and after['gd_loss90']==1


def test_same_day_and_old_events_are_excluded():
    raw=history()
    same=at_date(raw,pd.Timestamp('2024-01-21'))
    assert same['gd_count365']==0 and np.isnan(same['gd_age_days'])
    old=at_date(raw,pd.Timestamp('2025-04-23'))
    assert old['gd_count365']==0 and np.isnan(old['gd_age_days'])


def test_archive_date_can_delay_but_never_advance_availability():
    assert available_date(dict(publish_date='2024-01-20',url='https://example.test/finalpage/2024-01-22/a.pdf'))==pd.Timestamp('2024-01-22')
    assert available_date(dict(publish_date='2024-01-22',url='https://example.test/finalpage/2024-01-20/a.pdf'))==pd.Timestamp('2024-01-22')

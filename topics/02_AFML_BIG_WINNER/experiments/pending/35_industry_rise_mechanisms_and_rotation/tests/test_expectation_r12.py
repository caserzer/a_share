import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
from expectation_r12 import eligible_training

def test_training_purges_cross_year_and_boundary_labels():
    g=pd.DataFrame({'date':pd.to_datetime(['2024-10-01','2024-12-01','2024-12-01','2024-10-01','2025-01-01']),
        'maturity20':pd.to_datetime(['2024-11-01','2025-01-01','2025-01-02','2024-11-01','2025-02-01']),
        'excess20':[.1,.2,.3,float('nan'),.4]})
    assert eligible_training(g,2025,20).tolist()==[True,False,False,False,False]

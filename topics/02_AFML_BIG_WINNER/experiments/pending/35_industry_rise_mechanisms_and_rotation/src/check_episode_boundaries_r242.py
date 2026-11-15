from common import *
import pandas as pd
from reversal_episodes_r242 import catalogue

def fixture(values,days=None,blocks=None,valid=None):
 n=len(values)
 return pd.DataFrame(dict(era=['test']*n,level=['L2']*n,industry_code=['x']*n,day_i=list(range(n)) if days is None else days,block=[1]*n if blocks is None else blocks,valid=[True]*n if valid is None else valid,relative=values))
def run():
 # First peak is censored; repeated subthreshold days cannot become new episodes.
 e,_=catalogue(fixture([1,.92,.90,1,.92,1.1]));assert len(e)==2 and e.breach_i.tolist()==[1,4] and e.recovery_i.tolist()==[3,5] and e.left_boundary.tolist()==[True,False]
 # A new high must replace the old peak; ongoing episode has no invented recovery.
 e,_=catalogue(fixture([1,1.1,1.012,1.0]));assert len(e)==1 and e.peak_i.iloc[0]==1 and e.breach_i.iloc[0]==2 and e.right_censored.iloc[0] and not e.left_boundary.iloc[0]
 # Missing trading day and block changes must reset peaks and close as censored.
 for d in [fixture([1,1.1,1.0,.9,.8],days=[0,1,2,4,5]),fixture([1,1.1,1.0,.9,.8],blocks=[1,1,1,2,2])]:
  e,s=catalogue(d);assert len(s)==2 and len(e)==2 and e.right_censored.all() and pd.isna(e.recovery_i).all()
 # Invalid row cannot bridge two price segments.
 e,s=catalogue(fixture([1,1.1,float('nan'),.8,.9],valid=[True,True,False,True,True]));assert len(s)==2 and e.empty
 # Exact recovery and tied latest peaks are handled without overlapping events.
 e,_=catalogue(fixture([1,1.1,1.1,1.0,1.1,1.0]));assert e.peak_i.tolist()==[2,4] and e.breach_i.tolist()==[3,5]
 js(ROOT/'outputs/r242/boundary_verification.json',dict(status='PASS',scenarios=6,code_sha256=sha(Path(__file__))))
 print('PASS 6 boundary scenarios')
if __name__=='__main__':run()

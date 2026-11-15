from common import *
import pandas as pd
import argparse

def audit(contract_path,as_of):
 c=json.loads(Path(contract_path).read_text());cut=pd.Timestamp(as_of)
 if cut.tzinfo is None:raise ValueError('as_of must include timezone')
 if cut<pd.Timestamp(c['freeze_recorded_at']):raise ValueError('as_of precedes recorded freeze')
 for f,h in c['frozen_inputs'].items():
  path=(ROOT/f).resolve()
  if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or sha(path)!=h:raise ValueError('frozen artifact changed: '+f)
 p=pd.read_parquet(ROOT/'outputs/r281/predictions.parquet');rows=[]
 for h,g in p.groupby('horizon'):
  observed=g.target.notna()&g.maturity.notna();mature=observed&(pd.to_datetime(g.maturity).dt.tz_localize('Asia/Shanghai')<=cut)
  rows.append(dict(horizon=int(h),prediction_rows=len(g),signal_months=g.date.nunique(),archived_evaluable_rows=int(mature.sum()),archived_evaluable_months=g[mature].date.nunique(),missing_label_or_calendar_rows=int((~observed).sum()),known_but_not_mature_rows=int((observed&~mature).sum()),independent_prospective_rows=0,note='No prospective generation receipts supplied; date passage never creates them'))
 return dict(status='PASS',as_of=cut.isoformat(),contract_sha256=sha(contract_path),frozen_artifacts=len(c['frozen_inputs']),models=len(json.loads((ROOT/'outputs/r281/models.json').read_text())),rows=rows,prospective_status='NOT_STARTED_NO_RECEIPTS',adoption=False,strict_pit=False,parameters_year=2026,next_year_refit_required=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--as-of',required=True);parser.add_argument('--contract',default=str(ROOT/'protocols/r282.json'));args=parser.parse_args();print(json.dumps(audit(args.contract,args.as_of),ensure_ascii=False,indent=2))

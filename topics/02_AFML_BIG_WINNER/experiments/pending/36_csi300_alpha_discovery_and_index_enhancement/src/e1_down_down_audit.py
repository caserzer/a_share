from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,re
p=Path('topics/02_AFML_BIG_WINNER/experiments/pending/36_csi300_alpha_discovery_and_index_enhancement');d=p/'outputs/diagnostics/e1_down_down_account_20261117';sel=pd.read_csv(d/'selection.csv');sched=pd.read_csv(d/'schedule.csv');a=pd.read_csv(d/'DD_daily.csv',parse_dates=['date']).set_index('date');periods=pd.read_csv(d/'periods.csv');checks=[]
def check(name,ok):
 assert bool(ok),name
 checks.append({'check':name,'passed':True})
check('70 fixed original signal dates',len(sched)==70)
check('strict both negative selection',np.array_equal(sel.selected.to_numpy(),((sel.trend<0)&(sel['short']<0)).to_numpy()))
for date,g in sel.groupby('signal_date'):
 k=g.selected.sum();weights=g.loc[g.selected,'weight'];check(date+' equal reallocated weights',len(weights)==k and (k==0 or np.allclose(weights,1/k)))
check('8 no-stock targets cash',sched.selected_count.eq(0).sum()==8 and sched.loc[sched.selected_count.eq(0),'cash_target'].eq(1).all())
monthnav=a.nav.groupby(a.index.to_period('M')).last();independent=monthnav/monthnav.shift(fill_value=1)-1
m=periods[(periods.scope=='supplement')&(periods.frequency=='M')].set_index('period');check('monthly NAV endpoint returns',np.allclose(independent.to_numpy(),m.loc[independent.index.astype(str),'DD_return']))
check('annual linked returns',np.isclose(np.prod(1+periods.loc[(periods.scope=='supplement')&(periods.frequency=='Y'),'DD_return']),a.nav.iloc[-1]))
check('cash October2025',a.loc['2025-10'].holdings.eq(0).all() and a.loc['2025-10'].cash_weight.eq(1).all())
rec=json.loads((d/'freeze.json').read_text())
for x in rec['files']:check('hash '+Path(x['path']).name,hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'])
(d/'independent_audit.json').write_text(json.dumps({'status':'PASS','checks':checks},indent=2))
print('independent audit',len(checks),'PASS; single-name targets',int(sched.selected_count.eq(1).sum()));print('selection count min nonzero',sched.loc[sched.selected_count>0,'selected_count'].min());print('validation',json.loads((d/'validation.json').read_text())['selection_checks'])

from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r295';d=pd.read_csv(out/'summary.csv');w=d.pivot(index=['era','level','year','variant'],columns='method',values='brier');q=d[d.method.eq('daily')].pivot(index=['era','level','year'],columns='variant',values='brier');q['state_minus_base']=q.state-q.base;q['interaction_minus_base']=q.interaction-q.base;q.to_csv(out/'regime_comparisons.csv')
 f=json.loads((out/'folds.json').read_text());v=json.loads((out/'independent_verification.json').read_text());assert v['status']=='PASS'
 js(out/'summary.json',dict(status='PASS',models=len(f),daily_brier_improved=int((w.daily<w.monthly).sum()),state_improved=int((q.state_minus_base<0).sum()),interaction_improved=int((q.interaction_minus_base<0).sum()),contexts=len(q),slope_flips=sum(np.sign(x['coefficient'])!=np.sign(np.asarray(x['base_model']['calibration_coefficient']).item()) for x in f),adoption=False,independent_prospective=0,script_sha256=sha(__file__),inputs={p:sha(out/p) for p in ['summary.csv','folds.json','independent_verification.json']},comparison_sha256=sha(out/'regime_comparisons.csv')))
if __name__=='__main__':run()

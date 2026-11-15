from common import *
import pandas as pd
IDS=['era','level','cohort','horizon']
def metrics(a,b):
 if not len(a):return dict(mean=np.nan,loss_fraction=np.nan,downside_rms=np.nan,beta=np.nan)
 return dict(mean=float(np.mean(a)),loss_fraction=float(np.mean(a<0)),downside_rms=float(np.sqrt(np.mean(np.minimum(a,0)**2))),beta=float(np.cov(a,b,ddof=1)[0,1]/np.var(b,ddof=1)) if len(a)>=2 and np.var(b,ddof=1)>0 else np.nan)
def run():
 out=ROOT/'outputs/r236';out.mkdir(exist_ok=True);rows=[];reads=[];pairid=0
 for rnd in [210,211,212,214,215,216,217]:
  dp=ROOT/f'outputs/r{rnd}/daily_returns.parquet';cp=ROOT/f'outputs/r{rnd}/paired_risk.csv';reads += [dp,cp];d=pd.read_parquet(dp);cases=pd.read_csv(cp);lookup={k:g.set_index('date').sort_index() for k,g in d.groupby(IDS+['method'])}
  for row in cases.to_dict('records'):
   ident=dict(row,source_round=rnd,pair_id=pairid);pairid+=1
   if not row['both_whole']:rows.append(dict(ident,market_direction='not_evaluated',status='incomplete_original_path',days=0));continue
   key=tuple(row[k] for k in IDS);a=lookup[key+(row['method'],)];b=lookup[key+(row['control'],)];assert a.index.equals(b.index);assert np.allclose(a.benchmark,b.benchmark);assert a.whole_path_valid.all() and b.whole_path_valid.all();market=a.benchmark.to_numpy();av=a[row['cost']].to_numpy();bv=b[row['cost']].to_numpy()
   for label,mask in [('all',np.ones(len(a),dtype=bool)),('down',market<0),('up',market>0),('zero',market==0)]:
    aa=metrics(av[mask],market[mask]);bb=metrics(bv[mask],market[mask]);record=dict(ident,market_direction=label,status='complete_path_diagnostic',days=int(mask.sum()),start=str(a.index.min().date()),end=str(a.index.max().date()))
    for metric in aa:record['first_'+metric]=aa[metric];record['control_'+metric]=bb[metric];record['delta_'+metric]=aa[metric]-bb[metric]
    rows.append(record)
 result=pd.DataFrame(rows);result.to_csv(out/'directional_risk.csv',index=False);js(out/'verification.json',dict(status='PASS',original_pairs=pairid,eligible_pairs=result[result.market_direction.eq('all')].pair_id.nunique(),incomplete_pairs=int(result.status.eq('incomplete_original_path').sum()),records=len(result),scope='Contemporaneous market-direction risk attribution on complete paired paths only; not causal, timing or significance evidence',inputs={str(p):sha(p) for p in reads+[ROOT/'protocols/r236.json',Path(__file__)]},outputs={'directional_risk.csv':sha(out/'directional_risk.csv')},adoption=False));print(result.query("cost=='net50' and method=='interaction' and control=='base' and horizon==20 and market_direction in ['down','up']").groupby('market_direction').delta_mean.agg(['count','median',lambda x:sum(x>0)]).to_string())
if __name__=='__main__':run()

from common import *
import pandas as pd
from sklearn.metrics import roc_auc_score,average_precision_score

def run():
 out=ROOT/'outputs/r263';p=pd.read_parquet(out/'predictions.parquet');rows=[]
 for key,g in p.groupby(['era','level','task','horizon','method','variant','date']):
  v=g[g.y.notna()];two=v.y.nunique()==2;rows.append(dict(zip(['era','level','task','horizon','method','variant','date'],key),auc=roc_auc_score(v.y,v.prediction) if two else np.nan,ap=average_precision_score(v.y,v.prediction) if two else np.nan,brier=((v.prediction-v.y)**2).mean(),two_classes=two))
 d=pd.DataFrame(rows);d.to_csv(out/'secondary_date_metrics.csv',index=False);res=[]
 for key,g in d.groupby(['era','level','task','horizon','method']):
  for metric in ['brier','auc','ap']:
   w=g.pivot(index='date',columns='variant',values=metric)
   for a,b in [('state','base'),('interaction','base')]:
    delta=((w[b]-w[a]) if metric=='brier' else (w[a]-w[b])).dropna();annual=delta.groupby(delta.index.year).mean();res.append(dict(zip(['era','level','task','horizon','method'],key),metric=metric,comparison=a+'-'+b,improvement=delta.mean(),months=len(delta),annual=annual.to_dict(),status='descriptive_only'))
 js(out/'regime_comparisons.json',res);js(out/'evaluation_receipt.json',dict(predictions_sha256=sha(out/'predictions.parquet'),code_sha256=sha(__file__),comparisons=len(res),adoption=False));print('EVALUATED',len(res))
if __name__=='__main__':run()

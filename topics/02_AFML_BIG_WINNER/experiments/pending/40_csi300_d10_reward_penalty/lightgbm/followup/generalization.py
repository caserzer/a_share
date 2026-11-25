from common_inputs import *
from model import date_rankic
from collections import defaultdict

def main():
    data=prepare().sort_values(KEY)
    test=outer().merge(ledger.labels(),on=KEY,validate='1:1')
    rows=[];gains=[]
    for q,g in test.groupby('fold'):
        d=data[data.h10_mature<pd.Period(q).start_time]
        tree=lgb.Booster(model_file=str(OUT/'models'/q/'tree_rank.txt'))
        gain=tree.feature_importance('gain')
        gains.extend((q,c,v/gain.sum()) for c,v in zip(COLS,gain))
        med=pd.Series(json.loads((OUT/'models'/q/'medians.json').read_text()))
        for name,f in [('train',d),('test',g)]:
            for n in [20,80]:
                s=tree.predict(f[COLS].fillna(med),num_iteration=n,num_threads=3)
                ic=date_rankic(f.reset_index(drop=True),s)
                for date,value in zip(sorted(f.signal_date.unique()),ic):
                    rows.append((q,date,name,n,value))
    pd.DataFrame(rows,columns=['fold','date','sample','trees','rankic']).to_parquet(DEST/'learning.parquet',index=False)
    pd.DataFrame(gains,columns=['fold','feature','gain_share']).to_csv(DEST/'gain.csv',index=False)
if __name__=='__main__':main()

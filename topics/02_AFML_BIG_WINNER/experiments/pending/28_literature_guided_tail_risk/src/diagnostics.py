"""Complete fixed-warning error counts; descriptive, without new model selection."""
from core import *


def main():
    full=pd.read_parquet(CACHE/'all_predictions.parquet');rows=[]
    for (name,date),g in full.groupby(['model','date']):
        for fraction in [.05,.1,.2]:
            z=g.copy();z['flag']=warning(g.probability,g.instrument,fraction)
            z=z[z.actual.notna()].copy()
            if not len(z):continue
            z['event']=z.actual<-.2
            for dimension in ['all','year','regime','industry_id']:
                z['condition']='all' if dimension=='all' else str(date.year) if dimension=='year' else z[dimension].astype(str)
                for condition,a in z.groupby('condition'):
                    tp=int((a.flag&a.event).sum());fp=int((a.flag&~a.event).sum());fn=int((~a.flag&a.event).sum());tn=int((~a.flag&~a.event).sum())
                    rows.append(dict(model=name,date=date,fraction=fraction,dimension=dimension,condition=condition,rows=len(a),
                        TP=tp,FP=fp,FN=fn,TN=tn,recall=tp/(tp+fn) if tp+fn else np.nan,
                        false_positive_rate=fp/(fp+tn) if fp+tn else np.nan,
                        false_discovery_rate=fp/(tp+fp) if tp+fp else np.nan,
                        mean_return_flagged_non_event=float(a.loc[a.flag&~a.event,'actual'].mean()),
                        mean_return_missed_event=float(a.loc[~a.flag&a.event,'actual'].mean())))
    m=pd.DataFrame(rows);m.to_csv(OUT/'warning_errors_monthly.csv',index=False)
    m.groupby(['model','fraction','dimension','condition']).agg(stock_months=('rows','sum'),TP=('TP','sum'),FP=('FP','sum'),FN=('FN','sum'),TN=('TN','sum'),
        months=('date','nunique'),mean_month_recall=('recall','mean'),mean_month_fpr=('false_positive_rate','mean'),
        mean_month_false_discovery=('false_discovery_rate','mean'),mean_month_missed_return=('mean_return_missed_event','mean')).reset_index().to_csv(OUT/'warning_errors_summary.csv',index=False)
    bounds=pd.read_csv(OUT/'missing_paired_brier_bounds.csv')
    bounds.groupby('model').agg(delta_lower=('delta_lower','mean'),delta_upper=('delta_upper','mean'),missing=('missing','sum'),months=('date','nunique')).reset_index().to_csv(OUT/'missing_bounds_summary.csv',index=False)
    print('All fixed warnings and prescribed conditions accounted for',flush=True)


if __name__=='__main__':main()

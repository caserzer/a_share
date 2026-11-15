"""Read-only artifact verification, including independent stored-model replay."""
import pandas as pd
from scipy.special import expit
from common import *
from train_r02 import F,EXTRA,target


def run():
    assertions=[]
    for row in json.loads((ROOT/'outputs/r01/source_inventory.json').read_text()):
        assert sha(row['path'])==row['sha256'];assertions.append('source '+row['path'])
    for rid in ['r01','r02']:
        receipt=json.loads((ROOT/f'outputs/{rid}/run_receipt.json').read_text())
        assert receipt['protocol_sha256']==sha(ROOT/f'protocols/{rid}.json')
        assert receipt['panel_sha256']==sha(ROOT/'data/monthly_panel.parquet')
    ledger=pd.read_csv(ROOT/'outputs/r02/fold_ledger.csv');trained=ledger[ledger.status.eq('fit')]
    for row in trained.itertuples():
        cutoff=pd.Timestamp(row.year,1,1) if row.task=='return' else pd.Timestamp(row.year-1,7,1)
        assert pd.Timestamp(row.fit_max_maturity)<cutoff
        if row.task!='return':assert pd.Timestamp(row.cal_max_maturity)<pd.Timestamp(row.year,1,1)
    p=pd.read_parquet(ROOT/'outputs/r02/predictions.parquet')
    panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet');panel['log_members']=np.log(panel.members)
    models=json.loads((ROOT/'outputs/r02/model_parameters.json').read_text());maximum_error=0.;n=0
    for (era,level,cohort),params in pd.DataFrame(models).groupby(['era','level','cohort']):
        base=panel[panel.era.eq(era)&panel.level.eq(level)&panel.price_ready].dropna(subset=F+EXTRA[cohort])
        rank=base.groupby('date')[F+EXTRA[cohort]].transform(centered_rank)
        for m in params.to_dict('records'):
            subset=p[p.era.eq(era)&p.level.eq(level)&p.cohort.eq(cohort)&p.method.eq(m['method'])&p.year.eq(m['year'])&p.task.eq(m['task'])&p.horizon.eq(m['horizon'])]
            x=rank.loc[subset.row_id,m['columns']].to_numpy();x=(x-np.array(m['scaler_mean']))/np.array(m['scaler_scale'])
            coeff=np.array(m['coefficient']).reshape(-1);raw=x@coeff+np.array(m['intercept']).reshape(-1)[0]
            if m['task']!='return':
                predicted=expit(raw*np.array(m['calibration_coefficient']).reshape(-1)[0]+np.array(m['calibration_intercept']).reshape(-1)[0])
            else:predicted=raw
            error=float(np.max(np.abs(predicted-subset.prediction.to_numpy())));maximum_error=max(error,maximum_error)
            assert error<1e-10; n+=len(subset)
            expected,eligible=target(panel.loc[subset.row_id],m['task'],m['horizon'])
            assert eligible.all();assert np.allclose(expected,subset.y,equal_nan=True)
    assert n==len(p)
    # Paired comparisons must have exactly the same test rows, targets, and training windows.
    for key,g in p[p.cohort.ne('F')].groupby(['era','level','cohort','task','horizon','year']):
        a=g[g.method.eq('F')].sort_values('row_id');b=g[g.method.eq(key[2])].sort_values('row_id')
        assert a.row_id.tolist()==b.row_id.tolist();assert np.allclose(a.y,b.y,equal_nan=True)
    financial=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet')
    assert (financial.loc[financial.timing_valid,'proxy_available_date'].dropna()>financial.loc[financial.timing_valid,'effective_ann_date'].reindex(financial.loc[financial.timing_valid,'proxy_available_date'].dropna().index)).all()
    js(ROOT/'outputs/verification.json',dict(status='PASS',source_hash_checks=len(assertions),trained_folds=len(trained),replayed_prediction_rows=n,
        max_model_replay_error=maximum_error,paired_rows_targets_equal=True,fit_and_calibration_labels_mature=True,
        limitations=['does not prove vintage completeness, economic causality, statistical power, or investability']))
    print('VERIFIED',n,'predictions; max error',maximum_error)

if __name__=='__main__':run()

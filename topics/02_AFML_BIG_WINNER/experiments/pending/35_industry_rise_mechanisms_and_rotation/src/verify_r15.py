import pandas as pd
from common import *
from train_r02 import F
from expectation_r12 import eligible_training

def run():
    out=ROOT/'outputs/r15';p=pd.read_parquet(out/'predictions.parquet')
    expected=(ROOT/'src/expectation_r12.py').read_text().replace('outputs/r12','outputs/r15').replace('data/r11_revision_coverage.parquet','data/r15_revision_coverage.parquet').replace('protocols/r12.json','protocols/r15.json').replace('R12 predictions','R15 predictions')
    assert (ROOT/'src/expectation_r15.py').read_text()==expected, 'R12 model rules changed beyond source/output routing'
    pairs=pd.read_parquet(ROOT/'data/r15_company_pair_audit.parquet')
    assert not pairs.change.isin(['gained','changed_value']).any()
    surviving=pairs.revision_new.notna()
    assert np.allclose(pairs.loc[surviving,'revision_old'],pairs.loc[surviving,'revision_new'])
    old=pd.read_parquet(ROOT/'data/r11_revision_coverage.parquet')
    new=pd.read_parquet(ROOT/'data/r15_revision_coverage.parquet')
    joined=old.merge(new,on=KEY+['date','fy_offset'],suffixes=('_old','_new'),validate='one_to_one')
    assert len(joined)==len(old)==len(new)
    assert joined.members_old.eq(joined.members_new).all()
    assert joined.known_new.le(joined.known_old).all()
    assert new.eligible.eq(new.known.ge(5)&new.coverage.ge(.8)).all()
    unknown_new=joined.covered_member_median_new.isna()
    values_changed=(joined.covered_member_median_new.notna()&joined.covered_member_median_old.notna()&~np.isclose(joined.covered_member_median_new,joined.covered_member_median_old)).sum()
    js(out/'data_verification.json',dict(status='PASS',lost_broker_months=int(pairs.change.eq('lost').sum()),surviving_broker_months=int(surviving.sum()),industry_rows=len(new),industry_medians_changed=int(values_changed),
      checks=['no newly fabricated broker values','surviving broker revisions unchanged','full membership denominator unchanged','known coverage cannot increase','strict5/80 gate unchanged','R12 model source identical except routing']))
    params=json.loads((out/'model_parameters.json').read_text())
    panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet');panel['log_members']=np.log(panel.members)
    cov=pd.read_parquet(ROOT/'data/r15_revision_coverage.parquet')
    merged=cov.merge(panel,on=KEY+['date'],suffixes=('_coverage',''),validate='many_to_one')
    base=merged[merged.price_ready].dropna(subset=F+['covered_member_median']).copy()
    error=0.;rows=0
    for m in params:
        g=base[(base.era==m['era'])&(base.level==m['level'])&(base.fy_offset==m['fy_offset'])]
        g=g[g.eligible] if m['population']=='strict' else g[g.known.ge(5)&~g.eligible]
        g=g[g.groupby('date').date.transform('size')>=2].copy();g['expectation']=g.covered_member_median
        ranks=g.groupby('date')[F+['expectation']].transform(centered_rank)
        tr=g[eligible_training(g,m['year'],m['horizon'])]
        assert len(tr)>=300 and tr.date.nunique()>=18
        assert tr[f"maturity{m['horizon']}"].max()<pd.Timestamp(m['year'],1,1)
        q=p[(p.era==m['era'])&(p.level==m['level'])&(p.fy_offset==m['fy_offset'])&(p.population==m['population'])&(p.horizon==m['horizon'])&(p.year==m['year'])&(p.method==m['method'])]
        assert set(q.row_id)==set(g.index[g.date.dt.year.eq(m['year'])])
        x=ranks.loc[q.row_id,m['columns']].to_numpy();replay=((x-np.array(m['scaler_mean']))/np.array(m['scaler_scale']))@np.array(m['coef'])+m['intercept']
        delta=np.max(np.abs(replay-q.prediction.to_numpy()));error=max(error,float(delta));rows+=len(q)
        assert np.allclose(q.target,g.loc[q.row_id,f"excess{m['horizon']}"],equal_nan=True)
    assert error<1e-12 and rows==len(p)
    for _,g in p.groupby(['era','level','fy_offset','population','horizon','year']):
        frames=[z.sort_values('row_id').set_index('row_id') for _,z in g.groupby('method')]
        assert len(frames)==3
        for z in frames[1:]:
            assert frames[0].index.equals(z.index)
            assert np.allclose(frames[0].target,z.target,equal_nan=True)
    folds=pd.read_csv(out/'fold_ledger.csv')
    assert not ((folds.population=='strict')&(folds.status=='fit')).any()
    js(out/'verification.json',dict(status='PASS',prediction_rows=rows,max_replay_error=error,
        checks=['three methods exact paired cohort and labels','training labels mature strictly before test year','training minima preserved','all test origins retained including unknown outcomes','strict cohort not promoted'],
        limitation='partial covered-company diagnostic not full-industry predictive validation'))
    print('R15 VERIFIED',rows,'predictions; replay error',error)
if __name__=='__main__':run()

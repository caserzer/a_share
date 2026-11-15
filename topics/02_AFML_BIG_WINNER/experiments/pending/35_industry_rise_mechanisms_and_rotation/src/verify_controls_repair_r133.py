"""Direct finite-window covariance and complete cohort/rank audit."""
import pandas as pd
from common import *
from train_r02 import F
K=KEY+['date'];M=['market_beta126','residual_vol126'];D=['breadth21','breadth63'];C=F+['size_control']+M+D


def check_diff(a,b,columns,record):
    left=a.set_index(K);right=b.set_index(K);common=left.index.intersection(right.index)
    assert record['old_rows']==len(left) and record['new_rows']==len(right)
    assert record['added']==len(right.index.difference(left.index)) and record['removed']==len(left.index.difference(right.index));bad=np.zeros(len(common),bool)
    for c in columns:
        difference=~np.isclose(left.loc[common,c].to_numpy(float),right.loc[common,c].to_numpy(float),rtol=1e-12,atol=1e-12,equal_nan=True)
        assert int(difference.sum())==record['fields'][c];bad|=difference
    assert int(bad.sum())==record['changed_common']


def run():
    out=ROOT/'outputs/r133';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h,p
    assert sha(out/'market_controls.parquet')==receipt['sha256'];p=pd.read_parquet(out/'market_controls.parquet');old=pd.read_parquet(ROOT/'data/r54_market_controls.parquet')
    pd.testing.assert_frame_equal(p[p.level.eq('L1')].sort_values(K).reset_index(drop=True),old[old.level.eq('L1')].sort_values(K).reset_index(drop=True),check_exact=True)
    market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;target=p.set_index(K);checks=0;known=0;max_beta=0.;max_res=0.
    for path in [ROOT/'outputs/r129/daily_2026-10-21.parquet',ROOT/'data/l1_daily.parquet']:
        daily=pd.read_parquet(path,columns=K+['block','nav'])
        for key,g in daily.groupby(KEY+['block']):
            g=g.sort_values('date');dates=pd.DatetimeIndex(g.date);positions=market.index.get_indexer(dates);assert np.all(np.diff(positions)==1)
            nav=g.nav.to_numpy(float);bm=market.reindex(dates).to_numpy(float)
            for i,date in enumerate(dates):
                idx=key[:3]+(date,)
                if idx not in target.index:continue
                row=target.loc[idx];expected_count=np.nan if i<125 else 125. if i==125 else 126.
                assert np.isclose(row.paired_returns126,expected_count,equal_nan=True)
                if i<126:assert pd.isna(row.market_beta126) and pd.isna(row.residual_vol126)
                else:
                    a=nav[i-126:i+1];b=bm[i-126:i+1];rr=a[1:]/a[:-1]-1;mm=b[1:]/b[:-1]-1
                    cov=np.cov(rr,mm,ddof=1);vm=cov[1,1]
                    if vm<=0:assert pd.isna(row.market_beta126) and pd.isna(row.residual_vol126)
                    else:
                        beta=cov[0,1]/vm;res=np.sqrt(max(cov[0,0]-cov[0,1]**2/vm,0)*252);be=abs(row.market_beta126-beta);re=abs(row.residual_vol126-res);assert be<1e-8 and re<1e-10;max_beta=max(max_beta,be);max_res=max(max_res,re);known+=1
                checks+=1
    assert checks==len(p)
    expected_price=p.price_ready&p[F].notna().all(axis=1);expected_controls=p[M].notna().all(axis=1)
    assert p.price_complete.equals(expected_price) and p.market_controls_complete.equals(expected_controls);assert p.joint_complete.equals(expected_price&expected_controls&p.size_control.notna())
    check_diff(old,p,M+['paired_returns126','price_complete','market_controls_complete','joint_complete'],receipt['control_differences'])
    for side,control,monthly in [('old',old,ROOT/'data/monthly_panel.parquet'),('new',p,ROOT/'outputs/r130/monthly_panel.parquet')]:
        breadth=pd.concat([pd.read_parquet(q,columns=K+D) for q in [monthly,ROOT/'data/l1_monthly_panel.parquet']],ignore_index=True)
        full=control.merge(breadth,on=K,validate='one_to_one');expected=full[full.price_ready&full[C].notna().all(axis=1)].copy();saved=pd.read_parquet(out/f'cohort_{side}.parquet')
        for c in C:
            groups=expected.groupby(['era','level','date'])[c];expected['rank_'+c]=(groups.rank(method='average')-.5)/groups.transform('count')-.5
        pd.testing.assert_frame_equal(expected.sort_values(K).reset_index(drop=True),saved.sort_values(K).reset_index(drop=True),check_exact=True)
    a=pd.read_parquet(out/'cohort_old.parquet');b=pd.read_parquet(out/'cohort_new.parquet');check_diff(a,b,C+['rank_'+c for c in C],receipt['fsmd_differences'])
    summary=json.loads((out/'scope_summary.json').read_text())
    for path,digest in summary['reads'].items():assert sha(path)==digest
    ai=a.set_index(K);bi=b.set_index(K)
    pd.testing.assert_frame_equal(bi.loc[~bi.index.isin(ai.index)].reset_index(),pd.read_parquet(out/'cohort_added.parquet'))
    pd.testing.assert_frame_equal(ai.loc[~ai.index.isin(bi.index)].reset_index(),pd.read_parquet(out/'cohort_removed.parquet'))
    common=ai.index.intersection(bi.index);rankcols=['rank_'+c for c in C]
    mask=~np.isclose(ai.loc[common,rankcols],bi.loc[common,rankcols],rtol=1e-12,atol=1e-12,equal_nan=True).all(axis=1)
    pd.testing.assert_frame_equal(common[mask].to_frame(index=False),pd.read_parquet(out/'changed_rank_identities.parquet'))
    oi=old.set_index(K);ni=p.set_index(K);ix=oi.index.intersection(ni.index);ko=oi.loc[ix,'market_controls_complete'];kn=ni.loc[ix,'market_controls_complete']
    assert summary['controls_became_known']==int((~ko&kn).sum()) and summary['controls_became_unknown']==int((ko&~kn).sum())
    js(out/'verification.json',dict(status='PASS',direct_windows=checks,known_controls=known,max_beta_error=max_beta,max_residual_vol_error=max_res,unchanged_l1_rows=int(p.level.eq('L1').sum()),outcomes_read=False,scope='All control windows/completeness/cohort ranks, no downstream model validation'))
    print('PASS',checks,known,max_beta,max_res)

if __name__=='__main__':run()

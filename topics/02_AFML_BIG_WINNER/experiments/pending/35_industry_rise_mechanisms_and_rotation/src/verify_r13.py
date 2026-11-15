import pandas as pd
from common import *

def run():
    feature=pd.read_parquet(ROOT/'data/r13_sensitivities.parquet')
    state=pd.read_parquet(ROOT/'data/r13_macro_states.parquet')
    assert (state.available<state.date).all()
    assert (feature.fit_last_date<feature.date).all() and feature.n_fit.ge(24).all()
    cols=KEY+['date','price_ready','mom20','mom60','vol20','dd60','past_excess20','excess20','excess60']
    panel=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet',columns=cols)],ignore_index=True)
    panel['row_id']=panel.index
    # Independent ridge normal-equation reconstruction across levels and delays.
    checked=0;maxerror=0.
    for _,group in feature.groupby(['era','level','lag']):
        take=group.iloc[np.unique(np.linspace(0,len(group)-1,4,dtype=int))]
        for row in take.itertuples():
            g=panel[(panel.era==row.era)&(panel.level==row.level)&(panel.industry_code==row.industry_code)]
            st=state[state.lag==row.lag]
            q=g.merge(st,on='date',validate='one_to_one')
            h=q[(q.date<row.date)&(q.date>=row.date-pd.DateOffset(months=36))].dropna(subset=['lag_pmi','lag_money','past_excess20'])
            x=h[['lag_pmi','lag_money']].to_numpy();mu=x.mean(axis=0);sd=x.std(axis=0);z=(x-mu)/sd;y=h.past_excess20.to_numpy()
            coef=np.linalg.solve(z.T@z+np.eye(2),z.T@(y-y.mean()))
            current=st[st.date==row.date][['pmi','money']].iloc[0].to_numpy()
            values=[coef.mean(),coef@((current-mu)/sd)]
            maxerror=max(maxerror,float(np.max(np.abs(np.array(values)-[row.exposure,row.conditioned]))))
            assert np.allclose(mu,row.mu) and np.allclose(sd,row.sd)
            assert len(h)==row.n_fit
            checked+=1
    assert maxerror<1e-10
    m=pd.read_csv(ROOT/'outputs/r13/date_metrics.csv')
    assert (m.origins==m.known+m.unknown).all()
    assert m.loc[~m.top_complete,'top_excess'].isna().all()
    # Base price score must be identical across both availability assumptions.
    f=m[m.method=='F'].pivot(index=['era','level','date','horizon'],columns='lag',values='ic')
    assert np.allclose(f[45],f[75],equal_nan=True)
    selections=pd.read_parquet(ROOT/'outputs/r13/selections.parquet')
    common=set(feature.groupby('row_id').filter(lambda z:z.lag.nunique()==2).row_id)
    selection_checks=0
    for key,g in panel[panel.price_ready&panel.row_id.isin(common)].groupby(['era','level','date']):
        if len(g)<20:continue
        r=g[['mom20','mom60','vol20','dd60']].apply(centered_rank);f=((r.mom20+r.mom60)/2-r.vol20+r.dd60)/3
        for lag in [45,75]:
            z=g.join(feature[feature.lag==lag].set_index('row_id')[['exposure','conditioned']],on='row_id')
            for method,score in {'F':f,'F_exposure':(f+centered_rank(z.exposure))/2,'F_macro':(f+centered_rank(z.conditioned))/2}.items():
                expected=set(z.assign(score=score).sort_values(['score','industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(z)))).industry_code)
                selected=selections[(selections.era==key[0])&(selections.level==key[1])&(selections.date==key[2])&(selections.lag==lag)&(selections.method==method)]
                assert expected==set(selected.industry_code)
                selection_checks+=1
    js(ROOT/'outputs/r13/verification.json',dict(status='PASS',normal_equation_checks=checked,max_error=maxerror,selection_checks=selection_checks,
        checks=['strict macro availability','sensitivity training before signal','minimum24 past observations','normal-equation independent replay','same price baseline across delays','all top selections before outcomes','unknown group return suppressed']))
    print('R13 VERIFIED',checked,'sensitivity estimates;',selection_checks,'selections; error',maxerror)
if __name__=='__main__':run()

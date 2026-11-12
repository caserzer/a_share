import json
import numpy as np
import pandas as pd
from price_information import EP,OUT,CACHE,features,KEY,ID,sha

def main():
    seal=json.loads((OUT/'feature_seal.json').read_text())
    for path,h in seal['inputs'].items():assert sha(path)==h,path
    assert sha(OUT/'feature_panel.parquet')==seal['features_sha256']
    assert sha(OUT/'matched_members.csv.gz')==seal['members_sha256']
    f=pd.read_parquet(OUT/'feature_panel.parquet');p=pd.read_parquet(OUT/'evaluated_panel.parquet')
    pd.testing.assert_frame_equal(f[ID],p[ID])
    assert not any(c.startswith(('win','return','excess','status')) for c in f.columns)
    d=pd.read_parquet(CACHE/'daily_industries.parquet');d=d[d.level.eq('L3')];m=pd.read_parquet(CACHE/'CSI_ALL.parquet').close
    lookup={key:g.sort_values('date') for key,g in d.groupby(KEY)}
    checked=0
    for _,r in p[p.eligible].sample(60,random_state=401).iterrows():
        full=lookup[tuple(r[k] for k in KEY)];prefix=full[full.date.le(r.date)]
        v=features(prefix,m).iloc[-1]
        for c in ['rel21','rel63','abs63','risk63','eff63']:assert np.isclose(v[c],r[c],atol=1e-12)
        index=full.index[full.date.eq(r.date)][0];pos=full.index.get_loc(index)
        for h in [63,126,252]:
            if pos+1+h<len(full):
                start,stop=full.iloc[pos+1],full.iloc[pos+1+h]
                ret=stop.nav/start.nav-1;excess=ret-(m.loc[stop.date]/m.loc[start.date]-1)
                assert r[f'win{h}']==int(ret>0 and excess>0)
            else:assert pd.isna(r[f'win{h}'])
            checked+=1
    pairs=pd.read_csv(OUT/'matched_members.csv.gz');assert not pairs.duplicated(['hypothesis','row_id']).any()
    for hypothesis,g in pairs.groupby('hypothesis'):
        sizes=g.groupby(['date','cell','arm']).size().unstack('arm')
        assert sizes.notna().all().all()
        if hypothesis=='H1':assert (sizes>=3).all().all()
        else:assert (sizes.iloc[:,0]==sizes.iloc[:,1]).all() and (sizes>=2).all().all()
    summary=pd.read_csv(OUT/'summary.csv')
    for _,r in summary.iterrows():
        if r.unit!='state':continue
        z=p[p[r.method]];col=f'win{int(r.horizon)}'
        assert len(z)==r.total and z[col].notna().sum()==r.known and z[col].sum()==r.wins
    result={'status':'PASS','prefix_feature_checks':60,'raw_outcome_checks':checked,'feature_seal_verified':True,'matched_members_verified':len(pairs),'predictive_efficacy_established':False}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

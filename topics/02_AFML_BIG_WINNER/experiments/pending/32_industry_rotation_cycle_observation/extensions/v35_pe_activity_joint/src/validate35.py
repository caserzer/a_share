"""Independent formulas, missing windows, source identity and prefix checks."""
from common35 import *

def run():
    checks=[]
    def ck(name,ok):
        assert bool(ok),name;checks.append(name)
    receipt=json.loads((OUT/'feature_receipt.json').read_text())
    for name,key in [('features.parquet','features_sha256'),('daily_expansion.parquet','daily_sha256'),('stock_pe_panel.parquet','stock_panel_sha256')]:
        ck('frozen '+name,sha(CACHE/name)==receipt[key])
    features=pd.read_parquet(CACHE/'features.parquet');daily=pd.read_parquet(CACHE/'daily_expansion.parquet')
    panel=pd.read_parquet(CACHE/'stock_pe_panel.parquet')
    ck('no outcome columns in inputs',not set(['y','next_return','future_return','peak_date']).intersection(features.columns))
    ck('no infinite PE features',not np.isinf(features[PE].to_numpy()).any())
    ck('original feature row identity',len(features)==773934 and not features.duplicated(['row_id','threshold']).any())
    old=pd.read_parquet(V34/'expansion_features.parquet');cols=sum(ACTIVITY.values(),[])
    got=features[['row_id','threshold']+cols].merge(old[['row_id','threshold']+cols],on=['row_id','threshold'],suffixes=('_new','_old'),validate='one_to_one')
    ck('every original activity feature unchanged',all(np.allclose(got[c+'_new'],got[c+'_old'],equal_nan=True) for c in cols))
    x=pd.DataFrame({'a':np.linspace(8,60,1100),'b':np.linspace(15,9,1100)})
    full=stock_pe(x);altered=x.copy();altered.loc[800:]=np.nan
    prefix=stock_pe(altered)
    ck('future PE changes cannot alter past',all(np.allclose(full[c].iloc[:800],prefix[c].iloc[:800],equal_nan=True) for c in full))
    for w in [21,63,126,252]:
        ck('direct log ratio '+str(w),np.isclose(full['pe_change'+str(w)].iloc[799,0],np.log(x.a.iloc[799]/x.a.iloc[799-w])))
    bad=x.copy();bad.loc[790,'a']=-3;bad.loc[700,'b']=np.nan
    badf=stock_pe(bad)
    ck('negative and missing intervals not shrinkage',pd.isna(badf['pe_change21'].iloc[799,0]) and pd.isna(badf['pe_change126'].iloc[799,1]))
    ck('long rank formula',np.isclose(full['pe_rank756'].iloc[799,0],1.) and np.isclose(full['pe_rank504'].iloc[799,1],1/504))
    holes=pd.DataFrame({'a':np.full(1100,np.nan)});holes.loc[[0,21,1099],'a']=[10,20,30]
    ck('isolated snapshots never bridge gaps',all(v.isna().all().all() for v in stock_pe(holes).values()))
    members=pd.read_parquet(OLD.parent/'extension_v2/products/assignments.parquet',columns=['era','level','industry_code','month','security_id','unresolved'])
    sample=daily[daily.pe_change21.notna()&daily.date.between('2021-01-01','2024-09-30')].sample(16,random_state=35)
    for i,r in enumerate(sample.itertuples()):
        g=members[members.era.eq(r.era)&members.level.eq(r.level)&members.industry_code.eq(r.industry_code)&members.month.eq(r.date.to_period('M')-1)]
        t=panel.index.get_loc(r.date);v=panel.loc[:,g.security_id].iloc[t-21:t+1]
        positive=v.where(v.gt(0));valid=positive.notna().all(axis=0)
        values=np.log(positive.iloc[-1]/positive.iloc[0]).where(valid)
        n=len(g)+int(g.unresolved.max())
        ck('prior-members median '+str(i),len(g)>=5 and values.count()>=.8*n and np.isclose(values.median(),r.pe_change21,rtol=1e-6,atol=1e-7))
        ck('prior-members expansion breadth '+str(i),np.isclose(values.gt(0).sum()/values.count(),r.pe_breadth21))
        # Independently reconcile panel cells with sealed original daily vendor values.
        source=pd.read_parquet(PE_RELEASE/f'normalized/eastmoney/{r.date.date()}.parquet',columns=['security_id','vendor_pe_ttm']).set_index('security_id')
        wanted=source.vendor_pe_ttm.reindex(g.security_id).to_numpy()
        ck('sealed raw PE cell replay '+str(i),np.allclose(panel.loc[r.date,g.security_id].to_numpy(),wanted,equal_nan=True))
    for c in PE:ck('missingness control '+c,np.array_equal(features[c+'_missing'].to_numpy(),features[c].isna().astype(float).to_numpy()))
    ck('2017 has no filled PE',panel[panel.index.year==2017].isna().all().all())
    raw=panel.to_numpy();finite=raw[np.isfinite(raw)]
    js(OUT/'feature_validation.json',dict(status='PASS',checks=checks,checks_count=len(checks),
        known_pe_values=len(finite),positive=int((finite>0).sum()),negative=int((finite<0).sum()),
        pe_above_1000=int((finite>1000).sum()),near_zero_earnings_mechanism='UNRESOLVED_WITHOUT_ORIGINAL_PIT_EARNINGS',
        no_actual_historical_earnings_vintage_certification=True))
    print('PASS',len(checks),'feature checks',flush=True)

if __name__=='__main__':run()

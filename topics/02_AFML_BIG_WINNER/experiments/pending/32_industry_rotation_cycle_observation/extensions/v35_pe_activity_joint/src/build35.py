"""Single-source PE, fixed prior-month members; no outcomes read."""
import warnings
from common35 import *

def run():
    freeze()
    manifest_path=PE_RELEASE/'FULL_MANIFEST.json'
    complete=json.loads((PE_RELEASE/'COMPLETE.json').read_text())
    assert sha(manifest_path)==complete['full_manifest_sha256']
    manifest={x['relative_path']:x['sha256'] for x in json.loads(manifest_path.read_text())}
    assignment=OLD.parent/'extension_v2/products/assignments.parquet'
    members=pd.read_parquet(assignment,columns=['era','level','industry_code','month','security_id','unresolved'])
    assert sha(assignment)==json.loads((EXT/'v34_multiscale_expansion/outputs/feature_receipt.json').read_text())['source_hashes'][str(assignment)]
    sid_list=sorted(members.security_id.unique());sid_i={s:i for i,s in enumerate(sid_list)}
    calendar=pd.DatetimeIndex(pd.read_parquet(OLD/'CSI_ALL.parquet').index).sort_values()
    reads={str(assignment):sha(assignment),str(manifest_path):sha(manifest_path)}
    parts=[]
    for path in sorted((PE_RELEASE/'normalized/eastmoney').glob('*.parquet')):
        digest=sha(path);assert digest==manifest[str(path.relative_to(PE_RELEASE))]
        reads[str(path)]=digest
        f=pd.read_parquet(path,columns=['date','security_id','vendor_pe_ttm','known_at'])
        assert f.known_at.isna().all();parts.append(f.drop(columns='known_at'))
    f=pd.concat(parts,ignore_index=True);assert not f.duplicated(['date','security_id']).any()
    panel=f.pivot(index='date',columns='security_id',values='vendor_pe_ttm').reindex(index=calendar,columns=sid_list)
    del f,parts
    features=stock_pe(panel)
    prefix=stock_pe(panel.iloc[:1100,:4])
    assert all(np.allclose(prefix[c],features[c].iloc[:1100,:4],equal_nan=True) for c in prefix)
    arrays={k:v.to_numpy(np.float32) for k,v in features.items()};del features
    raw_pe=panel.to_numpy(np.float32)
    panel.to_parquet(CACHE/'stock_pe_panel.parquet')
    del panel
    month=calendar.to_period('M');rows=[]
    for (era,level,code,m),g in members.groupby(['era','level','industry_code','month'],sort=True):
        target=m+1
        if (era=='SW2014' and target>pd.Period('2021-11')) or (era=='SW2021' and target<pd.Period('2022-01')):continue
        days=np.flatnonzero(month==target)
        if not len(days):continue
        indexes=np.array([sid_i[s] for s in g.security_id]);n=len(indexes)+int(g.unresolved.max())
        r=pd.DataFrame(dict(date=calendar[days],era=era,level=level,industry_code=code,pe_members=n))
        raw=raw_pe[np.ix_(days,indexes)]
        r['pe_known_fraction']=np.isfinite(raw).sum(axis=1)/n
        r['pe_positive_fraction']=(raw>0).sum(axis=1)/n
        for name,values in arrays.items():
            v=values[np.ix_(days,indexes)];count=np.isfinite(v).sum(axis=1)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',RuntimeWarning);median=np.nanmedian(v,axis=1)
            median[(count<.8*n)|(n<5)]=np.nan;r[name]=median
            r[name+'_coverage']=count/n
        v=arrays['pe_change21'][np.ix_(days,indexes)];count=np.isfinite(v).sum(axis=1)
        r['pe_breadth21']=np.divide((v>0).sum(axis=1),count,out=np.full(len(days),np.nan),where=(count>=.8*n)&(n>=5))
        rows.append(r)
    raw=pd.concat(rows,ignore_index=True)
    v34receipt=json.loads((EXT/'v34_multiscale_expansion/outputs/feature_receipt.json').read_text())
    p=V34/'daily_expansion.parquet';assert sha(p)==v34receipt['daily_sha256'];reads[str(p)]=sha(p)
    daily=pd.read_parquet(p).drop(columns=['pe_change21','pe_change63'])
    daily=daily.merge(raw,on=['era','level','industry_code','date'],how='left',validate='one_to_one')
    daily.to_parquet(CACHE/'daily_expansion.parquet',index=False)
    p=V34/'expansion_features.parquet';assert sha(p)==v34receipt['features_sha256'];reads[str(p)]=sha(p)
    features=pd.read_parquet(p).drop(columns=['pe_change21','pe_change63'])
    features=features.merge(daily[KEY+['date']+PE+['pe_known_fraction','pe_positive_fraction']],on=KEY+['date'],how='left',validate='many_to_one')
    for c in PE:features[c+'_missing']=features[c].isna().astype(float)
    for k,v in ACTIVITY.items():features[k+'_joint_complete']=features[v+PE].notna().all(axis=1)
    assert not features.duplicated(['row_id','threshold']).any()
    assert not np.isinf(features[PE].to_numpy()).any()
    features.to_parquet(CACHE/'features.parquet',index=False)
    coverage=[]
    for (year,level),g in features.assign(year=features.date.dt.year).groupby(['year','level']):
        for c in PE+['pe_known_fraction','pe_positive_fraction']:
            coverage.append(dict(year=year,level=level,feature=c,rows=len(g),nonmissing=int(g[c].notna().sum()),mean=g[c].mean()))
        for k in ACTIVITY:coverage.append(dict(year=year,level=level,feature=k+'_joint_complete',rows=len(g),nonmissing=int(g[k+'_joint_complete'].sum())))
    pd.DataFrame(coverage).to_csv(OUT/'feature_coverage.csv',index=False)
    js(OUT/'feature_receipt.json',dict(source_hashes=reads,features_sha256=sha(CACHE/'features.parquet'),
        daily_sha256=sha(CACHE/'daily_expansion.parquet'),stock_panel_sha256=sha(CACHE/'stock_pe_panel.parquet'),
        rows=len(features),prefix_checks=len(prefix),code_sha256=sha(__file__),no_outcomes_used=True))
    print('FEATURES COMPLETE',len(features),flush=True)

if __name__=='__main__':run()

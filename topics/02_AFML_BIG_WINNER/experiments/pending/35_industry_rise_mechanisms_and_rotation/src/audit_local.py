"""Read-only source inventory and locally evidenced financial timing supplement."""
import pandas as pd
from common import *


def run():
    out=ROOT/'outputs/r01'; sources=[]
    daily=CACHE/'forecast_v5/daily_industries.parquet'
    expansion=CACHE/'joint_pe_v35/daily_expansion.parquet'
    receipts=[(daily,EP32/'extensions/v5_rdagent_onset_forecast/outputs/daily_input_audit.json','daily_sha256'),
              (expansion,EP32/'extensions/v35_pe_activity_joint/outputs/feature_receipt.json','daily_sha256')]
    for p,r,k in receipts:
        receipt=json.loads(r.read_text()); assert sha(p)==receipt[k], p
        sources.append(dict(path=str(r),sha256=sha(r),role='inherited provenance'))
    names=['forecast_v5/daily_industries.parquet','forecast_v5/CSI_ALL.parquet','joint_pe_v35/daily_expansion.parquet',
           'extension_v2/products/assignments.parquet','extension_v2/sources/legacy_catalog.parquet',
           'extension_v2/sources/legacy_members.parquet','industry_v1/L1.parquet','industry_v1/L2.parquet','industry_v1/L3.parquet','industry_v1/members.parquet']
    frames={}
    for name in names:
        p=CACHE/name; d=pd.read_parquet(p); frames[name]=d
        sources.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,rows=len(d),columns=list(d.columns),quality='Historical-proxy',role=name))
    d=frames[names[0]]; b=frames[names[1]]
    assert not d.duplicated(KEY+['date']).any()
    assert (d.membership_asof<=d.date).all()
    assert d.nav.gt(0).all()
    assert pd.DatetimeIndex(b.index).is_unique
    bad=0
    for _,g in d.groupby(KEY+['block']):
        bad+=int(g.sort_values('date').day_i.diff().dropna().ne(1).sum())
    assert bad==0
    catalog=frames['extension_v2/sources/legacy_catalog.parquet'].copy()
    catalog['era']='SW2014'
    cats=[catalog]
    for level in ['L1','L2','L3']:
        c=frames[f'industry_v1/{level}.parquet'].copy();c['era']='SW2021';cats.append(c)
    # Catalog codes are index_code; classification's industry_code is a different identifier.
    cat=pd.concat(cats,ignore_index=True)
    cat=cat.rename(columns={'industry_code':'classification_code','index_code':'industry_code'})
    counts=d.groupby(KEY).agg(rows=('date','size'),start=('date','min'),end=('date','max')).reset_index()
    cat=cat.merge(counts,on=KEY,how='left',validate='one_to_one')
    cat['basket_present']=cat.rows.notna();cat.to_csv(out/'industry_catalog.csv',index=False)
    cover=d.groupby(['era','level']).agg(rows=('date','size'),industries=('industry_code','nunique'),start=('date','min'),end=('date','max'))
    cover.to_csv(out/'daily_coverage.csv')
    # Preserve original versions and exact available times. Do not turn 15 facts into a whole-industry panel.
    p=Path('/home/xiaolv/.cache/a_share/ep30_d2/pit_v4/releases/a209472223fad6252a410f6910e132f1baa08242f4bb82d7c8055a51119d01e6/normalized/financial_reviewed_facts.parquet')
    f=pd.read_parquet(p); manifest=json.loads(Path(str(p)+'.manifest.json').read_text());assert sha(p)==manifest['sha256']
    assert f.known_at.notna().all() and f.record_id.is_unique
    evidence=[]
    for _,v in f[['source_path','source_sha256']].drop_duplicates().iterrows():
        q=Path(v.source_path); exists=q.exists()
        evidence.append(dict(path=str(q),exists=exists,hash_matches=exists and sha(q)==v.source_sha256))
    f['ep35_quality']='publication-timed partial facts; incomplete amendments; not representative'
    f.to_parquet(ROOT/'data/financial_timed_facts.parquet',index=False)
    sources.append(dict(path=str(p),sha256=sha(p),rows=len(f),role='partial publication-timed financial facts',quality='partial; no strict full-panel PIT claim'))
    js(out/'financial_timing_audit.json',dict(rows=len(f),issuers=f.security_id.nunique(),known_at_nonmissing=int(f.known_at.notna().sum()),
        quality_tiers=f.quality_tier.value_counts().to_dict(),source_evidence=evidence,all_amendments_complete=False,usable_for_industry_test=False,
        output_sha256=sha(ROOT/'data/financial_timed_facts.parquet')))
    js(out/'source_inventory.json',sources)
    js(out/'data_audit.json',dict(unique_industry_date=True,continuous_block_violations=bad,membership_not_future=True,
        benchmark_start=b.index.min(),benchmark_end=b.index.max(),quality='Historical-proxy',protocol_sha256=sha(ROOT/'protocols/r01.json'),
        catalog_counts=cat.groupby(['era','level']).size().to_dict(),price_baskets=cover.industries.to_dict()))
    print('AUDIT PASS',len(d),'daily rows;',len(f),'publication-timed facts')

if __name__=='__main__': run()

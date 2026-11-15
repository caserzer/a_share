"""Explain each missing selected path using the original audited stock partitions."""
import pandas as pd
from common import *


def run():
    audit=pd.read_csv(ROOT/'outputs/r04/missing_path_audit.csv',parse_dates=['entry','exit'])
    audit=audit.drop_duplicates(KEY+['entry','exit'])
    members=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet')
    d=pd.read_parquet(CACHE/'forecast_v5/daily_industries.parquet')
    days=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
    anchors=pd.Series(days,index=days.to_period('M')).groupby(level=0).max()
    rec=json.loads((EP32/'extensions/v5_rdagent_onset_forecast/outputs/daily_input_audit.json').read_text())
    paths={Path(k).stem:Path(k) for k in rec['reads'] if '/normalized/prices_qfq/' in k};cache={};rows=[]
    for r in audit.itertuples():
        required=days[(days>=r.entry)&(days<=r.exit)]
        existing=d[d.era.eq(r.era)&d.level.eq(r.level)&d.industry_code.eq(r.industry_code)].set_index('date')
        for date in required:
            if date in existing.index and pd.notna(existing.loc[date,'coverage']):continue
            mo=date.to_period('M')-1;anchor=anchors.get(mo)
            m=members[members.era.eq(r.era)&members.level.eq(r.level)&members.industry_code.eq(r.industry_code)&members.month.eq(mo)]
            n=len(m);den=n+(int(m.unresolved.max()) if n else 0)
            counts={'valid':0,'missing_price':0,'close_conflict':0,'chain_change':0}
            for sid in m.security_id:
                if sid not in cache:
                    path=paths[sid];assert sha(path)==rec['reads'][str(path)]
                    cache[sid]=pd.read_parquet(path,columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date')
                f=cache[sid].reindex([anchor,date])
                if f.qfq_close.isna().any() or not f.qfq_close.gt(0).all():counts['missing_price']+=1
                elif not f.close_conflict.eq(False).all():counts['close_conflict']+=1
                elif f.factor_chain_id.isna().any() or f.factor_chain_id.nunique()!=1:counts['chain_change']+=1
                else:counts['valid']+=1
            coverage=counts['valid']/den if den else np.nan
            reason='no_prior_members' if n==0 else 'fewer_than_5_members' if n<5 else 'below_80pct_valid_prices' if coverage<.8 else 'anchor_or_continuity_requires_review'
            rows.append(dict(era=r.era,level=r.level,industry_code=r.industry_code,date=date,entry=r.entry,exit=r.exit,
                prior_members=n,denominator=den,reconstructed_coverage=coverage,reason=reason,**counts))
    result=pd.DataFrame(rows).drop_duplicates(KEY+['date']);result.to_csv(ROOT/'outputs/r04/constituent_gap_diagnosis.csv',index=False)
    js(ROOT/'outputs/r04/constituent_gap_receipt.json',dict(source_partitions_checked=len(cache),diagnosed_industry_days=len(result),
        reasons=result.reason.value_counts().to_dict(),code_sha256=sha(__file__),
        action='retain gaps; no automatic relaxation, no edits to EP32 source baskets'))
    print(result.reason.value_counts().to_string())

if __name__=='__main__':run()

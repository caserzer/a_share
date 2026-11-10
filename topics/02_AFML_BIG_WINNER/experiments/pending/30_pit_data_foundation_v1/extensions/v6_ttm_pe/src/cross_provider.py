"""Report disagreements, never choose a source by downstream investment results."""
import pandas as pd
import numpy as np
from pe_common import OUT
from prepare_pe import BUILD

def main():
    parts=[]
    for path in sorted((BUILD/'normalized/baostock').glob('*.parquet')):
        other=BUILD/'normalized/eastmoney'/path.name
        if not other.exists():continue
        a=pd.read_parquet(path,columns=['date','security_id','vendor_pe_ttm'])
        b=pd.read_parquet(other,columns=['security_id','vendor_pe_ttm'])
        a=a[a.security_id.notna()];b=b[b.security_id.notna()]
        f=a.merge(b,on='security_id',suffixes=('_bao','_em'),validate='one_to_one')
        f['both_positive']=f.vendor_pe_ttm_bao.gt(0)&f.vendor_pe_ttm_em.gt(0)
        f['relative_difference']=(f.vendor_pe_ttm_em/f.vendor_pe_ttm_bao-1).abs().where(f.both_positive)
        f['sign_disagreement']=(np.sign(f.vendor_pe_ttm_bao)!=np.sign(f.vendor_pe_ttm_em)).where(f[['vendor_pe_ttm_bao','vendor_pe_ttm_em']].notna().all(axis=1))
        parts.append(f)
    f=pd.concat(parts,ignore_index=True)
    rows=[]
    for year,g in f.groupby(f.date.dt.year):
        v=g.relative_difference.dropna()
        rows.append(dict(year=year,paired_stock_days=len(g),positive_pairs=len(v),
            relative_difference_median=v.median(),relative_difference_p95=v.quantile(.95),
            fraction_above_5pct=v.gt(.05).mean(),sign_disagreement_rate=g.sign_disagreement.mean()))
    pd.DataFrame(rows).to_csv(OUT/'cross_provider_audit.csv',index=False)
    print(pd.DataFrame(rows).to_string(index=False),flush=True)

if __name__=='__main__':main()

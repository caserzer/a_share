"""Independent unit, publication-field, source-age and accounting checks for U2."""
from common import *
O=HERE/'results'
cov=pd.read_parquet(O/'signal_coverage.parquet')
base=cov.query('rule=="low_price"')
sc=pd.read_parquet(OUT800/'scores.parquet',columns=['instrument','signal_date'])
close=pd.read_parquet(LOCAL/'close.parquet')
i=close.index.get_indexer(sc.signal_date);j=close.columns.get_indexer(sc.instrument)
def take(name):
    f=pd.read_parquet(LOCAL/(name+'.parquet')).reindex_like(close)
    return f.to_numpy()[i,j]
ratio=close.to_numpy()[i,j]/take('qfq_close')
money=take('money');volume=take('volume')
avg=np.divide(money,volume,out=np.full_like(money,np.nan),where=volume>0)
lo=take('qfq_low')*ratio;hi=take('qfq_high')*ratio
ok=np.isfinite(avg)&np.isfinite(lo)&np.isfinite(hi)
outside=ok&((avg<lo-.011)|(avg>hi+.011))
receipts=[json.loads(f.read_text()) for f in sorted((PRIVATE36/'style_caps_20261117').glob('*.receipt.json'))]
susp=pd.read_parquet(LOCAL/'suspensions/daily.parquet')
limits=pd.read_parquet(LOCAL/'limits/daily.parquet')
d=pd.read_parquet(O/'accounts.parquet');o=pd.read_parquet(O/'net_orders.parquet')
order_fee=(o.net_order.clip(lower=0)*.001-o.net_order.clip(upper=0)*.002).groupby([o.arm,o.segment,o.date]).sum()
strict=d[d.mark=='strict'].set_index(['arm','segment','date'])
error=(order_fee.reindex(strict.index,fill_value=0)-strict.fee).abs().max()
assert error<1e-10
f=PRIVATE36/'suspensions/20230601_20230630.json'
raw=json.loads(f.read_text())
out=dict(eligible_rows=len(sc),money_volume_units_comparable=int(ok.sum()),outside_ohlc_plus_0011=int(outside.sum()),
         share_snapshot_receipts=len(receipts),first_vintage_certified=sum(r['first_vintage_certified'] for r in receipts),
         known_at_nonmissing=sum(r['known_at'] is not None for r in receipts),
         prior_snapshot_age_calendar_days=base.share_age_days.describe().to_dict(),
         announcement_raw_fields=raw['data']['fields'],suspension_fields=susp.columns.tolist(),suspension_rows=len(susp),
         limit_fields=limits.columns.tolist(),limit_rows=len(limits),max_abs_order_fee_residual=error,
         snapshot_receipt_digest=hashlib.sha256(''.join(sorted(r['sha256'] for r in receipts)).encode()).hexdigest(),
         actual_missing_strict_path=pd.read_csv(O/'gaps.csv').to_dict('records'),
         script_sha256=sha(Path(__file__)))
(O/'independent_audit.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='actual_missing_strict_path'},ensure_ascii=False,indent=2))

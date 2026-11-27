from fund_panel import *
import gzip,json
def audit():
    import pyarrow.parquet as pq
    ep35=next(ROOT.parent.glob('35_*'))
    paths=[ep35/'data/financial_archive_all_market.parquet',ep35/'outputs/r251/file_inventory.json',ep35/'outputs/r251/summary.json',ep35/'outputs/cnequity_fundamental_review_20261114/reviewed_financial_cells.json',Path.home()/'.cache/a_share/ep30_d2/vintages/facts.parquet',Path.home()/'.cache/a_share/ep30_d2/pit_v4/normalized/financial_reviewed_facts.parquet',Path.home()/'.cache/a_share/ep30_d2/pit_v4/normalized/financial_version_chains.parquet']
    r=[]
    for p in paths:
        count=pq.ParquetFile(p).metadata.num_rows if p.suffix=='.parquet' else len(json.loads(p.read_text()))
        r.append((str(p),count,hashlib.sha256(p.read_bytes()).hexdigest()))
    reports=json.loads((ep35/'outputs/cnequity_fundamental_review_20261114/original_receipts.json').read_text())
    for x in reports:
        p=ep35/'data/cnequity_fundamental_review_20261114'/x['symbol']/'2026H1.pdf'
        dig=hashlib.sha256(p.read_bytes()).hexdigest();assert dig==x['pdf_sha256'];r.append((str(p),x.get('parsed_rows',0),dig))
    pd.DataFrame(r,columns=['path','rows_or_entries','sha256']).to_csv(F/'prior_sources.csv',index=False)
    facts=pd.read_parquet(F/'versions.parquet');strict=pd.read_parquet(F/'strict/versions.parquet')
    fields=sum(tables.values(),[])
    rows=pd.concat([facts.groupby(['ts_code','end_date'])[fields].count().add_prefix('vendor_'),strict.groupby(['ts_code','end_date'])[fields].count().add_prefix('original_')],axis=1)
    universe=sorted(facts.ts_code.unique());quarters=[q.end_time.strftime('%Y%m%d') for q in pd.period_range('2013Q1','2026Q3',freq='Q')]
    all_names=pd.read_csv(F/'events_input_names.csv').ts_code.tolist()
    rows.reindex(pd.MultiIndex.from_product([all_names,quarters],names=['ts_code','end_date'])).fillna(0).astype(int).to_parquet(F/'F1_field_inventory.parquet')
    source=[]
    for p in sorted((src/'raw').glob('*.json.gz')):
        record=json.loads(gzip.decompress(p.read_bytes()));source.append((p.name,record['api'],json.dumps(record['params'],sort_keys=True),record['observed_at'],record['sha256'],record['code'],len(record['data'].get('items') or [])))
    pd.DataFrame(source,columns='file api params observed_at response_sha256 status rows'.split()).to_csv(F/'acquisition.csv',index=False)
    x=json.loads((ep35/'outputs/cnequity_fundamental_review_20261114/reviewed_financial_cells.json').read_text())
    out=[]
    for row in x:
        col={'revenue':'revenue','net_profit':'n_income_attr_p','net_cashflow_operating':'n_cashflow_act'}.get(row['item_code'])
        if col is None:continue
        f=facts[(facts.ts_code==row['symbol'])&(facts.end_date=='20260630')];delta=(f[col]-row['item_value']).abs().min() if len(f) else np.nan
        out.append((row['symbol'],row['item_code'],row['item_value'],row['pdf_page'],row['announce_date'],delta))
    pd.DataFrame(out,columns='ticker field original page date vendor_abs_difference'.split()).to_csv(F/'original_crosscheck.csv',index=False)
if __name__=='__main__':audit()

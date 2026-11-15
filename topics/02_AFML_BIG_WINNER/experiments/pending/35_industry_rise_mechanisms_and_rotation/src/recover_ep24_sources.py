"""Recover locally archived numerical sources; no network, labels or model fitting."""
import gzip
import pandas as pd
from common import *
EP24=ROOT.parent/'24_conditional_return_distribution_exploration'

def run():
    out=ROOT/'outputs/r11';out.mkdir(exist_ok=True)
    dest=EP24/'outputs/r19_eps_expectations';cache=EP24/'outputs/local_cache/r19_eps_html'
    audit=json.loads((dest/'extraction_validation.json').read_text())
    assert sha(EP24/'src/parse_eps_forecasts.py')==audit['parser_sha256']
    source=dest/'validated_extractions.parquet';raw=pd.read_parquet(source)
    meta=pd.read_parquet(dest/'selected_reports.parquet')[['infoCode','orgCode']]
    assert not raw.infoCode.duplicated().any()
    raw=raw.merge(meta,on='infoCode',validate='one_to_one')
    values=[];receipts=[]
    for row in raw.itertuples(index=False):
        path=cache/f'{row.infoCode}.html.gz';receipt_path=cache/f'{row.infoCode}.receipt.json'
        receipt=json.loads(receipt_path.read_text());digest=hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()
        assert digest==row.raw_sha256==receipt['sha256']
        receipts.append(dict(infoCode=row.infoCode,raw_path=str(path),raw_sha256=digest,receipt_sha256=sha(receipt_path),
            fetched_at=receipt['fetched_at'],url=receipt['url'],status=row.status))
        for basis,conflict in [('forecasts',row.eps_conflict),('profit_forecasts',row.profit_conflict)]:
            if pd.isna(conflict) or bool(conflict):continue
            for year,value in json.loads(getattr(row,basis)).items():
                if row.infoCode=='AP202504281663751625' and basis=='forecasts' and year=='2027':
                    assert digest=='70d0346322863dfeb89079fc3e181f928ac573270c938a8c5567597d28834077'
                    continue
                assert np.isfinite(value)
                values.append(dict(infoCode=row.infoCode,stock_code=row.stockCode,broker=row.orgCode,fiscal_year=int(year),
                    basis='eps_cny_per_share' if basis=='forecasts' else 'profit_cny',value=float(value),
                    publication_proxy_date=row.available_date,published_date=row.publishDate,body_date=row.source_date,
                    archived_at=receipt['fetched_at'],raw_sha256=digest,quality='Historical-proxy extracted original-body value'))
    long=pd.DataFrame(values);long['publication_proxy_date']=pd.to_datetime(long.publication_proxy_date)
    long.to_parquet(ROOT/'data/r11_analyst_forecasts.parquet',index=False)
    pd.DataFrame(receipts).to_parquet(ROOT/'data/r11_analyst_source_receipts.parquet',index=False)
    long.groupby(['basis','fiscal_year']).agg(values=('value','size'),companies=('stock_code','nunique'),reports=('infoCode','nunique')).to_csv(out/'forecast_coverage.csv')
    macro_manifest=EP24/'outputs/r33_domestic_macro/source_manifest.json';manifest=json.loads(macro_manifest.read_text())
    fields={'RPT_ECONOMY_PMI':{'MAKE_INDEX':('manufacturing_pmi','index'),'NMAKE_INDEX':('nonmanufacturing_pmi','index')},
      'RPT_ECONOMY_CURRENCY_SUPPLY':{'BASIC_CURRENCY':('m2_stock','CNY_100million'),'BASIC_CURRENCY_SAME':('m2_yoy','percent')},
      'RPT_ECONOMY_CPI':{'NATIONAL_SAME':('cpi_yoy','percent')},'RPT_ECONOMY_PPI':{'BASE_SAME':('ppi_yoy','percent')},
      'tsf':{'tiosfs':('tsf_flow','CNY_100million'),'rmblaon':('tsf_real_economy_rmb_loan','CNY_100million')}}
    macro=[]
    for item in manifest['series']+manifest['official']:assert sha(item['path'])==item['sha256']
    for item in manifest['series']:
        doc=json.loads(Path(item['path']).read_text());table=pd.DataFrame(doc if item['name']=='tsf' else doc['result']['data'])
        dates=pd.to_datetime(table['date'],format='%Y%m') if item['name']=='tsf' else pd.to_datetime(table.REPORT_DATE)
        assert dates.dt.to_period('M').is_unique
        for field,(metric,unit) in fields[item['name']].items():
            for month,value in zip(dates,pd.to_numeric(table[field],errors='raise')):
                end=month.to_period('M').end_time.normalize()
                macro.append(dict(metric=metric,unit=unit,economic_month=str(month.to_period('M')),value=value,
                    assumed_available_date=end+pd.Timedelta(days=45),verified_release_date=None,
                    source_path=item['path'],source_sha256=item['sha256'],quality='Historical-proxy; 45-day assumed lag; revisions possible'))
    macro=pd.DataFrame(macro);macro.to_parquet(ROOT/'data/r11_macro_observations.parquet',index=False)
    macro.groupby('metric').agg(rows=('value','size'),first=('economic_month','min'),last=('economic_month','max')).to_csv(out/'macro_coverage.csv')
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r11.json'),code_sha256=sha(__file__),
       source_extraction_sha256=sha(source),source_audit_sha256=sha(dest/'extraction_validation.json'),
       source_metadata_sha256=sha(dest/'selected_reports.parquet'),macro_manifest_sha256=sha(macro_manifest),
       verified_html_files=len(receipts),forecast_values=len(long),forecast_companies=long.stock_code.nunique(),
       macro_observations=len(macro),macro_raw_files_verified=13,
       publication_range=[str(long.publication_proxy_date.min()),str(long.publication_proxy_date.max())],
       archived_range=[min(x['fetched_at'] for x in receipts),max(x['fetched_at'] for x in receipts)],
       limitations=['EP24 monthly-latest report selection, not complete consensus','no immutable original release version certification','macro release dates not verified month by month','no predictive test run']))
    print(json.dumps(dict(reports=len(receipts),forecast_values=len(long),companies=int(long.stock_code.nunique()),macro_rows=len(macro))),flush=True)
if __name__=='__main__':run()

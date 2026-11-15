"""Systematic local body/units/year audit; no inference of corrected forecasts."""
import gzip,importlib.util,re
import pandas as pd
from bs4 import BeautifulSoup
from common import *
EP24=ROOT.parent/'24_conditional_return_distribution_exploration'
spec=importlib.util.spec_from_file_location('frozen_eps_parser',EP24/'src/parse_eps_forecasts.py');parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
DIMENSION=re.compile(r'^(?:[/／](?:吨|股|公斤|千克|克|千瓦|平方米|件|台)|每(?:吨|股|公斤|千克|平方米))')
SHARES=re.compile(r'送转|转增|除权|股本|摊薄|稀释')


def scan_paragraph(text,year):
 normalized=parser.normalize(text);flags=[]
 profits=parser.parse_profit_paragraph(text,year);eps=parser.parse_paragraph(text,year)
 for marker in parser.PROFIT_INDICATOR.finditer(normalized):
  prefix=normalized[max(0,marker.start()-450):marker.start()];years=parser.bound_years(prefix,year);match=parser.PROFIT_VALUES.match(normalized[marker.end():])
  if not years or match is None:continue
  after=normalized[marker.end()+match.end():]
  if not DIMENSION.match(after):continue
  nums=re.findall(parser.NUMBER,match.group('values'));units=re.findall(parser.UNIT,match.group('values'))
  if len(nums)!=len(years) or len(set(units))!=1:continue
  candidate=dict(zip(years,[float(x)*parser.MULTIPLIER[units[0]] for x in nums]))
  if candidate in profits:flags.append(dict(kind='profit_noncurrency_dimension',basis='profit_cny',candidate_values=candidate,suffix=after[:20]))
 if profits and eps:
  py=set().union(*(set(x) for x in profits));ey=set().union(*(set(x) for x in eps))
  if py!=ey:flags.append(dict(kind='cross_basis_year_sets',basis='review_both',profit_years=sorted(py),eps_years=sorted(ey)))
 if eps and SHARES.search(normalized):flags.append(dict(kind='share_basis_language',basis='eps_cny_per_share'))
 return flags


def run():
 out=ROOT/'outputs/r27';out.mkdir(exist_ok=True)
 source=EP24/'outputs/r19_eps_expectations/validated_extractions.parquet';raw=pd.read_parquet(source)
 forecast=ROOT/'data/r11_analyst_forecasts.parquet';values=pd.read_parquet(forecast);lookup={key:g for key,g in values.groupby('infoCode')}
 source_receipt=json.loads((ROOT/'outputs/r11/receipt.json').read_text());assert sha(source)==source_receipt['source_extraction_sha256']
 flags=[];support=[];files=[]
 for n,row in enumerate(raw.itertuples(index=False),1):
  path=EP24/f'outputs/local_cache/r19_eps_html/{row.infoCode}.html.gz';html=gzip.decompress(path.read_bytes());digest=hashlib.sha256(html).hexdigest();assert digest==row.raw_sha256
  decoded=html.decode('utf-8');parsed=parser.parse_report(decoded,str(row.publishDate),expected_stock=row.stockCode)
  files.append(dict(infoCode=row.infoCode,raw_sha256=digest,path=str(path),parsed_status=parsed['status']))
  for value in lookup.get(row.infoCode,pd.DataFrame()).itertuples(index=False):
   field='forecasts' if value.basis=='eps_cny_per_share' else 'profit_forecasts';match=parsed.get(field,{}).get(value.fiscal_year,np.nan)
   support.append(dict(infoCode=row.infoCode,basis=value.basis,fiscal_year=value.fiscal_year,value=value.value,reparsed_value=match,supported=bool(np.isclose(match,value.value,rtol=1e-12,atol=1e-8)),raw_sha256=digest))
  body=BeautifulSoup(decoded,'html.parser').select_one('#ctx-content')
  if body is not None:
   for i,p in enumerate(body.find_all('p')):
    text=p.get_text(' ',strip=True)
    for flag in scan_paragraph(text,int(str(parsed.get('source_date',row.publishDate))[:4])):
     flags.append(dict(infoCode=row.infoCode,stock_code=row.stockCode,paragraph=i,raw_sha256=digest,text=text,**flag))
  if n%2000==0:print('scanned',n,flush=True)
 pd.DataFrame(support).to_parquet(ROOT/'data/r27_value_support.parquet',index=False)
 js(out/'review_flags.json',flags);pd.DataFrame(files).to_csv(out/'source_files.csv',index=False)
 kinds=pd.Series([f['kind'] for f in flags]).value_counts().to_dict()
 js(out/'receipt.json',dict(status='SYSTEMATIC_SCREEN_NOT_SOURCE_CERTIFICATION',html_files=len(files),values_checked=len(support),unsupported_values=sum(not x['supported'] for x in support),flags_by_kind=kinds,flagged_reports=len({f['infoCode'] for f in flags}),reads={str(p):sha(p) for p in [source,forecast,EP24/'src/parse_eps_forecasts.py',ROOT/'protocols/r27.json',Path(__file__)]},outputs={str(p):sha(p) for p in [ROOT/'data/r27_value_support.parquet',out/'review_flags.json',out/'source_files.csv']},limitation='frozen parser agreement does not prove source units/FY/share bases correct; flags require review'))
 print(json.dumps(dict(flags=kinds,unsupported=sum(not x['supported'] for x in support)),ensure_ascii=False),flush=True)

if __name__=='__main__':run()

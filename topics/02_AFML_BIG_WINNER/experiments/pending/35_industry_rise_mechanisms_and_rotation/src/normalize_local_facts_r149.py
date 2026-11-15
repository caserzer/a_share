"""Local reviewed issuer facts with explicit period, basis and acquisition boundaries."""
from datetime import datetime,timezone
from decimal import Decimal
import pandas as pd
from common import *
FIELDS={'revenue':('income','revenue','flow','consolidated_revenue'),'net_profit':('income','n_income_attr_p','flow','parent_attributable_net_profit'),'net_cash_operate':('cashflow','n_cashflow_act','flow','consolidated_operating_cashflow'),'capex':('cashflow','c_pay_acq_const_fiolta','flow','positive_cash_expenditure_for_long_term_assets'),'total_assets':('balance','total_assets','stock','consolidated_assets'),'total_liabilities':('balance','total_liab','stock','consolidated_liabilities'),'total_equity':('balance','total_hldr_eqy_inc_min_int','stock','consolidated_equity_including_minority')}

def run():
 out=ROOT/'outputs/r149';out.mkdir(exist_ok=True);base=ROOT/'outputs/cnequity_fundamental_review_20261114';manifest=json.loads((base/'manifest.json').read_text());checks=[]
 for rel,h in manifest.items():assert sha(ROOT/rel)==h,rel;checks.append(dict(path=rel,sha256=h))
 cells=json.loads((base/'reviewed_financial_cells.json').read_text());receipts={x['symbol']:x for x in json.loads((base/'original_receipts.json').read_text())};calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index).sort_values();raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');rows=[];comparisons=[];now=datetime.now(timezone.utc).isoformat()
 for c in cells:
  receipt=receipts[c['symbol']];statement,field,kind,basis=FIELDS[c['item_code']];assert statement==c['statement_type'] and c['report_period']=='2026Q2';pdf=f"data/cnequity_fundamental_review_20261114/{c['symbol']}/2026H1.pdf";assert manifest[pdf]==receipt['pdf_sha256'];published=pd.Timestamp(c['announce_date']);i=calendar.searchsorted(published,side='right');proxy=str(calendar[i].date()) if i<len(calendar) else None
  rows.append(dict(symbol=c['symbol'],item_code=c['item_code'],canonical_field=field,statement_type=statement,amount_cny=c['item_value'],period_start='2026-01-01' if kind=='flow' else None,period_end='2026-06-30',period_kind='half_year_cumulative' if kind=='flow' else 'point_in_time_balance',basis=basis,announce_date=c['announce_date'],publication_date_precision='date_only',next_exchange_session_proxy=proxy,original_pdf_fetched_at=receipt['fetched_at'],normalized_at=now,source_pdf=pdf,source_pdf_sha256=manifest[pdf],source_pdf_page=c['pdf_page'],source_unit_multiplier=c['unit_multiplier'],source_reported_number=c['reported_number'],source_sign_rule=c['sign_rule'],source_review_status=c['status'],auto_pdf_parser_status='partial_nonempty' if receipt.get('parsed_rows',0) else 'empty_or_failed',strict_pit_certified=False,historical_model_admitted=False,provenance='existing local manual cell review; not newly visually reviewed in R149'))
  q=raw[raw.ts_code.eq(c['symbol'])&raw.end_date.eq(pd.Timestamp('2026-06-30'))]
  vals=sorted(q[field].dropna().unique().tolist()) if field in q else [];match=any(abs(v-c['item_value'])<=.02 for v in vals)
  comparisons.append(dict(symbol=c['symbol'],item_code=c['item_code'],canonical_field=field,old_archive_values=vals,new_amount=c['item_value'],status='matching_existing_amount' if match else 'field_absent_in_archive_schema' if field not in raw else 'no_existing_value' if not vals else 'different_existing_values'))
 js(out/'candidate_facts.json',rows);js(out/'archive_comparison.json',comparisons)
 release=json.loads((out/'original_entry_snapshot.json').read_text());legacy=[]
 for name,item in release['unreviewed_legacy_routes'].items():
  p=ROOT/item['path'];h=sha(p);legacy.append(dict(key=name,path=item['path'],snapshot_sha256=item['sha256'],current_sha256=h,hash_matches_snapshot=h==item['sha256'],status='original_route_integrity_checked_not_revalidated',bytes=p.stat().st_size))
 js(out/'remaining_original_routes.json',legacy)
 js(out/'receipt.json',dict(status='NORMALIZED_CANDIDATES_NOT_MODEL_ADOPTED',facts=len(rows),issuers=len(receipts),source_manifest_files_checked=len(checks),source_manifest_sha256=sha(base/'manifest.json'),original_routes=len(legacy),comparisons=pd.Series([x['status'] for x in comparisons]).value_counts().to_dict(),reads={str(p):sha(p) for p in [base/'reviewed_financial_cells.json',base/'original_receipts.json',base/'manifest.json',out/'original_entry_snapshot.json',ROOT/'data/financial_archive_all_market.parquet',CACHE/'forecast_v5/CSI_ALL.parquet',ROOT/'protocols/r149.json',Path(__file__)]},outputs={p.name:sha(p) for p in [out/'candidate_facts.json',out/'archive_comparison.json',out/'remaining_original_routes.json']}))
 print((out/'receipt.json').read_text())
if __name__=='__main__':run()

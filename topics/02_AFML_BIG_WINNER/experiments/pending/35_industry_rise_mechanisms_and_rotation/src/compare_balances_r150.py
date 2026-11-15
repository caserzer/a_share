"""Reviewed local comparative balances; descriptive only, never backdated."""
from decimal import Decimal as D
from common import *

def run():
 out=ROOT/'outputs/r150';raw=json.loads((out/'extraction_candidates.json').read_text());rows=[];summaries=[]
 for x in raw:
  index=1 if x['item_code']=='total_equity' and x['symbol'] in ['003021.SZ','600955.SH','605123.SH'] else 0
  page,prior,context=x['all_matches'][index]
  assert sha(ROOT/x['source_pdf'])==x['source_pdf_sha256']
  row={**x,'page':page,'prior_reported':prior,'context':context,'selected_match_index':index,'prior_cny':str(D(prior.replace(',',''))*D(str(x['unit']))),'current_cny':str(D(str(x['current']))),'prior_period_end':'2025-12-31','current_period_end':'2026-06-30','comparison_basis':'prior_year_end_as_presented_in_2026_half_year_report','consolidation':'group_including_minority','prior_first_publication_verified':False,'strict_pit_certified':False,'historical_model_admitted':False,'visual_review':'full header and total pages inspected; amount independently text checked'}
  row['review_images']={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'data/r150_review').glob(x['symbol']+'_*.png'))}
  rows.append(row)
 for symbol in sorted({x['symbol'] for x in rows}):
  q={x['item_code']:x for x in rows if x['symbol']==symbol};a,l,e=[q[k] for k in ['total_assets','total_liabilities','total_equity']]
  now=[D(x['current_cny']) for x in [a,l,e]];old=[D(x['prior_cny']) for x in [a,l,e]]
  for v in [now,old]:assert abs(v[0]-v[1]-v[2])<=D('.02')
  summaries.append(dict(symbol=symbol,industry_comparable=False,issuer_type='bank' if symbol=='002948.SZ' else 'nonbank',asset_change_pct=float((now[0]/old[0]-1)*100),liability_change_pct=float((now[1]/old[1]-1)*100),equity_change_pct=float((now[2]/old[2]-1)*100),prior_liabilities_assets_pct=float(old[1]/old[0]*100),current_liabilities_assets_pct=float(now[1]/now[0]*100),leverage_change_pp=float((now[1]/now[0]-old[1]/old[0])*100),causal_attribution='not_established',predictive_evidence=False))
 js(out/'reviewed_comparatives.json',rows);js(out/'issuer_changes.json',summaries)
 js(out/'receipt.json',dict(status='DESCRIPTIVE_COMPARATIVES_NOT_MODEL_ADOPTED',facts=30,issuers=10,visual_sheets_reviewed=10,ambiguous_equity_row_selections_corrected=3,inputs={str(p.relative_to(ROOT)):sha(p) for p in [out/'extraction_candidates.json',ROOT/'outputs/r149/candidate_facts.json',ROOT/'protocols/r150.json']},outputs={p.name:sha(p) for p in [out/'reviewed_comparatives.json',out/'issuer_changes.json']}))
 print(json.dumps(summaries,ensure_ascii=False,indent=2))
if __name__=='__main__':run()

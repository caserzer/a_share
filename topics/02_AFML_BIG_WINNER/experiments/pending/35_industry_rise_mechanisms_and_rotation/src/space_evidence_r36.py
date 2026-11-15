import pandas as pd
from common import *
from battery_evidence_r35 import canonical
BASE=Path('/home/xiaolv/code/golden_loop_artifacts/themes/中国商业航天规模化兑现--theme-ee71d9aa-d8ae-4ed2-b75c-e8da6f51c2e5')
def run():
 out=ROOT/'outputs/r36';out.mkdir(exist_ok=True);s=json.loads((BASE/'state.json').read_text());ev=[json.loads(x) for x in (BASE/'evidence.jsonl').read_text().splitlines() if x.strip()];docs={d['document_id']:d for d in s['documents']};assert len(docs)==len(s['documents'])
 files={str(p):sha(p) for p in BASE.rglob('*') if p.is_file()};hashpaths={}
 for path,h in files.items():hashpaths.setdefault(h,[]).append(path)
 rows=[]
 for e in ev:
  d=docs.get(e.get('document_id'),{});pub=pd.to_datetime(d.get('published_at'),utc=True);end=pd.to_datetime(e.get('period_end'),utc=True);eff=pd.to_datetime(e.get('effective_at'),utc=True);text=' '.join(str(e.get(k) or '') for k in ['original_quote','page_or_table','evidence_id'])
  rows.append(dict(evidence_id=e['evidence_id'],document_id=e.get('document_id'),document_found=bool(d),url=canonical(d.get('canonical_url')),quote=e.get('original_quote'),period_end=e.get('period_end'),published_at=d.get('published_at'),retrieved_at=d.get('retrieved_at'),effective_at=e.get('effective_at'),content_hash=d.get('content_hash'),local_raw_hash_match=bool(hashpaths.get(d.get('content_hash'))),period_after_publication=bool(pd.notna(pub) and pd.notna(end) and end>pub),effective_before_publication=bool(pd.notna(pub) and pd.notna(eff) and eff<pub),plan_keyword=any(w in text for w in ['计划','预计','拟','目标','将于','plan','guidance']),ep35_status='local_assertion_unverified'))
 a=pd.DataFrame(rows);a.to_csv(out/'evidence_audit.csv',index=False)
 obs=[]
 for x in s['metric_observations']:
  refs=[r for r in rows if r['evidence_id'] in x.get('evidence_ids',[])];q=dict(x);q['ep35_original_quality']=x.get('quality_flag');q['ep35_raw_verified']=bool(refs) and all(r['local_raw_hash_match'] for r in refs);q['ep35_numeric_factor_eligible']=False;obs.append(q)
 js(out/'numeric_observations.json',obs);o=pd.DataFrame(obs);groups=o.groupby(['metric_id','entity_id','normalized_unit','statement_class'],dropna=False).agg(observations=('observation_id','size'),distinct_periods=('period_end','nunique')).reset_index();groups.to_csv(out/'series_coverage.csv',index=False)
 d=pd.DataFrame(s['documents']);d['url']=d.canonical_url.map(canonical);d.groupby('url').agg(documents=('document_id','size')).query('documents>1').to_csv(out/'repeated_urls.csv')
 js(out/'local_file_manifest.json',files)
 summary=dict(evidence_rows=len(ev),document_rows=len(d),unique_urls=d.url.nunique(),missing_document_refs=int((~a.document_found).sum()),documents_missing_hash=int(d.content_hash.isna().sum()),documents_with_hash=int(d.content_hash.notna().sum()),document_hashes_matched_to_theme_files=sum(bool(hashpaths.get(x)) for x in d.content_hash.dropna()),effective_before_publication=int(a.effective_before_publication.sum()),period_after_publication_flags=int(a.period_after_publication.sum()),plan_keyword_flags=int(a.plan_keyword.sum()),numeric_observations=len(obs),metric_entity_unit_groups=len(groups),max_distinct_periods=int(groups.distinct_periods.max()),predictive_series_promoted=0)
 js(out/'receipt.json',dict(summary=summary,reads={str(p):sha(p) for p in [BASE/'state.json',BASE/'evidence.jsonl',ROOT/'protocols/r36.json',Path(__file__)]},scope='raw-byte search limited to this theme directory, not global absence proof'))
 print(json.dumps(summary,ensure_ascii=False));print(groups.to_string(index=False))
if __name__=='__main__':run()

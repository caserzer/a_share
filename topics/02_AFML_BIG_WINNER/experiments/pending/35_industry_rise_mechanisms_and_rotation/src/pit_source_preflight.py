"""Check relevance and bytes before promoting local candidates to industry PIT facts."""
import pandas as pd
from common import *


def run():
    out=ROOT/'outputs/r08';base=Path('/home/xiaolv/.cache/a_share/ep30_d2/pit_v4')
    candidate=base/'normalized/financial_value_candidates.parquet';reviewed=base/'normalized/financial_reviewed_facts.parquet'
    assignment=CACHE/'extension_v2/products/assignments.parquet'
    c=pd.read_parquet(candidate);f=pd.read_parquet(reviewed);m=pd.read_parquet(assignment,columns=['security_id','date'])
    last=m.groupby('security_id').date.max();c['last_member_date']=c.security_id.map(last);c['date_available']=pd.to_datetime(c.candidate_known_at).dt.tz_localize(None)
    c['already_reviewed_issuer']=c.security_id.isin(f.security_id);c['active_at_or_after_available']=c.date_available.le(c.last_member_date)
    c['relevance_reason']=np.where(c.last_member_date.isna(),'no_matching_membership',np.where(c.active_at_or_after_available,'later_membership_exists','available_after_last_observed_membership'))
    c[['security_id','art_code','report_period','date_available','last_member_date','already_reviewed_issuer','active_at_or_after_available','relevance_reason']].drop_duplicates().to_csv(out/'candidate_relevance.csv',index=False)
    source=Path('/home/xiaolv/code/golden_loop_artifacts/a_share_market_radar/reports/fixed_industry_pool/20261010-data-v1')
    p=source/'operating_observations.csv';ops=pd.read_csv(p);manifest=json.loads((source/'manifest.json').read_text());assert sha(p)==manifest['files'][p.name]
    ops['ep35_status']='unverified_original_bytes_local; not promoted to numeric predictive factor'
    ops.to_csv(out/'mechanism_evidence_staging.csv',index=False)
    docs=json.loads((source/'document_receipts.json').read_text());requests=[]
    for row in docs:
        if row['status']!='FETCHED':continue
        requests.append(dict(ts_code=row['ts_code'],url=row['url'],expected_sha256=row['sha256'],expected_bytes=row['bytes'],
            purpose='verify existing operating observations against complete original PDF pages',authorization='required_by_goal_section_3; not yet downloaded',
            cost='public URL, no paid purchase authorized',destination='EP35 data/primary_documents, gitignored',acceptance='SHA256 matches archived receipt; otherwise new version review'))
    js(out/'external_document_request.json',dict(documents=requests,total_expected_bytes=sum(x['expected_bytes'] for x in requests),
        permission_basis='GOAL.md section3: 数据采购、外部采集、部署及对外发布不由本目标文件自动授权',
        local_alternative='continue R06/R07 and other local source/label/industry checks; do not block entire research'))
    js(out/'receipt.json',dict(code_sha256=sha(__file__),sources={str(p):sha(p) for p in [candidate,reviewed,assignment,source/'operating_observations.csv',source/'document_receipts.json']},
        candidate_rows=len(c),active_candidate_rows_total=int(c.active_at_or_after_available.sum()),unreviewed_active_candidate_rows=int((~c.already_reviewed_issuer&c.active_at_or_after_available).sum()),
        operating_observations=len(ops),original_documents=len(requests),promoted_facts=0,
        decision='do not add post-retirement facts to active industry historical panel merely to increase PIT count'))
    print('PIT PREFLIGHT',len(c),'candidates;',int((~c.already_reviewed_issuer&c.active_at_or_after_available).sum()),'unreviewed active rows;',len(requests),'primary files awaiting permission')

if __name__=='__main__':run()

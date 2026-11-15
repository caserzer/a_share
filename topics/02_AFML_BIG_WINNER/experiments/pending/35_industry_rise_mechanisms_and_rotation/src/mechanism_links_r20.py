"""Attach reviewed issuer facts to time-specific membership; never infer sector mechanisms."""
import pandas as pd
from common import *

CLOCKS=['publication_proxy','inherited_archive','ep35_acquisition']
MEMBER_COLUMNS=KEY+['month','date','instrument','security_id','unresolved']
DIMENSIONS={
 'op-fiber-growth':('business_revenue_and_margin','reported_expansion'),
 'op-auto-sales':('business_revenue','reported_expansion'),
 'op-auto-margin':('business_margin','near_flat_increase'),
 'op-auto-ev-margin':('business_margin','reported_deterioration'),
 'op-broker-aum':('client_asset_stock','reported_scale_not_flow'),
 'op-broker-client-assets':('client_asset_stock','reported_expansion_not_flow'),
 'op-lithium-margin':('business_margin','level_only_not_growth'),
 'op-lithium-ocf':('cash_flow','positive_level_not_trend'),
 'op-office-365':('business_revenue','reported_expansion'),
 'op-office-core':('company_adjusted_profit','reported_expansion_non_gaap'),
 'op-office-investment':('investment_income','profit_composition_caution'),
 'op-office-rd':('research_expense','higher_expense_not_proven_payoff'),
 'op-office-cash':('cash_flow','reported_deterioration_management_adjustment_unverified'),
}


def eligible(fact,asof,clock):
    day=pd.Timestamp(asof).date()
    if clock=='publication_proxy':return pd.Timestamp(fact['published_date']).date()<day
    field={'inherited_archive':'recorded_at','ep35_acquisition':'ep35_fetched_at'}[clock]
    cutoff=pd.Timestamp(day).tz_localize('Asia/Shanghai')+pd.Timedelta(days=1)
    timestamp=pd.Timestamp(fact[field])
    if timestamp.tzinfo is None:raise ValueError('acquisition clock must specify timezone')
    return timestamp<cutoff


def build(facts,members,catalog,asof,clock):
    asof=pd.Timestamp(asof);month=asof.to_period('M')-1
    m=members[members.month.eq(month)&members.era.eq('SW2021')].copy()
    if not m.empty and (m.date>=asof).any():raise ValueError('future membership date')
    # Duplicated physical rows do not multiply known issuers or fact counts.
    m=m.drop_duplicates()
    base=catalog[catalog.era.eq('SW2021')][KEY+['industry_name']].copy()
    if base.duplicated(KEY).any():raise ValueError('ambiguous catalogue')
    keys=set(map(tuple,base[KEY].to_numpy()));links=[]
    for fact in facts:
        instrument=fact['ts_code'].split('.')[1]+fact['ts_code'].split('.')[0]
        known=eligible(fact,asof,clock)
        for level in ['L1','L2','L3']:
            g=m[m.level.eq(level)&m.instrument.eq(instrument)][KEY+['security_id']].drop_duplicates()
            state='mapped' if len(g)==1 else ('missing_identity' if len(g)==0 else 'ambiguous_identity')
            rec=dict(asof=asof,clock=clock,membership_month=str(month),evidence_id=fact['evidence_id'],ts_code=fact['ts_code'],instrument=instrument,level=level,era='SW2021',industry_code=None,security_id=None,
                clock_eligible=known,mapping_status=state,period=fact['period'],published_date=fact['published_date'],recorded_at=fact['recorded_at'],ep35_fetched_at=fact['ep35_fetched_at'],source_sha256=fact['source_sha256'],
                dimension=DIMENSIONS[fact['evidence_id']][0],company_direction=DIMENSIONS[fact['evidence_id']][1],economic_scope='issuer_business_not_whole_industry',industry_inference='not_established')
            if len(g)==1:
                rec.update(g.iloc[0].to_dict())
                if tuple(rec[k] for k in KEY) not in keys:rec['mapping_status']='outside_catalogue'
            links.append(rec)
    links=pd.DataFrame(links)
    usable=links[links.clock_eligible&links.mapping_status.eq('mapped')]
    den=m.groupby(KEY).agg(identified_members=('security_id','nunique'),unresolved_members=('unresolved','max')).reset_index()
    num=usable.groupby(KEY).agg(observed_issuers=('security_id','nunique'),facts=('evidence_id','nunique')).reset_index()
    full=base.merge(den,on=KEY,how='left',validate='one_to_one').merge(num,on=KEY,how='left',validate='one_to_one')
    full[['observed_issuers','facts']]=full[['observed_issuers','facts']].fillna(0).astype(int)
    full['known_member_sample_fraction']=full.observed_issuers/full.identified_members
    full['all_member_proxy_sample_fraction']=full.observed_issuers/(full.identified_members+full.unresolved_members)
    full['asof']=asof;full['clock']=clock;full['membership_month']=str(month)
    full['evidence_state']=np.where(full.identified_members.isna(),'membership_unknown',np.where(full.facts.gt(0),'selected_issuer_facts_only','no_eligible_reviewed_issuer_facts'))
    full['industry_mechanism']='not_established';full['economic_stage']='not_established'
    assert (full.observed_issuers<=full.identified_members.fillna(0)).all()
    return links,full


def run():
    out=ROOT/'outputs/r20';out.mkdir(exist_ok=True)
    paths=[ROOT/'outputs/r19/reviewed_operating_observations.json',CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'outputs/universe_current.csv',ROOT/'protocols/r20.json',Path(__file__)]
    facts=json.loads(paths[0].read_text());protocol=json.loads(paths[4].read_text())
    for f in facts:assert sha(f['pdf_path'])==f['source_sha256']
    members=pd.concat([pd.read_parquet(p,columns=MEMBER_COLUMNS) for p in paths[1:3]],ignore_index=True)
    catalog=pd.read_csv(paths[3]);ls=[];fs=[]
    for date in protocol['asofs']:
        for clock in CLOCKS:
            l,f=build(facts,members,catalog,date,clock);ls.append(l);fs.append(f)
    links=pd.concat(ls,ignore_index=True);full=pd.concat(fs,ignore_index=True)
    links.to_csv(out/'company_industry_links.csv',index=False);full.to_csv(out/'full_catalogue_evidence.csv',index=False)
    summary=full.groupby(['asof','clock','level']).agg(catalogue=('industry_code','size'),with_membership=('identified_members','count'),with_facts=('facts',lambda x:int(x.gt(0).sum())),fact_links=('facts','sum'),max_sample_fraction=('all_member_proxy_sample_fraction','max')).reset_index()
    summary.to_csv(out/'coverage_summary.csv',index=False)
    js(out/'receipt.json',dict(status='PASS_COMPANY_EVIDENCE_ONLY',reads={str(p):sha(p) for p in paths},full_catalogue_rows=len(full),link_rows=len(links),unique_facts=len(facts),unique_issuers=len({f['ts_code'] for f in facts}),mapping_states=links.mapping_status.value_counts().to_dict(),sources_quality='Historical-proxy identity; first-release chain not certified',independent_observations='five selected issuers in one economic period; hierarchy/clock repeats not independent',outputs={n:sha(out/n) for n in ['company_industry_links.csv','full_catalogue_evidence.csv','coverage_summary.csv']}))
    print(summary.to_string(index=False))

if __name__=='__main__':run()

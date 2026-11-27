"""Tabulate denominator, practical match coverage, tail errors and original cohort P&L."""
from pathlib import Path
import pandas as pd, numpy as np,sys,tempfile
from sources import HERE,OUT,OLD
def main():
    cov=pd.read_parquet(OUT/'covariates.parquet').set_index(['entry_idx','instrument'])
    tabs=[];capacity=[];outcomes=[]
    for sc in ['primary','later']:
        base=OUT/'books'/sc
        t=pd.read_parquet(base/'SellTree'/'decisions.parquet')
        trade=pd.read_parquet(OUT/'seller_execution.parquet').query('scope==@sc').set_index(['entry_idx','instrument'])
        for n in ['SellStyle','SellVolMatch']:
            alt=pd.read_parquet(base/n/'decisions.parquet')
            money=pd.read_parquet(base/n/'orders.parquet').set_index(['entry_idx','instrument','sleeve'])
            for a,b in zip(t.itertuples(),alt.itertuples()):
                assert a.entry_idx==b.entry_idx
                e=a.entry_idx; ph=(e-t.entry_idx.min())%10
                differences=[(o,c) for o,c in zip(a.removed,b.removed) if o!=c]
                assert len(differences)==b.style_pairs
                for orig,new in differences:
                    origvol=cov.at[(e,orig),'vol20'];newvol=cov.at[(e,new),'vol20']
                    mass=trade.at[(e,orig),'actual_mass']; pos=trade.at[(e,orig),'pre_position']
                    altsold=abs(min(0,money.at[(e,new,ph),'broker'])) if (e,new,ph) in money.index else 0
                    tabs.append((sc,n,e,orig,new,a.ticket,pos,0 if pd.isna(mass) else mass,altsold,origvol,newvol))
        for n in ['N1','N2','N3','Narrow','NarrowGate','WideGate','Combo','Combo1','Combo3']:
            f=pd.read_parquet(base/n/'decisions.parquet')
            for z in f.itertuples():
                seats={'N1':1,'N3':3,'Combo1':1,'Combo3':3}.get(n,2);capacity.append((sc,n,z.entry_idx,seats,len(z.added),z.ticket,seats*z.ticket,len(z.added)*z.ticket))
    tab=pd.DataFrame(tabs,columns='scope arm entry_idx original matched ticket original_position original_broker_altered alternate_sold original_vol20 alternate_vol20'.split())
    tab.to_parquet(OUT/'seller_match_seats.parquet',index=False)
    tab.groupby(['scope','arm']).agg(dates=('entry_idx','nunique'),seats=('matched','size'),planned=('ticket','sum'),original_position=('original_position','sum'),original_actual=('original_broker_altered','sum'),alternative_sold=('alternate_sold','sum'),original_vol20=('original_vol20','mean'),alternate_vol20=('alternate_vol20','mean')).to_csv(OUT/'seller_match_summary.csv')
    ex=pd.read_parquet(OUT/'seller_execution.parquet')
    ex.groupby(['scope','execution']).agg(seats=('instrument','size'),old_capital=('pre_position','sum'),actual_broker=('actual_mass','sum'),fee=('fee','sum'),proposed_ticket=('proposed_ticket','sum')).to_csv(OUT/'seller_actual_summary.csv')
    c=pd.DataFrame(capacity,columns='scope arm entry_idx maximum accepted ticket max_budget allocated'.split());c['unused']=c.max_budget-c.allocated
    c.groupby(['scope','arm']).agg(dates=('entry_idx','size'),potential=('maximum','sum'),accepted=('accepted','sum'),max_budget=('max_budget','sum'),allocated=('allocated','sum'),unused=('unused','sum')).assign(unused_seat_fraction=lambda d:1-d.accepted/d.potential).to_csv(OUT/'natural_replacement_coverage.csv')
    x=pd.read_parquet(OUT/'actual_switches.parquet')
    for k,g in x.groupby(['scope','arm','role']):
        seen=g.h10.notna()
        outcomes.append((*k,len(g),seen.sum(),g.planned.sum(),g.dollars_actual_new.sum(),g.loc[seen,'ticket_opportunity_h10'].sum(),g.new_gross_h10.sum(),g.loc[seen,'event'].sum(),g.loc[seen,'right'].sum(),g.loc[seen,'decile'].eq(10).sum(),g.loc[seen,'decile'].eq(1).sum(),g.fee.sum()))
    pd.DataFrame(outcomes,columns='scope arm role seats observed ticket actual_positive_net ticket_opportunity_profit positive_net_profit left_events right_events decile10 decile1 actual_fees'.split()).to_csv(OUT/'switch_outcomes.csv',index=False)
    h=pd.read_parquet(OUT/'common_h10.parquet')
    a=h[h.arm.isin(['SellTree','SellRidge'])].pivot(index=['scope','entry_idx'],columns='arm',values=['net','gross','fee','sleeve0']);z=pd.DataFrame({'net':a.net.SellTree-a.net.SellRidge,'gross':(a.gross.SellTree-a.gross.SellRidge)/a.sleeve0.SellTree,'fee':(a.fee.SellTree-a.fee.SellRidge)/a.sleeve0.SellTree})*1e4
    z.groupby(level='scope').mean().to_csv(OUT/'seller_common_start.csv')
    cov[['pos60','vol60','money_rel20']].isna().groupby(level='entry_idx').sum().to_csv(OUT/'seller_feature_missing.csv')
if __name__=='__main__':main()

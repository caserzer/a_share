from common import *
import pandas as pd
IDS=['era','level','cohort','horizon','method','origin']
def run():
 out=ROOT/'outputs/r237';out.mkdir(exist_ok=True);mp=CACHE/'extension_v2/products/assignments.parquet';lp=ROOT/'data/l1_assignments.parquet';cols=KEY+['month','date','security_id','unresolved'];m=pd.concat([pd.read_parquet(mp,columns=cols),pd.read_parquet(lp,columns=cols)],ignore_index=True);assert not m.duplicated(['era','level','month','security_id']).any();lookup={}
 for key,g in m.groupby(KEY+['month']):
  assert g.unresolved.nunique()==1;lookup[key]=(len(g),int(g.unresolved.iloc[0]),g.date.max())
 rows=[];pairs=[];reads=[mp,lp];linkrows=[]
 for rnd in [210,211,212,214,215,216,217]:
  hp=ROOT/f'outputs/r{rnd}/holdings.parquet';cp=ROOT/f'outputs/r{rnd}/paired_risk.csv';reads += [hp,cp];h=pd.read_parquet(hp);local={};records={}
  for key,g in h.groupby(IDS):
   ident=dict(zip(IDS,key),source_round=rnd);weights=dict(zip(g.industry_code,g.weight));assert len(weights)==len(g) and np.isclose(sum(weights.values()),1);unknown=0.;known=0.;hhi=0.;largest=0.;stocks=0;fractions={};missing=0
   for code,w in weights.items():
    item=lookup.get((ident['era'],ident['level'],code,ident['origin'].to_period('M')));usable=item is not None and item[2]<=ident['origin'];n,u,day=item if usable else (0,0,pd.NaT);den=n+u;frac=n/den if den else 0;uw=w*(1-frac);unknown+=uw;known+=w*frac;stocks+=n;hhi+=n*(w/den)**2 if den else 0;largest=max(largest,w/den if n else 0);fractions[code]=frac;missing+=not usable
    linkrows.append(dict(ident,industry_code=code,weight=w,known_members=n,unresolved_members=u if usable else None,denominator=den if usable else None,snapshot_date=day,status='nominal_snapshot' if usable else 'missing_or_future',known_fraction=frac))
   assert np.isclose(known+unknown,1);rec=dict(ident,industries=len(g),industry_hhi=sum(w*w for w in weights.values()),known_stocks=stocks,known_weight=known,unknown_weight=unknown,missing_industries=missing,known_hhi=hhi,hhi_lower=hhi,hhi_upper=min(1,hhi+2*largest*unknown+unknown**2),known_max_weight=largest,max_weight_upper=min(1,largest+unknown));rows.append(rec);local[key]=(weights,fractions);records[key]=rec
  cases=pd.read_csv(cp).drop_duplicates(['era','level','cohort','horizon','method','control']);originlookup={k:sorted(g.origin.unique()) for k,g in h.groupby(IDS[:-1])}
  for case in cases.to_dict('records'):
   prefix=tuple(case[k] for k in IDS[:4]);a=prefix+(case['method'],);b=prefix+(case['control'],);da=set(originlookup.get(a,[]));db=set(originlookup.get(b,[]));ident={k:case[k] for k in ['era','level','cohort','horizon','method','control']}
   for date in sorted(da|db):
    rec=dict(ident,source_round=rnd,origin=date,status='paired' if date in da&db else 'missing_target_side')
    if rec['status']=='paired':
     aw,af=local[a+(date,)];bw,bf=local[b+(date,)];ar=records[a+(date,)];br=records[b+(date,)];overlap=sum(min(aw[c],bw[c])*af[c] for c in set(aw)&set(bw));assert all(af[c]==bf[c] for c in set(aw)&set(bw));rec.update(known_overlap_lower=overlap,overlap_upper=min(1,overlap+ar['unknown_weight']+br['unknown_weight']),industry_overlap=sum(min(aw[c],bw[c]) for c in set(aw)&set(bw)))
     for metric in ['industry_hhi','known_stocks','unknown_weight','known_hhi','hhi_upper','known_max_weight']:rec['delta_'+metric]=ar[metric]-br[metric]
    pairs.append(rec)
 pd.DataFrame(rows).to_csv(out/'concentration.csv',index=False);pd.DataFrame(linkrows).to_parquet(out/'industry_links.parquet',index=False);pd.DataFrame(pairs).to_csv(out/'paired_overlap.csv',index=False);js(out/'verification.json',dict(status='PASS',target_portfolios=len(rows),industry_links=len(linkrows),pair_dates=len(pairs),paired_dates=sum(x['status']=='paired' for x in pairs),nominal_only=True,strict_pit=False,adoption=False,inputs={str(p):sha(p) for p in reads+[ROOT/'protocols/r237.json',Path(__file__)]},outputs={f:sha(out/f) for f in ['concentration.csv','industry_links.parquet','paired_overlap.csv']}));print(len(rows),len(linkrows),len(pairs))
if __name__=='__main__':run()

"""Reconstruct I2's industry target and budgets under the source taxonomy of each era."""
from ep41inputs import *
from hashlib import sha256
import json

def main():
    store=Path.home()/'.cache/a_share/ep32'
    old=store/'extension_v2/sources/legacy_members.parquet'
    new=store/'industry_v1/members.parquet'
    for path,key in [(old,'legacy_members_sha256'),(new,'membership_sha256')]:
        assert sha256(path.read_bytes()).hexdigest()==json.loads((path.parent/'manifest.json').read_text())[key]
    hist=pd.read_parquet(old).query("level=='L2'").rename(columns={'index_code':'l2','con_code':'code'}).assign(era='SW2014')
    rec=pd.read_parquet(new).rename(columns={'l2_code':'l2','ts_code':'code'}).assign(era='SW2021')
    src=pd.concat([hist,rec],ignore_index=True).drop_duplicates(['era','code','in_date','out_date','l2'])
    src['instrument']=src.code.str[-2:]+src.code.str[:6]
    src['in_date']=pd.to_datetime(src.in_date);src['out_date']=pd.to_datetime(src.out_date)
    d=pd.read_parquet(CACHE/'panel.parquet',columns=KEY+COLS+['weekly','outer','m10','h10'])
    out=pd.Series('未知',index=d.index)
    for stock,g in d.groupby('instrument'):
        sub=src[src.instrument.eq(stock)]
        sets={}
        for row in sub.itertuples():
            day=g.signal_date
            clock=day.lt('2021-12-01') if row.era=='SW2014' else day.ge('2022-01-01')
            valid=clock & day.gt(row.in_date)&(day.lt(row.out_date)|pd.isna(row.out_date))
            for ix in g.index[valid]:sets.setdefault(ix,set()).add(row.l2)
        one={idx:next(iter(ss)) for idx,ss in sets.items() if len(ss)==1}
        out.loc[list(one)]=list(one.values())
    d['sector']=out
    d['y_sector']=pct(d.h10,[d.signal_date,d.sector]).where(d.sector.ne('未知'))
    obs=[]
    qtr=d.signal_date.dt.to_period('Q')
    for q,g in d[d.outer].groupby(qtr[d.outer]):
        tr=d[d.weekly & d.m10.lt(q.start_time)&d.y_sector.notna()]
        obs.append(g[KEY+['sector']].assign(I2_stock=ep.predict(g[COLS],ep.ridge(tr,COLS,'y_sector'))))
    s=pd.concat(obs)
    s.to_parquet(CACHE/'i2_scores.parquet',index=False)
    s.assign(mapped=s.sector.ne('未知')).groupby('signal_date').agg(eligible=('instrument','size'),mapped=('mapped','sum')).to_csv(OUT/'i2_mapping.csv')
if __name__=='__main__':main()

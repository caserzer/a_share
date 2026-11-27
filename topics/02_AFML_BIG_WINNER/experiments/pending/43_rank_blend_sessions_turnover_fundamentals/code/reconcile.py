from accounts43 import *
def fix(pool):
    m=book(pool==800)
    for p in sorted((O/f'accounts/{pool}').glob('*/*/detail.csv')):
        meta=pd.read_csv(p);changed=False
        for seg,span in enumerate(SEG800 if pool==800 else SEG300,1):
            tr=p.parent/str(seg)/'transactions.parquet'
            if not tr.exists():continue
            life=allocate(pd.read_parquet(tr),m,span);life.to_parquet(tr.with_name('fifo.parquet'),index=False)
            idx=meta.index[(meta.segment==seg)&(meta.fee==1)][0];err=life.buy_fee.sum()+life.sell_fee.sum()-meta.at[idx,'totalfee'];assert abs(err)<1e-9,(p,seg,err)
            one=life[(life.age==10)&~life.still_open]
            for col,v in dict(fifo_fee_error=err,one_fee=(one.buy_fee+one.sell_fee).sum(),one_fee_ex_settle=(one.buy_fee+one.sell_fee)[~one.settlement].sum(),one_cap=one.principal.sum(),one_n=len(one),open_fee=life[life.still_open].buy_fee.sum(),one_loss_cap=one.loc[one.proceeds<one.principal,'principal'].sum(),one_rebuy_cap=one.loc[one.rebought_next_H10,'principal'].sum(),delayed_proceeds=life.loc[life.delayed_exit,'proceeds'].sum()).items():meta.loc[idx,col]=v
            changed=True
        if changed:meta.to_csv(p,index=False)
if __name__=='__main__':fix(int(sys.argv[1]))

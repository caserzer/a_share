from accounts43 import *
def main(pool):
    wide=pool==800;m=book(wide);f=frozen(wide);p=pack(m,f,f.refit_R if wide else f.R)
    # Rerun only the revised mechanical control.
    check=O/f'accounts/{pool}/W/mechanical/done'
    check.unlink(missing_ok=True)
    account(m,p,pool,'W','mechanical',5,trace=True)
    rows=[]
    for seg,span in enumerate(SEG800 if wide else SEG300,1):
        for arm,mode,cap,tau in [('LP',3,.05,.01),('QP',4,.05,.01),('capK',3,-1,0),('cap5',3,.05,0),('cap6',3,.06,0),('mechanical',5,.05,.01)]:
            with tempfile.NamedTemporaryFile() as tmp:
                m.lib.audit43_open(tmp.name.encode());mode_run(m,p,span,mode,cap,tau);m.lib.audit43_open(b'')
                v=pd.read_csv(tmp.name,header=None,names='day wealth residual bound kkt L1 invest hhi top10 locked'.split())
                rows.append(v.assign(pool=pool,segment=seg,arm=arm))
    out=pd.concat(rows,ignore_index=True);out.to_parquet(O/f'W1_solver_{pool}.parquet',index=False)
    v=out[out.arm!='mechanical'];assert v[['kkt','bound','residual']].abs().max().max()<1e-8,v[['kkt','bound','residual']].abs().max()
if __name__=='__main__':main(int(sys.argv[1]))

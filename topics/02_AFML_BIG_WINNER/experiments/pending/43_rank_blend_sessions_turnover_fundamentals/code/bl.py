from accounts43 import *
def fitgrid(m,f,scores,grid,family,pool):
    dates=m.days[np.sort(f.entry_idx.unique())-1]
    cal=Calibration.__new__(Calibration);cal.m=m;cal.board=SimpleNamespace(dates=dates);cal.wide=pool==800
    plans=[sliced(pack(m,f,s)) for s in scores]
    fit={};rows=[];m.lib.setup43(0,0.,0.)
    for q in pd.period_range('2021Q1','2026Q3',freq='Q'):
        span=cal.spans(q)
        mat=pd.concat([pd.concat([monthly(replay(m,p,s),m.days).net for s in span]).rename(str(v)) for v,p in zip(grid,plans)],axis=1).dropna() if span else pd.DataFrame()
        fit[str(q)]=grid[int(mat.mean().values.argmax())] if len(mat) else grid[0]
        for v in grid:
            rows.append((str(q),v,len(mat),mat[str(v)].mean() if len(mat) else np.nan,fit[str(q)],str(mat.index.max()) if len(mat) else '',len(mat)==0))
    pd.DataFrame(rows,columns='quarter candidate months mean_net chosen last_month fallback'.split()).to_csv(O/f'cal_{family}_{pool}.csv',index=False)
    return pd.Series(fit)
def ranks(f,s):
    g=s.groupby(f.entry_idx);return g.rank()/(g.transform('count')+1)
def run(pool,group):
    wide=pool==800;m=book(wide)
    fs=sorted((O/'models').glob('*.parquet'));assert len(fs)==31,len(fs)
    f=pd.concat([pd.read_parquet(file,filters=[('pool','=',pool)]) for file in fs],ignore_index=True)
    q=f.signal_date.dt.to_period('Q').astype(str)
    def a(fam,arm,s,md=0,tr=False,k=None):
        account(m,pack(m,f,s,k),pool,fam,arm,md,trace=tr)
    if group=='B':
        for col in ['T69','T69d','T60','T60d']:a('B',col,f[col])
        mask=pd.concat(pd.read_parquet(file,columns=KEY+['T','T_mask_trading']) for file in sorted((E/f'scale/a4/results/scores_{pool}').glob('*.parquet')))
        for arm in ['T','T_mask_trading']:account(m,pack(m,mask,mask[arm]),pool,'B',arm)
        grid=CFG['directions']['B']['b']
        r=ranks(f,f.R);t=ranks(f,f.T60d)
        b=fitgrid(m,f,[r*(1-v)+t*v for v in grid],grid,'b',pool)
        w=q.map(b).fillna(0);s=(1-w)*r+w*t
        for arm,score,md in [('B',s,0),('D',s,1),('fixed175',.825*r+.175*t,0),('fixed175_buf',.825*r+.175*t,1)]:a('B',arm,score,md,True)
        if wide:
            bn=pd.read_csv(O/'cal_b_300.csv').drop_duplicates('quarter').set_index('quarter').chosen
            w=q.map(bn).fillna(0)
            for typ,r0,t0 in [('transfer',ranks(f,f.transferR),ranks(f,f.transferT)),('native300b',r,t)]:
                h=r0*(1-w)+t0*w
                for arm,score,md in [('A',r0,0),('B',h,0),('C',r0,1),('D',h,1)]:
                    a(typ,arm,score,md,True)
                    if typ=='transfer':a('transfer_head',arm,score,md,False,frozen(False).groupby('entry_idx').size()//10)
    else:
        for arm in ['intra','over','total','treeover']:a('L',arm,f[arm],0,True)
        grid=CFG['directions']['L']['lambda']
        for limb in ['over','treeover']:
            scores=[f.intra+v*f[limb] for v in grid]
            fit=fitgrid(m,f,scores,grid,'lambda_'+limb,pool)
            for arm,score in [('eq_'+limb,scores[0]),('cal_'+limb,f.intra+q.map(fit).fillna(1)*f[limb])]:a('L',arm,score,0,True)
if __name__=='__main__':run(int(sys.argv[1]),sys.argv[2])

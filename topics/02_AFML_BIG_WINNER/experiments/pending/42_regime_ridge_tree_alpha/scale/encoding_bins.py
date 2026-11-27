"""Inspect S2 learning bins, repeated encoded values, endpoint saturation and altered masks."""
from fit_models import *

def main():
    f=data(STOCK)
    dates=f.signal_date.to_numpy();rows=[]
    for cm,x in [(False,f[STOCK]),(True,alias_mask(f[STOCK]))]:
        gg=x.groupby(f.signal_date);ranks=gg.rank('average')/(gg.transform('count')+1)
        for q,tr,te in outer_folds(f):
            ix=tr.index.to_numpy();iy=te.index.to_numpy()
            ct,_=reference_codes(x,ranks,ix,iy,dates)
            for arm,(a,b) in {'A':[x.iloc[ix],x.iloc[iy]],'B':[ranks.iloc[ix],ranks.iloc[iy]],**ct}.items():
                train=pd.DataFrame(a,columns=STOCK);test=pd.DataFrame(b,columns=STOCK)
                med=train.median().fillna(0)
                bins=lgb.Dataset(train.fillna(med),params=PARAM,free_raw_data=True).construct()
                for j,c in enumerate(STOCK):
                    at=train[c];bb=test[c];cnt=at.count();high=at.max();low=at.min()
                    rows.append((str(q),cm,arm,c,med[c],cnt,at.nunique(),cnt-at.nunique(),bins.feature_num_bin(j),bb.count(),int(bb.isin([low,high]).sum()),int((bb<low).sum()),int((bb>high).sum()),int((x.iloc[iy][c].isna()&~f.iloc[iy][c].isna()).sum())))
    pd.DataFrame(rows,columns='fold commonmask arm feature median observed_train distinct_train excess_tied_train lightgbm_bins observed_test test_training_endpoint below_training above_training alias_cells_removed'.split()).to_csv(RES/'S2_bins.csv',index=False)
if __name__=='__main__':main()

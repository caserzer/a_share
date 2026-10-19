"""Train-only weighted empirical ranks for additive multiclass probabilities."""
import numpy as np
from scipy.special import softmax


class WeightedRankDesign:
    def fit(self, frame, weights):
        weights=np.asarray(weights,dtype=float)
        assert len(weights)==len(frame) and np.isfinite(weights).all() and (weights>0).all()
        self.columns=list(frame.columns);self.numeric={};self.categorical={};self.names=[]
        for col in self.columns:
            if col=='industry_id':
                levels=sorted(frame[col].unique().tolist())
                assert all(isinstance(x,str) for x in levels)
                self.categorical[col]=levels;self.names.extend(col+'='+v for v in levels)
            else:
                a=frame[col].to_numpy(dtype=float);assert not np.isinf(a).any()
                valid=np.isfinite(a)
                values,inverse=np.unique(a[valid],return_inverse=True)
                mass=np.bincount(inverse,weights=weights[valid],minlength=len(values))
                cumulative=np.r_[0.,np.cumsum(mass)]
                if len(values):cumulative/=cumulative[-1]
                self.numeric[col]=(values,cumulative)
                self.names.extend([col,col+'__missing'])
        return self

    def transform(self,frame):
        assert list(frame.columns)==self.columns
        pieces=[]
        for col in self.columns:
            if col in self.categorical:
                a=frame[col].to_numpy()
                pieces.extend((a==v).astype(float) for v in self.categorical[col])
            else:
                a=frame[col].to_numpy(dtype=float);assert not np.isinf(a).any()
                valid=np.isfinite(a);values,cumulative=self.numeric[col];rank=np.zeros(len(a))
                if len(values):
                    lo=np.searchsorted(values,a[valid],side='left');hi=np.searchsorted(values,a[valid],side='right')
                    rank[valid]=cumulative[lo]+cumulative[hi]-1
                pieces.extend([rank,(~valid).astype(float)])
        result=np.column_stack(pieces)
        assert np.isfinite(result).all() and result.shape[1]==len(self.names)
        return result


def month_weights(train):
    return 1/train.groupby('date').date.transform('size').to_numpy(dtype=float)


def probabilities(design,coef,intercept,labels):
    p=np.zeros((len(design),7))
    p[:,np.asarray(labels,dtype=int)]=softmax(design@coef.T+intercept,axis=1)
    return p

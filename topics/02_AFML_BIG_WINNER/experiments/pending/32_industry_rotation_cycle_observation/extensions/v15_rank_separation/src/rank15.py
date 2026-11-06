import numpy as np
import pandas as pd
from scipy.special import expit,logit


def redistribute(scores,anchor,strength):
    scores=np.asarray(scores,float)
    if len(scores)==0:return np.array([],float)
    if anchor<=0:return np.zeros(len(scores))
    if anchor>=1:return np.ones(len(scores))
    percent=pd.Series(scores).rank(method='average',pct=True).to_numpy().clip(.01,.99)
    z=logit(percent)*strength;lo=-50.;hi=50.
    for _ in range(60):
        mid=(lo+hi)/2
        if expit(mid+z).mean()>anchor:hi=mid
        else:lo=mid
    return expit((lo+hi)/2+z)

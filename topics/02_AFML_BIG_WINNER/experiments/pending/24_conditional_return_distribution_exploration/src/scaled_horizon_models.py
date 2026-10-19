"""Known annualized risk scaling for coherent sign-preserving distributions."""
import numpy as np


def risk_scale(volatility, months):
    vol,h = np.broadcast_arrays(np.asarray(volatility,float),np.asarray(months,float))
    if not np.isfinite(vol).all() or not np.isfinite(h).all() or (vol<=0).any() or (h<=0).any():
        raise ValueError('Known positive annualized volatility and horizon required')
    return np.maximum(vol,.001)*np.sqrt(h/12)


def normalized_return(values, volatility, months):
    y=np.asarray(values,float)
    if not np.isfinite(y).all() or (y<=-1).any():raise ValueError('Mature finite simple returns above -1 required')
    return np.log1p(y)/risk_scale(volatility,months)/10


def normalize_training(train):
    result=train.copy()
    result['label_scale']=risk_scale(result.vol63,result.horizon_months)
    result['normalized_label']=normalized_return(result.label,result.vol63,result.horizon_months)
    return result


def restore_atoms(normalized_atoms, volatility, months):
    scale=np.atleast_1d(risk_scale(volatility,months));u=np.asarray(normalized_atoms,float)
    if u.ndim==1:u=np.tile(u,(len(scale),1))
    if u.ndim!=2 or len(u)!=len(scale) or not np.isfinite(u).all():raise ValueError('Invalid normalized support')
    with np.errstate(over='raise',invalid='raise'):
        result=np.expm1(u*10*scale[:,None])
    if not np.isfinite(result).all() or (result < -1).any():raise ValueError('Invalid restored support')
    np.testing.assert_array_equal(np.sign(result),np.sign(u))
    return result

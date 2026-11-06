import numpy as np


def add_risk(frame):
    g=frame.copy()
    h=-np.log1p(-g.threshold)
    s21=(g.vol21/np.sqrt(252)).clip(lower=.0001)
    s63=(g.vol63/np.sqrt(252)).clip(lower=.0001)
    t21=(h/s21)**2;t63=(h/s63)**2
    g['risk_clock21']=np.log1p(t21);g['risk_clock63']=np.log1p(t63)
    g['risk_vol_accel']=s21/s63
    g['risk_drift']=(np.log1p(g.mom63)/63*h/s63**2).clip(-20,20)
    drawdown=-np.log1p(g.state_drawdown)
    g['risk_distance']=np.where(g.state_direction.eq(1),(h-drawdown).clip(lower=0)/s63,0.)
    g['risk_progress']=np.log1p(g.state_drawup)/h
    g['risk_excess']=g.excess63/(s63*np.sqrt(63))
    g['risk_age']=g.state_age*90*252/365/t63
    return g

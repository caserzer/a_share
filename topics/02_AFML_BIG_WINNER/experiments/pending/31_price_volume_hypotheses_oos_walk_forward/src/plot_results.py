"""Exported research figure; endpoints stay on separate axes with their units."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import EP, OUT


def main():
    f=pd.read_csv(OUT/'metrics/pooled_oos_metrics.csv')
    f=f.loc[f.scheme.eq('expanding')]
    fig,axes=plt.subplots(1,3,figsize=(12,4),gridspec_kw={'width_ratios':[2,1,1]},layout='constrained')
    for ax,endpoint,title in zip(axes,['adjusted_return','log_variance_mse','downside_brier'],
                                ['Return partial slopes','H07: log-variance MSE gain','H10: downside Brier gain']):
        group=f.loc[f.endpoint.eq(endpoint)]
        y=np.arange(len(group))
        ax.errorbar(group.estimate,y,xerr=np.vstack([group.estimate-group.ci_low,group.ci_high-group.estimate]),fmt='o',capsize=4,color='#1f6b75')
        ax.set_yticks(y,group.hypothesis)
        ax.axvline(0,color='gray',linewidth=1,linestyle='--')
        ax.set_title(title,fontsize=10)
        ax.set_xlabel('Effect and 95% time-block CI')
        ax.grid(axis='x',alpha=.2)
    fig.suptitle('EP31 historical proxy OOS, available controls only; H09 blocked',fontsize=12)
    fig.supxlabel('No certified industry/PIT alpha; no independently matured forward evidence',fontsize=9)
    p=EP/'reports/figures';p.mkdir(exist_ok=True)
    fig.savefig(p/'primary_effects.png',dpi=180)
    fig.savefig(p/'primary_effects.svg')
    plt.close(fig)


if __name__=='__main__':main()

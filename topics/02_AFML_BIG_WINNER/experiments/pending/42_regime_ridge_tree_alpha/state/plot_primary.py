from core42 import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

def main():
    root=OUT/'main'
    w=pd.read_parquet(root/'weights_daily.parquet').loc['2021-01-08':]
    data=pd.read_csv(root/'monthly.csv')
    mat=data[data.arm.isin(['static','dynamic'])].pivot(index=['segment','month'],columns='arm',values='net')
    delta=(mat.dynamic-mat.static)*1e4
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True,layout='constrained')
    axes[0].plot(w.index,w.dynamic,label='State-dependent',lw=1.3,color='#146f73')
    axes[0].step(w.index,w.static,label='Quarterly static',where='post',lw=1.6,color='#793e35')
    axes[0].yaxis.set_major_formatter(PercentFormatter(1))
    axes[0].set_ylabel('Tree score weight');axes[0].legend(loc='upper left',ncol=2,frameon=False)
    dates=pd.PeriodIndex(delta.index.get_level_values('month'),freq='M').to_timestamp('M')
    axes[1].bar(dates,delta,width=24,color=np.where(delta>=0,'#146f73','#ab5944'))
    axes[1].axhline(0,color='#364047',lw=.6);axes[1].set_ylabel('Paired net return (bp/month)')
    for ax in axes:
        ax.axvline(pd.Timestamp('2025-03-03'),ls='--',color='#777',lw=1)
        ax.grid(axis='y',lw=.4,alpha=.4)
        ax.spines[['right','top']].set_visible(False)
    fig.suptitle('CSI 300  |  Registered D5 account replay',x=.08,ha='left',weight='bold')
    fig.savefig(root/'d5_weights_and_net.png',dpi=155,bbox_inches='tight')
if __name__=='__main__':main()


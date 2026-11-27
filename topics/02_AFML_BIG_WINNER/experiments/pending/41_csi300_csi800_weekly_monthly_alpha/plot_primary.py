from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
def main():
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    table=pd.read_csv(ROOT/'primary_inference.csv')
    fig,axes=plt.subplots(2,1,figsize=(8.6,5.4),sharex=True,gridspec_kw={'height_ratios':[4,3]})
    fig.subplots_adjust(left=.21,right=.95,top=.90,bottom=.16,hspace=.62)
    names={'1':'首段','2':'重启段','3':'后段','primary':'前段','later':'后段','all':'按有效月加权'}
    for ax,(test,g) in zip(axes,table.groupby('test',sort=False)):
        ax.axvline(0,c='#666',lw=1)
        ax.set_axisbelow(True)
        ax.grid(axis='x',color='#e9e9e9')
        for j,r in enumerate(g.itertuples()):
            color='#21577b' if r.segment!='all' else '#b3501b'
            ax.plot([r.low,r.high],[j,j],color=color,lw=2,solid_capstyle='round')
            ax.scatter(r.estimate,j,s=46,color=color,marker='D' if r.segment=='all' else 'o',zorder=3)
        ax.set_yticks(range(len(g)),[f'{names[r.segment]}（{r.months}月）' for r in g.itertuples()])
        ax.set_ylim(len(g)-.52,-.6)
        ax.tick_params(axis='both',length=0,pad=6)
        for spine in ax.spines.values():spine.set_visible(False)
        ax.set_title({'P1':'P1　中证800头部减下一档候补','P2':'P2　沪深300树补位减 Ridge 顺位补位'}[test],fontsize=12,loc='left')
    axes[-1].set_xlabel('配对净收益差（bp/月），横线为段内三个月块自助法的95%区间',labelpad=10)
    fig.savefig(ROOT/'primary_intervals.png',dpi=160,facecolor='white')
    plt.close(fig)

if __name__=='__main__':main()

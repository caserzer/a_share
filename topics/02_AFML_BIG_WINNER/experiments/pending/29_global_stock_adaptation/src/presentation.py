"""Deterministic presentation of completed scores; no model selection or fitting."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *


def table(frame):
    def fmt(v):
        if pd.isna(v):return 'NA'
        if isinstance(v,(float,np.floating)):return f'{v:.8g}'
        return str(v).replace('|','/')
    return '| '+' | '.join(frame.columns)+' |\n| '+' | '.join(['---']*len(frame.columns))+' |\n'+''.join(
        '| '+' | '.join(fmt(v) for v in row)+' |\n' for row in frame.itertuples(index=False,name=None))


def main():
    report=EP/'reports';fig=report/'figures';fig.mkdir(exist_ok=True)
    summary=pd.read_csv(OUT/'summary.csv');intervals=pd.read_csv(OUT/'paired_intervals.csv')
    cohort=json.loads((EP/'configs/target_cohort.yaml').read_text())
    rel=pd.read_csv(OUT/'reliability.csv')
    fig1,ax=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
    for j,foundation in enumerate(['M_R','L2']):
        for name in C['formal_models']:
            z=rel[(rel.foundation==foundation)&(rel.model==name)].copy();z['w']=z.rows/z.origin_rows
            z['wp']=z.w*z.predicted;z['wy']=z.w*z.observed
            b=z.groupby('bin')[['w','wp','wy']].sum()
            ax[j].plot(b.wp/b.w,b.wy/b.w,'o-',label=name,markersize=4)
        ax[j].plot([0,1],[0,1],'k--',lw=.8);ax[j].set(xlim=(0,1),ylim=(0,1),xlabel='Predicted probability',ylabel='Observed frequency',title=foundation+' | month-weighted bins')
        ax[j].legend()
    fig1.savefig(fig/'reliability.png',dpi=160);plt.close(fig1)
    s=pd.read_csv(EP/'outputs/predictions/single_stock_M_R.csv',parse_dates=['date'])
    f,ax=plt.subplots(3,1,figsize=(12,8),sharex=True,constrained_layout=True)
    for name in C['formal_models']:ax[0].plot(s.date,s[name],label=name,lw=1.2)
    active=s.individual_reason.eq('adapted')
    ax[0].fill_between(s.date,s.GPI_lower.where(active),s.GPI_upper.where(active),alpha=.15,color='purple',label='conditional issuer interval only')
    known=s.actual.notna();ax[0].scatter(s.loc[known,'date'],labels(s.loc[known,'actual']),s=14,c='black',label='realized event')
    ax[0].set(ylabel='6-month loss probability',ylim=(-.03,1.03),title=cohort['single_stock']+' | historical exploration');ax[0].legend(ncol=4,fontsize=8)
    ax[1].plot(s.date,s.peer_offset,label='Peer logit shift');ax[1].plot(s.date,s.individual_offset_GP,label='Issuer logit shift')
    ax[1].axhline(0,color='black',lw=.5);ax[1].set_ylabel('Logit correction');ax[1].legend()
    ax[2].plot(s.date,s.individual_months,label='Mature months');ax[2].plot(s.date,s.nonoverlap_events,label='Disjoint event windows')
    ax[2].set_ylabel('Available history');ax[2].legend()
    f.savefig(fig/'single_stock_path.png',dpi=160);plt.close(f)
    peer=pd.read_parquet(CACHE/'real_M_R_peers.parquet') if (CACHE/'real_M_R_peers.parquet').exists() else pd.concat(
        [pd.read_parquet(p) for p in sorted(CACHE.glob('real_M_R_*_peers.parquet'))],ignore_index=True)
    peer[peer.instrument.eq(cohort['single_stock'])&peer.date.ge(C['prediction_start'])].to_csv(EP/'outputs/predictions/single_stock_peers.csv',index=False)
    main=intervals[(intervals.population=='D0')&(intervals.candidate=='GPI')&(intervals.baseline=='G')&(intervals.weighting=='month')]
    selected=intervals[(intervals.foundation=='M_R')&(intervals.population=='D0')&(intervals.weighting=='month')&(intervals.block==6)]
    formal=summary[summary.model.isin(C['formal_models'])]
    text='# 全部固定比较的展示表\n\n所有结果均为反复研究历史的探索性结果；负差值为改善。\n\n'
    text+='## 模型评分（月等权，另列公司与股票月等权）\n\n'+table(formal[['foundation','population','model','brier','pooled_brier','company_equal_brier','auc','pr_auc','base_rate','ece','bias']])
    text+='\n## D0 主比较：月份等权区间\n\n'+table(main[['foundation','block','estimate','low95','high95','low_secondary','high_secondary','relative_improvement_percent','approximate_80pct_detectable_effect']])
    text+='\n## 主 M_R 所有预注册消融与原诊断（6月块）\n\n'+table(selected[['candidate','baseline','estimate','low95','high95','low_secondary','high_secondary','relative_improvement_percent']])
    text+='\n## 主要比较的全部权重与区间\n\n'+table(intervals[(intervals.candidate=='GPI')&(intervals.baseline=='G')][['foundation','population','weighting','block','estimate','low95','high95']])
    phases=pd.read_csv(OUT/'phase_intervals.csv')
    text+='\n## 两个预指定阶段\n\n'+table(phases[(phases.foundation=='M_R')&(phases.candidate=='GPI')&(phases.baseline=='G')&(phases.block==6)][['population','phase','months','estimate','low95','high95']])
    companies=pd.read_csv(OUT/'company_scores.csv');a=companies[(companies.foundation=='M_R')&(companies.model=='GPI')]
    b=companies[(companies.foundation=='M_R')&(companies.model=='G')][['instrument','brier']].rename(columns={'brier':'G_brier'})
    a=a.merge(b,on='instrument');a['delta']=a.brier-a.G_brier
    text+='\n## 预选40家公司，代码排序；不作单股显著性宣称\n\n'+table(a.sort_values('instrument')[['instrument','months','events','risk_stages','nonoverlap_events','G_brier','brier','delta']])
    con=pd.read_csv(OUT/'conditional_summary.csv');con=con[con.foundation=='M_R']
    a=con[con.model=='GPI'];b=con[con.model=='G'][['dimension','condition','brier']].rename(columns={'brier':'G_brier'})
    a=a.merge(b,on=['dimension','condition']);a['delta']=a.brier-a.G_brier
    text+='\n## 所有事前分组，含全部行业；描述性多重比较\n\n'+table(a.sort_values(['dimension','condition'])[['dimension','condition','months','stock_months','events','G_brier','brier','delta']])
    (report/'result_tables.md').write_text(text)
    print('Presentation tables, reliability diagram, single-stock path and peer trace complete')


if __name__=='__main__':main()

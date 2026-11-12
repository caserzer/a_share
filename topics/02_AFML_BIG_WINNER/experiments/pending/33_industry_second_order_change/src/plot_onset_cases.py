"""Retrospective charts of cases selected before their outcomes were inspected."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from onset_replay import EP


def main():
    font_path='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    font_manager.fontManager.addfont(font_path)
    font_name=font_manager.FontProperties(fname=font_path).get_name()
    plt.rcParams.update({'font.family':font_name,'axes.unicode_minus':False,'font.size':10})
    root=EP/'outputs/r06';out=root/'figures';out.mkdir(exist_ok=True)
    cases=pd.read_csv(root/'cases.csv');refs=pd.read_csv(EP/'outputs/r07/references.csv.gz',parse_dates=['date'])
    for _,case in cases[cases.deep_read].iterrows():
        records=[json.loads(x) for x in (root/'replay'/f'{case.case_id}.jsonl').read_text().splitlines()]
        f=pd.DataFrame(records);f['date']=pd.to_datetime(f['asof'])
        fig,axes=plt.subplots(5,1,figsize=(12,13),sharex=True,gridspec_kw={'height_ratios':[1.5,1.3,1.1,.8,1.2]})
        x=pd.to_numeric(f.x,errors='coerce');axes[0].plot(f.date,100*np.expm1(x-x.dropna().iloc[0]),color='#174a73',lw=2,label='相对价格路径（片段首日=0）')
        axes[0].set_ylabel('相对价格变化 %')
        for col,label,color in [('rate5','5日速度','#acb5bd'),('rate20','20日速度','#146b94'),('rate60','60日速度','#b65a35')]:
            axes[1].plot(f.date,pd.to_numeric(f[col],errors='coerce')*100,label=label,color=color,lw=1.6)
        axes[1].axhline(0,color='#808080',lw=.8);axes[1].set_ylabel('相对速度 %/5交易日')
        axes[2].plot(f.date,pd.to_numeric(f.breadth21,errors='coerce')*100,color='#21846b',label='绝对上涨公司比例')
        axes[2].axhline(50,color='#777777',ls=':',lw=1);axes[2].set_ylabel('上涨宽度 %');axes[2].set_ylim(-5,105)
        ax=axes[2].twinx();ax.step(f.date,pd.to_numeric(f.new_low_count10,errors='coerce'),color='#b65a35',alpha=.6,where='mid',label='近10日新低次数');ax.set_ylabel('新低次数');ax.set_ylim(-.5,10.5)
        axes[3].plot(f.date,f.volume_ratio,color='#6a5b98',label='量比（已有63日基准）');axes[3].axhline(1,color='#777',ls=':');axes[3].set_ylabel('量比')
        axes[4].step(f.date,pd.to_numeric(f.finance_acceleration,errors='coerce')*100,color='#8a517e',where='post',label='收入增速变化代理')
        axes[4].set_ylabel('收入同比变化 pp')
        ax4=axes[4].twinx();ax4.plot(f.date,pd.to_numeric(f.finance_coverage,errors='coerce')*100,color='#999999',ls='--',label='财务覆盖');ax4.set_ylim(0,105);ax4.set_ylabel('财务覆盖 %')
        slow=f[pd.to_numeric(f.rate20,errors='coerce').lt(0)&pd.to_numeric(f.rate_change,errors='coerce').gt(0)]
        confirm=f[pd.to_numeric(f.rate20,errors='coerce').gt(0)&pd.to_numeric(f.breadth21,errors='coerce').ge(.5)]
        for date,color,label in [(slow.date.iloc[0] if len(slow) else None,'#cb8a21','片段内首次弱势减速'),(confirm.date.iloc[0] if len(confirm) else None,'#398566','片段内首次广泛确认')]:
            if date is not None:
                for j,a in enumerate(axes):a.axvline(date,color=color,ls='--',alpha=.75,label=label if j==0 else None)
        rr=refs[refs.era.eq(case.era)&refs.industry_code.eq(case.industry_code)&refs.reference.eq('trough_w4')&refs.date.between(case.entry,case.end)]
        for j,date in enumerate(rr.date):axes[0].axvline(date,color='#555555',ls=':',alpha=.55,label='事后参考低点（非当时可知）' if j==0 else None)
        for a in axes:a.grid(alpha=.18);a.legend(loc='upper left',fontsize=8,ncol=2)
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        fig.suptitle(f'{case.industry_name} | {case.period}\n连续过程回放：先看变化，再看确认',fontsize=16,y=.985)
        fig.text(.08,.015,'事后展示完整片段；早期逐周记录及分段反思已保留。指标不是经济周期真值，财务变化须结合覆盖解读。',fontsize=9,color='#555')
        fig.tight_layout(rect=[0,.035,1,.95]);fig.savefig(out/f'{case.case_id}.png',dpi=140);plt.close(fig)
    print('case plots generated',len(cases[cases.deep_read]))

if __name__=='__main__':main()

from event_account import *
def main():
    s=Study();m=s.m
    p=OUT/'events_h20';t=pd.read_parquet(p/'targets.parquet')
    support=pd.read_parquet(OUT/'event_details/support.parquet')
    arms=['deducted_accel','deducted_accel_match','revenue_growth','revenue_growth_match']
    plans={};dens={}
    for name in arms:
        rows=t[t.arm==name]
        plan={e:np.empty(0,int) for e in s.pool}
        plan.update({e:d.security_idx.to_numpy(int) for e,d in rows.groupby('entry_idx')});plans[name]=plan
        d=support[support.arm==name.replace('_match','')].set_index('entry_idx').eligible
        dens[name]=d.to_dict()
    # The original stage's full account stopped before the first missing held mark.
    # Start the replacement subinterval after June 30, without valuing the missing position.
    engine.RANGES=[('2021-01-11','2025-03-03','2022-06-29'),('2022-07-01','2025-03-03','2023-06-15'),*engine.RANGES[1:]]
    s.run('events_h20_restart',plans,[(arms[0],arms[1]),(arms[2],arms[3])],20,dens)
if __name__=='__main__':main()

from event_account import *
def main():
    for f in OUT.glob('*/comparisons.csv'):
        if f.parent.name=='etf':continue
        c=pd.read_csv(f)[['arm','comparator']].drop_duplicates()
        summarize_months(f.parent,pd.read_csv(f.parent/'months.csv'),list(c.itertuples(index=False,name=None)))
if __name__=='__main__':main()

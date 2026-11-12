import sys
import unittest
import random
from functools import lru_cache
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from capacity_oracle import allocate


class OracleBound(unittest.TestCase):
    def test_interval_greedy_against_exact_assignment(self):
        rng=random.Random(3403)
        for _ in range(200):
            cap=rng.choice([1,2]);jobs=[]
            for i in range(rng.randrange(1,8)):
                a=rng.randrange(4);b=rng.randrange(a,4)
                jobs.append(dict(process_id=str(i),weeks=list(range(a,b+1))))
            @lru_cache(None)
            def solve(i,used):
                if i==len(jobs):return 0
                best=solve(i+1,used)
                for week in jobs[i]['weeks']:
                    if used[week]<cap:
                        counts=list(used);counts[week]+=1
                        best=max(best,1+solve(i+1,tuple(counts)))
                return best
            self.assertEqual(len(allocate(jobs,cap)),solve(0,(0,0,0,0)))


if __name__=='__main__':unittest.main()

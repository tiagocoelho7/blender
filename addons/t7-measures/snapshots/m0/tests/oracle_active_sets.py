"""Independent oracle: exact convex QP by active-set KKT enumeration.

No imports from t7m and no segment/triangle distance formulas. Only suitable for
convex simplices, deliberately different from kernel primitive decomposition.
"""
from fractions import Fraction as F
from itertools import combinations

def solve(a,b):
    n = len(b)
    a = [list(row)+[value] for row,value in zip(a,b)]
    for col in range(n):
        pivot = next((r for r in range(col,n) if a[r][col]),None)
        if pivot is None: return None
        a[col],a[pivot] = a[pivot],a[col]
        x = a[col][col]
        a[col] = [v/x for v in a[col]]
        for r in range(n):
            if r==col: continue
            x = a[r][col]
            a[r] = [v-x*w for v,w in zip(a[r],a[col])]
    return [a[r][-1] for r in range(n)]

def subsets(n):
    return [c for k in range(1,n+1) for c in combinations(range(n),k)]

def distance2(a,b):
    a,b = [tuple(map(F,p)) for p in a],[tuple(map(F,p)) for p in b]
    best = None
    for ia in subsets(len(a)):
        for ib in subsets(len(b)):
            columns = [a[i] for i in ia]+[tuple(-v for v in b[i]) for i in ib]
            n = len(columns)
            h = [[2*sum((x*y for x,y in zip(c,d)),F(0)) for d in columns] for c in columns]
            c1 = [F(i<len(ia)) for i in range(n)]
            c2 = [1-v for v in c1]
            kkt = [row+[c1[i],c2[i]] for i,row in enumerate(h)]
            kkt += [c1+[F(0),F(0)],c2+[F(0),F(0)]]
            ans = solve(kkt,[F(0)]*n+[F(1),F(1)])
            if ans is None or any(v<0 for v in ans[:n]): continue
            delta = [sum((ans[i]*columns[i][j] for i in range(n)),F(0)) for j in range(3)]
            sq = sum((x*x for x in delta),F(0))
            best = sq if best is None else min(best,sq)
    if best is None: raise AssertionError('oracle found no feasible support')
    return best

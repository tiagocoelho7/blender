"""Measured cost probes matching the original A cases; synthetic only."""
from fixtures import f,d
import json,time,tracemalloc
import numpy as np
records=[]
for n in (100,200,240):
    for limit,pair_seconds in ((60000,4.),(512*1024**2,.01)):
        mesh=f.Mesh([(0,0,0)]*n,[],[]);q=np.zeros((n,3),dtype=np.int64);order=np.arange(n)
        budget=d.BudgetContext(d.Limits(mem_pair_bytes=limit,pair_seconds=pair_seconds,total_seconds=5))
        tracemalloc.start();start=time.monotonic()
        try:
            with d.bound_budget(budget),budget.pair():
                equal=d._ambiguous_isomorphism(mesh,mesh,q,q,order,order)
            outcome='EXACT_EQUAL' if equal else 'EXACT_DIFFERENT';reason=None
        except d.ComplexityBudgetExceeded as ex:outcome='INCONCLUSIVE_NO_DELETE';reason=str(ex)
        elapsed=time.monotonic()-start;current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        row={'n':n,'pair_cap':limit,'pair_seconds':pair_seconds,'outcome':outcome,'reason':reason,
             'elapsed_s':elapsed,'python_peak_bytes':peak,'sampled_rss_delta':budget.rss_peak-budget.initial_rss,
             'states':budget.total_states,'requests_bytes':budget.pair_allocation_requests,
             'largest_accepted_request':budget.global_allocation_peak_request}
        print(json.dumps(row),flush=True);records.append(row)
        if limit==60000:assert outcome=='INCONCLUSIVE_NO_DELETE' and budget.total_states==0
        if pair_seconds==.01:assert outcome=='INCONCLUSIVE_NO_DELETE' and elapsed<.15

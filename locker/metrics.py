from .model import transition_universe


def calculate_coverage(executed_traces):
    """executed_traces: iterable of lists of model Transition labels (one list per sequence).
    State coverage      = visited / 4 model states (initial AVAILABLE counts as visited).
    Transition coverage = distinct (src,op,outcome,dst) / all 35 reachable model transitions
                          (accepted and rejected outcomes are separate transitions).
    Pair coverage       = distinct adjacent (t1,t2) / all 305 pairs with t1.dst == t2.src;
                          adjacency is within one sequence only (every sequence restarts from a fresh locker)."""
    states, trans, pairs = transition_universe()
    vs, vt, vp = set(), set(), set()
    for tr in executed_traces:
        if tr:
            vs.add(tr[0].src)
        for i, t in enumerate(tr):
            vs.add(t.dst); vt.add(t)
            if i:
                vp.add((tr[i - 1], t))
    return {"state_cov": len(vs) / len(states), "transition_cov": len(vt) / len(trans),
            "pair_cov": len(vp) / len(pairs),
            "states": f"{len(vs)}/{len(states)}", "transitions": f"{len(vt)}/{len(trans)}",
            "pairs": f"{len(vp)}/{len(pairs)}"}


def mutation_summary(mutant_results):
    """mutant_results: {name: {"killed": bool, "equivalent": bool}}.
    score = killed non-equivalent / all non-equivalent. Equivalent mutants are reported separately."""
    real = {n: r for n, r in mutant_results.items() if not r["equivalent"]}
    killed = sorted(n for n, r in real.items() if r["killed"])
    survived = sorted(n for n, r in real.items() if not r["killed"])
    return {"killed": killed, "survived": survived,
            "equivalent": sorted(n for n, r in mutant_results.items() if r["equivalent"]),
            "score": len(killed) / len(real) if real else 0.0}

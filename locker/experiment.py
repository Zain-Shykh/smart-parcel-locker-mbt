"""Experiment runner: python -m locker.experiment [--count 500] [--max-length 20] [--seeds 1 2 3 4 5] [--out results]
Writes raw_tests.csv, mutant_results.csv, coverage.csv, summary.json, summary.md, charts (SVG)."""
import argparse, csv, json, statistics as st, time
from pathlib import Path

from .generators import ALL_GENERATORS
from .metrics import calculate_coverage, mutation_summary
from .mutants import MUTANTS
from .runner import SequenceRunner

BUDGETS = [1, 5, 10, 25, 50, 100, 500]


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def mean(xs):
    return sum(xs) / len(xs)


def run(count, max_length, seeds, out):
    out.mkdir(exist_ok=True)
    raw, mut_rows, cov_rows = [], [], []
    for G in ALL_GENERATORS:
        for seed in seeds:
            t0 = time.perf_counter()
            seqs = G(seed, max_length).generate(count)
            gen_t = time.perf_counter() - t0
            t0 = time.perf_counter()
            runner = SequenceRunner()
            recs = [runner.run(s, f"{G.name}-s{seed}-{i:03d}", G.name) for i, s in enumerate(seqs)]
            exec_t = time.perf_counter() - t0
            cov = calculate_coverage(r["trace"] for r in recs)
            dup = 1 - len({r["sequence"] for r in recs}) / len(recs)
            cov_rows.append(dict(strategy=G.name, seed=seed, **cov, gen_time_s=round(gen_t, 4),
                                 exec_time_s=round(exec_t, 4), duplicate_ratio=round(dup, 4),
                                 mean_length=round(mean([r["length"] for r in recs]), 2),
                                 reference_failures=sum(r["outcome"] == "FAIL" for r in recs)))
            raw += [{k: v for k, v in r.items() if k != "trace"} | {"seed": seed} for r in recs]
            t0 = time.perf_counter()
            for M in MUTANTS:
                mr = SequenceRunner(sut_factory=M)
                fails = [(i, r) for i, s in enumerate(seqs)
                         if (r := mr.run(s, recs[i]["test_id"], G.name))["outcome"] == "FAIL"]
                first = fails[0][1] if fails else None
                mut_rows.append(dict(strategy=G.name, seed=seed, mutant=M.name, equivalent=M.equivalent,
                                     killed=bool(fails), killing_tests=len(fails),
                                     tests_to_first_kill=fails[0][0] + 1 if fails else "",
                                     first_killing_test=first["test_id"] if first else "",
                                     first_killing_sequence=first["sequence"] if first else "",
                                     failure_details=first["failure_details"] if first else ""))
            print(f"{G.name} seed {seed}: {cov['transitions']} trans, {cov['pairs']} pairs, "
                  f"mutant phase {time.perf_counter() - t0:.1f}s", flush=True)
    write_csv(out / "raw_tests.csv", raw)
    write_csv(out / "coverage.csv", cov_rows)
    write_csv(out / "mutant_results.csv", mut_rows)
    return summarise(cov_rows, mut_rows, out, count, max_length, seeds)


def summarise(cov_rows, mut_rows, out, count, max_length, seeds):
    S = {"config": dict(count=count, max_length=max_length, seeds=seeds), "strategies": {}}
    for name in dict.fromkeys(r["strategy"] for r in cov_rows):
        cr = [r for r in cov_rows if r["strategy"] == name]
        mr = [r for r in mut_rows if r["strategy"] == name]
        scores, union = [], {}
        for seed in seeds:
            res = {r["mutant"]: dict(killed=r["killed"], equivalent=r["equivalent"]) for r in mr if r["seed"] == seed}
            scores.append(mutation_summary(res)["score"])
            for m, v in res.items():
                union[m] = dict(killed=v["killed"] or union.get(m, v)["killed"], equivalent=v["equivalent"])
        real = [r for r in mr if not r["equivalent"]]
        budget = {n: mean([mean([1 if (r["tests_to_first_kill"] != "" and r["tests_to_first_kill"] <= n) else 0
                                   for r in real if r["seed"] == s]) for s in seeds]) for n in BUDGETS}
        f = lambda k: round(mean([r[k] for r in cr]), 4)
        S["strategies"][name] = dict(
            state_cov=f("state_cov"), transition_cov=f("transition_cov"), pair_cov=f("pair_cov"),
            pair_cov_min=min(r["pair_cov"] for r in cr), pair_cov_max=max(r["pair_cov"] for r in cr),
            mutation_score_mean=round(mean(scores), 4), mutation_score_min=min(scores),
            union_summary=mutation_summary(union), gen_time_s=f("gen_time_s"), exec_time_s=f("exec_time_s"),
            duplicate_ratio=f("duplicate_ratio"), mean_length=f("mean_length"),
            reference_failures=sum(r["reference_failures"] for r in cr),
            mean_tests_to_first_kill=round(mean([r["tests_to_first_kill"] for r in real if r["killed"]]), 2),
            kill_by_budget={str(k): round(v, 4) for k, v in budget.items()},
            per_mutant={m: dict(killed_in_seeds=sum(r["killed"] for r in mr if r["mutant"] == m),
                                mean_tests_to_first_kill=(round(mean([r["tests_to_first_kill"] for r in mr
                                    if r["mutant"] == m and r["killed"]]), 1) if any(r["killed"] for r in mr if r["mutant"] == m) else None),
                                mean_killing_tests=round(mean([r["killing_tests"] for r in mr if r["mutant"] == m]), 1))
                        for m in dict.fromkeys(r["mutant"] for r in mr)})
    (out / "summary.json").write_text(json.dumps(S, indent=2, default=str))
    write_md(S, out); write_charts(S, out)
    return S


def write_md(S, out):
    st_ = S["strategies"]; names = list(st_)
    L = ["| Strategy | State cov | Transition cov | Pair cov (min-max) | Mutation score | Mean tests to 1st kill | Gen s | Exec s | Dup. ratio |", "|---|---|---|---|---|---|---|---|---|"]
    for n, s in st_.items():
        L.append(f"| {n} | {s['state_cov']:.0%} | {s['transition_cov']:.0%} | {s['pair_cov']:.1%} ({s['pair_cov_min']:.1%}-{s['pair_cov_max']:.1%}) | "
                 f"{s['mutation_score_mean']:.0%} | {s['mean_tests_to_first_kill']} | {s['gen_time_s']} | {s['exec_time_s']} | {s['duplicate_ratio']:.1%} |")
    L += ["", "Mutation score by test budget (first N sequences, mean over seeds):", "", "| Strategy | " + " | ".join(f"N={b}" for b in BUDGETS) + " |", "|---|" + "---|" * len(BUDGETS)]
    for n, s in st_.items():
        L.append(f"| {n} | " + " | ".join(f"{s['kill_by_budget'][str(b)]:.0%}" for b in BUDGETS) + " |")
    L += ["", "Per mutant: killed in X/5 seeds, mean tests-to-first-kill:", "", "| Mutant | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for m in st_[names[0]]["per_mutant"]:
        L.append(f"| {m} | " + " | ".join(f"{st_[n]['per_mutant'][m]['killed_in_seeds']}/{len(S['config']['seeds'])}, {st_[n]['per_mutant'][m]['mean_tests_to_first_kill']}" for n in names) + " |")
    (out / "summary.md").write_text("\n".join(L) + "\n")


def _svg_bars(path, title, series, groups, ymax=1.0, fmt="{:.0%}"):
    """series: {name: [value per group]}; grouped bar chart as plain SVG."""
    W, H, pad = 760, 380, 60
    cols = ["#2a6fbb", "#e08a1e", "#3a9a5b"]
    gw = (W - 2 * pad) / len(groups); bw = gw / (len(series) + 1)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="white"/><text x="{W/2}" y="22" text-anchor="middle" font-size="15">{title}</text>']
    for t in range(0, 6):
        y = H - pad - (H - 2 * pad) * t / 5
        o.append(f'<line x1="{pad}" x2="{W-pad}" y1="{y}" y2="{y}" stroke="#ddd"/><text x="{pad-6}" y="{y+4}" text-anchor="end">{fmt.format(ymax*t/5)}</text>')
    for gi, g in enumerate(groups):
        o.append(f'<text x="{pad+gw*gi+gw/2}" y="{H-pad+18}" text-anchor="middle">{g}</text>')
        for si, (n, vals) in enumerate(series.items()):
            h = (H - 2 * pad) * min(vals[gi] / ymax, 1); x = pad + gw * gi + bw * (si + 0.5)
            o.append(f'<rect x="{x}" y="{H-pad-h}" width="{bw*0.9}" height="{h}" fill="{cols[si%3]}"/><text x="{x+bw*0.45}" y="{H-pad-h-3}" text-anchor="middle" font-size="10">{fmt.format(vals[gi])}</text>')
    for si, n in enumerate(series):
        o.append(f'<rect x="{pad+si*170}" y="{H-22}" width="12" height="12" fill="{cols[si%3]}"/><text x="{pad+si*170+16}" y="{H-12}">{n}</text>')
    path.write_text("\n".join(o + ["</svg>"]))


def write_charts(S, out):
    s = S["strategies"]
    _svg_bars(out / "coverage.svg", "Coverage by strategy (mean of seeds)",
              {n: [v["state_cov"], v["transition_cov"], v["pair_cov"]] for n, v in s.items()}, ["State", "Transition", "Transition-pair"])
    _svg_bars(out / "mutation_by_budget.svg", "Mutation score vs. number of sequences executed",
              {n: [v["kill_by_budget"][str(b)] for b in BUDGETS] for n, v in s.items()}, [f"N={b}" for b in BUDGETS])
    mx = max(v["gen_time_s"] + v["exec_time_s"] for v in s.values())
    _svg_bars(out / "time.svg", "Time per 500 sequences (s): generation | execution",
              {"generation": [v["gen_time_s"] for v in s.values()], "execution": [v["exec_time_s"] for v in s.values()]},
              list(s), ymax=mx, fmt="{:.2f}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--count", type=int, default=500); a.add_argument("--max-length", type=int, default=20)
    a.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5]); a.add_argument("--out", default="results")
    a = a.parse_args()
    run(a.count, a.max_length, a.seeds, Path(a.out))
    print(Path(a.out, "summary.md").read_text())

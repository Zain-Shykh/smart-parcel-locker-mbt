# Smart Parcel Locker - Model-Based Testing

Python 3.10+ (tested 3.12). **No third-party dependencies** (charts are plain SVG).

## Layout
| File | Role |
|---|---|
| `locker/sut.py`, `types.py` | provided SUT and types (unchanged) |
| `locker/model.py` | independent executable state machine, invariants, input alphabet, coverage universe |
| `locker/generators.py` | Strategy A random walk, B coverage-guided, C transition-pair planning |
| `locker/runner.py` | executor + oracle (result, full snapshot, invariants, no-mutation-on-reject) |
| `locker/metrics.py` | state / transition / pair coverage, mutation score |
| `locker/mutants.py` | 14 mutants (13 killable, 1 equivalent) |
| `locker/experiment.py` | experiment runner -> `results/` |
| `demo.py` | short demonstration |
| `REPORT.md` | technical report |

## Run
```
python3 -m unittest discover -s tests -v      # smoke + model + framework tests
python3 demo.py                                # model, generation, execution, fault detection
python3 -m locker.experiment                   # full experiment: 3 strategies x 5 seeds x 500 seqs x len<=20 x 14 mutants (~1 min)
python3 -m locker.experiment --count 100 --seeds 1 2   # smaller run, other output: --out DIR
```
Run one strategy alone:
```python
from locker.generators import CoverageGuidedGenerator   # or RandomWalkGenerator / TransitionPairGenerator
seqs = CoverageGuidedGenerator(seed=1, max_length=20).generate(500)
from locker.runner import SequenceRunner; rec = SequenceRunner().run(seqs[0], "t0", "coverage_guided")
```
Run against one mutant: `SequenceRunner(sut_factory=locker.mutants.M03_RetrieveNoAuth)`.

## Outputs (`results/`)
`raw_tests.csv` (every test on reference SUT: id, strategy, sequence, initial/final states, expected/actual result, outcome, details), `coverage.csv`, `mutant_results.csv` (per strategy/seed/mutant, first killing test + sequence), `summary.json`, `summary.md`, `coverage.svg`, `mutation_by_budget.svg`, `time.svg`.
Results are deterministic for given seeds (timings vary by machine).

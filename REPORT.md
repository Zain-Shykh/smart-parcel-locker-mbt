# Technical Report - Model-Based Testing of a Smart Parcel Locker

## 1. Introduction
An executable state-machine model of one locker compartment drives three test-generation strategies. A runner/oracle compares the reference SUT (and 14 mutants) against the model. All numbers below come from `python3 -m locker.experiment` (raw data in `results/`). AI-assisted coding (Claude) was used; all code is reviewed and explainable.

## 2. Requirements and assumptions
Rules 1-12 of `data/requirements.md` are implemented. Added assumptions:
- **A1** Reject precedence: state check, then credential, then expiry flag (e.g. DEPOSIT with a wrong code in AVAILABLE is `not_reserved`).
- **A2** Observable contract = `Result(accepted, message)` + full `Snapshot`; messages are compared (they are the only rejection-reason channel).
- **A3** INVALID_ACCESS is rejected in every state, never mutates.
- **A4** EXPIRE/CANCEL/RETRIEVE clear customer, reservation and retrieval codes (rules 3, 7, 8). DISABLE of OCCUPIED/RESERVED is rejected (rule 9, answers "maintenance while parcel inside": no).
- **A5** Customer IDs drawn from {C1, C2}; customer id is never empty. One compartment only.
- State variables: `customer_id`, `reservation_code = R-<cust>`, `retrieval_code = P-<cust>` (same as snapshot fields; no hidden state).

## 3. State-machine model (`locker/model.py`)
States AVAILABLE, RESERVED, OCCUPIED, MAINTENANCE. Events = 8 operations.

| Op | Accepted when (guard) | Effect | Rejected -> message |
|---|---|---|---|
| RESERVE | AVAILABLE | RESERVED, set customer, `R-c` | `locker_not_available` |
| CANCEL | RESERVED | AVAILABLE, clear | `not_reserved` |
| DEPOSIT | RESERVED and code==`R-c` | OCCUPIED, `P-c` | `not_reserved` / `invalid_reservation_code` |
| RETRIEVE | OCCUPIED and code==`P-c` | AVAILABLE, clear | `no_parcel` / `invalid_retrieval_code` |
| EXPIRE | RESERVED and expired=True | AVAILABLE, clear | `not_reserved` / `not_expired` |
| DISABLE | AVAILABLE | MAINTENANCE | `cannot_disable` |
| ENABLE | MAINTENANCE | AVAILABLE | `not_in_maintenance` |
| INVALID_ACCESS | never | - | `invalid_access` |

Invariants (`check_invariants`): INV1 AVAILABLE/MAINTENANCE hold no customer/credentials; INV2 RESERVED has customer, `R-<cust>`, no retrieval code; INV3/INV4 OCCUPIED has customer and `P-<cust>`; plus rule 12 (rejected => unchanged).

**Independence from the SUT.** The model never imports or calls the SUT. It is structured differently: a pure `_decide` (guard + outcome) separated from `_apply` (effects, run only on acceptance), so "rejection never mutates" holds by construction instead of by careful coding. The oracle adds model-free checks (invariants, SUT-snapshot-unchanged-on-reject), so a requirement misreading shared by model and SUT is still partly caught by invariants. Residual risk: model and SUT written from the same text can share a misreading (see 9).

## 4. Test generation (`locker/generators.py`)
Shared input alphabet (`candidate_commands`): for every state, valid and invalid inputs - correct code, `WRONG`, code of the wrong kind (`P-` for deposit, `R-` for retrieve), other customer's code, expired True/False, both customers.
Sequences start from a fresh locker; length is controlled by `max_length` (=20); seeds via `random.Random(seed)`.

- **A Random walk** - uniform operation choice, then uniform input variant; length uniform in [1,20]; no feedback. + trivially cheap, unbiased; - rare deep states reached by luck, redundant sequences.
- **B Coverage-guided** - at every step peek every candidate on a model clone and choose among those with the least-executed transition (uncovered first, ties random); counters persist across the 500 sequences. + drives transition coverage and finds rare states quickly; - one-step lookahead, label-level coverage blind to data values, ~10x slower generation (cloning).
- **C Transition-pair** - picks a random *uncovered pair* (t1,t2), plans a BFS shortest path on the model to t1, executes t1,t2, then extends greedily choosing commands that complete further uncovered pairs. + reaches 100% pair coverage, nearly no duplicates; - slowest generation, still label-level.
All three differ in mechanism (no feedback / greedy feedback / goal-directed planning), not just parameters.

## 5. Execution and oracle (`locker/runner.py`)
Fresh SUT and model per sequence. After each command: (1) result (accepted, message) equals model, (2) complete snapshot equals model, (3) invariants on SUT snapshot, (4) rejected command left SUT snapshot unchanged, (5) SUT exceptions are failures. First divergence is recorded (index, expected/actual, whole sequence). Records hold test id, strategy, sequence, initial state, expected/actual result, expected/actual final state, PASS/FAIL, details (`raw_tests.csv`). The reference SUT passed all 7500 tests (0 failures).

## 6. Mutation testing (`locker/mutants.py`)
14 mutants (13 non-equivalent). Detection = any sequence fails.

| Mutant | Defect | Exposed by (example, from `mutant_results.csv`) |
|---|---|---|
| M01 | RESERVE accepted in OCCUPIED | DEPOSIT then RESERVE: result/state mismatch |
| M02 | DEPOSIT accepted in MAINTENANCE | DISABLE, DEPOSIT |
| M03 | RETRIEVE without valid code | RESERVE, DEPOSIT, RETRIEVE(WRONG) |
| M04 | EXPIRE ignores flag | RESERVE, EXPIRE(expired=False) |
| M05 | retrieval code retained after retrieve | full lifecycle; snapshot + INV1 violated (see demo) |
| M06 | CANCEL accepted in OCCUPIED | deposit then CANCEL |
| M07 | rejected wrong-code DEPOSIT erases reservation code | RESERVE, DEPOSIT(WRONG): snapshot diff + "rejected mutated state" |
| M08 | DISABLE accepted in RESERVED | RESERVE, DISABLE |
| M09 | ENABLE accepted in AVAILABLE | ENABLE on fresh locker |
| M10 | INVALID_ACCESS cancels reservation | RESERVE, INVALID_ACCESS |
| M11 | EXPIRE leaves customer_id | RESERVE, EXPIRE(True): snapshot diff |
| M12 | DEPOSIT accepts any `R-*` code | RESERVE(C1), DEPOSIT(code=R-C2) - needs cross-customer input |
| M13 | rejected RESERVE overwrites customer_id | RESERVE(C1), RESERVE(C2) - needs 2nd customer |
| M14 | RESERVE also sets retrieval_code=None | **equivalent**: retrieval_code is already None in AVAILABLE, the mutation is unobservable; excluded from score, survived in 100% of runs |

Mutation score = killed / 13. M14 is reported separately.

## 7. Experimental setup
3 strategies x 5 seeds (1-5) x 500 sequences, max length 20, 14 mutants; Python 3.12, Linux, single process. Metrics: state coverage (4), transition coverage (35 = every reachable (src,op,outcome,dst); accepted and rejected outcomes are distinct transitions, enumerated by BFS over the model), **transition-pair coverage** (305 pairs (t1,t2) with t1.dst==t2.src, counted only for adjacent commands in the same sequence), mutation score, generation/execution time, duplicate-sequence ratio, plus mutation score as a function of test budget N (first N sequences).

## 8. Results (mean over 5 seeds)
| Strategy | State | Transition | Pair (min-max) | Mutation score | Mean tests to 1st kill | Gen s | Exec s | Dup. |
|---|---|---|---|---|---|---|---|---|
| random_walk | 100% | 100% | 94.3% (91.8-97.0) | 100% | 19.23 | 0.11 | 0.06 | 3.1% |
| coverage_guided | 100% | 100% | 94.0% (93.4-94.4) | 100% | 7.26 | 1.36 | 0.06 | 3.9% |
| transition_pair | 100% | 100% | 100.0% (100-100) | 100% | 5.75 | 2.64 | 0.06 | 0.1% |

Mutation score vs budget:
| Strategy | N=1 | 5 | 10 | 25 | 50 | 100 | 500 |
|---|---|---|---|---|---|---|---|
| random_walk | 15% | 51% | 69% | 83% | 94% | 97% | 100% |
| coverage_guided | 14% | 52% | 75% | 98% | 100% | 100% | 100% |
| transition_pair | 11% | 65% | 91% | 98% | 100% | 100% | 100% |

Per-mutant detail: `results/summary.md`. Charts: `results/coverage.svg`, `mutation_by_budget.svg`, `time.svg`.

## 9. Discussion
- **Highest state/transition coverage:** all tie at 100%/100% at 500 sequences (the model is small). **Pair coverage:** only C reaches 100%; A and B plateau at ~94% (random never produced some rare 2-step combinations in 500 tests).
- **Most mutants:** all strategies kill 13/13 (score 100%) in every seed at 500 tests; the plain budget protocol cannot separate them. Separation appears with small budgets: at N=10 C 91% vs B 75% vs A 69%; at N=50 A is still 94%.
- **Higher coverage => higher score?** Not at full budget (A and B have lower pair coverage yet equal score), and not always per mutant: M12 (cross-customer code) and M13 (second customer on rejected RESERVE) were found faster by A (5.8 / 4.0 tests) than by B (16.4 / 12.0) and C (12.4 / 14.6). Label-level coverage ignores data values, so a coverage-saturating strategy can steer away from the input that matters. M05 (stale credentials) needed a mean of 149 tests under A but 8.4 (B) and 4.6 (C) because it requires a *completed* lifecycle, which pair/coverage guidance builds deliberately.
- **Efficiency:** A generates ~12-24x faster (0.11s vs 1.36s B, 2.64s C); execution time is equal (0.06s). Per detected mutant C is cheapest in tests (5.75 to first kill); in wall clock A is cheapest to produce 500 tests but needs 3.3x more tests to first kill. At this model size every run takes seconds, so test count, not time, is the meaningful cost.
- **Redundancy:** A and B produced 3-4% duplicate sequences (short sequences repeat), C 0.1%.
- **Limitations / threats to validity:** single small model (4 states) so coverage saturates; 14 hand-written mutants chosen by me (author bias; mutants resemble the oracle's checks); model and oracle derived by one person from the same text as the SUT, so a shared misreading is possible; A1/A2 assumptions (reject precedence, message compare) would flag a differently-ordered but valid SUT; 5 seeds give small-sample variance (pair-cov range reported); timings are single-machine wall-clock; coverage is abstract (labels), not data-aware; the mutation score of 100% means the experiment is ceiling-limited, so ranking relies on the budget curve and tests-to-kill.

## 10. Conclusion
All strategies reach full state/transition coverage and full mutation score with 500 sequences; transition-pair planning gives complete pair coverage and the best early fault detection per test, coverage-guided is a cheap middle ground, and random is fastest to generate but needs more tests and is weakest on faults needing deep sequences (M05). Coverage did not predict detection for data-dependent faults (M12, M13). Improvements: data-aware coverage (customer/code classes), longer-lookahead or mutant-feedback guidance, more compartments, larger mutant set including instructor variants.

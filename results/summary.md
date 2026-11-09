| Strategy | State cov | Transition cov | Pair cov (min-max) | Mutation score | Mean tests to 1st kill | Gen s | Exec s | Dup. ratio |
|---|---|---|---|---|---|---|---|---|
| random_walk | 100% | 100% | 94.3% (91.8%-97.0%) | 100% | 19.23 | 0.1131 | 0.0584 | 3.1% |
| coverage_guided | 100% | 100% | 94.0% (93.4%-94.4%) | 100% | 7.26 | 1.3647 | 0.0588 | 3.9% |
| transition_pair | 100% | 100% | 100.0% (100.0%-100.0%) | 100% | 5.75 | 2.6411 | 0.0649 | 0.1% |

Mutation score by test budget (first N sequences, mean over seeds):

| Strategy | N=1 | N=5 | N=10 | N=25 | N=50 | N=100 | N=500 |
|---|---|---|---|---|---|---|---|
| random_walk | 15% | 51% | 69% | 83% | 94% | 97% | 100% |
| coverage_guided | 14% | 52% | 75% | 98% | 100% | 100% | 100% |
| transition_pair | 11% | 65% | 91% | 98% | 100% | 100% | 100% |

Per mutant: killed in X/5 seeds, mean tests-to-first-kill:

| Mutant | random_walk | coverage_guided | transition_pair |
|---|---|---|---|
| M01_reserve_when_occupied | 5/5, 14.0 | 5/5, 13.6 | 5/5, 5.2 |
| M02_deposit_in_maintenance | 5/5, 8.6 | 5/5, 2.8 | 5/5, 1.6 |
| M03_retrieve_no_auth | 5/5, 19.2 | 5/5, 7.6 | 5/5, 3.2 |
| M04_expire_ignores_flag | 5/5, 8.8 | 5/5, 4.0 | 5/5, 2.8 |
| M05_stale_retrieval_code | 5/5, 149.0 | 5/5, 8.4 | 5/5, 4.6 |
| M06_cancel_when_occupied | 5/5, 26.0 | 5/5, 13.6 | 5/5, 6.8 |
| M07_bad_deposit_mutates | 5/5, 2.8 | 5/5, 2.8 | 5/5, 3.8 |
| M08_disable_when_reserved | 5/5, 2.0 | 5/5, 4.4 | 5/5, 5.6 |
| M09_enable_when_available | 5/5, 2.2 | 5/5, 1.8 | 5/5, 2.8 |
| M10_invalid_access_cancels | 5/5, 2.8 | 5/5, 5.0 | 5/5, 6.2 |
| M11_expire_keeps_customer | 5/5, 4.8 | 5/5, 2.0 | 5/5, 5.2 |
| M12_deposit_prefix_only | 5/5, 5.8 | 5/5, 16.4 | 5/5, 12.4 |
| M13_rejected_reserve_mutates | 5/5, 4.0 | 5/5, 12.0 | 5/5, 14.6 |
| M14_equivalent_reserve_resets_retrieval | 0/5, None | 0/5, None | 0/5, None |

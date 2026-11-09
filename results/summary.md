| Strategy | State cov | Transition cov | Pair cov (min-max) | Mutation score | Mean tests to 1st kill | Gen s | Exec s | Dup. ratio |
|---|---|---|---|---|---|---|---|---|
| random_walk | 100% | 100% | 94.8% (92.1%-96.7%) | 100% | 16.08 | 0.0667 | 0.0341 | 3.1% |
| coverage_guided | 100% | 100% | 94.4% (94.1%-95.4%) | 100% | 7.15 | 0.7717 | 0.0331 | 3.2% |
| transition_pair | 100% | 100% | 100.0% (100.0%-100.0%) | 100% | 6.4 | 1.5242 | 0.038 | 0.3% |

Mutation score by test budget (first N sequences, mean over seeds):

| Strategy | N=1 | N=5 | N=10 | N=25 | N=50 | N=100 | N=500 |
|---|---|---|---|---|---|---|---|
| random_walk | 12% | 48% | 63% | 85% | 92% | 97% | 100% |
| coverage_guided | 15% | 54% | 80% | 98% | 100% | 100% | 100% |
| transition_pair | 11% | 65% | 89% | 97% | 97% | 100% | 100% |

Per mutant: killed in X/5 seeds, mean tests-to-first-kill:

| Mutant | random_walk | coverage_guided | transition_pair |
|---|---|---|---|
| M01_reserve_when_occupied | 5/5, 15.0 | 5/5, 14.4 | 5/5, 4.8 |
| M02_deposit_in_maintenance | 5/5, 8.6 | 5/5, 2.8 | 5/5, 1.8 |
| M03_retrieve_no_auth | 5/5, 36.2 | 5/5, 5.8 | 5/5, 5.4 |
| M04_expire_ignores_flag | 5/5, 8.8 | 5/5, 4.0 | 5/5, 4.4 |
| M05_stale_retrieval_code | 5/5, 83.0 | 5/5, 8.2 | 5/5, 4.6 |
| M06_cancel_when_occupied | 5/5, 22.0 | 5/5, 16.2 | 5/5, 8.4 |
| M07_bad_deposit_mutates | 5/5, 3.2 | 5/5, 2.8 | 5/5, 3.8 |
| M08_disable_when_reserved | 5/5, 2.0 | 5/5, 4.4 | 5/5, 5.2 |
| M09_enable_when_available | 5/5, 2.2 | 5/5, 1.8 | 5/5, 2.8 |
| M10_invalid_access_cancels | 5/5, 2.8 | 5/5, 5.0 | 5/5, 5.0 |
| M11_expire_keeps_customer | 5/5, 4.8 | 5/5, 2.0 | 5/5, 4.8 |
| M12_deposit_prefix_only | 5/5, 16.4 | 5/5, 14.4 | 5/5, 16.2 |
| M13_rejected_reserve_mutates | 5/5, 4.0 | 5/5, 11.2 | 5/5, 16.0 |
| M14_equivalent_reserve_resets_retrieval | 0/5, None | 0/5, None | 0/5, None |

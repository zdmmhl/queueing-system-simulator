# Historical Design Report

> Historical saved results, not fresh reruns. Original figures are omitted. Confidence intervals for allocations 6 and 7 overlap: the smallest observed mean does not establish statistically significant superiority. Use the current README for execution; filenames may differ.

# COMP9334 Project Report 

Author identifiers omitted.

## 1. Objective

The design task is to choose `n0` when total servers are fixed at `n=12`.  
The objective is to minimise `W = 0.95 * T0 + 0.052 * T1`.

- `T0` is the mean response time of completed Class 0 jobs.
- `T1` is the mean response time of Class 1 jobs.

This objective compares system-level performance, not just one class.

---

## 2. Simulation Configuration

The experiment uses the fixed design parameters from Section 5.2:

- `n=12`
- `Tlimit=2.5`
- Interarrival parameters: `lambda=2.7`, `a2l=0.85`, `a2u=1.21`
- Indication probability: `p0=0.81`
- Group 0 service parameters: `alpha0=0.5`, `beta0=4.7`, `theta0=1.9`
- Group 1 service parameters: `alpha1=2.2`, `theta1=2.4`
- Weights: `w0=0.95`, `w1=0.052`

I evaluated all feasible allocations `n0=1..11`.  
Each configuration uses 30 independent replications.  
Each replication runs to `time_end=3000`.  
Jobs with `dep_time <= 500` are removed as warmup.  
The base seed is `20260412` for reproducibility.

---

## 3. Output Artifacts

The design workflow is automated by `design_experiment.py`.  
It produces:

- `design_results/per_replication.csv` for replication-level results
- `design_results/summary_by_n0.csv` for means and 95% confidence intervals
- `design_results/best_n0.txt` for the final selected design
- `design_results/experiment_parameters.txt` for full parameter records

The folder `design_results/work/config` stores the generated input files for this design run, and `design_results/work/output` stores run-time simulation outputs such as `mrt_0.txt` and `dep_0.txt`.  
The final report analysis uses the summary artifacts in the root of `design_results`, especially `best_n0.txt`, `summary_by_n0.csv`, and `per_replication.csv`.

---

## 4. Results

From `design_results/best_n0.txt`, the best observed design is `n0=7`.  
Its weighted mean is `W_mean=1.003931`.  
Its 95% confidence interval is `[1.001127, 1.006736]`.

The full comparison from `design_results/summary_by_n0.csv` is shown in Table 1.

| n0 | W_mean | W_95CI_low | W_95CI_high | T0_mean | T1_mean |
|---|---:|---:|---:|---:|---:|
| 1 | 798.704830 | 791.284219 | 806.125441 | 840.536780 | 3.747870 |
| 2 | 6.883655 | 6.097194 | 7.670115 | 7.039239 | 3.776491 |
| 3 | 1.217799 | 1.207849 | 1.227749 | 1.076135 | 3.759057 |
| 4 | 1.046602 | 1.043845 | 1.049358 | 0.895383 | 3.768993 |
| 5 | 1.012929 | 1.009889 | 1.015969 | 0.858635 | 3.792814 |
| 6 | 1.006241 | 1.003849 | 1.008633 | 0.850378 | 3.815040 |
| 7 | 1.003931 | 1.001127 | 1.006736 | 0.847111 | 3.830302 |
| 8 | 1.021067 | 1.015030 | 1.027103 | 0.847540 | 4.151994 |
| 9 | 1.092751 | 1.074335 | 1.111167 | 0.846725 | 5.545433 |
| 10 | 6.813245 | 5.938337 | 7.688152 | 0.847867 | 115.534066 |
| 11 | 48.532140 | 47.524611 | 49.539668 | 0.847758 | 917.822489 |

Table 1: Mean response time results by `n0`.

[Original screenshot omitted.]

Figure 1: Weighted mean response time `W` by `n0` with 95% CI.

[Original screenshot omitted.]

Figure 2: Mean response time `T0` and `T1` by `n0`.

Table 1, Figure 1, and Figure 2 show a clear trade-off:

- When `n0` is too small, `T0` grows sharply because Group 0 is congested.
- When `n0` is too large, `T1` grows sharply because Group 1 is under-provisioned.
- The best region is around `n0=6` to `n0=7`.
- `n0=7` gives the smallest observed `W_mean`.

---

### 4.1 Random Generator Verification for Criterion 1(b)

I verified the random generators with a large independent sample using the same parameter set as the design experiment. The verification covers the three required components.

- Inter-arrival generator: sampled exponential and uniform components, and their product.
- Server-group choice generator: checked empirical probabilities against `p0=0.81` and `1-p0=0.19`.
- Service time generators: checked Group 0 and Group 1 samplers against their target distributions.

The numerical summary is shown in Table 2.

| Metric | Theoretical | Empirical | Absolute Error |
|---|---:|---:|---:|
| Exponential component mean | 0.370370 | 0.369367 | 0.001003 |
| Uniform component mean | 1.030000 | 1.030114 | 0.000114 |
| Inter-arrival mean | 0.381481 | 0.380570 | 0.000911 |
| Group 0 probability | 0.810000 | 0.809365 | 0.000635 |
| Group 1 probability | 0.190000 | 0.190635 | 0.000635 |
| Group 0 service mean | 0.928202 | 0.927520 | 0.000682 |
| Group 1 service mean | 3.771429 | 3.763205 | 0.008224 |

Table 2: Random generator verification summary.

[Original screenshot omitted.]

Figure 4: Inter-arrival component verification.

[Original screenshot omitted.]

Figure 5: Server-group probability verification.

[Original screenshot omitted.]

Figure 6: Service time distribution verification.

Table 2 and Figure 4 to Figure 6 show close agreement between empirical samples and the target model. 

In Figure 4, the empirical histograms follow the theoretical curves well for both exponential and uniform components, and there is no obvious systematic skew from the target shapes. 

In Figure 5, empirical group probabilities are very close to the theoretical values for Group 0 and Group 1, which supports correct implementation of the Bernoulli group selector. 

In Figure 6, both service-time histograms are smooth and consistent with their corresponding theoretical density lines over the main support region, with only minor tail noise expected from finite sampling.

These observations, together with the small absolute errors in Table 2, support that the random generators used in random mode are consistent with the required distributions.

---

## 5. Parameter Choice 

Key parameter choices:

- Replications per `n0`: `30`
- Simulation horizon per replication: `time_end=3000`
- Warmup removal rule: discard jobs with `dep_time <= 500`
- Candidate set: `n0=1..11`

These settings were chosen to balance stability and runtime. In random mode, one run can fluctuate a lot, so using 30 replications reduces noise and makes the estimate of `W` more reliable for close candidates such as `n0=6` and `n0=7`. The value `time_end=3000` provides enough completed jobs after warmup, so the response time means are based on a meaningful sample size. Warmup removal reduces initial empty-system bias and is applied uniformly to all candidates, which keeps the comparison fair. Overall, this setup gives clear separation between weak and strong designs while keeping the full sweep practical to run and repeat.

## 6. Confidence Interval Method for Selecting `n0`

Method steps:

- For each `n0`, run 30 replications after applying the same warmup rule.
- Compute one weighted value per replication: `W = 0.95 * T0 + 0.052 * T1`.
- Estimate `W_mean` and the 95% confidence interval for each candidate.
- Compare candidates by mean value and interval consistency.

The decision combines point estimates and uncertainty. First, I locate the low-`W` region from `W_mean`. Then I check whether this region remains strong when interval uncertainty is considered. Results show the best region is around `n0=6` to `n0=7`, and `n0=7` has the lowest observed `W_mean` with a tight 95% interval. Candidates with very small `n0` suffer from high `T0`, while candidates with very large `n0` suffer from high `T1`, so both ends are clearly suboptimal. Based on this interval-based comparison, `n0=7` is selected as the final design.

Figure 3 shows replication variability and confirms that the selected design region is stable across repeated runs.

[Original screenshot omitted.]

Figure 3: Replication-level `W` by `n0`.

Figure 3 also shows that extreme allocations are consistently poor across repeated runs. The distributions for very small `n0` and very large `n0` are much higher, which means those designs are not competitive even after accounting for random variation. In contrast, the region around `n0=6` and `n0=7` remains low and comparatively concentrated across replications. This supports that the final design choice is stable under repeated simulation, not a one-run artifact.

## 7. Reproducibility Statement

To improve reproducibility, I wrote a design experiment script that runs the full pipeline and saves all key artifacts. To reproduce the design results, run: python3 design_experiment.py. This uses the default settings replications=30, time_end=3000, warmup=500, and outdir=design_results.

The script `design_experiment.py` performs the same sweep and processing steps every time. The parameter file `design_results/experiment_parameters.txt` records the full run configuration, including replication count, simulation length, warmup rule, and random seed policy. The file `design_results/per_replication.csv` preserves replication-level outputs, and `design_results/summary_by_n0.csv` preserves aggregated means and confidence intervals. Because the seed schedule is deterministic, rerunning the same command reproduces the same result files on the same implementation.

The file `design_results/best_n0.txt` is the direct summary of the final design choice. It records the selected `n0`, the corresponding `W_mean`, and the 95% confidence interval.

[Original screenshot omitted.]

Figure 7: Screenshot of `best_n0.txt`.

---

## 8. Supporting Materials Included

The submitted supporting materials include:

- `main.py` as the simulation engine
- `run_test.sh` as the required test runner entry
- `design_experiment.py` for the design sweep and confidence interval statistics
- `design_results/*` as the exact result artifacts used in this section
- `generate_report_artifacts.py` for generating all report figures and RNG verification artifacts

These files allow the whole analysis pipeline to be re-executed and verified.

---

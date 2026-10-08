# Historical results

For the recorded model and configuration, `n0=7` has the smallest observed weighted mean: `W_mean=1.003931`, with the recorded approximate 95% interval `[1.001127, 1.006736]`.

The experiment uses 30 replications per allocation, a simulation horizon of 3000, and excludes departures at or before time 500 as warmup. The interval uses `1.96 * sd / sqrt(n)`; adjacent candidates' intervals overlap. The observation does not establish a generally optimal server allocation or statistical superiority over every neighbouring candidate.

The root working source and submitted source differ. This package deliberately chooses the submitted source as its baseline. Provenance and immutable hashes are in the parent review manifest.

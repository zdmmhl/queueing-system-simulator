# Queueing System Simulator

A discrete-event simulation and server-allocation experiment with trace/random modes, repeated runs and recorded results.

## Contents

- `main.py`: simulation engine.
- `design_experiment.py`: generated random-mode configurations and allocation sweep.
- `generate_report_artifacts.py`: analysis figures and generator checks.
- `historical-results/`: original replication tables and parameter records.

## Experiment entry point

```bash
python -m pip install -r requirements.txt
python design_experiment.py --replications 30 --time-end 3000 --warmup 500 --outdir runs/design
```

The experiment script generates its own configurations and recreates the specified output directory; use a dedicated disposable run directory. Full sweeps were not rerun here. See [historical interpretation](docs/results.md) for scope and uncertainty.

A small independently authored trace is in `examples/simple-trace`. Run `python main.py 0 --config-dir examples/simple-trace --output-dir runs/simple-trace`. Its two tasks are expected to depart at 1 and 2, respectively, with mean response time 1 in each class. This check passed during preparation.


## Provenance

Originated in UNSW COMP9334. The source baseline is the `project_submit` source set; teaching inputs and reference outputs are omitted. Historical result tables are retained for traceability.

## Verification status

A synthetic two-task trace passed on 8 October 2026: departures at times 1 and 2 and mean response time 1 for each class. The historical allocation sweep was not rerun.

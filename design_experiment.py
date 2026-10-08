#!/usr/bin/env python3
"""Run design experiments for n0=1..11 and save report-friendly outputs."""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import subprocess
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List, Tuple


W0 = 0.95
W1 = 0.052


def write_random_config(config_dir: Path, test_id: int, n: int, n0: int, t_limit: float, time_end: float) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / f"mode_{test_id}.txt").write_text("random\n", encoding="utf-8")
    (config_dir / f"para_{test_id}.txt").write_text(
        f"{n}\n{n0}\n{t_limit}\n{time_end}\n",
        encoding="utf-8",
    )
    # interarrival: lambda, a2l, a2u
    (config_dir / f"interarrival_{test_id}.txt").write_text("2.7 0.85 1.21\n", encoding="utf-8")
    # service: p0; alpha0 beta0 theta0; alpha1 theta1
    (config_dir / f"service_{test_id}.txt").write_text(
        "0.81\n0.5 4.7 1.9\n2.2 2.4\n",
        encoding="utf-8",
    )


def parse_dep_metrics(dep_file: Path, warmup_dep_time: float) -> Tuple[float, float, float, int, int]:
    t0_vals: List[float] = []
    t1_vals: List[float] = []

    with dep_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            arr_s, dep_s, cls = line.split()
            arr_t = float(arr_s)
            dep_t = float(dep_s)
            if dep_t <= warmup_dep_time:
                continue
            rt = dep_t - arr_t
            if cls == "0":
                t0_vals.append(rt)
            elif cls == "1":
                t1_vals.append(rt)

    t0 = mean(t0_vals) if t0_vals else math.nan
    t1 = mean(t1_vals) if t1_vals else math.nan
    w = W0 * t0 + W1 * t1 if (not math.isnan(t0) and not math.isnan(t1)) else math.nan
    return t0, t1, w, len(t0_vals), len(t1_vals)


def ci95(values: List[float]) -> Tuple[float, float, float]:
    clean = [v for v in values if not math.isnan(v)]
    if not clean:
        return math.nan, math.nan, math.nan
    m = mean(clean)
    if len(clean) == 1:
        return m, m, m
    # Normal approximation (sufficient for moderate replication counts).
    sd = pstdev(clean) * math.sqrt(len(clean) / (len(clean) - 1))
    half = 1.96 * sd / math.sqrt(len(clean))
    return m, m - half, m + half


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replications", type=int, default=30)
    parser.add_argument("--time-end", type=float, default=3000.0)
    parser.add_argument("--warmup", type=float, default=500.0, help="Discard jobs with dep_time <= warmup")
    parser.add_argument("--base-seed", type=int, default=20260412)
    parser.add_argument("--outdir", type=str, default="design_results")
    args = parser.parse_args()

    root = Path.cwd()
    outdir = root / args.outdir
    workdir = outdir / "work"
    config_dir = workdir / "config"
    output_dir = workdir / "output"
    test_id = 0

    if outdir.exists():
        shutil.rmtree(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rep_csv = outdir / "per_replication.csv"
    sum_csv = outdir / "summary_by_n0.csv"
    best_txt = outdir / "best_n0.txt"
    param_txt = outdir / "experiment_parameters.txt"

    per_rows: List[Dict[str, float]] = []

    for n0 in range(1, 12):
        write_random_config(config_dir, test_id, n=12, n0=n0, t_limit=2.5, time_end=args.time_end)
        for r in range(args.replications):
            seed = args.base_seed + n0 * 100000 + r
            cmd = [
                "python",
                "main.py",
                str(test_id),
                "--seed",
                str(seed),
                "--config-dir",
                str(config_dir),
                "--output-dir",
                str(output_dir),
            ]
            subprocess.run(cmd, check=True)
            dep_file = output_dir / f"dep_{test_id}.txt"
            t0, t1, w, n0_count, n1_count = parse_dep_metrics(dep_file, warmup_dep_time=args.warmup)
            per_rows.append(
                {
                    "n0": n0,
                    "replication": r,
                    "seed": seed,
                    "T0": t0,
                    "T1": t1,
                    "W": w,
                    "n_class0": n0_count,
                    "n_class1": n1_count,
                }
            )

    outdir.mkdir(parents=True, exist_ok=True)
    with rep_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["n0", "replication", "seed", "T0", "T1", "W", "n_class0", "n_class1"],
        )
        writer.writeheader()
        writer.writerows(per_rows)

    summary_rows = []
    for n0 in range(1, 12):
        group = [r for r in per_rows if r["n0"] == n0]
        w_values = [r["W"] for r in group]
        t0_values = [r["T0"] for r in group]
        t1_values = [r["T1"] for r in group]
        w_mean, w_lo, w_hi = ci95(w_values)
        t0_mean, t0_lo, t0_hi = ci95(t0_values)
        t1_mean, t1_lo, t1_hi = ci95(t1_values)
        summary_rows.append(
            {
                "n0": n0,
                "W_mean": w_mean,
                "W_ci95_low": w_lo,
                "W_ci95_high": w_hi,
                "T0_mean": t0_mean,
                "T0_ci95_low": t0_lo,
                "T0_ci95_high": t0_hi,
                "T1_mean": t1_mean,
                "T1_ci95_low": t1_lo,
                "T1_ci95_high": t1_hi,
            }
        )

    with sum_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "n0",
                "W_mean",
                "W_ci95_low",
                "W_ci95_high",
                "T0_mean",
                "T0_ci95_low",
                "T0_ci95_high",
                "T1_mean",
                "T1_ci95_low",
                "T1_ci95_high",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    best = min(summary_rows, key=lambda x: x["W_mean"])
    best_txt.write_text(
        (
            "Best n0 by weighted mean response time (W = 0.95*T0 + 0.052*T1)\n"
            f"n0 = {best['n0']}\n"
            f"W_mean = {best['W_mean']:.6f}\n"
            f"W_95CI = [{best['W_ci95_low']:.6f}, {best['W_ci95_high']:.6f}]\n"
        ),
        encoding="utf-8",
    )
    param_txt.write_text(
        (
            "Design experiment parameters\n"
            f"replications = {args.replications}\n"
            f"time_end = {args.time_end}\n"
            f"warmup_departure_time = {args.warmup}\n"
            f"base_seed = {args.base_seed}\n"
            "fixed model params: n=12, Tlimit=2.5, lambda=2.7, a2l=0.85, a2u=1.21,\n"
            "p0=0.81, group0(alpha,beta,theta)=(0.5,4.7,1.9), group1(alpha,theta)=(2.2,2.4)\n"
        ),
        encoding="utf-8",
    )

    print(f"Saved: {rep_csv}")
    print(f"Saved: {sum_csv}")
    print(f"Saved: {best_txt}")
    print(f"Saved: {param_txt}")


if __name__ == "__main__":
    run()

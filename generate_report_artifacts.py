#!/usr/bin/env python3
"""Generate all report artifacts: design plots + RNG verification artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def resolve_design_input_dir(preferred: str) -> Path:
    p = Path(preferred)
    if p.exists():
        return p
    fallback = Path("design_results_smoke")
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"Cannot find '{preferred}' or fallback 'design_results_smoke'.")


def plot_w_ci(summary: pd.DataFrame, out_path: Path) -> None:
    x = summary["n0"].to_numpy()
    y = summary["W_mean"].to_numpy()
    yerr_low = y - summary["W_ci95_low"].to_numpy()
    yerr_high = summary["W_ci95_high"].to_numpy() - y

    plt.figure(figsize=(8, 4.8))
    plt.errorbar(x, y, yerr=[yerr_low, yerr_high], fmt="o-", capsize=4, linewidth=1.6)
    plt.xlabel("n0")
    plt.ylabel("Weighted mean response time (W)")
    plt.title("W vs n0 with 95% CI")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_t0_t1(summary: pd.DataFrame, out_path: Path) -> None:
    x = summary["n0"].to_numpy()
    t0 = summary["T0_mean"].to_numpy()
    t1 = summary["T1_mean"].to_numpy()

    plt.figure(figsize=(8, 4.8))
    plt.plot(x, t0, "o-", label="T0_mean")
    plt.plot(x, t1, "s-", label="T1_mean")
    plt.xlabel("n0")
    plt.ylabel("Mean response time")
    plt.title("T0 and T1 vs n0")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_w_box(per_rep: pd.DataFrame, out_path: Path) -> None:
    groups = []
    labels = []
    for n0 in sorted(per_rep["n0"].unique()):
        vals = per_rep.loc[per_rep["n0"] == n0, "W"].dropna().to_numpy()
        groups.append(vals)
        labels.append(str(n0))

    plt.figure(figsize=(9, 4.8))
    plt.boxplot(groups, tick_labels=labels, showfliers=False)
    plt.xlabel("n0")
    plt.ylabel("Replication-level W")
    plt.title("Distribution of W across replications")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def generate_design_plots(input_dir: Path, output_dir: Path) -> list[Path]:
    summary = pd.read_csv(input_dir / "summary_by_n0.csv")
    per_rep = pd.read_csv(input_dir / "per_replication.csv")

    p1 = output_dir / "fig_w_vs_n0_ci.png"
    p2 = output_dir / "fig_t0_t1_vs_n0.png"
    p3 = output_dir / "fig_w_boxplot_by_n0.png"

    plot_w_ci(summary, p1)
    plot_t0_t1(summary, p2)
    plot_w_box(per_rep, p3)
    return [p1, p2, p3]


def sample_group0_service(alpha0: float, beta0: float, theta0: float, size: int, rng: np.random.Generator) -> np.ndarray:
    u = rng.random(size=size)
    a = alpha0 ** (-theta0)
    b = beta0 ** (-theta0)
    x = a - u * (a - b)
    return x ** (-1.0 / theta0)


def sample_group1_service(alpha1: float, theta1: float, size: int, rng: np.random.Generator) -> np.ndarray:
    u = rng.random(size=size)
    return alpha1 / ((1.0 - u) ** (1.0 / theta1))


def theoretical_means(
    lam: float, a2l: float, a2u: float, p0: float,
    alpha0: float, beta0: float, theta0: float, alpha1: float, theta1: float
) -> dict:
    exp_mean = 1.0 / lam
    uni_mean = (a2l + a2u) / 2.0
    inter_mean = exp_mean * uni_mean
    group0_prob = p0
    group1_prob = 1.0 - p0

    c0 = alpha0 ** (-theta0) - beta0 ** (-theta0)
    group0_mean = (theta0 / c0) * ((alpha0 ** (1.0 - theta0) - beta0 ** (1.0 - theta0)) / (theta0 - 1.0))
    group1_mean = theta1 * alpha1 / (theta1 - 1.0)
    return {
        "exp_component_mean": exp_mean,
        "uniform_component_mean": uni_mean,
        "interarrival_mean": inter_mean,
        "group0_prob": group0_prob,
        "group1_prob": group1_prob,
        "service_group0_mean": group0_mean,
        "service_group1_mean": group1_mean,
    }


def generate_rng_artifacts(output_dir: Path, sample_size: int, seed: int) -> list[Path]:
    lam = 2.7
    a2l, a2u = 0.85, 1.21
    p0 = 0.81
    alpha0, beta0, theta0 = 0.5, 4.7, 1.9
    alpha1, theta1 = 2.2, 2.4

    rng = np.random.default_rng(seed)
    n = sample_size

    exp_comp = rng.exponential(scale=1.0 / lam, size=n)
    uni_comp = rng.uniform(a2l, a2u, size=n)
    inter_arr = exp_comp * uni_comp

    group_choice = rng.random(size=n) < p0
    g0_prob_emp = float(group_choice.mean())
    g1_prob_emp = 1.0 - g0_prob_emp

    s0 = sample_group0_service(alpha0, beta0, theta0, n, rng)
    s1 = sample_group1_service(alpha1, theta1, n, rng)

    theo = theoretical_means(lam, a2l, a2u, p0, alpha0, beta0, theta0, alpha1, theta1)
    emp = {
        "exp_component_mean": float(exp_comp.mean()),
        "uniform_component_mean": float(uni_comp.mean()),
        "interarrival_mean": float(inter_arr.mean()),
        "group0_prob": g0_prob_emp,
        "group1_prob": g1_prob_emp,
        "service_group0_mean": float(s0.mean()),
        "service_group1_mean": float(s1.mean()),
    }

    rows = []
    for key in [
        "exp_component_mean",
        "uniform_component_mean",
        "interarrival_mean",
        "group0_prob",
        "group1_prob",
        "service_group0_mean",
        "service_group1_mean",
    ]:
        rows.append(
            {
                "metric": key,
                "theoretical": theo[key],
                "empirical": emp[key],
                "abs_error": abs(emp[key] - theo[key]),
            }
        )
    summary = pd.DataFrame(rows)
    summary_path = output_dir / "rng_verification_summary.csv"
    summary.to_csv(summary_path, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    x_exp = np.linspace(0, np.quantile(exp_comp, 0.99), 300)
    y_exp = lam * np.exp(-lam * x_exp)
    axes[0].hist(exp_comp, bins=80, density=True, alpha=0.65, label="empirical")
    axes[0].plot(x_exp, y_exp, "r-", lw=1.8, label="theoretical")
    axes[0].set_title("Exponential component")
    axes[0].set_xlabel("x")
    axes[0].set_ylabel("density")
    axes[0].legend()

    x_uni = np.linspace(a2l - 0.05, a2u + 0.05, 300)
    y_uni = np.where((x_uni >= a2l) & (x_uni <= a2u), 1.0 / (a2u - a2l), 0.0)
    axes[1].hist(uni_comp, bins=80, density=True, alpha=0.65, label="empirical")
    axes[1].plot(x_uni, y_uni, "r-", lw=1.8, label="theoretical")
    axes[1].set_title("Uniform component")
    axes[1].set_xlabel("x")
    axes[1].set_ylabel("density")
    axes[1].legend()
    fig.tight_layout()
    p1 = output_dir / "fig_rng_interarrival_components.png"
    fig.savefig(p1, dpi=180)
    plt.close(fig)

    fig = plt.figure(figsize=(6.2, 4.2))
    labels = ["Group 0", "Group 1"]
    theo_vals = [p0, 1.0 - p0]
    emp_vals = [g0_prob_emp, g1_prob_emp]
    x = np.arange(2)
    width = 0.35
    plt.bar(x - width / 2, theo_vals, width=width, label="theoretical")
    plt.bar(x + width / 2, emp_vals, width=width, label="empirical")
    plt.xticks(x, labels)
    plt.ylabel("probability")
    plt.ylim(0, 1.0)
    plt.title("Server-group selection probability")
    plt.legend()
    plt.tight_layout()
    p2 = output_dir / "fig_rng_group_probability.png"
    plt.savefig(p2, dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    x0 = np.linspace(alpha0, beta0, 400)
    c0 = alpha0 ** (-theta0) - beta0 ** (-theta0)
    y0 = (theta0 / c0) * (x0 ** (-(theta0 + 1.0)))
    axes[0].hist(s0, bins=100, density=True, alpha=0.65, label="empirical")
    axes[0].plot(x0, y0, "r-", lw=1.8, label="theoretical")
    axes[0].set_title("Service time for Group 0")
    axes[0].set_xlabel("x")
    axes[0].set_ylabel("density")
    axes[0].set_xlim(alpha0, beta0)
    axes[0].legend()

    x1 = np.linspace(alpha1, np.quantile(s1, 0.99), 400)
    y1 = theta1 * (alpha1 ** theta1) * (x1 ** (-(theta1 + 1.0)))
    axes[1].hist(s1, bins=100, density=True, alpha=0.65, label="empirical")
    axes[1].plot(x1, y1, "r-", lw=1.8, label="theoretical")
    axes[1].set_title("Service time for Group 1")
    axes[1].set_xlabel("x")
    axes[1].set_ylabel("density")
    axes[1].legend()

    fig.tight_layout()
    p3 = output_dir / "fig_rng_service_distributions.png"
    fig.savefig(p3, dpi=180)
    plt.close(fig)

    return [summary_path, p1, p2, p3]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design-input-dir", default="design_results")
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--sample-size", type=int, default=200000)
    parser.add_argument("--seed", type=int, default=20260415)
    parser.add_argument(
        "--mode",
        choices=["all", "design", "rng"],
        default="all",
        help="Select which artifacts to generate.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    if args.mode in ("all", "design"):
        design_input = resolve_design_input_dir(args.design_input_dir)
        print(f"Design input dir: {design_input}")
        saved.extend(generate_design_plots(design_input, output_dir))
    if args.mode in ("all", "rng"):
        saved.extend(generate_rng_artifacts(output_dir, args.sample_size, args.seed))

    for p in saved:
        print(f"Saved: {p}")


if __name__ == "__main__":
    main()

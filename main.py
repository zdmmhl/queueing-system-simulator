#!/usr/bin/env python3
from __future__ import annotations

import math
import os
import random
import sys
import argparse
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple


EPS = 1e-12
INF = float("inf")


@dataclass
class Job:
    original_arrival: float
    service_time: float
    indicated_group: int  # 0 or 1 (user-indicated group)
    recirculated: bool = False


@dataclass
class ServerTask:
    job: Job
    departure_time: float
    killed: bool


class Simulator:
    def __init__(
        self,
        test_id: int,
        seed: Optional[int] = None,
        config_dir: str = "config",
        output_dir: str = "output",
    ) -> None:
        self.test_id = test_id
        self.config_dir = config_dir
        self.output_dir = output_dir

        self.mode = self._read_mode()
        self.n, self.n0, self.t_limit, self.time_end = self._read_para()
        self.n1 = self.n - self.n0

        self.queue0: Deque[Job] = deque()
        self.queue1: Deque[Job] = deque()
        self.server_tasks: List[Optional[ServerTask]] = [None] * self.n

        self.dep_rows: List[Tuple[float, float, str]] = []
        self.rt_class0: List[float] = []
        self.rt_class1: List[float] = []

        self.clock = 0.0
        self.rng = random.Random()
        if seed is not None:
            self.rng.seed(seed)

        # Arrival process state
        self.arrival_cursor = 0
        self.next_arrival_time = INF
        self.trace_arrival_times: List[float] = []
        self.trace_services: List[Tuple[float, int]] = []
        self.random_params = None
        self._init_arrival_process()

    # Read simulation mode
    def _read_mode(self) -> str:
        # read mode_*.txt
        path = os.path.join(self.config_dir, f"mode_{self.test_id}.txt")
        with open(path, "r", encoding="utf-8") as f:
            mode = f.read().strip()
        if mode not in ("trace", "random"):
            raise ValueError(f"Unsupported mode {mode!r}")
        return mode

    # Read core parameters (including time_end in random mode)
    def _read_para(self) -> Tuple[int, int, float, Optional[float]]:
        # read para_*.txt
        path = os.path.join(self.config_dir, f"para_{self.test_id}.txt")
        with open(path, "r", encoding="utf-8") as f:
            lines = [x.strip() for x in f if x.strip()]

        n = int(lines[0])
        n0 = int(lines[1])
        t_limit = float(lines[2])
        time_end = float(lines[3]) if self.mode == "random" else None
        return n, n0, t_limit, time_end

    # Initialize trace/random arrival inputs
    def _init_arrival_process(self) -> None:
        # locate interarrival_*.txt and service_*.txt
        interarrival_path = os.path.join(self.config_dir, f"interarrival_{self.test_id}.txt")
        service_path = os.path.join(self.config_dir, f"service_{self.test_id}.txt")

        if self.mode == "trace":
            # Trace mode: read interarrival trace
            with open(interarrival_path, "r", encoding="utf-8") as f:
                interarrivals = [float(x.strip()) for x in f if x.strip()]

            # Convert interarrival list to absolute arrival times
            cumulative = 0.0
            for d in interarrivals:
                cumulative += d
                self.trace_arrival_times.append(cumulative)

            # Trace mode: read (service_time, indicated_group)
            with open(service_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    s, g = line.split()
                    self.trace_services.append((float(s), int(g)))

            if len(self.trace_arrival_times) > 0:
                self.next_arrival_time = self.trace_arrival_times[0]
            else:
                self.next_arrival_time = INF
        else:
            # Random mode: read distribution parameters
            with open(interarrival_path, "r", encoding="utf-8") as f:
                lam, a2l, a2u = [float(x) for x in f.read().strip().split()]
            with open(service_path, "r", encoding="utf-8") as f:
                lines = [x.strip() for x in f if x.strip()]
            p0 = float(lines[0])
            alpha0, beta0, theta0 = [float(x) for x in lines[1].split()]
            alpha1, theta1 = [float(x) for x in lines[2].split()]

            self.random_params = {
                "lam": lam,
                "a2l": a2l,
                "a2u": a2u,
                "p0": p0,
                "alpha0": alpha0,
                "beta0": beta0,
                "theta0": theta0,
                "alpha1": alpha1,
                "theta1": theta1,
            }
            self.next_arrival_time = self._draw_next_arrival(0.0)

    def _draw_next_arrival(self, current_time: float) -> float:
        # Random mode interarrival = exponential * uniform
        p = self.random_params
        exp_part = self.rng.expovariate(p["lam"])
        uni_part = self.rng.uniform(p["a2l"], p["a2u"])
        return current_time + exp_part * uni_part

    def _draw_service_group0(self) -> float:
        # Draw Group 0 service time (truncated heavy-tail form)
        p = self.random_params
        alpha = p["alpha0"]
        beta = p["beta0"]
        theta = p["theta0"]
        u = self.rng.random()
        a = alpha ** (-theta)
        b = beta ** (-theta)
        x = a - u * (a - b)
        return x ** (-1.0 / theta)

    def _draw_service_group1(self) -> float:
        # Draw Group 1 service time (Pareto-like form)
        p = self.random_params
        alpha = p["alpha1"]
        theta = p["theta1"]
        u = self.rng.random()
        return alpha / ((1.0 - u) ** (1.0 / theta))

    def _create_new_job(self, t: float) -> Job:
        if self.mode == "trace":
            # Trace mode: consume next traced job
            service_time, indicated_group = self.trace_services[self.arrival_cursor]
        else:
            # Random mode: sample group then sample service time
            indicated_group = 0 if self.rng.random() < self.random_params["p0"] else 1
            if indicated_group == 0:
                service_time = self._draw_service_group0()
            else:
                service_time = self._draw_service_group1()
        self.arrival_cursor += 1
        return Job(original_arrival=t, service_time=service_time, indicated_group=indicated_group)

    def _next_departure_time(self) -> float:
        t = INF
        for task in self.server_tasks:
            if task is not None and task.departure_time < t:
                t = task.departure_time
        return t

    def _group_idle_server(self, group: int) -> Optional[int]:
        start = 0 if group == 0 else self.n0
        end = self.n0 if group == 0 else self.n
        for i in range(start, end):
            if self.server_tasks[i] is None:
                return i
        return None

    def _start_service(self, server_idx: int, job: Job, now: float) -> None:
        in_group0 = server_idx < self.n0
        if in_group0 and job.service_time > self.t_limit:
            departure = now + self.t_limit
            killed = True
        else:
            departure = now + job.service_time
            killed = False
        self.server_tasks[server_idx] = ServerTask(job=job, departure_time=departure, killed=killed)

    def _dispatch(self, job: Job, group: int, now: float) -> None:
        idle = self._group_idle_server(group)
        if idle is not None:
            self._start_service(idle, job, now)
        else:
            if group == 0:
                self.queue0.append(job)
            else:
                self.queue1.append(job)

    def _refill_from_queue(self, group: int, now: float) -> None:
        while True:
            idle = self._group_idle_server(group)
            if idle is None:
                return
            q = self.queue0 if group == 0 else self.queue1
            if not q:
                return
            job = q.popleft()
            self._start_service(idle, job, now)

    def _complete_job(self, job: Job, dep_time: float) -> None:
        if job.recirculated:
            cls = "r0"
        elif job.indicated_group == 0:
            cls = "0"
        else:
            cls = "1"

        self.dep_rows.append((job.original_arrival, dep_time, cls))
        rt = dep_time - job.original_arrival
        if cls == "0":
            self.rt_class0.append(rt)
        elif cls == "1":
            self.rt_class1.append(rt)

    def _process_departures_at(self, t: float) -> None:
        departed_indices: List[int] = []
        for i, task in enumerate(self.server_tasks):
            if task is not None and abs(task.departure_time - t) <= EPS:
                departed_indices.append(i)

        killed_jobs: List[Job] = []
        for i in departed_indices:
            task = self.server_tasks[i]
            self.server_tasks[i] = None
            if task.killed:
                task.job.recirculated = True
                killed_jobs.append(task.job)
            else:
                self._complete_job(task.job, t)

        # A departing server first serves waiting jobs in its own group queue.
        self._refill_from_queue(0, t)
        self._refill_from_queue(1, t)

        # Then dispatcher handles jobs killed in Group 0 and sends them to Group 1.
        for job in killed_jobs:
            self._dispatch(job, 1, t)

    def _process_one_arrival(self, t: float) -> None:
        job = self._create_new_job(t)
        self._dispatch(job, job.indicated_group, t)

        if self.mode == "trace":
            if self.arrival_cursor < len(self.trace_arrival_times):
                self.next_arrival_time = self.trace_arrival_times[self.arrival_cursor]
            else:
                self.next_arrival_time = INF
        else:
            self.next_arrival_time = self._draw_next_arrival(t)

    def _write_outputs(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)

        mrt0 = sum(self.rt_class0) / len(self.rt_class0) if self.rt_class0 else 0.0
        mrt1 = sum(self.rt_class1) / len(self.rt_class1) if self.rt_class1 else 0.0
        # write mrt_*.txt
        mrt_path = os.path.join(self.output_dir, f"mrt_{self.test_id}.txt")
        with open(mrt_path, "w", encoding="utf-8") as f:
            f.write(f"{mrt0:.4f} {mrt1:.4f}\n")

        # write dep_*.txt
        dep_path = os.path.join(self.output_dir, f"dep_{self.test_id}.txt")
        with open(dep_path, "w", encoding="utf-8") as f:
            for arr, dep, cls in self.dep_rows:
                f.write(f"{arr:.4f} {dep:.4f} {cls}\n")

    # Main event loop with random-mode time_end stop
    def run(self) -> None:
        while True:
            next_dep = self._next_departure_time()
            next_event = min(self.next_arrival_time, next_dep)
            if next_event == INF:
                break

            # Random mode only: stop when master clock exceeds time_end
            if self.mode == "random" and next_event > self.time_end + EPS:
                break

            self.clock = next_event

            if abs(next_dep - self.clock) <= EPS:
                self._process_departures_at(self.clock)

            if abs(self.next_arrival_time - self.clock) <= EPS:
                self._process_one_arrival(self.clock)

        self._write_outputs()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("test_id", type=int, help="Test index")
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed")
    parser.add_argument(
        "--config-dir",
        type=str,
        default="config",
        help="Directory containing mode_*.txt, para_*.txt, interarrival_*.txt, service_*.txt",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to write mrt_*.txt and dep_*.txt",
    )
    args = parser.parse_args()
    sim = Simulator(
        test_id=args.test_id,
        seed=args.seed,
        config_dir=args.config_dir,
        output_dir=args.output_dir,
    )
    sim.run()


if __name__ == "__main__":
    main()

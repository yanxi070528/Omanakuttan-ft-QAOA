"""Replay the main 8-SAT notebook's Sparrow benchmark using only Python's standard library."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1] / "qaoa_aa_3sat"
DATA = PROJECT / "results/8sat_n10_m176/experiments/data"


def run(executable, cnf, clauses, n, seed):
    command = [str(executable), "--randomc", "1", "-a", "--runs", "1",
               "--maxflips", "1000000", str(cnf), str(seed)]
    start = time.perf_counter_ns()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=5, check=False,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return (seed, (time.perf_counter_ns() - start) * 1e-9, "TIMEOUT", "", "")
    seconds = (time.perf_counter_ns() - start) * 1e-9
    flips = re.search(r"totalFlips\s*:\s*(\d+)", proc.stderr)
    if proc.returncode == 0 and "c UNKNOWN best(" in proc.stderr:
        return (seed, seconds, "UNKNOWN", "", flips[1] if flips else "")
    if proc.returncode != 10 or "s SATISFIABLE" not in proc.stdout.splitlines():
        raise RuntimeError(f"seed {seed}: unexpected solver output\n{proc.stdout}\n{proc.stderr}")
    model = {int(v) for line in proc.stdout.splitlines() if line.startswith("v ")
             for v in line.split()[1:] if v != "0"}
    if (len(model) != n or {abs(v) for v in model} != set(range(1, n + 1))
            or not all(model.intersection(clause) for clause in clauses)):
        raise ValueError(f"seed {seed}: invalid assignment")
    bits = "".join("1" if v in model else "0" for v in range(n, 0, -1))
    return (seed, seconds, "SAT", bits, flips[1] if flips else "")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="save per-seed timings and verified models to a new CSV")
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("choose a new output file")
    default = HERE / "bin" / ("sparrow.exe" if os.name == "nt" else "sparrow")
    executable = Path(os.environ.get("SPARROW_EXE", default)).expanduser().resolve()
    if not executable.is_file():
        parser.error(f"missing executable: {executable}")

    summary = json.loads((DATA / "experiment_summary.json").read_text(encoding="utf-8"))
    cnf = (PROJECT / "data" / summary["CNF"]).read_text(encoding="ascii")
    hashes = [hashlib.sha256(text.encode("ascii")).hexdigest()
              for text in (cnf, cnf.replace("\n", "\r\n"))]
    if summary["cnf_sha256"] not in hashes:
        parser.error("CNF differs from the recorded experiment")
    lines = [line for line in cnf.splitlines() if line and not line.startswith("c")]
    _, _, n, m = lines[0].split()
    clauses = [tuple(map(int, line.split()[:-1])) for line in lines[1:]]
    if len(clauses) != int(m) or any(len(c) != 8 for c in clauses):
        parser.error("expected the original 8-SAT instance")
    with (DATA / "04_sparrow_1000_runs.csv").open(encoding="utf-8-sig", newline="") as f:
        baseline = list(csv.DictReader(f))
    seeds = [int(row["seed"]) for row in baseline]
    if seeds != list(range(1, 1001)):
        parser.error("expected the recorded 1000 seeds")

    with tempfile.TemporaryDirectory(prefix="sat_meeting_") as folder:
        path = Path(folder) / "instance.cnf"
        path.write_text("\n".join(lines) + "\n", encoding="ascii")
        for seed in range(900000, 900003):
            run(executable, path, clauses, int(n), seed)
        rows = [run(executable, path, clauses, int(n), seed) for seed in seeds]
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(["seed", "process_s", "status", "bitstring", "flips"])
            writer.writerows(rows)
    previous = [float(r["process_s"]) for r in baseline]
    current = [r[1] for r in rows]
    for name, times, valid in [("Reference CSV", previous, sum(r["valid"] == "True" for r in baseline)),
                               ("This run", current, sum(r[2] == "SAT" for r in rows))]:
        print(f"{name}: {valid}/{len(times)} SAT, median {1000 * statistics.median(times):.3f} ms,"
              f" mean {1000 * statistics.mean(times):.3f} ms")
    print(f"Reference / current median wall time: {statistics.median(previous) / statistics.median(current):.2f}x")


if __name__ == "__main__":
    main()

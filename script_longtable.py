#!/usr/bin/env python3
import argparse
import glob
import os
import re
from collections import defaultdict

# version can contain letters+digits (v0, v1a, v1b, v2...)
FILENAME_RE = re.compile(
    r"^v(?P<version>[A-Za-z0-9]+)"
    r"_O(?P<opt_flag>\d+)"
    r"_(?P<fast_math>\w+)"
    r"_T(?P<threads>\d+)"
    r"_N(?P<dataset_size>\d+)\.out$"
)

# Time (Single Thread) = 0.206825 sec
TIME_LINE_RE = re.compile(
    r"^Time\s*\((?P<program_type>.+?)\)\s*=\s*(?P<time_sec>[0-9]*\.?[0-9]+)\s*sec"
)


def natural_key(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


def parse_filename(filename: str):
    m = FILENAME_RE.match(filename)
    if not m:
        return None
    return {
        "version": m.group("version"),               # string, not numeric
        "opt_flag": int(m.group("opt_flag")),
        "fast_math": m.group("fast_math"),
        "threads": int(m.group("threads")),
        "dataset_size": int(m.group("dataset_size")),
    }


def extract_times_from_file(path: str):
    results = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            m = TIME_LINE_RE.match(line)
            if m:
                results.append({
                    "program_type": m.group("program_type"),
                    "time_sec": m.group("time_sec"),   # keep as raw string
                })
    return results


def collect_all_runs(results_dir: str):
    all_results = []
    for path in glob.glob(os.path.join(results_dir, "*.out")):
        filename = os.path.basename(path)
        meta = parse_filename(filename)
        if not meta:
            continue
        for t in extract_times_from_file(path):
            all_results.append({
                **meta,
                "filename": filename,
                "program_type": t["program_type"],
                "time_sec": t["time_sec"],
            })
    return all_results


# ---------- LaTeX longtable output ----------

def normalize_fast_math(value: str) -> str:
    v = value.lower()
    if v in ("ffm", "fm", "fast", "fastmath", "fast_math"):
        return "ON"
    if v in ("nofm", "noffm", "off", "slow", "default"):
        return "OFF"
    if v in ("on", "off"):
        return v.upper()
    return value


def generate_latex_tables(runs):
    grouped = defaultdict(list)
    for r in runs:
        r = dict(r)
        r["fast_math"] = normalize_fast_math(r["fast_math"])
        grouped[(r["version"], r["opt_flag"])].append(r)

    for (version, opt_flag) in sorted(grouped.keys(),
                                      key=lambda x: (natural_key(x[0]), x[1])):

        data = grouped[(version, opt_flag)]
        off_rows = sorted([d for d in data if d["fast_math"] == "OFF"],
                          key=lambda x: (x["dataset_size"], x["threads"]))
        on_rows  = sorted([d for d in data if d["fast_math"] == "ON"],
                          key=lambda x: (x["dataset_size"], x["threads"]))

        caption = f"Execution times v{version} — optimization -O{opt_flag}"
        print(r"% -------------------------------------------------------------------")
        print(rf"% {caption}")
        print(r"% -------------------------------------------------------------------")
        print(rf"\begin{{longtable}}{{cccc}}")
        print(rf"\caption{{{caption}}}\\")
        print(r"\hline")
        print(r"FastMath & Threads & $N$ & Time [s] \\ \hline")
        print(r"\endfirsthead")
        print(r"\hline FastMath & Threads & $N$ & Time [s] \\ \hline")
        print(r"\endhead")

        for row in off_rows:
            print(rf"OFF & {row['threads']} & {row['dataset_size']} & {row['time_sec']} \\")
        if off_rows and on_rows:
            print(r"\hline")
        for row in on_rows:
            print(rf"ON  & {row['threads']} & {row['dataset_size']} & {row['time_sec']} \\")
        
        print(r"\hline")
        print(r"\end{longtable}")
        print()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("results_dir", nargs="?", default=".",
                   help="Directory with .out files (default: current)")
    args = p.parse_args()
    generate_latex_tables(collect_all_runs(args.results_dir))


if __name__ == "__main__":
    main()


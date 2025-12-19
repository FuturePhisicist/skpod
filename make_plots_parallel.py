#!/usr/bin/env python3
import argparse
import glob
import os
import re
from collections import defaultdict

# v0_O2_ffm_T4_N8192.out
FILENAME_RE = re.compile(
    r"^v(?P<version>[A-Za-z0-9]+)"
    r"_O(?P<opt_flag>\d+)"
    r"_(?P<fast_math>\w+)"
    r"_T(?P<threads>\d+)"
    r"_N(?P<dataset_size>\d+)\.out$"
)

# Time (Single Thread) = 0.206825 sec
# Supports scientific notation too: 1.23e-04, 2E+01
TIME_LINE_RE = re.compile(
    r"^Time\s*\((?P<program_type>.+?)\)\s*=\s*"
    r"(?P<time_sec>[0-9]*\.?[0-9]+(?:[eE][+-]?\d+)?)\s*sec"
)

def normalize_fast_math(value: str) -> str:
    v = value.lower()
    if v in ("ffm", "fm", "fast", "fastmath", "fast_math", "on"):
        return "ON"
    if v in ("nofm", "noffm", "off", "slow", "default"):
        return "OFF"
    return value.upper()

def parse_filename(filename: str):
    m = FILENAME_RE.match(filename)
    if not m:
        return None
    return {
        "version": m.group("version"),
        "opt_flag": int(m.group("opt_flag")),
        "fast_math": normalize_fast_math(m.group("fast_math")),
        "threads": int(m.group("threads")),
        "dataset_size": int(m.group("dataset_size")),
    }

def extract_first_time(path: str, program_filter: str | None):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            m = TIME_LINE_RE.match(line)
            if not m:
                continue
            prog = m.group("program_type").strip()
            if program_filter and prog != program_filter:
                continue
            return float(m.group("time_sec"))
    return None

def latex_escape(s: str) -> str:
    return (s.replace("\\", r"\textbackslash{}")
             .replace("_", r"\_")
             .replace("%", r"\%")
             .replace("&", r"\&")
             .replace("#", r"\#")
             .replace("{", r"\{")
             .replace("}", r"\}")
            )

def collect_data(results_dir: str, program_filter: str | None):
    """
    Collect points keyed by:
      version -> T -> {N: time}
    for O2 & FastMath ON only.
    """
    data = defaultdict(lambda: defaultdict(dict))  # v -> T -> {N: time}

    for path in glob.glob(os.path.join(results_dir, "*.out")):
        fn = os.path.basename(path)
        meta = parse_filename(fn)
        if not meta:
            continue

        # Filter: O2 and fast-math ON
        if meta["opt_flag"] != 2:
            continue
        if meta["fast_math"] != "ON":
            continue

        t = extract_first_time(path, program_filter)
        if t is None:
            continue

        v = meta["version"]
        T = meta["threads"]
        N = meta["dataset_size"]
        data[v][T][N] = t

    return data

def emit_tex(data, title_prefix: str, x_log: bool, y_log: bool):
    print(r"\documentclass[tikz,border=6pt]{standalone}")
    print(r"\usepackage{pgfplots}")
    print(r"\pgfplotsset{compat=1.18}")
    print(r"\begin{document}")
    print()

    # one plot per version
    for v in sorted(data.keys(), key=lambda s: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", s)]):
        by_T = data[v]
        threads = sorted(by_T.keys())
        if not threads:
            continue

        print(r"\begin{tikzpicture}")
        axis_opts = [
            "width=14cm",
            "height=9cm",
            "grid=both",
            "xlabel={$N$}",
            "ylabel={Time [s]}",
            f"title={{{latex_escape(title_prefix)} (v{v}, O2, FastMath ON)}}",
            "legend pos=north west",
            "legend cell align=left",
            # чтобы разные T отличались автоматически
            "cycle list name=color list",
            "mark options={scale=0.9}",
        ]
        if x_log:
            axis_opts.append("xmode=log")
            axis_opts.append("log basis x=2")
        if y_log:
            axis_opts.append("ymode=log")

        print(r"\begin{axis}[" + ",".join(axis_opts) + "]")

        for T in threads:
            pts = by_T[T]
            if not pts:
                continue
            coords = " ".join(f"({N},{pts[N]})" for N in sorted(pts.keys()))
            # одна кривая на каждый T
            print(
                r"\addplot+[thick, mark=*] "
                rf"coordinates {{{coords}}};"
            )
            print(rf"\addlegendentry{{T={T}}}")

        print(r"\end{axis}")
        print(r"\end{tikzpicture}")
        print()

    print(r"\end{document}")

def main():
    ap = argparse.ArgumentParser(
        description="LaTeX/pgfplots: for each version one plot; on that plot one curve per T (O2 + FastMath ON)."
    )
    ap.add_argument("results_dir", nargs="?", default=".", help="Directory with .out files")
    ap.add_argument("--program", default=None, help="Exact match for Time(<program>) label (optional)")
    ap.add_argument("--title", default="Execution time vs N", help="Title prefix")
    ap.add_argument("--xlog", action="store_true", help="Use log2 scale for X axis (N)")
    ap.add_argument("--ylog", action="store_true", help="Use log scale for Y axis (time)")
    args = ap.parse_args()

    data = collect_data(args.results_dir, args.program)
    if not data:
        raise SystemExit("No data found for O2 + FastMath ON. Check directory, filenames, and Time(...) format.")

    emit_tex(data, args.title, x_log=args.xlog, y_log=args.ylog)

if __name__ == "__main__":
    main()

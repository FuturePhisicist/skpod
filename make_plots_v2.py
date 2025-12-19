#!/usr/bin/env python3
import argparse
import glob
import os
import re
from collections import defaultdict

# v0_O2_noffm_T1_N8192.out
FILENAME_RE = re.compile(
    r"^v(?P<version>[A-Za-z0-9]+)"
    r"_O(?P<opt_flag>\d+)"
    r"_(?P<fast_math>\w+)"
    r"_T(?P<threads>\d+)"
    r"_N(?P<dataset_size>\d+)\.out$"
)

# Time (Single Thread) = 0.206825 sec
# also supports scientific notation: 1.23e-04, 2E+01
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

def extract_times_from_file(path: str, program_filter: str | None):
    """Return list of (program_type, time_float)."""
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            m = TIME_LINE_RE.match(line)
            if not m:
                continue
            program_type = m.group("program_type").strip()
            if program_filter and program_filter != program_type:
                continue
            t = float(m.group("time_sec"))
            out.append((program_type, t))
    return out

def collect_runs(results_dir: str, version_filter: str | None, program_filter: str | None):
    """
    Collect points keyed by (threads, opt_flag, fast_math) -> {N: time}.
    If multiple time lines exist in a file, we take the first match after filtering.
    """
    series = defaultdict(dict)  # (T,O,FM) -> {N: time}
    seen_versions = set()

    for path in glob.glob(os.path.join(results_dir, "*.out")):
        fn = os.path.basename(path)
        meta = parse_filename(fn)
        if not meta:
            continue
        seen_versions.add(meta["version"])
        if version_filter and meta["version"] != version_filter:
            continue

        times = extract_times_from_file(path, program_filter)
        if not times:
            continue

        # take first matching time line
        _, t = times[0]

        key = (meta["threads"], meta["opt_flag"], meta["fast_math"])
        series[key][meta["dataset_size"]] = t

    return series, sorted(seen_versions)

def latex_escape(s: str) -> str:
    return (s.replace("\\", r"\textbackslash{}")
             .replace("_", r"\_")
             .replace("%", r"\%")
             .replace("&", r"\&")
             .replace("#", r"\#")
             .replace("{", r"\{")
             .replace("}", r"\}")
            )

LINE_STYLES = {
    (0, "OFF"): {"color": "red",             "dash": "solid"},
    (0, "ON"):  {"color": "red",             "dash": "dashed"},
    (1, "OFF"): {"color": "blue",            "dash": "solid"},
    (1, "ON"):  {"color": "blue",            "dash": "dashed"},
    (2, "OFF"): {"color": "green!70!black",  "dash": "solid"},
    (2, "ON"):  {"color": "green!70!black",  "dash": "dashed"},
    (3, "OFF"): {"color": "orange",          "dash": "solid"},
    (3, "ON"):  {"color": "orange",          "dash": "dashed"},
}

def emit_tex(series, title_prefix: str, x_log: bool, y_log: bool):
    # Determine available thread counts
    threads = sorted({T for (T, O, FM) in series.keys()})

    # fixed order: O0 OFF, O0 ON, O1 OFF, O1 ON, O2 OFF, O2 ON, O3 OFF, O3 ON
    order = []
    for O in (0, 1, 2, 3):
        for FM in ("OFF", "ON"):
            order.append((O, FM))

    # print(r"\documentclass[tikz,border=6pt]{standalone}")
    # print(r"\usepackage{pgfplots}")
    # print(r"\pgfplotsset{compat=1.18}")
    # print(r"\begin{document}")
    # print()

    for T in threads:
        print(r"\begin{tikzpicture}")
        axis_opts = [
            "width=14cm",
            "height=9cm",
            "grid=both",
            "xlabel={$N$}",
            "ylabel={Time [s]}",
            f"title={{{latex_escape(title_prefix)} (T={T})}}",
            "legend pos=north west",
            "legend cell align=left",
            "mark options={scale=0.9}",
        ]
        if x_log:
            axis_opts.append("xmode=log")
            axis_opts.append("log basis x=2")
        if y_log:
            axis_opts.append("ymode=log")

        print(r"\begin{axis}[" + ",".join(axis_opts) + "]")

        for (O, FM) in order:
            key = (T, O, FM)
            pts = series.get(key, {})
            if not pts:
                # still put legend entry but skip plot? лучше пропустить полностью:
                continue
            coords = " ".join(f"({N},{pts[N]})" for N in sorted(pts.keys()))
            legend = f"-O{O}, FastMath {FM}"

            st = LINE_STYLES.get((O, FM), {"color": "black", "dash": "solid"})
            c = st["color"]
            d = st["dash"]

            print(
                rf"\addplot+["
                rf"{c}, thick, {d}, "
                rf"mark=*, "
                rf"mark options={{draw={c}, fill={c}}}"
                rf"] coordinates {{{coords}}};"
            )
            print(rf"\addlegendentry{{{latex_escape(legend)}}}")

        print(r"\end{axis}")
        print(r"\end{tikzpicture}")
        print()

    # print(r"\end{document}")

def main():
    ap = argparse.ArgumentParser(
        description="Generate LaTeX/pgfplots graphs: per T one plot with 8 curves (O0..O3 × FastMath OFF/ON)."
    )
    ap.add_argument("results_dir", nargs="?", default=".", help="Directory with .out files")
    ap.add_argument("--version", default=None, help="Filter by version (e.g. 0 for v0). If omitted, uses all versions found.")
    ap.add_argument("--program", default=None, help="Filter by program type inside Time(...) line (exact match).")
    ap.add_argument("--title", default="Execution time vs N", help="Plot title prefix")
    ap.add_argument("--xlog", action="store_true", help="Use log2 scale for X axis (N)")
    ap.add_argument("--ylog", action="store_true", help="Use log scale for Y axis (time)")
    args = ap.parse_args()

    series, versions = collect_runs(args.results_dir, args.version, args.program)

    if not series:
        raise SystemExit("No data collected. Check results_dir/version/program filters and filename/time formats.")

    title = args.title
    if args.version is not None:
        title += f" (v{args.version})"
    elif versions:
        # if multiple versions exist and user didn't filter, mention it in title
        if len(versions) == 1:
            title += f" (v{versions[0]})"
        else:
            title += f" (versions: {', '.join('v'+v for v in versions)})"

    emit_tex(series, title, x_log=args.xlog, y_log=args.ylog)

if __name__ == "__main__":
    main()


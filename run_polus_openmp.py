import itertools, os, subprocess

def run_cmd(cmd):
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True, # text=True for old Python
        )
        if r.stdout:
            print("STDOUT:")
            print(r.stdout)
        if r.stderr:
            print("STDERR:")
            print(r.stderr)

        return r
    except subprocess.CalledProcessError as e:
        print("Command failed!")
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        if e.stderr:
            print("STDERR:")
            print(e.stderr)

        return -1
    print()

import polus_constants



SOURCE_CODE_FILES = ["v1a", "v1b"]
BASE_DIRECTORY = "openmp"

os.makedirs(BASE_DIRECTORY + "/" + polus_constants.BINARIES_DIRECTORY, exist_ok=True)
os.makedirs(BASE_DIRECTORY + "/" + polus_constants.RESULTS_DIRECTORY,  exist_ok=True)

cnt = 0
for i, code in enumerate(SOURCE_CODE_FILES, start=1):
    print(f"= {i}: {code} =")

    for O, fm, t, n in itertools.product(
        polus_constants.COMPILER_O_FLAGS,
        polus_constants.FFAST_MATH_FLAGS,
        polus_constants.THREADS_CNT_LIST,
        polus_constants.DATASET_SIZE_LIST,
    ):
        opt_tag = O.replace("-", "")       # O0/O1/O2/O3
        fm_tag  = "ffm" if "-ffast-math" in fm else "noffm" # ffm/noffm

        cnt += 1
        print(f"{cnt:>4} | OPT={opt_tag:<3} | FM={fm_tag:<6} | T={t:<3} | N={n:<7}")

        tag = f"{code}_{opt_tag}_{fm_tag}_T{t}_N{n}"

        bin_path = f"{BASE_DIRECTORY}/{polus_constants.BINARIES_DIRECTORY}/{tag}"
        if not os.path.exists(bin_path):
            compile_command = f"gcc -std=c99 -fopenmp {O} {fm} -o {bin_path} {code}.c"

            print("COMPILING:")
            print(compile_command)
            run_cmd(compile_command)
            print()

        file_name = f"{BASE_DIRECTORY}/{polus_constants.RESULTS_DIRECTORY}/{tag}"
        out = file_name + ".out"
        err = file_name + ".err"
        if os.path.exists(out) or os.path.exists(err):
            continue

        m = min(t // 8 + 1, 20) # the number of cores in one host
        run_command = f"bsub -n {m} -W 15 -R span[hosts=1] -oo {out} -eo {err} \"OMP_NUM_THREADS={t} ./{bin_path} {n}\""

        print("Running:")
        print(run_command)
        run_cmd(run_command)
        print()


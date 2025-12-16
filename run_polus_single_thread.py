import itertools, os, subprocess

import polus_constants

polus_constants.THREADS_CNT_LIST = [1] # NO PARALLELISM HERE

SOURCE_CODE_FILES = ["v0"]
BASE_DIRECTORY = "single_thread"

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
            compile_command = f"gcc -std=gnu99 {O} {fm} -o {bin_path} {code}.c" # no "-fopenmp"; GNU99 for wall time!

            print(compile_command)
            subprocess.run(compile_command, shell=True, check=True)

        file_name = f"{BASE_DIRECTORY}/{polus_constants.RESULTS_DIRECTORY}/{tag}"
        out = file_name + ".out"
        err = file_name + ".err"
        if os.path.exists(out) or os.path.exists(err):
            continue

        run_command = f"bsub -n 1 -W 15 -oo {out} -eo {err} \"./{bin_path} {n}\"" # no OMP_NUM_THREADS={t}

        print(run_command)
        subprocess.run(run_command, shell=True, check=True)

        print()

COMPILER_O_FLAGS   = ["-O0", "-O1", "-O2", "-O3"]
FFAST_MATH_FLAGS   = ["-fno-fast-math", "-ffast-math"]
THREADS_CNT_LIST   = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 40, 60, 80, 100, 120, 140, 160]
# THREADS_CNT_LIST   = [1, 2, 4]
DATASET_SIZE_LIST  = [2**i for i in range(8, 15)]
# DATASET_SIZE_LIST = [66, 100]
BINARIES_DIRECTORY = "binaries"
RESULTS_DIRECTORY  = "results"


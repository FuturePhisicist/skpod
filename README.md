## Execution

```bash
python3 run_polus_single_thread.py > single_thread_tests.log 2>&1 &
tail -f single_thread_tests.log

python3 run_polus_openmp.py > openmp_tests.log 2>&1 &
tail -f openmp_tests.log

module load SpectrumMPI
python3 run_polus_mpi.py > mpi_tests.log 2>&1 &
tail -f mpi_tests.log
```


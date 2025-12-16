#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <omp.h>

static const double maxeps = 0.1e-7;
static const size_t itmax = 100;

static double eps = 0.0;

void init(double *A, const size_t N);
void relax_omp_task(double *A, const size_t N);
void verify(const double *A, const size_t N);

static double max_double(const double a, const double b)
{
    return (a > b) ? a : b;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "Usage: %s N\n", argv[0]);

        return 1;
    }

    const size_t N = (size_t)atoll(argv[1]);
    if (N <= 2) {
        fprintf(stderr, "N must be > 2\n");

        return 1;
    }

    double *A = calloc(N * N, sizeof(*A));
    if (A == NULL) {
        perror("calloc");

        return 1;
    }

    init(A, N);

    const double t0 = omp_get_wtime();
    for (size_t it = 1; it <= itmax; ++it) {
        eps = 0.0;
        relax_omp_task(A, N);

        printf("it=%4zu   eps=%e\n", it, eps);

        if (eps < maxeps){
            break;
        }
    }

    const double t1 = omp_get_wtime();
    printf("Time (OpenMP task) = %f sec\n", t1 - t0);

    verify(A, N);

    free(A);

    return 0;
}

void init(double *A, const size_t N)
{
    for (size_t j = 0; j < N; ++j) {
        for (size_t i = 0; i < N; ++i) {
            if (i == 0 || i == N - 1 || j == 0 || j == N - 1) {
                A[i * N + j] = 0.0;
            }
            else {
                A[i * N + j] = 1.0 + (double)i + (double)j;
            }
        }
    }
}

void relax_omp_task(double *A, const size_t N)
{
#pragma omp parallel
    {
#pragma omp single
        {
            // Phase 1: tasks per column j
            for (size_t j = 1; j < N - 1; ++j) {
#pragma omp task firstprivate(j)
                {
                    for (size_t i = 1; i < N - 1; ++i) {
                        A[i * N + j] =
                            0.5 * (
                                A[(i - 1) * N + j] +
                                A[(i + 1) * N + j]
                        );
                    }
                }
            }

#pragma omp taskwait

            // Phase 2: tasks per line i
            for (size_t i = 1; i < N - 1; ++i) {
#pragma omp task firstprivate(i)
                {
                    double local_eps = 0.0;
                    for (size_t j = 1; j < N - 1; ++j) {
                        const double e = A[i * N + j];
                        A[i * N + j] =
                            0.5 * (
                                A[i * N + (j - 1)] +
                                A[i * N + (j + 1)]
                        );
                        const double diff = fabs(e - A[i * N + j]);
                        local_eps = max_double(local_eps, diff);
                    }
#pragma omp critical
                    eps = max_double(eps, local_eps);
                }
            }

#pragma omp taskwait
        }
    }
}

void verify(const double *A, const size_t N)
{
    double s = 0.0;
    for (size_t j = 0; j < N; ++j) {
        for (size_t i = 0; i < N; ++i) {
            s += 
                A[i * N + j] *
                (double)(i + 1) *
                (double)(j + 1) /
                (double)(N * N);
        }
    }

    printf("  S = %f\n", s);
}

#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

// analogue of omp_get_wtime()
double wtime()
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);

    return ts.tv_sec + ts.tv_nsec * 1e-9;     // return seconds as double
}


static const double maxeps = 0.1e-7;
static const size_t itmax = 100;

static double eps = 0.0;

void init(double *A, const size_t N);
void relax(double *A, const size_t N);
void verify(const double *A, const size_t N);

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

    const double t0 = wtime();
    for (size_t it = 1; it <= itmax; ++it) {
        eps = 0.0;
        relax(A, N);

        printf("it=%4zu   eps=%e\n", it, eps);

        if (eps < maxeps) {
            break;
        }
    }

    const double t1 = wtime();
    printf("Time (Single Thread) = %f sec\n", t1 - t0);

    verify(A, N);

    free(A);

    return 0;
}

void init(double *A, const size_t N)
{
    for (size_t j = 0; j < N; ++j) {
        for (size_t i = 0; i < N; ++i) {
            if ((i == 0) || (i == N - 1) || (j == 0) || (j == N - 1)) {
                A[i * N + j] = 0.0;
            }
            else {
                A[i * N + j] = 1.0 + (double)i + (double)j;
            }
        }
    }
}

static double max_double(const double a, const double b)
{
    return (a > b) ? a : b;
}

void relax(double *A, const size_t N)
{
    for (size_t j = 1; j < N - 1; ++j) {
        for (size_t i = 1; i < N - 1; ++i) {
            A[i * N + j] =
                0.5 * (
                    A[(i - 1) * N + j] +
                    A[(i + 1) * N + j]
            );
        }
    }

    for (size_t j = 1; j < N - 1; ++j) {
        for (size_t i = 1; i < N - 1; ++i) {
            const double e = A[i * N + j];
            A[i * N + j] =
                0.5 * (
                    A[i * N + (j - 1)] +
                    A[i * N + (j + 1)]
            );
            const double diff = fabs(e - A[i * N + j]);
            eps = max_double(eps, diff);
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

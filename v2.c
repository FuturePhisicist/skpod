#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <mpi.h>

static const double maxeps = 0.1e-7;
static const size_t itmax = 100;

static double max_double(const double a, const double b)
{
    return (a > b) ? a : b;
}

void init_local(
    double *A,
    const size_t N,
    const size_t local_n,
    const int rank,
    const int size
);

void relax_mpi(
    double *A,
    const size_t N,
    const size_t local_n,
    const int rank,
    const int size,
    double *eps
);

void verify_mpi(
    const double *A,
    const size_t N,
    const size_t local_n,
    const int rank,
    const int size
);

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);

    int rank = 0;
    int size = 0;

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    size_t N = 0;
    if (rank == 0) {
        if (argc < 2) {
            fprintf(stderr, "Usage: %s N\n", argv[0]);

            MPI_Abort(MPI_COMM_WORLD, 1);
        }

        N = (size_t)atoll(argv[1]);
        if (N <= 2) {
            fprintf(stderr, "N must be > 2\n");

            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    }

    MPI_Bcast(&N, 1, MPI_UNSIGNED_LONG, 0, MPI_COMM_WORLD);

    const size_t inner = N - 2;
    const size_t local_n = inner / (size_t)size;

    if ((inner % (size_t)size != 0) && (rank == 0)) {
        fprintf(
            stderr,
            "Warning: (N-2) %% size != 0, the remaining lines are ignored\n"
        );
    }

    double *A = calloc((size_t)(local_n + 2) * N, sizeof(*A));
    if (A == NULL) {
        perror("calloc");

        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    init_local(A, N, local_n, rank, size);

    const double t0 = MPI_Wtime();
    for (size_t it = 1; it <= itmax; ++it) {
        double eps = 0.0;
        double global_eps = 0.0;

        relax_mpi(
            A,
            N,
            local_n,
            rank,
            size,
            &eps
        );

        MPI_Allreduce(
            &eps,
            &global_eps,
            1,
            MPI_DOUBLE,
            MPI_MAX,
            MPI_COMM_WORLD
        );

        if (rank == 0) {
            printf("it=%4zu   eps=%e\n", it, global_eps);
        }

        if (global_eps < maxeps) {
            break;
        }
    }
    const double t1 = MPI_Wtime();

    if (rank == 0) {
        printf("Time (MPI) = %f sec\n", t1 - t0);
    }

    verify_mpi(A, N, local_n, rank, size);

    free(A);

    MPI_Finalize();

    return 0;
}

void init_local(
    double *A,
    const size_t N,
    const size_t local_n,
    const int rank,
    const int size
)
{
    const size_t inner = N - 2;
    const size_t chunk = inner / (size_t)size;
    const size_t i_global_start = 1 + (size_t)rank * chunk;

    for (size_t i_local = 0; i_local <= local_n + 1; ++i_local) {
        const size_t ig = i_global_start + i_local - 1; // global row index
        for (size_t j = 0; j <= N - 1; ++j) {
            if ((ig == 0) || (ig == N - 1) || (j == 0) || (j == N - 1)) {
                A[(size_t)i_local * N + j] = 0.0;
            } else {
                A[(size_t)i_local * N + j] = 1.0 + ig + j;
            }
        }
    }
}

void relax_mpi(
    double *A,
    const size_t N,
    const size_t local_n,
    const int rank,
    const int size,
    double *eps
)
{
    const int up = (rank == 0) ? MPI_PROC_NULL : rank - 1;
    const int down = (rank == size - 1) ? MPI_PROC_NULL : rank + 1;
    const int tag_updown_0 = 0;
    const int tag_updown_1 = 1;
    const int tag_wave = 2;

    MPI_Sendrecv(
        &A[(size_t)1 * N],             (int)N, MPI_DOUBLE, up,   tag_updown_0,
        &A[(size_t)(local_n + 1) * N], (int)N, MPI_DOUBLE, down, tag_updown_0,
        MPI_COMM_WORLD, MPI_STATUS_IGNORE
    );

    MPI_Sendrecv(
        &A[(size_t)local_n * N], (int)N, MPI_DOUBLE, down, tag_updown_1,
        &A[0],                   (int)N, MPI_DOUBLE, up,   tag_updown_1,
        MPI_COMM_WORLD, MPI_STATUS_IGNORE
    );

    for (size_t j = 1; j <= N - 2; ++j) {

        if (rank != 0) {
            MPI_Recv(
                &A[j], 1, MPI_DOUBLE, up, tag_wave,
                MPI_COMM_WORLD, MPI_STATUS_IGNORE
            );
        }

        for (size_t i_local = 1; i_local <= local_n; ++i_local) {
            A[(size_t)i_local * N + j] =
                0.5 * (A[(size_t)(i_local - 1) * N + j] +
                       A[(size_t)(i_local + 1) * N + j]);
        }

        if (rank != size - 1) {
            MPI_Send(
                &A[(size_t)local_n * N + j], 1, MPI_DOUBLE, down, tag_wave,
                MPI_COMM_WORLD
            );
        }
    }

    double local_eps = 0.0;
    for (size_t j = 1; j <= N - 2; ++j) {
        for (size_t i_local = 1; i_local <= local_n; ++i_local) {
            const double e = A[(size_t)i_local * N + j];
            A[(size_t)i_local * N + j] =
                0.5 * (A[(size_t)i_local * N + (j - 1)] +
                       A[(size_t)i_local * N + (j + 1)]);
            const double diff = fabs(e - A[(size_t)i_local * N + j]);
            local_eps = max_double(local_eps, diff);
        }
    }

    *eps = local_eps;
}

void verify_mpi(
    const double *A,
    const size_t N,
    const size_t local_n,
    const int rank,
    const int size
)
{
    const size_t inner = N - 2;
    const size_t chunk = inner / (size_t)size;
    const size_t i_global_start = 1 + (size_t)rank * chunk;

    double local_s = 0.0;

    for (size_t i_local = 1; i_local <= local_n; ++i_local) {
        const size_t ig = i_global_start + i_local - 1;
        for (size_t j = 0; j <= N - 1; ++j) {
            local_s +=
                A[(size_t)i_local * N + j] *
                (ig + 1) *
                (j + 1) /
                (double)(N * N);
        }
    }

    double global_s = 0.0;
    MPI_Reduce(
        &local_s,
        &global_s,
        1,
        MPI_DOUBLE,
        MPI_SUM,
        0,
        MPI_COMM_WORLD
    );

    if (rank == 0) {
        printf("  S = %f\n", global_s);
    }
}

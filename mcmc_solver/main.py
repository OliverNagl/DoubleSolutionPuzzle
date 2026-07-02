"""
CLI entry point for the MCMC double-solution puzzle generator.

Usage
-----
    python -m mcmc_solver                    # defaults: n=10, K=6
    python -m mcmc_solver --n 15 --K 9
    python -m mcmc_solver --n 20 --K 12 --max-steps 5000000 --save
"""

import argparse
import time
import sys
import numpy as np

from .solver import MCMCSolver
from .verify import verify_solution, solution_statistics
from .convert import save_solution, mcmc_to_legacy_format


def recommended_K(n: int) -> int:
    """Return recommended K ≈ 0.6n (slightly below uniqueness threshold)."""
    return max(3, int(0.6 * n))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MCMC double-solution jigsaw puzzle generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--n", type=int, default=10,
                   help="Grid size (n × n puzzle)")
    p.add_argument("--K", type=int, default=None,
                   help="Number of base edge types (default: auto ≈ 0.6n)")
    p.add_argument("--max-steps", type=int, default=None,
                   help="Max MCMC steps per restart (default: 10·n⁴)")
    p.add_argument("--max-mappings", type=int, default=20,
                   help="Number of mapping attempts")
    p.add_argument("--max-restarts", type=int, default=10,
                   help="Restarts per mapping")
    p.add_argument("--patience", type=int, default=50_000,
                   help="Steps without improvement before reheat")
    p.add_argument("--batch-size", type=int, default=1000,
                   help="Numba recolor batch size")
    p.add_argument("--seed", type=int, default=None,
                   help="Random seed for reproducibility")
    p.add_argument("--save", action="store_true",
                   help="Save solution to Solutions/ folder")
    p.add_argument("--output-dir", type=str, default="Solutions",
                   help="Directory for saved solutions")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress progress output")
    return p


def main(args=None):
    parser = build_parser()
    opts = parser.parse_args(args)

    n = opts.n
    K = opts.K if opts.K is not None else recommended_K(n)

    if opts.seed is not None:
        np.random.seed(opts.seed)
        import random
        random.seed(opts.seed)

    print(f"MCMC Double-Solution Puzzle Generator")
    print(f"  n={n}  K={K}  m={2*K+1}  max_steps={opts.max_steps or 10*n**4:,}")
    print(f"  patience={opts.patience:,}  batch={opts.batch_size}")
    print()

    t0 = time.time()

    solver = MCMCSolver(
        n=n,
        K=K,
        max_mapping_attempts=opts.max_mappings,
        max_restarts_per_mapping=opts.max_restarts,
        max_steps=opts.max_steps,
        patience=opts.patience,
        batch_size=opts.batch_size,
        verbose=not opts.quiet,
    )

    state = solver.solve()
    elapsed = time.time() - t0

    if state is None:
        print(f"\nNo solution found after {elapsed:.1f}s")
        sys.exit(1)

    # --- Verify ---
    print(f"\nVerifying solution...")
    try:
        verify_solution(state)
        print("  All checks passed!")
    except AssertionError as e:
        print(f"  VERIFICATION FAILED: {e}")
        sys.exit(2)

    # --- Statistics ---
    stats = solution_statistics(state)
    print(f"\nSolution statistics:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print(f"\nTotal time: {elapsed:.1f}s")

    # --- Save ---
    if opts.save:
        paths = save_solution(state, output_dir=opts.output_dir)
        print(f"\nSaved to:")
        for p in paths:
            print(f"  {p}")

    return state


if __name__ == "__main__":
    main()

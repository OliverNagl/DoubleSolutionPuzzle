"""
Run the MCMC double-solution puzzle generator.

Edit the parameters below, then run:
    python run_mcmc.py
"""

from mcmc_solver.solver import MCMCSolver
from mcmc_solver.verify import verify_solution, solution_statistics
from mcmc_solver.convert import save_solution
import numpy as np
import random
import time

# =====================================================================
#  PARAMETERS — edit these
# =====================================================================

n = 30          # Grid size (n × n puzzle)
K = max(4, int(round(0.7 * n)))  # Auto-scaled edge types
                # Rule of thumb: K ≈ ceil(0.7 * n)
                #   n=5→K=4, n=8→K=6, n=10→K=7, n=12→K=8, n=15→K=11

seed = None     # Set to an integer for reproducibility, or None

# MCMC tuning
max_mapping_attempts = 5     # How many different mappings to try
max_restarts_per_mapping = 2 # Edge restarts per mapping
max_steps = 4_000_000              # Max steps per restart (None = 200 * n^4)
patience = 4_000_000          # Steps without improvement before reheat
                              # (auto-scaled up to 5× when mm is low)
batch_size = 1000             # Numba recolor batch size
T_final = 0.01               # Final temperature for geometric cooling
max_reheats = 8               # Max mild reheats before giving up a restart
reheat_factor = 10          # How aggressively to reheat temperature
                              # 1.5 = mild, 3–5 = aggressive, 10+ = near-restart
repair_threshold = 6       # Mismatch count to enter repair (None = 2*n)
                              # Lower → MCMC runs longer before expensive
                              # greedy repair kicks in

# Energy weights  (E = w_mm * mismatches + w_div * diversity + w_bal * balance + w_idp * identical)
w_mismatch = 10.0             # Weight for S2 mismatch count (main objective)
w_diversity = 0.1             # Penalty for too few distinct edge types used
w_balance = 0.1               # Penalty for any single type dominating
                              # Lower → allows more uneven type distribution,
                              #   which gives the solver more freedom
w_identical = 0.0             # Penalty for identical (non-unique) S1 pieces
                              # Set > 0 to penalise duplicate pieces
track_identical = True        # Print idp count during descent (O(n²) per log)
                              # Always printed at end of trajectory regardless

# Output
save_solution_flag = True     # Save .npy files to output_dir
output_dir = "Solutions"      # Output directory

# =====================================================================

if __name__ == "__main__":
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    m = 2 * K + 1
    print(f"MCMC Double-Solution Puzzle Generator")
    print(f"  n={n}  K={K}  m={m}")

    # Warn if K seems too low for n
    recommended_K = max(3, int(round(0.7 * n)))
    if K < recommended_K - 1:
        print(f"  ⚠ K={K} may be too low for n={n}.  Recommended: K≈{recommended_K}")

    print(f"  max_steps={max_steps or 200 * n**4:,}  patience={patience:,}")
    print(f"  T_final={T_final}  batch_size={batch_size}  seed={seed}")
    print()

    t0 = time.time()

    solver = MCMCSolver(
        n=n,
        K=K,
        max_mapping_attempts=max_mapping_attempts,
        max_restarts_per_mapping=max_restarts_per_mapping,
        max_steps=max_steps,
        patience=patience,
        T_final=T_final,
        batch_size=batch_size,
        max_reheats=max_reheats,
        reheat_factor=reheat_factor,
        repair_threshold=repair_threshold,
        w_mismatch=w_mismatch,
        w_diversity=w_diversity,
        w_balance=w_balance,
        w_identical=w_identical,
        track_identical=track_identical,
        verbose=True,
    )

    state = solver.solve()
    elapsed = time.time() - t0

    if state is None:
        print(f"\nNo solution found after {elapsed:.1f}s")
    else:
        print(f"\nVerifying...")
        try:
            verify_solution(state)
            print("  All checks passed!")
        except AssertionError as e:
            print(f"  FAILED: {e}")

        stats = solution_statistics(state)
        print(f"\nSolution statistics:")
        for k, v in stats.items():
            print(f"  {k}: {v}")

        if save_solution_flag:
            paths = save_solution(state, output_dir=output_dir)
            print(f"\nSaved to:")
            for p in paths:
                print(f"  {p}")

        print(f"\nTotal time: {elapsed:.1f}s")

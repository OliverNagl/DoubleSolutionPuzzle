"""
Energy function components for the MCMC solver.

The total energy is:
    E = w1 * M2 + w2 * E_diversity + w3 * E_balance

where:
    M2             — number of S2 adjacency mismatches (target: 0)
    E_diversity    — penalty for using too few distinct edge types
    E_balance      — penalty for any single type dominating
"""

import numpy as np
import numba as nb


# ---------------------------------------------------------------------------
# Default weights
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = {
    "w_mismatch": 10.0,
    "w_diversity": 1.0,
    "w_balance": 0.5,
}


# ---------------------------------------------------------------------------
# Numba-accelerated energy helpers
# ---------------------------------------------------------------------------

@nb.njit(cache=True)
def mismatch_count_full(n: int, s2: np.ndarray) -> int:
    """Count every S2 internal adjacency mismatch. O(n²)."""
    count = 0
    for i in range(n):
        for j in range(n):
            # right neighbour
            if j < n - 1:
                if s2[i, j, 1] + s2[i, j + 1, 3] != 0:
                    count += 1
            # bottom neighbour
            if i < n - 1:
                if s2[i, j, 2] + s2[i + 1, j, 0] != 0:
                    count += 1
    return count


@nb.njit(cache=True)
def mismatch_delta_at_positions(
    n: int,
    s2: np.ndarray,
    pos_a_y: int, pos_a_x: int,
    pos_b_y: int, pos_b_x: int,
) -> int:
    """Count mismatches involving positions A and/or B in S2.

    Each internal adjacency is counted at most once even when both positions
    are adjacent.

    Returns the number of mismatches among those adjacencies.
    """
    # We'll enumerate all adjacencies touching A or B, deduplicating via a
    # small fixed-size buffer (at most 8 adjacencies).
    # Each adjacency is stored as (y1, x1, s1, y2, x2, s2_side).
    # Represent as a flat array: 8 entries × 6 values.

    # Neighbour deltas: (dy, dx, my_side, their_side)
    DY = np.array([-1, 0, 1, 0], dtype=np.int32)
    DX = np.array([0, 1, 0, -1], dtype=np.int32)
    MY_SIDE = np.array([0, 1, 2, 3], dtype=np.int32)
    TH_SIDE = np.array([2, 3, 0, 1], dtype=np.int32)

    count = 0
    # Track edges we've already counted: store as encoded key = y1*n*10+x1*10+side
    seen = np.zeros(16, dtype=np.int64)
    n_seen = 0

    for pidx in range(2):
        if pidx == 0:
            py, px = pos_a_y, pos_a_x
        else:
            py, px = pos_b_y, pos_b_x

        for k in range(4):
            ny = py + DY[k]
            nx = px + DX[k]
            if 0 <= ny < n and 0 <= nx < n:
                # canonical key: smaller position first
                if (py, px) < (ny, nx):
                    key = py * n * 10 + px * 10 + MY_SIDE[k]
                else:
                    key = ny * n * 10 + nx * 10 + TH_SIDE[k]

                already = False
                for si in range(n_seen):
                    if seen[si] == key:
                        already = True
                        break
                if already:
                    continue
                seen[n_seen] = key
                n_seen += 1

                if s2[py, px, MY_SIDE[k]] + s2[ny, nx, TH_SIDE[k]] != 0:
                    count += 1

    return count


def diversity_penalty(type_freq: np.ndarray, K: int) -> float:
    """Penalty for using too few distinct edge types."""
    K_used = int(np.count_nonzero(type_freq[1:]))
    K_min = max(1, int(0.8 * K))
    return float(max(0, K_min - K_used) ** 2)


def balance_penalty(type_freq: np.ndarray, K: int, n: int) -> float:
    """Penalty for any single edge type exceeding 150 % of uniform."""
    total_edges = 2 * n * (n - 1)
    f_max = int(np.ceil(1.5 * total_edges / K))
    excess = np.maximum(0, type_freq[1:] - f_max)
    return float(np.sum(excess))


def total_energy(mismatch: int, div_pen: float, bal_pen: float,
                 w: dict | None = None) -> float:
    """Compute weighted total energy."""
    if w is None:
        w = DEFAULT_WEIGHTS
    return (w["w_mismatch"] * mismatch
            + w["w_diversity"] * div_pen
            + w["w_balance"] * bal_pen)

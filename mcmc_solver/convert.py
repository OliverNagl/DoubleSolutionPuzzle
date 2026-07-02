"""
Conversion utilities: MCMC internal representation ↔ legacy codebase format.

MCMC uses signed edge values:
    +t  → outie of base type t
    -t  → innie of base type t
     0  → flat (boundary)

Legacy codebase uses:
    2t-1 → outie (odd)
    2t   → innie (even)
    0    → flat

This module also provides NumPy-array output compatible with the existing
Solutions/ folder format.
"""

import numpy as np
import os
import time


def _signed_to_legacy(v: int) -> int:
    """Convert a single signed side value to legacy odd/even format."""
    if v == 0:
        return 0
    elif v > 0:
        return 2 * v - 1   # outie → odd
    else:
        return 2 * (-v)    # innie → even


def _legacy_to_signed(v: int) -> int:
    """Convert a single legacy side value to signed format."""
    if v == 0:
        return 0
    elif v % 2 == 1:
        return (v + 1) // 2   # odd → +t  (outie)
    else:
        return -(v // 2)      # even → -t  (innie)


def mcmc_to_legacy_format(state):
    """Convert MCMC solution to the legacy list-of-lists format.

    Returns
    -------
    sol0 : list[list[list[int]]]
        S1 puzzle: sol0[i][j] = [top, right, bottom, left] in legacy encoding.
    sol1 : list[list[list[int]]]
        S2 puzzle: same format.
    """
    n = state.n
    sol0 = [[[0] * 4 for _ in range(n)] for _ in range(n)]
    sol1 = [[[0] * 4 for _ in range(n)] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            for s in range(4):
                sol0[i][j][s] = _signed_to_legacy(int(state.s1_pieces[i, j, s]))
                sol1[i][j][s] = _signed_to_legacy(int(state.s2_pieces[i, j, s]))

    return sol0, sol1


def mcmc_to_numpy_solutions(state):
    """Convert MCMC solution to NumPy arrays in legacy encoding.

    Returns
    -------
    sol0 : ndarray (n, n, 4) int32 — S1 pieces in legacy format
    sol1 : ndarray (n, n, 4) int32 — S2 pieces in legacy format
    mapping : ndarray (n, n, 3) int32 — forward mapping [y2, x2, rotation]
    """
    n = state.n
    sol0 = np.zeros((n, n, 4), dtype=np.int32)
    sol1 = np.zeros((n, n, 4), dtype=np.int32)

    for i in range(n):
        for j in range(n):
            for s in range(4):
                sol0[i, j, s] = _signed_to_legacy(int(state.s1_pieces[i, j, s]))
                sol1[i, j, s] = _signed_to_legacy(int(state.s2_pieces[i, j, s]))

    return sol0, sol1, state.map_fwd.copy()


def mcmc_to_mapping_dict(state) -> dict:
    """Convert mapping to legacy dict format: (y,x,0) → (y2,x2,rot)."""
    mapping = {}
    n = state.n
    for y in range(n):
        for x in range(n):
            y2, x2, rot = state.map_fwd[y, x]
            mapping[(y, x, 0)] = (int(y2), int(x2), int(rot))
    return mapping


def save_solution(state, output_dir: str = "Solutions", prefix: str = "MCMC"):
    """Save the solved state to .npy files compatible with the existing pipeline.

    Files created:
        Solution_{n}_{m}_0_{id}.npy  — S1
        Solution_{n}_{m}_1_{id}.npy  — S2
        Mapping_{n}_{m}_{id}.npy     — forward mapping
    """
    os.makedirs(output_dir, exist_ok=True)

    sol0, sol1, mapping = mcmc_to_numpy_solutions(state)
    n = state.n
    m = 2 * state.K + 1  # legacy m parameter
    uid = int(time.time())

    s0_path = os.path.join(output_dir, f"Solution_{n}_{m}_0_{uid}.npy")
    s1_path = os.path.join(output_dir, f"Solution_{n}_{m}_1_{uid}.npy")
    map_path = os.path.join(output_dir, f"Mapping_{n}_{m}_{uid}.npy")

    np.save(s0_path, sol0)
    np.save(s1_path, sol1)
    np.save(map_path, mapping)

    return s0_path, s1_path, map_path

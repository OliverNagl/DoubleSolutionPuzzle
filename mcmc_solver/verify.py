"""
Verification routines for MCMC-generated double-solution puzzles.

Provides:
  - O(n²) internal consistency checks (S1 valid, S2 valid, piece multiset)
  - Piece uniqueness / diversity statistics
"""

import numpy as np
from collections import Counter


# Side-index constants
TOP, RIGHT, BOTTOM, LEFT = 0, 1, 2, 3


def verify_solution(state) -> bool:
    """Run all O(n²) verification checks. Raises AssertionError on failure.

    Returns True if everything passes.
    """
    n = state.n
    s1 = state.s1_pieces
    s2 = state.s2_pieces

    # ------------------------------------------------------------------
    # 1. S1 boundary check (should all be 0 = flat)
    # ------------------------------------------------------------------
    for i in range(n):
        assert s1[i, 0, LEFT] == 0, f"S1 left boundary fail at ({i},0)"
        assert s1[i, n - 1, RIGHT] == 0, f"S1 right boundary fail at ({i},{n-1})"
    for j in range(n):
        assert s1[0, j, TOP] == 0, f"S1 top boundary fail at (0,{j})"
        assert s1[n - 1, j, BOTTOM] == 0, f"S1 bottom boundary fail at ({n-1},{j})"

    # ------------------------------------------------------------------
    # 2. S1 adjacency check (should always pass by construction)
    # ------------------------------------------------------------------
    for i in range(n):
        for j in range(n):
            if j < n - 1:
                assert s1[i, j, RIGHT] + s1[i, j + 1, LEFT] == 0, \
                    f"S1 horizontal mismatch at ({i},{j})-({i},{j+1})"
            if i < n - 1:
                assert s1[i, j, BOTTOM] + s1[i + 1, j, TOP] == 0, \
                    f"S1 vertical mismatch at ({i},{j})-({i+1},{j})"

    # ------------------------------------------------------------------
    # 3. S2 adjacency check (the main goal: M2 == 0)
    # ------------------------------------------------------------------
    for i in range(n):
        for j in range(n):
            if j < n - 1:
                assert s2[i, j, RIGHT] + s2[i, j + 1, LEFT] == 0, \
                    f"S2 horizontal mismatch at ({i},{j})-({i},{j+1})"
            if i < n - 1:
                assert s2[i, j, BOTTOM] + s2[i + 1, j, TOP] == 0, \
                    f"S2 vertical mismatch at ({i},{j})-({i+1},{j})"

    # ------------------------------------------------------------------
    # 4. S2 boundary check
    # ------------------------------------------------------------------
    for i in range(n):
        assert s2[i, 0, LEFT] == 0, f"S2 left boundary fail at ({i},0)"
        assert s2[i, n - 1, RIGHT] == 0, f"S2 right boundary fail at ({i},{n-1})"
    for j in range(n):
        assert s2[0, j, TOP] == 0, f"S2 top boundary fail at (0,{j})"
        assert s2[n - 1, j, BOTTOM] == 0, f"S2 bottom boundary fail at ({n-1},{j})"

    # ------------------------------------------------------------------
    # 5. Piece multiset equivalence: same pieces in S1 and S2
    #    (S2 pieces are rotated versions of S1 pieces)
    # ------------------------------------------------------------------
    s1_multiset = Counter()
    s2_multiset = Counter()
    for i in range(n):
        for j in range(n):
            s1_canonical = _canonical(tuple(s1[i, j]))
            s2_canonical = _canonical(tuple(s2[i, j]))
            s1_multiset[s1_canonical] += 1
            s2_multiset[s2_canonical] += 1
    assert s1_multiset == s2_multiset, \
        "Piece multiset mismatch between S1 and S2!"

    # ------------------------------------------------------------------
    # 6. Mapping consistency
    # ------------------------------------------------------------------
    fwd = state.map_fwd
    inv = state.map_inv
    for y in range(n):
        for x in range(n):
            y2, x2, rot = fwd[y, x]
            y_back, x_back, rot_back = inv[y2, x2]
            assert y_back == y and x_back == x, \
                f"Mapping inconsistency: fwd({y},{x})=({y2},{x2}), " \
                f"inv({y2},{x2})=({y_back},{x_back})"
            assert rot_back == rot, \
                f"Rotation inconsistency at ({y},{x}): fwd rot={rot}, inv rot={rot_back}"

    return True


def _canonical(piece: tuple) -> tuple:
    """Rotation-canonical form: smallest lexicographic rotation."""
    best = piece
    for i in range(1, 4):
        rotated = piece[i:] + piece[:i]
        if rotated < best:
            best = rotated
    return best


def solution_statistics(state) -> dict:
    """Compute summary statistics for a solved state.

    Returns a dict with keys:
      - n, K
      - K_used: distinct base types actually used
      - n_distinct_pieces: number of distinct pieces (rotation-canonicalised)
      - max_piece_freq: highest multiplicity of any single piece
      - mismatch_s1, mismatch_s2
      - mapping_fixed_points
      - mapping_displaced
    """
    n = state.n
    s1 = state.s1_pieces
    s2 = state.s2_pieces

    K_used = int(np.count_nonzero(state.type_freq[1:]))

    s1_canonical = Counter()
    for i in range(n):
        for j in range(n):
            s1_canonical[_canonical(tuple(s1[i, j]))] += 1

    n_distinct = len(s1_canonical)
    max_freq = max(s1_canonical.values()) if s1_canonical else 0

    # Fixed points
    fixed = 0
    for y in range(n):
        for x in range(n):
            y2, x2, r = state.map_fwd[y, x]
            if y2 == y and x2 == x and r == 0:
                fixed += 1

    return {
        "n": n,
        "K": state.K,
        "K_used": K_used,
        "n_distinct_pieces": n_distinct,
        "max_piece_freq": max_freq,
        "mismatch_s1": 0,  # always 0 by construction
        "mismatch_s2": state.mismatch_count,
        "mapping_fixed_points": fixed,
        "mapping_displaced": n * n - fixed,
    }

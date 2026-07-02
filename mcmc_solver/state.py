"""
MCMCState — Core state representation for the MCMC puzzle solver.

Stores edge colorings (base type + direction), cached S1/S2 piece arrays,
type frequency counters, and cached energy components. All derived data is
kept in sync through incremental updates in the move engine.
"""

import numpy as np
import numba as nb


# ---------------------------------------------------------------------------
# Numba-accelerated helpers
# ---------------------------------------------------------------------------

@nb.njit(cache=True)
def _side_val(base_type, direction, is_first_cell):
    """
    Compute signed side value for one cell side.

    Parameters
    ----------
    base_type : int
        Edge connection type in [1, K].
    direction : int
        0 or 1. Convention: direction==0 → first cell gets +t (outie).
    is_first_cell : bool
        True for the top/left cell of the edge pair.

    Returns
    -------
    int  Signed side value (+t, -t, or 0).
    """
    if base_type == 0:
        return 0
    if is_first_cell:
        return base_type if direction == 0 else -base_type
    else:
        return -base_type if direction == 0 else base_type


@nb.njit(cache=True)
def compute_piece_s1(i, j, n, h_type, h_dir, v_type, v_dir):
    """Compute [top, right, bottom, left] signed sides for S1 cell (i, j)."""
    # Top
    if i == 0:
        top = 0
    else:
        top = _side_val(v_type[i - 1, j], v_dir[i - 1, j], False)
    # Right
    if j == n - 1:
        right = 0
    else:
        right = _side_val(h_type[i, j], h_dir[i, j], True)
    # Bottom
    if i == n - 1:
        bottom = 0
    else:
        bottom = _side_val(v_type[i, j], v_dir[i, j], True)
    # Left
    if j == 0:
        left = 0
    else:
        left = _side_val(h_type[i, j - 1], h_dir[i, j - 1], False)
    return top, right, bottom, left


@nb.njit(cache=True)
def rotate_piece(t, r, b, l, rot):
    """Rotate piece *rot* times 90° clockwise.

    [t,r,b,l] → rot=1 → [l,t,r,b]
    """
    for _ in range(rot % 4):
        t, r, b, l = l, t, r, b
    return t, r, b, l


@nb.njit(cache=True)
def _recompute_all(n, h_type, h_dir, v_type, v_dir, map_inv, s1, s2):
    """Full recompute of s1_pieces and s2_pieces arrays."""
    for i in range(n):
        for j in range(n):
            t, r, b, l = compute_piece_s1(i, j, n, h_type, h_dir, v_type, v_dir)
            s1[i, j, 0] = t
            s1[i, j, 1] = r
            s1[i, j, 2] = b
            s1[i, j, 3] = l

    for i in range(n):
        for j in range(n):
            sy = map_inv[i, j, 0]
            sx = map_inv[i, j, 1]
            rot = map_inv[i, j, 2]
            t, r, b, l = rotate_piece(
                s1[sy, sx, 0], s1[sy, sx, 1], s1[sy, sx, 2], s1[sy, sx, 3], rot
            )
            s2[i, j, 0] = t
            s2[i, j, 1] = r
            s2[i, j, 2] = b
            s2[i, j, 3] = l


@nb.njit(cache=True)
def _full_mismatch(n, s2):
    """Count all S2 internal adjacency mismatches."""
    count = 0
    for i in range(n):
        for j in range(n):
            if j < n - 1:
                if s2[i, j, 1] + s2[i, j + 1, 3] != 0:
                    count += 1
            if i < n - 1:
                if s2[i, j, 2] + s2[i + 1, j, 0] != 0:
                    count += 1
    return count


@nb.njit(cache=True)
def _init_freq(h_type, v_type, type_freq):
    """Count frequency of each base type across all edges."""
    type_freq[:] = 0
    for i in range(h_type.shape[0]):
        for j in range(h_type.shape[1]):
            type_freq[h_type[i, j]] += 1
    for i in range(v_type.shape[0]):
        for j in range(v_type.shape[1]):
            type_freq[v_type[i, j]] += 1


# ---------------------------------------------------------------------------
# MCMCState class
# ---------------------------------------------------------------------------

class MCMCState:
    """Complete state for the MCMC edge-coloring search."""

    def __init__(self, n: int, K: int, map_fwd: np.ndarray, map_inv: np.ndarray,
                 *, w_mismatch: float = 10.0, w_diversity: float = 1.0,
                 w_balance: float = 0.5, w_identical: float = 0.0,
                 track_identical: bool = False):
        """
        Parameters
        ----------
        n : int
            Grid size (n × n puzzle).
        K : int
            Number of distinct base edge types (1..K).
        map_fwd : ndarray, shape (n, n, 3), int32
            Forward mapping: map_fwd[y, x] = [y2, x2, rotation].
        map_inv : ndarray, shape (n, n, 3), int32
            Inverse mapping: map_inv[y2, x2] = [y, x, rotation].
        w_mismatch : float
            Weight for S2 mismatch count in total energy (default 10.0).
        w_diversity : float
            Weight for diversity penalty (default 1.0).
        w_balance : float
            Weight for balance penalty (default 0.5).
        w_identical : float
            Weight for identical-pieces penalty (default 0.0 = off).
        track_identical : bool
            If True, compute identical-pieces count during progress
            logging.  Expensive O(n²) so off by default.
        """
        self.n = n
        self.K = K
        self.w_mismatch = w_mismatch
        self.w_diversity = w_diversity
        self.w_balance = w_balance
        self.w_identical = w_identical
        self.track_identical = track_identical

        # Mapping arrays (fixed during edge search)
        self.map_fwd = map_fwd.astype(np.int32)
        self.map_inv = map_inv.astype(np.int32)

        # Edge state — random initialisation
        self.h_type = np.random.randint(1, K + 1, size=(n, n - 1), dtype=np.int32)
        self.h_dir = np.random.randint(0, 2, size=(n, n - 1), dtype=np.int32)
        self.v_type = np.random.randint(1, K + 1, size=(n - 1, n), dtype=np.int32)
        self.v_dir = np.random.randint(0, 2, size=(n - 1, n), dtype=np.int32)

        # Type-frequency tracker
        self.type_freq = np.zeros(K + 1, dtype=np.int32)
        _init_freq(self.h_type, self.v_type, self.type_freq)

        # Cached piece arrays
        self.s1_pieces = np.zeros((n, n, 4), dtype=np.int32)
        self.s2_pieces = np.zeros((n, n, 4), dtype=np.int32)
        self.recompute_all_pieces()

        # Cached energy components
        self.mismatch_count = int(_full_mismatch(n, self.s2_pieces))
        self.diversity_pen = self.compute_diversity_penalty()
        self.balance_pen = self.compute_balance_penalty()
        self.identical_pieces = 0  # updated on demand

    # ------------------------------------------------------------------
    # Recomputation
    # ------------------------------------------------------------------

    def recompute_all_pieces(self):
        """Full O(n²) recomputation of S1 and S2 piece caches."""
        _recompute_all(
            self.n,
            self.h_type, self.h_dir,
            self.v_type, self.v_dir,
            self.map_inv,
            self.s1_pieces, self.s2_pieces,
        )

    def full_recompute_energy(self):
        """Recompute all energy components from scratch (for validation)."""
        _init_freq(self.h_type, self.v_type, self.type_freq)
        self.recompute_all_pieces()
        self.mismatch_count = int(_full_mismatch(self.n, self.s2_pieces))
        self.diversity_pen = self.compute_diversity_penalty()
        self.balance_pen = self.compute_balance_penalty()
        if self.track_identical or self.w_identical > 0:
            self.identical_pieces = self.count_identical_pieces()

    # ------------------------------------------------------------------
    # Energy helpers
    # ------------------------------------------------------------------

    def compute_diversity_penalty(self) -> float:
        """Penalty for using too few distinct edge types."""
        K_used = int(np.count_nonzero(self.type_freq[1:]))
        K_min = max(1, int(0.8 * self.K))
        return float(max(0, K_min - K_used) ** 2)

    def compute_balance_penalty(self) -> float:
        """Penalty for any single type dominating."""
        total_edges = 2 * self.n * (self.n - 1)
        f_max = int(np.ceil(1.5 * total_edges / self.K))
        excess = np.maximum(0, self.type_freq[1:] - f_max)
        return float(np.sum(excess))

    def count_identical_pieces(self) -> int:
        """Count the number of non-unique S1 pieces.

        Returns n² minus the number of distinct piece signatures.
        E.g. if all 400 pieces are unique → 0.  If 3 pieces share
        the same signature → contributes 2 to the count.
        """
        n = self.n
        seen = set()
        for i in range(n):
            for j in range(n):
                sig = (int(self.s1_pieces[i, j, 0]),
                       int(self.s1_pieces[i, j, 1]),
                       int(self.s1_pieces[i, j, 2]),
                       int(self.s1_pieces[i, j, 3]))
                seen.add(sig)
        return n * n - len(seen)

    @property
    def energy(self) -> float:
        return (self.w_mismatch * self.mismatch_count
                + self.w_diversity * self.diversity_pen
                + self.w_balance * self.balance_pen
                + self.w_identical * self.identical_pieces)
